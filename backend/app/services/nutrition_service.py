"""
Nutrition Service - Wrapper around the Edamam Nutrition Analysis API.
"""

from typing import List, Dict, Any

import httpx

from app.core.config import settings


class NutritionCredentialsError(RuntimeError):
    """Raised when Edamam credentials are not configured."""


class NutritionService:
    """Service responsible for obtaining nutrition facts from Edamam."""

    def __init__(self) -> None:
        self.app_id = settings.EDAMAM_APP_ID
        self.app_key = settings.EDAMAM_API_KEY
        self.base_url = "https://api.edamam.com/api/nutrition-details"

    async def analyze_ingredients(
        self,
        title: str,
        ingredient_lines: List[str],
    ) -> Dict[str, Any]:
        """
        Request nutrition analysis for the provided ingredients.

        Args:
            title: Recipe title used for logging purposes.
            ingredient_lines: List of ingredient strings, e.g. ["2 cups rice"].

        Returns:
            Parsed JSON payload from Edamam.
        """
        if not ingredient_lines:
            raise ValueError("ingredient_lines must contain at least one entry.")

        if not self.app_id or not self.app_key:
            raise NutritionCredentialsError(
                "Edamam credentials are missing. "
                "Set EDAMAM_APP_ID and EDAMAM_API_KEY in the backend .env file."
            )

        params = {
            "app_id": self.app_id,
            "app_key": self.app_key,
        }
        payload = {
            "title": title or "FridgeScan Recipe",
            "ingr": ingredient_lines,
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(self.base_url, params=params, json=payload)
            response.raise_for_status()
            return response.json()


# Global instance
nutrition_service = NutritionService()


def get_nutrition_service() -> NutritionService:
    return nutrition_service

