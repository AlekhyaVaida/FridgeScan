import os
import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import transforms
from torch.utils.data import Dataset, DataLoader
from PIL import Image
from sklearn.manifold import TSNE
import matplotlib.pyplot as plt

class Autoencoder(nn.Module):
    def __init__(self):
        super(Autoencoder, self).__init__()
        self.encoder = nn.Sequential(
            nn.Conv2d(3, 16, 3, stride=2, padding=1),
            nn.ReLU(),
            nn.Conv2d(16, 32, 3, stride=2, padding=1),
            nn.ReLU()
        )
        self.decoder = nn.Sequential(
            nn.ConvTranspose2d(32, 16, 3, stride=2, padding=1, output_padding=1),
            nn.ReLU(),
            nn.ConvTranspose2d(16, 3, 3, stride=2, padding=1, output_padding=1),
            nn.Sigmoid()
        )

    def forward(self, x):
        encoded = self.encoder(x)
        decoded = self.decoder(encoded)
        return decoded, encoded

class FreshDataset(Dataset):
    def __init__(self, directory):
        self.files = [os.path.join(directory, f) for f in os.listdir(directory) if "fresh" in f.lower()]
        self.transform = transforms.Compose([
            transforms.Resize((128, 128)),
            transforms.ToTensor()
        ])

    def __len__(self):
        return len(self.files)

    def __getitem__(self, idx):
        image = Image.open(self.files[idx]).convert("RGB")
        return self.transform(image)

def train_model():
    dataset = FreshDataset("data/train")
    loader = DataLoader(dataset, batch_size=16, shuffle=True)

    model = Autoencoder()
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    criterion = nn.MSELoss()

    for epoch in range(10):
        for imgs in loader:
            outputs, _ = model(imgs)
            loss = criterion(outputs, imgs)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
        print(f"Epoch [{epoch+1}/10], Loss: {loss.item():.4f}")

    os.makedirs("models", exist_ok=True)
    torch.save(model.state_dict(), "models/autoencoder.pt")

    features = []
    for img in loader:
        with torch.no_grad():
            _, encoded = model(img)
            features.append(encoded.view(encoded.size(0), -1))
    import numpy as np
    features = torch.cat(features).numpy()
    tsne = TSNE(n_components=2)
    reduced = tsne.fit_transform(features)
    plt.scatter(reduced[:, 0], reduced[:, 1])
    os.makedirs("outputs/tsne", exist_ok=True)
    plt.savefig("outputs/tsne/tsne_plot.png")

if __name__ == "__main__":
    train_model()
