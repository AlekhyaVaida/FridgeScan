from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, JSON, Enum, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum
from app.db.database import Base


def generate_uuid():
    return str(uuid.uuid4())


class FreshnessStatus(str, enum.Enum):
    FRESH = "fresh"
    SPOILED = "spoiled"
    UNKNOWN = "unknown"


class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    fridge_items = relationship("FridgeItem", back_populates="user", cascade="all, delete-orphan")
    pantry_items = relationship("PantryItem", back_populates="user", cascade="all, delete-orphan")
    favorite_recipes = relationship("FavoriteRecipe", back_populates="user", cascade="all, delete-orphan")


class FridgeItem(Base):
    __tablename__ = "fridge_items"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    category = Column(String, default="uncategorized")
    quantity = Column(Float, default=1.0)
    unit = Column(String, default="item")
    freshness_status = Column(Enum(FreshnessStatus), default=FreshnessStatus.UNKNOWN)
    detected_date = Column(DateTime, default=datetime.utcnow)
    confidence_score = Column(Float, nullable=True)
    image_url = Column(String, nullable=True)
    
    # Relationship
    user = relationship("User", back_populates="fridge_items")


class PantryItem(Base):
    __tablename__ = "pantry_items"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    category = Column(String, default="uncategorized")
    quantity = Column(Float, default=1.0)
    unit = Column(String, default="item")
    expiry_date = Column(DateTime, nullable=True)
    added_date = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    user = relationship("User", back_populates="pantry_items")


class Recipe(Base):
    __tablename__ = "recipes"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    external_id = Column(String, nullable=True)  # ID from external API
    user_id = Column(String, ForeignKey("users.id"), nullable=True)  # For custom recipes
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    image_url = Column(String, nullable=True)
    cuisine_type = Column(String, nullable=True)
    meal_type = Column(String, nullable=True)
    cooking_time = Column(Integer, nullable=True)  # in minutes
    servings = Column(Integer, default=4)
    ingredients = Column(JSON, nullable=False)  # List of ingredients
    instructions = Column(JSON, nullable=False)  # Step-by-step instructions
    nutrition_data = Column(JSON, nullable=True)
    source = Column(String, default="custom")  # spoonacular, openai, custom
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    favorites = relationship("FavoriteRecipe", back_populates="recipe", cascade="all, delete-orphan")


class FavoriteRecipe(Base):
    __tablename__ = "favorite_recipes"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    recipe_id = Column(String, ForeignKey("recipes.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="favorite_recipes")
    recipe = relationship("Recipe", back_populates="favorites")





