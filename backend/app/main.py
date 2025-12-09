"""
Smart Fridge Recipe App - Main FastAPI Application
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.endpoints import fridge, pantry, recipes, nutrition, dashboard

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Smart Fridge Recipe App - AI-powered food management and recipe suggestions"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(fridge.router, prefix=f"{settings.API_V1_STR}/fridge", tags=["fridge"])
app.include_router(pantry.router, prefix=f"{settings.API_V1_STR}/pantry", tags=["pantry"])
app.include_router(recipes.router, prefix=f"{settings.API_V1_STR}/recipes", tags=["recipes"])
app.include_router(nutrition.router, prefix=f"{settings.API_V1_STR}/nutrition", tags=["nutrition"])
app.include_router(dashboard.router, prefix=f"{settings.API_V1_STR}/dashboard", tags=["dashboard"])


@app.on_event("startup")
def on_startup():
    """Initialize database on startup"""
    print("Starting Smart Fridge Recipe App...")
    print("API documentation: http://localhost:8000/docs")
    print("Backend running on: http://localhost:8000")


@app.get("/")
def root():
    """Root endpoint - API health check"""
    return {
        "message": "Smart Fridge Recipe App API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)





