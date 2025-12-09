"""MongoDB client helpers using Motor.

This module centralizes creation of the AsyncIOMotorClient instance so that the
FastAPI dependency system can reuse the same client across requests.
"""

from functools import lru_cache
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings


@lru_cache
def _get_client() -> AsyncIOMotorClient:
    """Return a cached Motor client built from settings."""

    return AsyncIOMotorClient(settings.MONGODB_URI)


def get_database():
    """Return the default application database."""

    client = _get_client()
    return client[settings.MONGODB_DB]


def get_collection(name: str):
    """Convenience helper to grab a named collection from the default DB."""

    db = get_database()
    return db[name]



