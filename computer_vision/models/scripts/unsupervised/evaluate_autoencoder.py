import os
import torch
from torchvision import transforms
from PIL import Image

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts.train_autoencoder import Autoencoder


model = Autoencoder()
model.load_state_dict(torch.load("models/autoencoder.pt", map_location=torch.device("cpu")))
model.eval()

transform = transforms.Compose([
    transforms.Resize((128, 128)),
    transforms.ToTensor()
])

def get_loss(image_path):
    image = Image.open(image_path).convert("RGB")
    img_tensor = transform(image).unsqueeze(0)
    with torch.no_grad():
        output, _ = model(img_tensor)
        loss = torch.nn.functional.mse_loss(output, img_tensor).item()
    return loss

# Config
threshold = 0.01
test_dir = "data/test"
tp = fp = tn = fn = 0

print(f"{'File':<30} | {'Label':<6} | {'Predicted':<8} | Loss")
print("-" * 70)

for filename in os.listdir(test_dir):
    if not filename.lower().endswith((".jpg", ".png")):
        continue
    filepath = os.path.join(test_dir, filename)
    label = "fresh" if "fresh" in filename.lower() else "spoiled"
    loss = get_loss(filepath)
    predicted = "fresh" if loss < threshold else "spoiled"

    if label == "fresh" and predicted == "fresh":
        tp += 1
    elif label == "fresh" and predicted == "spoiled":
        fn += 1
    elif label == "spoiled" and predicted == "spoiled":
        tn += 1
    elif label == "spoiled" and predicted == "fresh":
        fp += 1

    print(f"{filename:<30} | {label:<6} | {predicted:<8} | {loss:.4f}")

# Metrics
total = tp + tn + fp + fn
accuracy = (tp + tn) / total if total > 0 else 0
print("\n--- Evaluation Metrics ---")
print(f"Accuracy: {accuracy:.2%}")
print(f"True Positives (fresh correctly): {tp}")
print(f"True Negatives (spoiled correctly): {tn}")
print(f"False Positives (spoiled misclassified as fresh): {fp}")
print(f"False Negatives (fresh misclassified as spoiled): {fn}")


fresh_losses = []
spoiled_losses = []

for filename in os.listdir(test_dir):
    if not filename.lower().endswith((".jpg", ".png")):
        continue
    filepath = os.path.join(test_dir, filename)
    label = "fresh" if "fresh" in filename.lower() else "spoiled"
    loss = get_loss(filepath)

    if label == "fresh":
        fresh_losses.append(loss)
    else:
        spoiled_losses.append(loss)

# Calculate average losses
print("\n--- Average Reconstruction Loss ---")
print(f"Fresh images: {sum(fresh_losses)/len(fresh_losses):.4f}")
print(f"Spoiled images: {sum(spoiled_losses)/len(spoiled_losses):.4f}")
