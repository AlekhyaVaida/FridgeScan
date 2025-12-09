"""
Dashboard API Endpoints backed by MongoDB.
"""

from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db import schemas
from app.db.mongo import get_database
from app.api.endpoints.fridge import _serialize_fridge_item  # reuse serializer


router = APIRouter()
DEFAULT_USER_ID = "default-user"


def _serialize_fridge_item_dashboard(doc: dict) -> schemas.FridgeItem:
    return _serialize_fridge_item(doc)


def _serialize_expiring_item(doc: dict, days_until: int) -> schemas.ExpiringItem:
    return schemas.ExpiringItem(
        id=str(doc["_id"]),
        name=doc.get("name", ""),
        type="pantry",
        expiry_date=doc.get("expiry_date"),
        days_until_expiry=days_until,
    )


@router.get("/stats", response_model=schemas.DashboardStats)
async def get_dashboard_stats(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Return aggregated dashboard counters."""
    user_filter = {"user_id": DEFAULT_USER_ID}

    total_fridge = await db.fridge_items.count_documents(user_filter)
    fresh_items = await db.fridge_items.count_documents({**user_filter, "freshness_status": "fresh"})
    spoiled_items = await db.fridge_items.count_documents({**user_filter, "freshness_status": "spoiled"})

    total_pantry = await db.pantry_items.count_documents(user_filter)

    now = datetime.utcnow()
    deadline = now + timedelta(days=7)
    expiring_filter = {
        **user_filter,
        "expiry_date": {"$gte": now, "$lte": deadline},
    }
    expiring_soon = await db.pantry_items.count_documents(expiring_filter)

    favorites_count = await db.favorite_recipes.count_documents({"user_id": DEFAULT_USER_ID})

    return schemas.DashboardStats(
        total_fridge_items=total_fridge,
        total_pantry_items=total_pantry,
        fresh_items=fresh_items,
        spoiled_items=spoiled_items,
        expiring_soon=expiring_soon,
        favorite_recipes_count=favorites_count,
    )


@router.get("/expiring-items", response_model=List[schemas.ExpiringItem])
async def get_expiring_items(days: int = 7, db: AsyncIOMotorDatabase = Depends(get_database)):
    """Return pantry items expiring within the specified number of days."""
    now = datetime.utcnow()
    deadline = now + timedelta(days=days)

    cursor = db.pantry_items.find(
        {
            "user_id": DEFAULT_USER_ID,
            "expiry_date": {"$gte": now, "$lte": deadline},
        }
    )
    items: List[schemas.ExpiringItem] = []
    async for doc in cursor:
        expiry_date = doc.get("expiry_date")
        if not expiry_date:
            continue
        days_until = max(0, (expiry_date - now).days)
        items.append(_serialize_expiring_item(doc, days_until))

    items.sort(key=lambda x: x.days_until_expiry)
    return items


@router.get("/recent-scans", response_model=List[schemas.FridgeItem])
async def get_recent_scans(
    limit: int = 10,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Return the most recent fridge scans."""
    cursor = (
        db.fridge_items.find({"user_id": DEFAULT_USER_ID})
        .sort("detected_date", -1)
        .limit(limit)
    )
    items: List[schemas.FridgeItem] = []
    async for doc in cursor:
        items.append(_serialize_fridge_item_dashboard(doc))
    return items


@router.post("/shopping-list/generate", response_model=dict)
async def generate_shopping_list(recipe_ids: List[str]):
    """Placeholder for shopping list generation."""
    return {
        "items": [],
        "total_cost_estimate": 0,
        "message": "Shopping list generation coming soon!",
    }





