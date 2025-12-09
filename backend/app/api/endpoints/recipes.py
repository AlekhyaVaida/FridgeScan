"""
Recipe API Endpoints
"""

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db import schemas
from app.db.mongo import get_database
from app.services.recipe_service import get_recipe_service, RecipeService

router = APIRouter()
DEFAULT_USER_ID = "default-user"


def _serialize_recipe(doc: dict) -> schemas.Recipe:
    return schemas.Recipe(
        id=str(doc["_id"]),
        external_id=doc.get("external_id"),
        title=doc.get("title", ""),
        description=doc.get("description"),
        image_url=doc.get("image_url"),
        cuisines=doc.get("cuisines"),
        meal_types=doc.get("meal_types"),
        cooking_time=doc.get("cooking_time"),
        servings=doc.get("servings"),
        ingredients=doc.get("ingredients", []),
        instructions=doc.get("instructions", []),
        nutrition=doc.get("nutrition"),
        created_at=doc.get("created_at", datetime.utcnow()),
        created_by=doc.get("created_by", "system"),
        is_favorite=doc.get("is_favorite", False),
    )


@router.get("/suggestions", response_model=List[dict])
async def get_recipe_suggestions(
    max_results: int = 10,
    db: AsyncIOMotorDatabase = Depends(get_database),
    recipe_service: RecipeService = Depends(get_recipe_service)
):
    """
    Get recipe suggestions based on available fridge and pantry items
    
    - Combines fridge + pantry ingredients
    - Queries Spoonacular API (or returns mock data)
    - Returns recipes ranked by ingredient match
    """
    user_id = DEFAULT_USER_ID

    fridge_cursor = db.fridge_items.find(
        {"user_id": user_id, "freshness_status": {"$ne": "spoiled"}}
    )
    pantry_cursor = db.pantry_items.find({"user_id": user_id})

    available_ingredients: List[str] = []
    async for item in fridge_cursor:
        name = item.get("name")
        if name:
            available_ingredients.append(name)

    async for item in pantry_cursor:
        name = item.get("name")
        if name:
            available_ingredients.append(name)

    # Remove duplicates while preserving order
    available_ingredients = list(dict.fromkeys(available_ingredients))

    if not available_ingredients:
        return []
    
    favorite_docs = await db.favorite_recipes.find({"user_id": DEFAULT_USER_ID}).to_list(length=None)
    favorite_ids = {doc.get("recipe_id") for doc in favorite_docs}
    
    recipes = await recipe_service.search_by_ingredients(
        ingredients=available_ingredients,
        number=max_results
    )
    
    results = []
    for recipe in recipes:
        # Get parsed meal data for servings and cooking_time
        parsed = recipe_service._parse_meal(recipe.get("meal", {})) if hasattr(recipe_service, '_parse_meal') else {}
        summary_doc = {
            "external_id": str(recipe.get("id")),
            "title": recipe.get("title"),
            "description": None,
            "image_url": recipe.get("image"),
            "cuisines": [recipe.get("area")] if recipe.get("area") else [],
            "meal_types": [recipe.get("category")] if recipe.get("category") else [],
            "cooking_time": recipe.get("cooking_time"),
            "servings": recipe.get("servings"),
            "ingredients": recipe.get("ingredients", []),
            "instructions": recipe.get("instructions", []),
            "nutrition": None,
            "created_by": "themealdb",
            "updated_at": datetime.utcnow(),
        }

        summary_doc["is_favorite"] = summary_doc["external_id"] in favorite_ids

        await db.recipes.update_one(
            {"external_id": summary_doc["external_id"]},
            {
                "$set": summary_doc,
                "$setOnInsert": {"created_at": datetime.utcnow()},
            },
            upsert=True,
        )

        results.append({
            "id": recipe.get("id"),
            "title": recipe.get("title"),
            "image": recipe.get("image"),
            "match_percentage": recipe.get("match_percentage", 0),
            "used_ingredients": recipe.get("used_ingredients", []),
            "missing_ingredients": recipe.get("missed_ingredients", []),
            "is_favorite": summary_doc["external_id"] in favorite_ids,
            "servings": recipe.get("servings"),
            "cooking_time": recipe.get("cooking_time"),
        })
    
    return results


