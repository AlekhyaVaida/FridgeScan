"""
Recipe Service - Integrates with TheMealDB API and provides recipe suggestions.
"""

import httpx
from typing import List, Dict, Any, Optional

from app.core.config import settings


class RecipeService:
    """Service for ingredient-based recipe search using TheMealDB."""

    def __init__(self):
        self.base_url = settings.THEMEALDB_BASE_URL.rstrip("/")

    async def search_by_ingredients(
        self,
        ingredients: List[str],
        number: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search recipes by available ingredients using TheMealDB.
        Returns a list of detailed recipe dicts with match metadata.
        """
        base_ingredients = [
            ing.strip().lower()
            for ing in dict.fromkeys(ingredients)
            if ing and ing.strip()
        ]

        if not base_ingredients:
            return self._fallback_recipes()

        def expand_terms(value: str) -> List[str]:
            terms = {value}
            manual_map = {
                "chicken breast": ["chicken"],
                "baby spinach": ["spinach"],
                "greek yogurt": ["yogurt"],
            }
            for key, extras in manual_map.items():
                if value.startswith(key):
                    terms.update(extras)
            words = [w for w in value.replace("-", " ").split(" ") if w]
            if words:
                terms.update(words)
            return list(dict.fromkeys(filter(None, terms)))

        expanded_ingredients = []
        for ingredient in base_ingredients:
            expanded_ingredients.extend(expand_terms(ingredient))

        unique_ingredients = list(dict.fromkeys(expanded_ingredients))

        meal_matches: Dict[str, Dict[str, Any]] = {}

        async with httpx.AsyncClient() as client:
            # Gather candidate meals for each ingredient
            for ingredient in unique_ingredients:
                try:
                    resp = await client.get(
                        f"{self.base_url}/filter.php",
                        params={"i": ingredient},
                        timeout=10.0,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                except Exception as exc:
                    print(f"TheMealDB filter error ({ingredient}): {exc}")
                    data = {}

                for meal in data.get("meals") or []:
                    meal_id = meal.get("idMeal")
                    if not meal_id:
                        continue
                    entry = meal_matches.setdefault(
                        meal_id,
                        {"count": 0, "meal": meal},
                    )
                    entry["count"] += 1

            if not meal_matches:
                return []

            # Pick top matches by overlap count
            sorted_candidates = sorted(
                meal_matches.items(),
                key=lambda item: item[1]["count"],
                reverse=True,
            )[: number * 2]  # fetch extra to account for missing details

            results: List[Dict[str, Any]] = []
            for meal_id, entry in sorted_candidates:
                detail = await self._get_meal_details(client, meal_id)
                if not detail:
                    continue

                parsed = self._parse_meal(detail)
                match_info = self._calculate_match(parsed["ingredient_names"], unique_ingredients)

                results.append(
                    {
                        "id": meal_id,
                        "title": parsed["title"],
                        "image": parsed["image"],
                        "category": parsed["category"],
                        "area": parsed["area"],
                        "ingredients": parsed["ingredients"],
                        "instructions": parsed["instructions"],
                        "used_ingredients": match_info["used"],
                        "missed_ingredients": match_info["missed"],
                        "match_percentage": match_info["match_percentage"],
                        "servings": parsed.get("servings"),
                        "cooking_time": parsed.get("cooking_time"),
                    }
                )

        if not results:
            return self._fallback_recipes()

        return sorted(results, key=lambda item: item.get("match_percentage", 0), reverse=True)[:number]

    async def get_recipe_details(self, recipe_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a full recipe record from TheMealDB."""
        try:
            async with httpx.AsyncClient() as client:
                detail = await self._get_meal_details(client, recipe_id)
        except Exception as exc:
            print(f"TheMealDB lookup error ({recipe_id}): {exc}")
            detail = None

        if not detail:
            return None

        parsed = self._parse_meal(detail)
        return {
            "id": recipe_id,
            "title": parsed["title"],
            "image": parsed["image"],
            "cuisines": [parsed["area"]] if parsed["area"] else [],
            "meal_types": [parsed["category"]] if parsed["category"] else [],
            "servings": parsed["servings"],
            "cooking_time": parsed.get("cooking_time"),
            "instructions": "\n".join(parsed["instructions"]),
            "extendedIngredients": [
                {"name": item["name"], "amount": item["measure"], "unit": ""}
                for item in parsed["ingredients"]
            ],
            "nutrition": None,
        }

    async def get_similar_recipes(self, recipe_id: str, number: int = 5) -> List[Dict[str, Any]]:
        """Simple similar recipe lookup based on category."""
        detail = await self.get_recipe_details(recipe_id)
        if not detail:
            return []

        category = detail.get("meal_types", [None])[0]
        if not category:
            return []

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.base_url}/filter.php",
                    params={"c": category},
                    timeout=10.0,
                )
                resp.raise_for_status()
                data = resp.json()
                return data.get("meals", [])[:number]
        except Exception as exc:
            print(f"TheMealDB similar error ({category}): {exc}")
            return []

    async def search_by_name(self, query: str, number: int = 10) -> List[Dict[str, Any]]:
        """Search recipes by name."""
        if not query:
            return []

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.base_url}/search.php",
                    params={"s": query},
                    timeout=10.0,
                )
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            print(f"TheMealDB search error ({query}): {exc}")
            data = {}

        meals = data.get("meals") or []
        results = []
        for meal in meals[:number]:
            parsed = self._parse_meal(meal)
            results.append(
                {
                    "id": meal.get("idMeal"),
                    "title": parsed["title"],
                    "image": parsed["image"],
                    "cuisines": [parsed["area"]] if parsed["area"] else [],
                    "meal_types": [parsed["category"]] if parsed["category"] else [],
                    "ingredients": parsed["ingredients"],
                    "instructions": parsed["instructions"],
                }
            )
        return results

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    async def _get_meal_details(self, client: httpx.AsyncClient, meal_id: str) -> Optional[Dict[str, Any]]:
        try:
            resp = await client.get(
                f"{self.base_url}/lookup.php",
                params={"i": meal_id},
                timeout=10.0,
            )
            resp.raise_for_status()
            data = resp.json()
            meals = data.get("meals")
            if isinstance(meals, list) and meals:
                return meals[0]
        except Exception as exc:
            print(f"TheMealDB lookup error ({meal_id}): {exc}")
        return None

    def _parse_meal(self, meal: Dict[str, Any]) -> Dict[str, Any]:
        ingredients = []
        ingredient_names = []
        for idx in range(1, 21):
            name = meal.get(f"strIngredient{idx}")
            measure = meal.get(f"strMeasure{idx}")
            if name and name.strip():
                display = f"{measure.strip()} {name.strip()}" if measure and measure.strip() else name.strip()
                ingredients.append(
                    {
                        "name": name.strip(),
                        "measure": measure.strip() if measure and measure.strip() else None,
                        "display": display.strip(),
                    }
                )
                ingredient_names.append(name.strip().lower())

        instructions_raw = meal.get("strInstructions") or ""
        instructions = [
            step.strip()
            for step in instructions_raw.split("\n")
            if step.strip()
        ]

        # Estimate servings based on number of ingredients (rough estimate)
        # Most recipes serve 4-6 people, but we'll estimate based on ingredient count
        estimated_servings = max(2, min(6, len(ingredients) // 2)) if ingredients else 4
        
        # Estimate cooking time based on instruction length and complexity
        # Rough estimate: ~5 minutes per instruction step, minimum 15 minutes
        estimated_time = max(15, len(instructions) * 5) if instructions else 30
        
        return {
            "title": meal.get("strMeal"),
            "image": meal.get("strMealThumb"),
            "category": meal.get("strCategory"),
            "area": meal.get("strArea"),
            "ingredients": ingredients,
            "ingredient_names": ingredient_names,
            "instructions": instructions,
            "servings": estimated_servings,
            "cooking_time": estimated_time,
        }

    def _calculate_match(
        self,
        recipe_ingredients: List[str],
        available_ingredients: List[str],
    ) -> Dict[str, Any]:
        available_set = {ing.lower() for ing in available_ingredients}
        used = []
        missed = []

        for ingredient in recipe_ingredients:
            if any(ingredient in avail or avail in ingredient for avail in available_set):
                used.append({"name": ingredient})
            else:
                missed.append({"name": ingredient})

        total = len(recipe_ingredients)
        match_percentage = (len(used) / total * 100) if total else 0

        return {
            "used": [item["name"] for item in used],
            "missed": [item["name"] for item in missed],
            "match_percentage": round(match_percentage, 1),
        }

    def _fallback_recipes(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "fallback-1",
                "title": "Simple Chicken & Spinach Skillet",
                "image": "https://images.unsplash.com/photo-1512058564366-18510be2db19?auto=format&fit=crop&w=800&q=60",
                "category": "Dinner",
                "area": "American",
                "servings": 2,
                "ready_in_minutes": 25,
                "ingredients": [
                    {"name": "Chicken Breast", "measure": "2 pieces", "display": "2 chicken breasts"},
                    {"name": "Spinach", "measure": "2 cups", "display": "2 cups fresh spinach"},
                    {"name": "Greek Yogurt", "measure": "1/2 cup", "display": "1/2 cup greek yogurt"},
                    {"name": "Garlic", "measure": "2 cloves", "display": "2 cloves garlic"},
                ],
                "instructions": [
                    "Season chicken with salt and pepper, then sear in a skillet until browned.",
                    "Add minced garlic and cook for 1 minute until fragrant.",
                    "Stir in spinach and cook until wilted.",
                    "Finish with greek yogurt and a splash of stock; simmer until creamy.",
                ],
                "used_ingredients": ["chicken breast", "spinach", "greek yogurt"],
                "missed_ingredients": ["garlic"],
                "match_percentage": 75.0,
            },
            {
                "id": "fallback-2",
                "title": "Mediterranean Yogurt Bowl",
                "image": "https://images.unsplash.com/photo-1506086679524-493c64fdfaa6?auto=format&fit=crop&w=800&q=60",
                "category": "Lunch",
                "area": "Mediterranean",
                "servings": 1,
                "ready_in_minutes": 15,
                "ingredients": [
                    {"name": "Greek Yogurt", "measure": "1 cup", "display": "1 cup greek yogurt"},
                    {"name": "Chicken Breast", "measure": "1 piece", "display": "1 grilled chicken breast"},
                    {"name": "Spinach", "measure": "1 cup", "display": "1 cup spinach"},
                    {"name": "Olive Oil", "measure": "1 tbsp", "display": "1 tbsp olive oil"},
                ],
                "instructions": [
                    "Slice grilled chicken breast into strips.",
                    "Toss spinach with olive oil, salt, and pepper.",
                    "Add yogurt to a bowl, top with chicken and spinach.",
                    "Finish with lemon juice or herbs if available.",
                ],
                "used_ingredients": ["greek yogurt", "chicken breast", "spinach"],
                "missed_ingredients": ["olive oil"],
                "match_percentage": 70.0,
            },
        ]


# Global instance
recipe_service = RecipeService()


# Helper function
def get_recipe_service() -> RecipeService:
    return recipe_service





