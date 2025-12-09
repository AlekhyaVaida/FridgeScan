"""Utility script to seed MongoDB with starter data for local testing."""

import asyncio
from datetime import datetime, timedelta

from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings


USER_ID = "default-user"


async def seed_database() -> None:
    """Populate MongoDB collections with sample records."""

    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_DB]

    # Clear existing demo data for the default owner
    await asyncio.gather(
        db.fridge_items.delete_many({"user_id": USER_ID}),
        db.pantry_items.delete_many({"user_id": USER_ID}),
        db.recipes.delete_many({}),
        db.favorites.delete_many({"user_id": USER_ID}),
        db.nutrition_logs.delete_many({"user_id": USER_ID}),
    )

    now = datetime.utcnow()

    await db.pantry_items.insert_many(
        [
            {
                "user_id": USER_ID,
                "name": "Chicken Breast",
                "category": "protein",
                "quantity": 4,
                "unit": "pieces",
                "expiry_date": now + timedelta(days=3),
                "freshness_status": "fresh",
                "added_date": now,
                "notes": "Costco pack",
            },
            {
                "user_id": USER_ID,
                "name": "Baby Spinach",
                "category": "vegetable",
                "quantity": 1,
                "unit": "bag",
                "expiry_date": now + timedelta(days=5),
                "freshness_status": "fresh",
                "added_date": now,
            },
            {
                "user_id": USER_ID,
                "name": "Greek Yogurt",
                "category": "dairy",
                "quantity": 2,
                "unit": "tub",
                "expiry_date": now + timedelta(days=10),
                "freshness_status": "fresh",
                "added_date": now,
            },
        ]
    )

    await db.recipes.insert_many(
        [
            {
                "external_id": "spoonacular-715538",
                "title": "Chicken Stir Fry",
                "image_url": "https://images.unsplash.com/photo-1603133872878-684f208fb84b?w=400",
                "cuisine": "asian",
                "meal_type": "dinner",
                "ingredients": [
                    {"name": "chicken breast", "amount": 2, "unit": "pieces"},
                    {"name": "bell pepper", "amount": 1, "unit": "piece"},
                    {"name": "soy sauce", "amount": 2, "unit": "tbsp"},
                    {"name": "garlic", "amount": 2, "unit": "clove"},
                    {"name": "rice", "amount": 2, "unit": "cups"},
                ],
                "instructions": [
                    "Cut chicken into strips",
                    "Stir fry with vegetables",
                    "Add sauce and serve with rice",
                ],
                "nutrition": {
                    "servings": 4,
                    "per_serving": {
                        "calories": 320,
                        "protein": 28,
                        "carbs": 35,
                        "fat": 8,
                    },
                },
                "created_at": now,
                "created_by": "system",
            },
            {
                "external_id": "spoonacular-716268",
                "title": "Simple Scrambled Eggs",
                "image_url": "https://images.unsplash.com/photo-1525351484163-7529414344d8?w=400",
                "cuisine": "american",
                "meal_type": "breakfast",
                "ingredients": [
                    {"name": "eggs", "amount": 4, "unit": "piece"},
                    {"name": "butter", "amount": 1, "unit": "tbsp"},
                    {"name": "salt", "amount": 0.5, "unit": "tsp"},
                    {"name": "black pepper", "amount": 0.25, "unit": "tsp"},
                ],
                "instructions": [
                    "Crack eggs into a bowl",
                    "Whisk with salt and pepper",
                    "Cook in butter until softly set",
                ],
                "nutrition": {
                    "servings": 2,
                    "per_serving": {
                        "calories": 180,
                        "protein": 12,
                        "carbs": 2,
                        "fat": 14,
                    },
                },
                "created_at": now,
                "created_by": "system",
            },
        ]
    )

    await asyncio.gather(
        db.pantry_items.create_index([("user_id", 1), ("expiry_date", 1)]),
        db.fridge_items.create_index([("user_id", 1), ("detected_date", -1)]),
        db.recipes.create_index([("title", "text"), ("cuisine", 1)]),
        db.favorites.create_index([("user_id", 1), ("recipe_id", 1)], unique=True),
    )

    print("MongoDB seed complete.")


if __name__ == "__main__":
    asyncio.run(seed_database())

