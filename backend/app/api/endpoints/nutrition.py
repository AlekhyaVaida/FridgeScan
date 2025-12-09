"""
Nutrition API Endpoints powered by Edamam Nutrition Analysis.
"""

from datetime import datetime, timedelta
from typing import List

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db import schemas
from app.db.mongo import get_database
from app.services.recipe_service import get_recipe_service, RecipeService
from app.services.nutrition_service import (
    get_nutrition_service,
    NutritionService,
    NutritionCredentialsError,
)


router = APIRouter()
DEFAULT_USER_ID = "default-user"


def _build_ingredient_lines(recipe: dict) -> List[str]:
    """Convert recipe ingredient objects into strings for Edamam."""
    ingredients = recipe.get("ingredients") or []
    lines: List[str] = []
    for item in ingredients:
        if isinstance(item, dict):
            if item.get("display"):
                lines.append(item["display"])
            else:
                measure = item.get("measure") or item.get("amount") or ""
                name = item.get("name") or ""
                line = f"{measure} {name}".strip()
                if line:
                    lines.append(line)
        elif isinstance(item, str):
            value = item.strip()
            if value:
                lines.append(value)
    return [line for line in lines if line]


def _parse_nutrition_response(data: dict, servings: float) -> schemas.NutritionResponse:
    base_servings = data.get("yield") or 1
    total_nutrients = data.get("totalNutrients") or {}

    def nutrient_amount(tag: str) -> float:
        return float(total_nutrients.get(tag, {}).get("quantity", 0.0))

    total_calories = float(data.get("calories", 0.0))
    per_serving_factor = 1 / base_servings if base_servings else 1

    per_serving = schemas.NutritionInfo(
        calories=round(total_calories * per_serving_factor, 2),
        protein=round(nutrient_amount("PROCNT") * per_serving_factor, 2),
        carbs=round(nutrient_amount("CHOCDF") * per_serving_factor, 2),
        fats=round(nutrient_amount("FAT") * per_serving_factor, 2),
        fiber=round(nutrient_amount("FIBTG") * per_serving_factor, 2),
        sugar=round(nutrient_amount("SUGAR") * per_serving_factor, 2),
        sodium=round(nutrient_amount("NA") * per_serving_factor, 2),
    )

    total_multiplier = servings
    total = schemas.NutritionInfo(
        calories=round(per_serving.calories * total_multiplier, 2),
        protein=round(per_serving.protein * total_multiplier, 2),
        carbs=round(per_serving.carbs * total_multiplier, 2),
        fats=round(per_serving.fats * total_multiplier, 2),
        fiber=round((per_serving.fiber or 0) * total_multiplier, 2) if per_serving.fiber is not None else None,
        sugar=round((per_serving.sugar or 0) * total_multiplier, 2) if per_serving.sugar is not None else None,
        sodium=round((per_serving.sodium or 0) * total_multiplier, 2) if per_serving.sodium is not None else None,
    )

    return schemas.NutritionResponse(
        recipe_id="",
        servings=int(servings),
        per_serving=per_serving,
        total=total,
    )


@router.get("/{recipe_id}", response_model=schemas.NutritionResponse)
async def get_recipe_nutrition(
    recipe_id: str,
    servings: float = 1,
    db: AsyncIOMotorDatabase = Depends(get_database),
    recipe_service: RecipeService = Depends(get_recipe_service),
    nutrition_service: NutritionService = Depends(get_nutrition_service),
):
    """Return nutrition analysis for a saved recipe."""
    recipe_doc = await db.recipes.find_one({"external_id": str(recipe_id)})
    if not recipe_doc:
        recipe = await recipe_service.get_recipe_details(recipe_id)
        if not recipe:
            raise HTTPException(status_code=404, detail="Recipe not found")
        recipe_doc = {
            "external_id": recipe_id,
            "title": recipe.get("title", f"Recipe {recipe_id}"),
            "ingredients": recipe.get("extendedIngredients", []),
        }

    ingredient_lines = _build_ingredient_lines(recipe_doc)
    if not ingredient_lines:
        raise HTTPException(status_code=400, detail="Recipe does not contain ingredient details.")

    try:
        data = await nutrition_service.analyze_ingredients(
            recipe_doc.get("title") or "FridgeScan Recipe",
            ingredient_lines,
        )
    except NutritionCredentialsError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=f"Nutrition provider error: {exc.response.text}",
        ) from exc
    except Exception as exc:  # pragma: no cover - unexpected
        raise HTTPException(status_code=500, detail=f"Nutrition analysis failed: {exc}") from exc

    response = _parse_nutrition_response(data, servings)
    response.recipe_id = str(recipe_id)
    return response


