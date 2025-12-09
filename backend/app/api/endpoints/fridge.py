"""Fridge Scanner API Endpoints backed by MongoDB."""

from datetime import datetime
import logging
from typing import List, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db import schemas
from app.db.mongo import get_database
from app.services.detection_service import (
    DetectionModelNotReady,
    DetectionService,
    get_detection_service,
)

LOGGER = logging.getLogger(__name__)

router = APIRouter()
DEFAULT_USER_ID = "default-user"


def _object_id(item_id: str) -> ObjectId:
    if not ObjectId.is_valid(item_id):
        raise HTTPException(status_code=400, detail="Invalid item id")
    return ObjectId(item_id)


def _serialize_fridge_item(doc: dict) -> schemas.FridgeItem:
    if not doc:
        raise ValueError("Document cannot be None")

    freshness_value = doc.get("freshness_status", schemas.FreshnessStatus.UNKNOWN.value)
    try:
        freshness_status = schemas.FreshnessStatus(freshness_value)
    except ValueError:
        freshness_status = schemas.FreshnessStatus.UNKNOWN

    return schemas.FridgeItem(
        id=str(doc["_id"]),
        user_id=doc["user_id"],
        name=doc.get("name", ""),
        category=doc.get("category"),
        quantity=doc.get("quantity"),
        unit=doc.get("unit"),
        freshness_status=freshness_status,
        detected_date=doc.get("detected_date"),
        confidence_score=doc.get("confidence_score"),
        image_url=doc.get("image_url"),
    )


@router.post("/scan", response_model=schemas.DetectionResult)
async def scan_fridge(
    file: UploadFile = File(...),
    db: AsyncIOMotorDatabase = Depends(get_database),
    detection_service: DetectionService = Depends(get_detection_service),
):
    """
    Scan a fridge image, detect ingredients, store results, and return them.
    """
    image_bytes = await file.read()
    
    # Get results from both models separately
    try:
        both_models_result = detection_service.detect_ingredients_both_models(image_bytes)
        model1_items = both_models_result.get("model1", [])
        model2_items = both_models_result.get("model2", [])
        
        # Use model1 results for database storage (or merge if preferred)
        detected_items = model1_items if model1_items else model2_items
    except DetectionModelNotReady as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - unexpected errors
        LOGGER.exception("Unexpected error during detection: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to process image.") from exc

    now = datetime.utcnow()
    documents = []
    serialized_items: List[schemas.FridgeItem] = []
    model1_serialized: List[schemas.FridgeItem] = []
    model2_serialized: List[schemas.FridgeItem] = []

    # Process model1 results
    for idx, item_data in enumerate(model1_items):
        try:
            freshness, _ = detection_service.check_freshness_mock(
                image_bytes, item_data["name"]
            )
        except Exception:
            freshness = schemas.FreshnessStatus.UNKNOWN.value

        document = {
            "user_id": DEFAULT_USER_ID,
            "name": item_data["name"],
            "category": item_data.get("category", "uncategorized"),
            "quantity": item_data.get("quantity", 1),
            "unit": item_data.get("unit", "item"),
            "freshness_status": freshness,
            "detected_date": now,
            "confidence_score": float(item_data.get("confidence", 0.0)),
            "image_url": None,
        }
        documents.append(document)
        model1_serialized.append(
            schemas.FridgeItem(
                id=f"temp-model1-{idx}",
                user_id=DEFAULT_USER_ID,
                name=item_data["name"],
                category=item_data.get("category", "uncategorized"),
                quantity=item_data.get("quantity", 1),
                unit=item_data.get("unit", "item"),
                freshness_status=schemas.FreshnessStatus(freshness),
                detected_date=now,
                confidence_score=float(item_data.get("confidence", 0.0)),
            )
        )

    # Process model2 results (for display only, not stored in DB)
    for idx, item_data in enumerate(model2_items):
        try:
            freshness, _ = detection_service.check_freshness_mock(
                image_bytes, item_data["name"]
            )
        except Exception:
            freshness = schemas.FreshnessStatus.UNKNOWN.value

        model2_serialized.append(
            schemas.FridgeItem(
                id=f"temp-model2-{idx}",
                user_id=DEFAULT_USER_ID,
                name=item_data["name"],
                category=item_data.get("category", "uncategorized"),
                quantity=item_data.get("quantity", 1),
                unit=item_data.get("unit", "item"),
                freshness_status=schemas.FreshnessStatus(freshness),
                detected_date=now,
                confidence_score=float(item_data.get("confidence", 0.0)),
            )
        )

    # Store model1 results in database (or merge logic here)
    if documents:
        result = await db.fridge_items.insert_many(documents)
        inserted_docs = await db.fridge_items.find(
            {"_id": {"$in": result.inserted_ids}}
        ).to_list(length=len(result.inserted_ids))

        for doc in inserted_docs:
            serialized_items.append(_serialize_fridge_item(doc))

    return schemas.DetectionResult(
        items=serialized_items,
        total_detected=len(serialized_items),
        message=(
            f"Successfully detected {len(serialized_items)} items"
            if serialized_items
            else "No items detected"
        ),
        model1_results=model1_serialized if model1_serialized else None,
        model2_results=model2_serialized if model2_serialized else None,
    )


