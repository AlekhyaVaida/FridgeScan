from fastapi import FastAPI, File, UploadFile
from app.infer_spoilage import classify_image
import shutil
import os

app = FastAPI()

@app.post("/check_spoilage")
async def check_spoilage(file: UploadFile = File(...)):
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    label, loss = classify_image(temp_path)
    os.remove(temp_path)

    return {"label": label, "reconstruction_loss": loss}
