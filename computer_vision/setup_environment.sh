#!/bin/bash
# Setup script for Fridge Spoilage Detection
# This ensures everyone gets the exact same environment

echo "🚀 Setting up Fridge Spoilage Detection Environment"
echo "=================================================="

# Create conda environment
echo "📦 Creating conda environment..."
conda create -n fridge_detection python=3.9 -y

# Activate environment
echo "🔄 Activating environment..."
conda activate fridge_detection

# Install exact dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Test installation
echo "🧪 Testing installation..."
python -c "
import torch
import cv2
import ultralytics
import pandas
import tqdm
print('✅ All dependencies working!')
print(f'PyTorch version: {torch.__version__}')
print(f'OpenCV version: {cv2.__version__}')
print(f'Ultralytics version: {ultralytics.__version__}')
"

echo "🎉 Setup complete!"
echo ""
echo "📝 To use this environment:"
echo "1. conda activate fridge_detection"
echo "2. python scripts/detection/enhanced_detection.py --help"
echo "3. python scripts/detection/train_yolov8.py --help"
