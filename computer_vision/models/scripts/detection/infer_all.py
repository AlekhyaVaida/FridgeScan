# scripts/detection/infer_all.py
import torch
from torchvision import transforms
from PIL import Image
import os

from scripts.detection.run_yolov8 import detect_items
from scripts.detection.run_ocr import run_ocr
from scripts.supervised.train_classifier import FreshSpoiledDataset
from scripts.supervised.export_classifier import ClassifierNet  # if you have one

# Load spoilage model
model = torch.load('models/classifier_traced.pt')
model.eval()

transform = transforms.Compose([
    transforms.Resize((128, 128)),
    transforms.ToTensor()
])

def check_spoilage(image_path):
    image = Image.open(image_path).convert("RGB")
    tensor = transform(image).unsqueeze(0)
    with torch.no_grad():
        outputs = model(tensor)
        pred = torch.argmax(outputs, dim=1).item()
        return 'fresh' if pred == 0 else 'spoiled'

def infer_fridge_items(image_path):
    items = detect_items(image_path, save_crops=True)
    results = []

    for item in items:
        label = item['label']
        if label in ['box', 'carton', 'unknown']:
            ocr_result = run_ocr(item['crop_path'])
            if ocr_result and 'milk' in ocr_result:
                label = 'milk'
        spoilage = check_spoilage(item['crop_path'])

        results.append({
            'item': label,
            'source': 'ocr' if label == 'milk' else 'detection',
            'status': spoilage,
            'confidence': round(item['conf'], 2)
        })

    return results

if __name__ == "__main__":
    results = infer_fridge_items("data/test/fridge_snapshot.jpg")
    for r in results:
        print(r)
