# 🤖 Machine Learning Models

This directory contains all machine learning models, training scripts, and inference utilities.

## 📁 Structure

```
models/
├── detection/          # YOLOv8 object detection
├── supervised/         # ResNet18 classification  
├── unsupervised/       # Autoencoder spoilage detection
├── classifier.pt       # Trained ResNet18 weights
├── classifier_traced.pt # Production-ready traced model
├── autoencoder.pt      # Trained autoencoder weights
└── yolov8n.pt         # Pre-trained YOLOv8 model
```

## 🚀 Quick Start

### Train YOLOv8 Model
```bash
python detection/train_yolov8.py \
    --model yolov8n.pt \
    --data ../datasets/detection_dataset/data.yaml \
    --epochs 10
```

### Run Detection
```bash
python detection/enhanced_detection.py \
    --model yolov8n.pt \
    --source path/to/image.jpg \
    --save-crops
```

### Export Models
```bash
python detection/model_exporter.py \
    --model runs/detect/train/weights/best.pt \
    --formats onnx tflite coreml
```

## 📊 Model Performance

### YOLOv8 Object Detection
- **mAP50**: 92.7%
- **mAP50-95**: 80.5%
- **Precision**: 91.3%
- **Recall**: 85.8%

### ResNet18 Classification
- **Accuracy**: 95%+
- **F1-Score**: 0.94
- **Inference Time**: <50ms

### Autoencoder Detection
- **Threshold**: 0.01 reconstruction loss
- **Accuracy**: 90%+
- **Processing Time**: <30ms

## 🛠️ Training Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `detection/train_yolov8.py` | Train YOLOv8 models | See above |
| `detection/enhanced_detection.py` | Run inference with NMS | See above |
| `detection/model_exporter.py` | Export to multiple formats | See above |
| `detection/batch_inference.py` | Process multiple images | `python batch_inference.py --help` |
| `supervised/train_classifier.py` | Train ResNet18 classifier | `python train_classifier.py` |
| `unsupervised/train_autoencoder.py` | Train autoencoder | `python train_autoencoder.py` |

## 📈 Supported Export Formats

- **ONNX**: Cross-platform inference
- **TensorFlow Lite**: Mobile deployment
- **CoreML**: iOS deployment
- **OpenVINO**: Intel optimization
- **TorchScript**: PyTorch optimization

## 🔧 Configuration

Models are configured via YAML files:
- `detection_dataset/data.yaml` - YOLOv8 dataset config
- Training parameters in each script
- Model paths in `../config/requirements.txt`
