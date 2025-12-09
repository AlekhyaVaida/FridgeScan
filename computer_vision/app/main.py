from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from PIL import Image
import torch
from torchvision import transforms
import io

app = FastAPI()

model = torch.jit.load("models/classifier_traced.pt", map_location="cpu")
model.eval()

transform = transforms.Compose([
    transforms.Resize((128, 128)),
    transforms.ToTensor()
])

@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert("RGB")
        img_tensor = transform(image).unsqueeze(0)

        with torch.no_grad():
            output = model(img_tensor)
            pred = torch.argmax(output, dim=1).item()

        label = "fresh" if pred == 0 else "spoiled"
        return {"prediction": label}
    
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
