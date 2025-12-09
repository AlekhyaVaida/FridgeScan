"""
Computer Vision Detection Service.

This implementation attempts to load a YOLO model (Ultralytics) from
`computer_vision/models/best.pt`. If the model or its metadata is not
available, the service raises a `DetectionModelNotReady` error so the
API layer can respond gracefully instead of crashing. Mock helpers are
retained for local development.
"""

from __future__ import annotations

import io
import logging
import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
from PIL import Image

from app.core.config import settings

try:  # Optional dependency for the real detector
    from ultralytics import YOLO  # type: ignore
except Exception:  # pragma: no cover - package not installed
    YOLO = None  # type: ignore

LOGGER = logging.getLogger(__name__)


class DetectionModelNotReady(RuntimeError):
    """Raised when the detection model cannot be loaded or used."""


class DetectionService:
    """Service responsible for food detection and freshness checks.
    
    Supports multiple models with automatic fallback:
    - Primary model: best.pt (or configured primary)
    - Secondary model: best2.pt (or configured secondary) - used as fallback
    - Can use both models in ensemble mode for better accuracy
    """

    def __init__(self) -> None:
        self._primary_model: Optional[YOLO] = None
        self._secondary_model: Optional[YOLO] = None
        self._primary_class_names: Dict[int, str] = {}
        self._secondary_class_names: Dict[int, str] = {}
        self._primary_model_error: Optional[str] = None
        self._secondary_model_error: Optional[str] = None
        self._use_ensemble: bool = getattr(settings, "CV_USE_ENSEMBLE", False)
        self._load_models()
        # Apply ensemble setting from config after models are loaded
        if self._use_ensemble:
            self.set_ensemble_mode(True)

    # ------------------------------------------------------------------
    # Model loading helpers
    # ------------------------------------------------------------------
    def _models_dir(self) -> Path:
        root_dir = Path(__file__).resolve().parents[3]
        return root_dir / "computer_vision" / "models"

    def _load_models(self) -> None:
        """Attempt to load primary and secondary YOLO models with class metadata."""

        if YOLO is None:
            error_msg = "Ultralytics package not installed. Run `pip install ultralytics`."
            self._primary_model_error = error_msg
            self._secondary_model_error = error_msg
            LOGGER.warning(error_msg)
            return

        models_dir = self._models_dir()
        
        # Load primary model (from config or default: best.pt)
        primary_model_name = getattr(settings, "CV_PRIMARY_MODEL", "best.pt")
        self._load_single_model(
            model_path=models_dir / primary_model_name,
            yaml_path=models_dir / "data.yaml",
            is_primary=True
        )
        
        # Load secondary model (from config or auto-detect)
        secondary_model_name = getattr(settings, "CV_SECONDARY_MODEL", None)
        if secondary_model_name:
            # Use configured secondary model
            yaml_path = models_dir / "data2.yaml"  # Try data2.yaml first for secondary
            if not yaml_path.exists():
                yaml_path = models_dir / "data.yaml"  # Fallback to data.yaml
            self._load_single_model(
                model_path=models_dir / secondary_model_name,
                yaml_path=yaml_path,
                is_primary=False
            )
        else:
            # Auto-detect secondary model (try common names)
            secondary_paths = [
                models_dir / "best2.pt",
                models_dir / "alternative.pt",
                models_dir / "backup.pt",
                models_dir / "model2.pt",
            ]
            
            secondary_loaded = False
            for sec_path in secondary_paths:
                if sec_path.exists():
                    yaml_path = models_dir / "data2.yaml"  # Try data2.yaml first
                    if not yaml_path.exists():
                        yaml_path = models_dir / "data.yaml"  # Fallback to data.yaml
                    self._load_single_model(
                        model_path=sec_path,
                        yaml_path=yaml_path,
                        is_primary=False
                    )
                    secondary_loaded = True
                    LOGGER.info("Auto-detected secondary model: %s", sec_path.name)
                    break
            
            if not secondary_loaded:
                LOGGER.info("No secondary model found. Only primary model will be used.")

    def _load_single_model(
        self, model_path: Path, yaml_path: Path, is_primary: bool
    ) -> None:
        """Load a single YOLO model and its class names."""
        
        if not model_path.exists():
            error_msg = f"Model weights not found at {model_path}"
            if is_primary:
                self._primary_model_error = error_msg
            else:
                self._secondary_model_error = error_msg
            LOGGER.warning(error_msg)
            return

        # Load class names from YAML
        class_names = {}
        if yaml_path.exists():
            try:
                yaml_data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
                names = yaml_data.get("names", {})
                if isinstance(names, dict):
                    class_names = {int(k): str(v) for k, v in names.items()}
                elif isinstance(names, list):
                    class_names = {idx: str(name) for idx, name in enumerate(names)}
            except Exception as exc:
                LOGGER.warning("Failed to read %s: %s", yaml_path, exc)

        try:
            model = YOLO(str(model_path))
            if is_primary:
                self._primary_model = model
                self._primary_class_names = class_names
                LOGGER.info("Loaded PRIMARY detection model from %s", model_path)
            else:
                self._secondary_model = model
                self._secondary_class_names = class_names
                LOGGER.info("Loaded SECONDARY detection model from %s", model_path)
        except Exception as exc:
            error_msg = f"Failed to load detection model from {model_path}: {exc}"
            if is_primary:
                self._primary_model_error = error_msg
                self._primary_model = None
            else:
                self._secondary_model_error = error_msg
                self._secondary_model = None
            LOGGER.exception(error_msg)

    @property
    def model_ready(self) -> bool:
        """Check if at least one model is ready."""
        return self._primary_model is not None or self._secondary_model is not None

    @property
    def primary_model_ready(self) -> bool:
        """Check if primary model is ready."""
        return self._primary_model is not None

    @property
    def secondary_model_ready(self) -> bool:
        """Check if secondary model is ready."""
        return self._secondary_model is not None

    def set_ensemble_mode(self, enabled: bool) -> None:
        """Enable/disable ensemble mode (use both models together)."""
        self._use_ensemble = enabled and self.primary_model_ready and self.secondary_model_ready
        if enabled and not self._use_ensemble:
            LOGGER.warning("Ensemble mode requested but both models not available.")
    
    @property
    def ensemble_mode(self) -> bool:
        """Get ensemble mode status."""
        return self._use_ensemble

    # ------------------------------------------------------------------
    # Real detection
    # ------------------------------------------------------------------
    def detect_ingredients(self, image_bytes: bytes) -> List[Dict[str, Any]]:
        """
        Detect ingredients using available models.
        
        Strategy:
        1. If ensemble mode: use both models and merge results
        2. If primary available: use primary
        3. If only secondary available: use secondary as fallback
        4. Otherwise: raise error
        """
        if not image_bytes:
            raise DetectionModelNotReady("Image payload was empty.")

        if not self.model_ready:
            message = (
                self._primary_model_error or self._secondary_model_error
                or "No detection models are available."
            )
            raise DetectionModelNotReady(message)

        try:
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        except Exception as exc:
            raise DetectionModelNotReady(f"Failed to decode image: {exc}") from exc

        # Ensemble mode: use both models and merge results
        if self._use_ensemble and self.primary_model_ready and self.secondary_model_ready:
            return self._detect_with_ensemble(image)

        # Try primary model first
        if self._primary_model is not None:
            try:
                return self._detect_with_model(
                    self._primary_model, self._primary_class_names, image
                )
            except Exception as exc:
                LOGGER.warning("Primary model failed, trying secondary: %s", exc)
                # Fall through to secondary if primary fails

        # Fallback to secondary model
        if self._secondary_model is not None:
            try:
                return self._detect_with_model(
                    self._secondary_model, self._secondary_class_names, image
                )
            except Exception as exc:
                raise DetectionModelNotReady(
                    f"Both primary and secondary models failed. Last error: {exc}"
                ) from exc

        # No models available
        message = (
            self._primary_model_error or self._secondary_model_error
            or "Detection models are not available."
        )
        raise DetectionModelNotReady(message)

    def _detect_with_model(
        self, model: YOLO, class_names: Dict[int, str], image: Image.Image
    ) -> List[Dict[str, Any]]:
        """Run detection with a single model."""
        results = model(image, verbose=False)
        detections: List[Dict[str, Any]] = []
        
        for result in results:
            boxes = getattr(result, "boxes", None)
            if not boxes:
                continue

            cls_list = boxes.cls.tolist() if getattr(boxes, "cls", None) is not None else []
            conf_list = boxes.conf.tolist() if getattr(boxes, "conf", None) is not None else []
            xyxy_list = boxes.xyxy.tolist() if getattr(boxes, "xyxy", None) is not None else []

            for cls_idx, confidence, bbox in zip(cls_list, conf_list, xyxy_list):
                int_cls = int(cls_idx)
                label = class_names.get(int_cls, f"class_{int_cls}")
                detections.append(
                    {
                        "name": label,
                        "category": self._category_from_label(label),
                        "quantity": 1,
                        "confidence": float(confidence),
                        "bbox": [float(x) for x in bbox],
                    }
                )

        return detections

    def _detect_with_ensemble(self, image: Image.Image) -> List[Dict[str, Any]]:
        """
        Use both models and merge their results.
        For overlapping detections, keep the one with higher confidence.
        """
        primary_detections = self._detect_with_model(
            self._primary_model, self._primary_class_names, image
        )
        secondary_detections = self._detect_with_model(
            self._secondary_model, self._secondary_class_names, image
        )

        # Merge detections: combine both lists, preferring higher confidence for duplicates
        merged: Dict[str, Dict[str, Any]] = {}
        
        for det in primary_detections + secondary_detections:
            name = det["name"].lower()
            # Use IoU or simple name matching to detect duplicates
            # For now, simple approach: same name = same detection, keep higher confidence
            if name not in merged or det["confidence"] > merged[name]["confidence"]:
                merged[name] = det

        return list(merged.values())

    def detect_ingredients_both_models(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Detect ingredients using both models separately and return results from each.
        Returns a dict with 'model1' and 'model2' results, with duplicates grouped and counted.
        """
        if not image_bytes:
            raise DetectionModelNotReady("Image payload was empty.")

        if not self.primary_model_ready and not self.secondary_model_ready:
            message = (
                self._primary_model_error or self._secondary_model_error
                or "No detection models are available."
            )
            raise DetectionModelNotReady(message)

        try:
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        except Exception as exc:
            raise DetectionModelNotReady(f"Failed to decode image: {exc}") from exc

        result = {
            "model1": [],
            "model2": [],
        }

        # Run primary model (Model 1)
        if self._primary_model is not None:
            try:
                raw_detections = self._detect_with_model(
                    self._primary_model, self._primary_class_names, image
                )
                # Group duplicates and count
                result["model1"] = self._group_and_count_detections(raw_detections)
            except Exception as exc:
                LOGGER.warning("Primary model failed: %s", exc)
                result["model1"] = []

        # Run secondary model (Model 2)
        if self._secondary_model is not None:
            try:
                raw_detections = self._detect_with_model(
                    self._secondary_model, self._secondary_class_names, image
                )
                # Group duplicates and count
                result["model2"] = self._group_and_count_detections(raw_detections)
            except Exception as exc:
                LOGGER.warning("Secondary model failed: %s", exc)
                result["model2"] = []

        return result

    def detect_ingredients_real(self, image_bytes: bytes) -> List[Dict[str, Any]]:
        """Backward-compatible alias for the real detector."""
        return self.detect_ingredients(image_bytes)

    # ------------------------------------------------------------------
    # Mock helpers (unchanged)
    # ------------------------------------------------------------------
    def detect_ingredients_mock(self, image_bytes: bytes) -> List[Dict[str, Any]]:  # pragma: no cover - dev only
        mock_items = [
            {
                "name": random.choice(["tomato", "apple", "banana", "milk", "cheese"]),
                "category": random.choice(["fruit", "vegetable", "dairy"]),
                "quantity": random.randint(1, 5),
                "confidence": round(random.uniform(0.85, 0.99), 2),
                "bbox": [100, 100, 200, 200],
            }
            for _ in range(random.randint(2, 6))
        ]
        return mock_items

    def check_freshness_mock(self, image_bytes: bytes, item_name: str) -> Tuple[str, float]:  # pragma: no cover
        freshness = random.choice(["fresh", "fresh", "fresh", "spoiled"])
        confidence = round(random.uniform(0.80, 0.98), 2)
        return freshness, confidence

    def check_freshness_real(self, image_bytes: bytes, item_name: str) -> Tuple[str, float]:
        raise NotImplementedError("Replace this with actual classifier integration!")

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------
    def _category_from_label(self, label: str) -> str:
        """Map detected labels to categories based on data.yaml items."""
        lower_label = label.lower().strip()
        
        # Fruits
        fruits = ["apple", "banana", "blue berry", "stawberry", "strawberry", "lemon", "orange"]
        # Vegetables
        vegetables = [
            "brinjal", "cabbage", "capsicum", "carrot", "corn", "cucumber",
            "ginger", "green beans", "green chilly", "green leaves", "lettuce",
            "mushroom", "potato", "sweet potato", "tomato", "spinach", "broccoli"
        ]
        # Dairy
        dairy = ["milk", "cheese", "butter", "fresh cream", "yogurt", "egg"]
        # Meat/Protein
        meat = ["chicken", "meat", "shrimp"]
        # Grains/Bakery
        grains = ["bread", "flour"]
        # Other
        other = ["chocolate"]
        
        # Check exact matches first
        if lower_label in fruits:
            return "fruits"
        if lower_label in vegetables:
            return "vegetables"
        if lower_label in dairy:
            return "dairy"
        if lower_label in meat:
            return "meat"
        if lower_label in grains:
            return "grains"
        if lower_label in other:
            return "other"
        
        # Check partial matches
        for fruit in fruits:
            if fruit in lower_label:
                return "fruits"
        for veg in vegetables:
            if veg in lower_label:
                return "vegetables"
        for d in dairy:
            if d in lower_label:
                return "dairy"
        for m in meat:
            if m in lower_label:
                return "meat"
        for g in grains:
            if g in lower_label:
                return "grains"
        
        # Fallback patterns
        if "fruit" in lower_label or "berry" in lower_label:
            return "fruits"
        if "veg" in lower_label or "leaf" in lower_label:
            return "vegetables"
        if "milk" in lower_label or "cream" in lower_label or "cheese" in lower_label:
            return "dairy"
        if "chicken" in lower_label or "meat" in lower_label or "fish" in lower_label or "shrimp" in lower_label:
            return "meat"
        if "bread" in lower_label or "flour" in lower_label or "grain" in lower_label:
            return "grains"
        
        return "uncategorized"
    
    def _group_and_count_detections(self, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Group duplicate detections and count them."""
        grouped: Dict[str, Dict[str, Any]] = {}
        
        for det in detections:
            name = det["name"].lower().strip()
            category = det.get("category", "uncategorized")
            
            # Use name+category as key to group
            key = f"{name}_{category}"
            
            if key in grouped:
                # Increment quantity
                grouped[key]["quantity"] += 1
                # Update confidence to average (or keep max)
                existing_conf = grouped[key].get("confidence", 0.0)
                new_conf = det.get("confidence", 0.0)
                grouped[key]["confidence"] = max(existing_conf, new_conf)  # Keep highest confidence
            else:
                # First occurrence
                grouped[key] = {
                    "name": det["name"],
                    "category": category,
                    "quantity": 1,
                    "unit": "item",
                    "confidence": det.get("confidence", 0.0),
                    "bbox": det.get("bbox", []),
                }
        
        return list(grouped.values())


# Global instance ------------------------------------------------------------
detection_service = DetectionService()


def get_detection_service() -> DetectionService:
    return detection_service





