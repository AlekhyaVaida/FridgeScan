FridgeScan is an AI-powered mobile app that scans your fridge, detects ingredients with computer vision, and recommends recipes info so you can cook with what you already have and reduce waste.
**Tech Stack**
Frontend: React Native (Expo), React Navigation, Axios
Backend: FastAPI (Python), Pydantic, Motor (async MongoDB), Uvicorn
Computer Vision: YOLOv8 (PyTorch/Ultralytics), custom dataset (30 classes), dual-model fallback
Data: MongoDB Atlas
External APIs: TheMealDB (recipes, keyless), Edamam (nutrition)
Dev/Tooling: Node 18+, Python 3.10+, optional CUDA GPU, ONNX/TFLite export for models
