# scripts/detection/run_yolov8.py
import torch
from ultralytics import YOLO
import cv2
import os

def detect_items(image_path, model_path='models/yolov8.pt', save_crops=False, crop_dir='outputs/crops'):
    """
    Legacy detection function - kept for backward compatibility
    For enhanced detection, use enhanced_detection.py
    """
    model = YOLO(model_path)
    results = model(image_path)[0]  # Assume single image

    os.makedirs(crop_dir, exist_ok=True)
    items = []

    image = cv2.imread(image_path)

    for i, box in enumerate(results.boxes):
        cls_id = int(box.cls[0])
        conf = float(box.conf[0])
        label = model.names[cls_id]
        x1, y1, x2, y2 = map(int, box.xyxy[0])

        crop = image[y1:y2, x1:x2]
        crop_path = os.path.join(crop_dir, f'{label}_{i}.jpg')
        if save_crops:
            cv2.imwrite(crop_path, crop)

        items.append({
            'label': label,
            'bbox': [x1, y1, x2, y2],
            'conf': conf,
            'crop_path': crop_path
        })

    return items