import torch
from scripts.train_autoencoder import Autoencoder

model = Autoencoder()
model.load_state_dict(torch.load("models/autoencoder.pt", map_location=torch.device("cpu")))
model.eval()

example_input = torch.randn(1, 3, 128, 128)
traced = torch.jit.trace(model, example_input)
traced.save("models/autoencoder_scripted.pt")
