import torch
from torchvision import transforms
from PIL import Image
from scripts.train_autoencoder import Autoencoder

def load_model():
    model = Autoencoder()
    model.load_state_dict(torch.load("models/autoencoder.pt", map_location=torch.device("cpu")))
    model.eval()
    return model

def classify_image(image_path, threshold=0.01):
    model = load_model()
    transform = transforms.Compose([
        transforms.Resize((128, 128)),
        transforms.ToTensor()
    ])
    image = Image.open(image_path).convert("RGB")
    input_tensor = transform(image).unsqueeze(0)

    with torch.no_grad():
        reconstructed, _ = model(input_tensor)
        loss = torch.nn.functional.mse_loss(reconstructed, input_tensor).item()

    return ("spoiled" if loss > threshold else "fresh"), loss