@router.post("/calculate", response_model=schemas.NutritionResponse)
async def calculate_custom_nutrition(
    payload: schemas.CustomNutritionRequest,
    nutrition_service: NutritionService = Depends(get_nutrition_service),
):
    """Calculate nutrition for a custom list of ingredient strings."""
    ingredient_lines = [line.strip() for line in payload.ingredients if line.strip()]
    if not ingredient_lines:
        raise HTTPException(status_code=400, detail="Provide at least one ingredient string.")

    try:
        data = await nutrition_service.analyze_ingredients(
            payload.title or "Custom Meal",
            ingredient_lines,
        )
    except NutritionCredentialsError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=f"Nutrition provider error: {exc.response.text}",
        ) from exc

    response = _parse_nutrition_response(data, payload.servings)
    response.recipe_id = "custom"
    return response


@router.post("/logs", response_model=schemas.NutritionLog)
async def log_recipe_nutrition(
    payload: schemas.NutritionLogCreate,
    db: AsyncIOMotorDatabase = Depends(get_database),
    recipe_service: RecipeService = Depends(get_recipe_service),
    nutrition_service: NutritionService = Depends(get_nutrition_service),
):
    """Analyze nutrition for a recipe and store the result as a log entry."""
    nutrition = await get_recipe_nutrition(
        recipe_id=payload.recipe_id,
        servings=payload.servings,
        db=db,
        recipe_service=recipe_service,
        nutrition_service=nutrition_service,
    )

    recipe_doc = await db.recipes.find_one({"external_id": str(payload.recipe_id)})
    recipe_name = recipe_doc.get("title") if recipe_doc else f"Recipe {payload.recipe_id}"

    doc = {
        "user_id": DEFAULT_USER_ID,
        "recipe_id": str(payload.recipe_id),
        "recipe_name": recipe_name,
        "servings": payload.servings,
        "per_serving": nutrition.per_serving.dict(),
        "total": nutrition.total.dict(),
        "logged_at": datetime.utcnow(),
    }
    result = await db.nutrition_logs.insert_one(doc)
    doc["_id"] = result.inserted_id

    return schemas.NutritionLog(
        id=str(doc["_id"]),
        recipe_id=doc["recipe_id"],
        recipe_name=doc["recipe_name"],
        servings=doc["servings"],
        per_serving=schemas.NutritionInfo(**doc["per_serving"]),
        total=schemas.NutritionInfo(**doc["total"]),
        logged_at=doc["logged_at"],
    )


@router.get("/logs", response_model=schemas.NutritionHistory)
async def list_nutrition_logs(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Return recent nutrition log entries."""
    cursor = (
        db.nutrition_logs.find({"user_id": DEFAULT_USER_ID})
        .sort("logged_at", -1)
        .limit(limit)
    )
    logs: List[schemas.NutritionLog] = []
    async for doc in cursor:
        logs.append(
            schemas.NutritionLog(
                id=str(doc["_id"]),
                recipe_id=doc["recipe_id"],
                recipe_name=doc["recipe_name"],
                servings=doc["servings"],
                per_serving=schemas.NutritionInfo(**doc["per_serving"]),
                total=schemas.NutritionInfo(**doc["total"]),
                logged_at=doc["logged_at"],
            )
        )
    return schemas.NutritionHistory(logs=logs)


@router.get("/daily-summary", response_model=schemas.DailyNutritionSummary)
async def daily_nutrition_summary(
    date: str = Query(default=None, description="ISO date (YYYY-MM-DD), defaults to today"),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Aggregate nutrition totals for a specific day."""
    if date:
        try:
            target_date = datetime.fromisoformat(date).date()
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid date format; use YYYY-MM-DD") from exc
    else:
        target_date = datetime.utcnow().date()

    start_dt = datetime.combine(target_date, datetime.min.time())
    end_dt = start_dt + timedelta(days=1)

    cursor = db.nutrition_logs.find(
        {
            "user_id": DEFAULT_USER_ID,
            "logged_at": {"$gte": start_dt, "$lt": end_dt},
        }
    )

    totals = {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fats": 0.0, "fiber": 0.0, "sugar": 0.0, "sodium": 0.0}
    async for doc in cursor:
        total = doc.get("total", {})
        totals["calories"] += float(total.get("calories", 0.0))
        totals["protein"] += float(total.get("protein", 0.0))
        totals["carbs"] += float(total.get("carbs", 0.0))
        totals["fats"] += float(total.get("fats", 0.0))
        totals["fiber"] += float(total.get("fiber") or 0.0)
        totals["sugar"] += float(total.get("sugar") or 0.0)
        totals["sodium"] += float(total.get("sodium") or 0.0)

    totals_info = schemas.NutritionInfo(
        calories=round(totals["calories"], 2),
        protein=round(totals["protein"], 2),
        carbs=round(totals["carbs"], 2),
        fats=round(totals["fats"], 2),
        fiber=round(totals["fiber"], 2),
        sugar=round(totals["sugar"], 2),
        sodium=round(totals["sodium"], 2),
    )
    return schemas.DailyNutritionSummary(date=target_date, totals=totals_info)

