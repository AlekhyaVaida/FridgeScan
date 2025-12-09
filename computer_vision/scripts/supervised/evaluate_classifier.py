import os
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image

# === CONFIG ===
TEST_DIR = "data/test"
MODEL_PATH = "models/classifier.pt"

# === DEVICE ===
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# === TRANSFORMS ===
transform = transforms.Compose([
    transforms.Resize((128, 128)),
    transforms.ToTensor()
])

# === LOAD MODEL ===
model = models.resnet18(weights=None)
model.fc = nn.Linear(model.fc.in_features, 2)
model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
model = model.to(device)
model.eval()

# === EVALUATION LOOP ===
tp = tn = fp = fn = 0

print(f"{'File':<30} | {'Label':<6} | {'Predicted':<9}")
print("-" * 60)

with torch.no_grad():
    for filename in os.listdir(TEST_DIR):
        if not filename.lower().endswith((".jpg", ".png")):
            continue

        filepath = os.path.join(TEST_DIR, filename)
        label = 0 if "fresh" in filename.lower() else 1

        image = Image.open(filepath).convert("RGB")
        img_tensor = transform(image).unsqueeze(0).to(device)

        output = model(img_tensor)
        pred = torch.argmax(output, dim=1).item()

        predicted_label = pred
        actual_label = label

        if predicted_label == 0 and actual_label == 0:
            tp += 1
        elif predicted_label == 1 and actual_label == 1:
            tn += 1
        elif predicted_label == 0 and actual_label == 1:
            fp += 1
        elif predicted_label == 1 and actual_label == 0:
            fn += 1

        pred_str = "fresh" if predicted_label == 0 else "spoiled"
        label_str = "fresh" if actual_label == 0 else "spoiled"
        print(f"{filename:<30} | {label_str:<6} | {pred_str:<9}")

# === METRICS ===
total = tp + tn + fp + fn
accuracy = (tp + tn) / total if total > 0 else 0

print("\n--- Evaluation Results ---")
print(f"Accuracy: {accuracy:.2%}")
print(f"True Positives (fresh → fresh): {tp}")
print(f"True Negatives (spoiled → spoiled): {tn}")
print(f"False Positives (spoiled → fresh): {fp}")
print(f"False Negatives (fresh → spoiled): {fn}")
