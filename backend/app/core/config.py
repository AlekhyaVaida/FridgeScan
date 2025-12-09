from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Legacy SQL support (kept optional while migrating to MongoDB)
    DATABASE_URL: Optional[str] = None
    # MongoDB
    MONGODB_URI: str
    MONGODB_DB: str
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production-09876543210"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # External APIs
    SPOONACULAR_API_KEY: Optional[str] = None
    USDA_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    EDAMAM_APP_ID: Optional[str] = None
    EDAMAM_API_KEY: Optional[str] = None
    
    # External APIs - MealDB (no key required)
    THEMEALDB_BASE_URL: str = "https://www.themealdb.com/api/json/v1/1"
    
    # Computer Vision - Model Configuration
    CV_MODEL_PATH: str = "../computer_vision/models/yolov8n.pt"
    CV_CLASSIFIER_PATH: str = "../computer_vision/models/classifier_traced.pt"
    # Multi-model support
    CV_USE_ENSEMBLE: bool = False  # Set to True to use both primary and secondary models together
    CV_PRIMARY_MODEL: str = "best.pt"  # Primary model filename
    CV_SECONDARY_MODEL: Optional[str] = None  # Secondary model filename (auto-detected if None)
    
    # CORS
    FRONTEND_URL: str = "http://localhost:3000"
    
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Smart Fridge Recipe App"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()





