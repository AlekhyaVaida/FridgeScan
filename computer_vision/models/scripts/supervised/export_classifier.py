import os
import torch
from torchvision import models

os.makedirs("models", exist_ok=True)

model = models.resnet18(weights=None)
model.fc = torch.nn.Linear(model.fc.in_features, 2)
model.load_state_dict(torch.load("models/classifier.pt", map_location="cpu"))
model.eval()

dummy_input = torch.rand(1, 3, 128, 128)
traced_model = torch.jit.trace(model, dummy_input)

traced_model.save("models/classifier_traced.pt")
print("✅ Exported model to models/classifier_traced.pt")
