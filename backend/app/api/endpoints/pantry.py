"""Pantry Management API backed by MongoDB."""

from datetime import datetime
from typing import List, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db import schemas
from app.db.mongo import get_database


router = APIRouter()
DEFAULT_USER_ID = "default-user"


def _serialize_pantry_item(doc: dict) -> schemas.PantryItem:
    """Convert a MongoDB pantry document into a Pydantic schema."""

    if not doc:
        raise ValueError("Document cannot be None")

    return schemas.PantryItem(
        id=str(doc["_id"]),
        user_id=doc["user_id"],
        name=doc.get("name", ""),
        category=doc.get("category"),
        quantity=doc.get("quantity"),
        unit=doc.get("unit"),
        expiry_date=doc.get("expiry_date"),
        added_date=doc.get("added_date"),
    )


def _object_id(item_id: str) -> ObjectId:
    """Validate and convert a string ID into ObjectId."""

    if not ObjectId.is_valid(item_id):
        raise HTTPException(status_code=400, detail="Invalid item id")
    return ObjectId(item_id)


@router.post("/items", response_model=schemas.PantryItem)
async def create_pantry_item(
    item: schemas.PantryItemCreate,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Add a new item to the pantry."""

    document = item.dict(exclude_unset=True)
    document.update(
        {
            "user_id": DEFAULT_USER_ID,
            "added_date": datetime.utcnow(),
        }
    )

    result = await db.pantry_items.insert_one(document)
    document["_id"] = result.inserted_id
    return _serialize_pantry_item(document)


@router.get("/items", response_model=List[schemas.PantryItem])
async def get_pantry_items(
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Return paginated pantry items for the default user."""

    query: dict = {"user_id": DEFAULT_USER_ID}
    if category:
        query["category"] = category

    cursor = db.pantry_items.find(query).skip(skip).limit(limit)

    items: List[schemas.PantryItem] = []
    async for doc in cursor:
        items.append(_serialize_pantry_item(doc))

    return items


@router.get("/items/{item_id}", response_model=schemas.PantryItem)
async def get_pantry_item(
    item_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Fetch a single pantry item by its id."""

    obj_id = _object_id(item_id)
    doc = await db.pantry_items.find_one({"_id": obj_id, "user_id": DEFAULT_USER_ID})
    if not doc:
        raise HTTPException(status_code=404, detail="Item not found")
    return _serialize_pantry_item(doc)


@router.put("/items/{item_id}", response_model=schemas.PantryItem)
async def update_pantry_item(
    item_id: str,
    item_update: schemas.PantryItemUpdate,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Update an existing pantry item."""

    update_data = item_update.dict(exclude_unset=True)
    if not update_data:
        return await get_pantry_item(item_id, db)

    obj_id = _object_id(item_id)
    result = await db.pantry_items.update_one(
        {"_id": obj_id, "user_id": DEFAULT_USER_ID},
        {"$set": update_data},
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")

    doc = await db.pantry_items.find_one({"_id": obj_id, "user_id": DEFAULT_USER_ID})
    if not doc:
        raise HTTPException(status_code=404, detail="Item not found")

    return _serialize_pantry_item(doc)


@router.delete("/items/{item_id}")
async def delete_pantry_item(
    item_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Delete a pantry item."""

    obj_id = _object_id(item_id)
    result = await db.pantry_items.delete_one({"_id": obj_id, "user_id": DEFAULT_USER_ID})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")

    return {"message": "Item deleted successfully"}


@router.get("/categories", response_model=List[str])
async def get_pantry_categories(
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Return distinct pantry categories for the default user."""

    categories = await db.pantry_items.distinct(
        "category", {"user_id": DEFAULT_USER_ID}
    )
    return [cat for cat in categories if cat]