@router.get("/items", response_model=List[schemas.FridgeItem])
async def get_fridge_items(
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Return paginated fridge items for the default user."""
    query: dict = {"user_id": DEFAULT_USER_ID}
    if category:
        query["category"] = category

    cursor = (
        db.fridge_items.find(query)
        .sort("detected_date", -1)
        .skip(skip)
        .limit(limit)
    )

    items: List[schemas.FridgeItem] = []
    async for doc in cursor:
        items.append(_serialize_fridge_item(doc))
    return items


@router.get("/items/{item_id}", response_model=schemas.FridgeItem)
async def get_fridge_item(
    item_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Return a single fridge item."""
    doc = await db.fridge_items.find_one(
        {"_id": _object_id(item_id), "user_id": DEFAULT_USER_ID}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Item not found")
    return _serialize_fridge_item(doc)


@router.put("/items/{item_id}", response_model=schemas.FridgeItem)
async def update_fridge_item(
    item_id: str,
    item_update: schemas.FridgeItemUpdate,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Update fields on a fridge item."""
    update_data = item_update.dict(exclude_unset=True)
    if not update_data:
        return await get_fridge_item(item_id, db)

    result = await db.fridge_items.update_one(
        {"_id": _object_id(item_id), "user_id": DEFAULT_USER_ID},
        {"$set": update_data},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")

    doc = await db.fridge_items.find_one(
        {"_id": _object_id(item_id), "user_id": DEFAULT_USER_ID}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Item not found")
    return _serialize_fridge_item(doc)


@router.delete("/items/{item_id}")
async def delete_fridge_item(
    item_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Delete a single fridge item."""
    result = await db.fridge_items.delete_one(
        {"_id": _object_id(item_id), "user_id": DEFAULT_USER_ID}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"message": "Item deleted successfully"}


@router.delete("/items")
async def clear_all_fridge_items(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Delete every fridge item for the default user."""
    result = await db.fridge_items.delete_many({"user_id": DEFAULT_USER_ID})
    return {"message": f"Cleared {result.deleted_count} items from fridge"}


@router.get("/model-status")
async def get_model_status(
    detection_service: DetectionService = Depends(get_detection_service),
):
    """Get the status of detection models (primary and secondary)."""
    return {
        "model_ready": detection_service.model_ready,
        "primary_model_ready": detection_service.primary_model_ready,
        "secondary_model_ready": detection_service.secondary_model_ready,
        "primary_model_error": getattr(detection_service, "_primary_model_error", None),
        "secondary_model_error": getattr(detection_service, "_secondary_model_error", None),
        "ensemble_mode": detection_service.ensemble_mode,
    }