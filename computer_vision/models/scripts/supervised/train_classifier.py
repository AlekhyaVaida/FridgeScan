import os
import torch
import torch.nn as nn
from torchvision import models, transforms
from torch.utils.data import Dataset, DataLoader
from PIL import Image

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

class FreshSpoiledDataset(Dataset):
    def __init__(self, folder):
        self.folder = folder
        self.image_paths = [os.path.join(folder, f) for f in os.listdir(folder)
                            if f.endswith((".jpg", ".png"))]
        self.transform = transforms.Compose([
            transforms.Resize((128, 128)),
            transforms.ToTensor()
        ])

    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, idx):
        path = self.image_paths[idx]
        label = 0 if "fresh" in os.path.basename(path).lower() else 1
        img = Image.open(path).convert("RGB")
        return self.transform(img), label

# Load data
train_loader = DataLoader(FreshSpoiledDataset("data/train"), batch_size=32, shuffle=True)
valid_loader = DataLoader(FreshSpoiledDataset("data/valid"), batch_size=32)

# Load model
model = models.resnet18(pretrained=True)
model.fc = nn.Linear(model.fc.in_features, 2)  # 2 classes: fresh, spoiled
model = model.to(device)

# Loss and optimizer
criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.Adam(model.parameters(), lr=1e-4)

# Train loop
for epoch in range(5):
    model.train()
    total_loss = 0
    for imgs, labels in train_loader:
        imgs, labels = imgs.to(device), labels.to(device)
        optimizer.zero_grad()
        outputs = model(imgs)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()
    print(f"Epoch {epoch+1}, Loss: {total_loss/len(train_loader):.4f}")

# Save model
torch.save(model.state_dict(), "models/classifier.pt")
