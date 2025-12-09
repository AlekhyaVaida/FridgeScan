# 🤖 Computer Vision Models

This folder contains all the machine learning models, datasets, and training scripts for the fridge spoilage detection system.

## 📁 Structure

```
computer_vision/
├── 📊 data/                    # All datasets (train/valid/test)
├── 🤖 models/                 # Trained model files (.pt)
├── 📝 scripts/                # Training and inference scripts
│   ├── detection/             # YOLOv8 object detection
│   ├── supervised/            # ResNet18 classification
│   └── unsupervised/          # Autoencoder spoilage detection
├── 🧪 tests/                  # Test suites
├── 📈 outputs/                # Results and visualizations
├── 🏃 runs/                   # Training run outputs
├── 🚀 app/                    # FastAPI applications
├── 📋 requirements.txt        # Dependencies
├── ⚙️ setup_environment.sh    # Setup script
└── 🧪 *_test.py              # Test scripts
```

## 🚀 Quick Start

```bash
# Set up environment
./setup_environment.sh
conda activate fridge_detection

# Test everything works
python final_test.py

# Train YOLOv8 model
python scripts/detection/train_yolov8.py --model yolov8n.pt --data data/detection_dataset/data.yaml --epochs 10

# Run detection
python scripts/detection/enhanced_detection.py --model yolov8n.pt --source path/to/image.jpg
```

## 🎯 Models Included

- **YOLOv8**: Object detection for food items
- **ResNet18**: Binary classification (fresh vs spoiled)
- **Autoencoder**: Unsupervised spoilage detection

## 📊 Datasets

- **Detection Dataset**: 2,425 images with 10 food classes
- **Classification Dataset**: ~9,286 images (fresh/spoiled)
- **All datasets ready to use** with proper train/valid/test splits

## 🛠️ Scripts Available

- **Training**: `train_yolov8.py`, `train_classifier.py`, `train_autoencoder.py`
- **Inference**: `enhanced_detection.py`, `batch_inference.py`
- **Export**: `model_exporter.py` (ONNX, TFLite, CoreML)
- **Testing**: `final_test.py`, `test_setup.py`

## 📈 Performance

- **YOLOv8 mAP50**: 92.7%
- **Classification Accuracy**: 95%+
- **Processing Speed**: <100ms per image

---

**All computer vision work is contained in this folder!** 🎉

