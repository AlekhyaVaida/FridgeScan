from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum


class FreshnessStatus(str, Enum):
    FRESH = "fresh"
    SPOILED = "spoiled"
    UNKNOWN = "unknown"


# User Schemas
class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# Fridge Item Schemas
class FridgeItemBase(BaseModel):
    name: str
    category: Optional[str] = "uncategorized"
    quantity: Optional[float] = 1.0
    unit: Optional[str] = "item"
    freshness_status: Optional[FreshnessStatus] = FreshnessStatus.UNKNOWN


class FridgeItemCreate(FridgeItemBase):
    pass


class FridgeItemUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    freshness_status: Optional[FreshnessStatus] = None


class FridgeItem(FridgeItemBase):
    id: str
    user_id: str
    detected_date: datetime
    confidence_score: Optional[float] = None
    image_url: Optional[str] = None
    
    class Config:
        from_attributes = True


# Pantry Item Schemas
class PantryItemBase(BaseModel):
    name: str
    category: Optional[str] = "uncategorized"
    quantity: Optional[float] = 1.0
    unit: Optional[str] = "item"
    expiry_date: Optional[datetime] = None


class PantryItemCreate(PantryItemBase):
    pass


class PantryItemUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    expiry_date: Optional[datetime] = None


class PantryItem(PantryItemBase):
    id: str
    user_id: str
    added_date: datetime
    
    class Config:
        from_attributes = True


# Recipe Schemas
class RecipeBase(BaseModel):
    title: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    cuisines: Optional[List[str]] = None
    meal_types: Optional[List[str]] = None
    cooking_time: Optional[int] = None
    servings: Optional[int] = 4
    ingredients: List[Dict[str, Any]]
    instructions: List[str]
    nutrition: Optional[Dict[str, Any]] = None
    is_favorite: Optional[bool] = False


class RecipeCreate(RecipeBase):
    pass


class Recipe(RecipeBase):
    id: str
    external_id: Optional[str] = None
    created_by: str = "system"
    created_at: datetime
    
    class Config:
        from_attributes = True


class RecipeMatch(BaseModel):
    """Recipe with match percentage based on available ingredients"""
    recipe: Recipe
    match_percentage: float
    available_ingredients: List[str]
    missing_ingredients: List[str]


# Favorite Recipe Schemas
class FavoriteRecipeCreate(BaseModel):
    recipe_id: str


class FavoriteRecipe(BaseModel):
    id: str
    user_id: str
    recipe_id: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# Image Upload Schema
class ImageUpload(BaseModel):
    image: str  # base64 encoded


# Detection Response
class DetectionResult(BaseModel):
    items: List[FridgeItem]
    total_detected: int
    message: str
    model1_results: Optional[List[FridgeItem]] = None
    model2_results: Optional[List[FridgeItem]] = None


# Nutrition Schemas
class NutritionInfo(BaseModel):
    calories: float
    protein: float
    carbs: float
    fats: float
    fiber: Optional[float] = None
    sugar: Optional[float] = None
    sodium: Optional[float] = None


class NutritionResponse(BaseModel):
    recipe_id: str
    servings: int
    per_serving: NutritionInfo
    total: NutritionInfo


class NutritionLogCreate(BaseModel):
    recipe_id: str
    servings: float = 1.0


class NutritionLog(BaseModel):
    id: str
    recipe_id: str
    recipe_name: str
    servings: float
    per_serving: NutritionInfo
    total: NutritionInfo
    logged_at: datetime


class NutritionHistory(BaseModel):
    logs: List[NutritionLog]


class CustomNutritionRequest(BaseModel):
    ingredients: List[str]
    servings: int = 1
    title: Optional[str] = None


class DailyNutritionSummary(BaseModel):
    date: date
    totals: NutritionInfo


# Dashboard Schema
class DashboardStats(BaseModel):
    total_fridge_items: int
    total_pantry_items: int
    fresh_items: int
    spoiled_items: int
    expiring_soon: int
    favorite_recipes_count: int


class ExpiringItem(BaseModel):
    id: str
    name: str
    type: str  # "fridge" or "pantry"
    expiry_date: Optional[datetime]
    days_until_expiry: int