@router.get("/{recipe_id}", response_model=schemas.Recipe)
async def get_recipe_details(
    recipe_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    recipe_service: RecipeService = Depends(get_recipe_service)
):
    """Get detailed information about a specific recipe"""
    # Look for cached recipe
    doc = await db.recipes.find_one({"external_id": str(recipe_id)})
    if doc:
        return _serialize_recipe(doc)

    recipe = await recipe_service.get_recipe_details(recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

        # Cache the recipe for future requests
        document = {
            "external_id": str(recipe_id),
            "title": recipe.get("title"),
            "description": None,
            "image_url": recipe.get("image"),
            "cuisines": recipe.get("cuisines"),
            "meal_types": recipe.get("meal_types"),
            "cooking_time": recipe.get("cooking_time"),
            "servings": recipe.get("servings"),
            "ingredients": recipe.get("extendedIngredients", []),
            "instructions": (recipe.get("instructions") or "").split("\n"),
            "nutrition": recipe.get("nutrition"),
            "created_at": datetime.utcnow(),
            "created_by": "themealdb",
        }
    result = await db.recipes.insert_one(document)
    document["_id"] = result.inserted_id
    return _serialize_recipe(document)


@router.post("/favorites", response_model=schemas.FavoriteRecipe)
async def add_favorite_recipe(
    favorite: schemas.FavoriteRecipeCreate,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Save a recipe as favorite"""
    existing = await db.favorite_recipes.find_one({
        "user_id": DEFAULT_USER_ID,
        "recipe_id": favorite.recipe_id
    })

    if existing:
        return schemas.FavoriteRecipe(
            id=str(existing["_id"]),
            user_id=existing["user_id"],
            recipe_id=existing["recipe_id"],
            created_at=existing.get("created_at", datetime.utcnow())
        )

    doc = {
        "user_id": DEFAULT_USER_ID,
        "recipe_id": favorite.recipe_id,
        "created_at": datetime.utcnow()
    }
    result = await db.favorite_recipes.insert_one(doc)
    doc["_id"] = result.inserted_id
    return schemas.FavoriteRecipe(
        id=str(doc["_id"]),
        user_id=doc["user_id"],
        recipe_id=doc["recipe_id"],
        created_at=doc["created_at"]
    )


@router.get("/favorites/list", response_model=List[schemas.FavoriteRecipe])
async def get_favorite_recipes(
    skip: int = 0,
    limit: int = 50,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get all favorite recipes for the current user"""
    cursor = db.favorite_recipes.find({"user_id": DEFAULT_USER_ID}).skip(skip).limit(limit)
    favorites: List[schemas.FavoriteRecipe] = []
    async for doc in cursor:
        favorites.append(
            schemas.FavoriteRecipe(
                id=str(doc["_id"]),
                user_id=doc["user_id"],
                recipe_id=doc["recipe_id"],
                created_at=doc.get("created_at", datetime.utcnow())
            )
        )
    return favorites


@router.delete("/favorites/{recipe_id}")
async def remove_favorite_recipe(
    recipe_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Remove a recipe from favorites"""
    result = await db.favorite_recipes.delete_one({
        "user_id": DEFAULT_USER_ID,
        "recipe_id": recipe_id
    })

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Favorite not found")
    return {"message": "Removed from favorites"}


@router.get("/search/by-name", response_model=List[schemas.Recipe])
async def search_recipes_by_name(
    query: str,
    number: int = 10,
    db: AsyncIOMotorDatabase = Depends(get_database),
    recipe_service: RecipeService = Depends(get_recipe_service),
):
    """Search recipes by name or keywords."""
    results = await recipe_service.search_by_name(query=query, number=number)
    serialized: List[schemas.Recipe] = []
    for recipe in results:
        summary_doc = {
            "external_id": str(recipe.get("id")),
            "title": recipe.get("title"),
            "description": None,
            "image_url": recipe.get("image"),
            "cuisines": recipe.get("cuisines"),
            "meal_types": recipe.get("meal_types"),
            "cooking_time": None,
            "servings": None,
            "ingredients": recipe.get("ingredients", []),
            "instructions": recipe.get("instructions", []),
            "nutrition": None,
            "created_by": "themealdb",
            "updated_at": datetime.utcnow(),
        }

        await db.recipes.update_one(
            {"external_id": summary_doc["external_id"]},
            {
                "$set": summary_doc,
                "$setOnInsert": {"created_at": datetime.utcnow()},
            },
            upsert=True,
        )

        doc = await db.recipes.find_one({"external_id": summary_doc["external_id"]})
        if doc:
            serialized.append(_serialize_recipe(doc))

    return serialized





