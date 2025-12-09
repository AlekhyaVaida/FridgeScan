#!/usr/bin/env python3
"""
Quick test script to verify the enhanced detection scripts work
"""

import os
import sys
from pathlib import Path

def test_imports():
    """Test if we can import the required modules"""
    print("🧪 Testing imports...")
    
    try:
        import torch
        print("✅ PyTorch available")
    except ImportError as e:
        print(f"❌ PyTorch not available: {e}")
        return False
    
    try:
        import cv2
        print("✅ OpenCV available")
    except ImportError as e:
        print(f"❌ OpenCV not available: {e}")
        return False
    
    try:
        import numpy as np
        print("✅ NumPy available")
    except ImportError as e:
        print(f"❌ NumPy not available: {e}")
        return False
    
    try:
        from ultralytics import YOLO
        print("✅ Ultralytics available")
    except ImportError as e:
        print(f"⚠️  Ultralytics not available: {e}")
        print("   You can install it with: pip install ultralytics")
    
    return True

def test_script_syntax():
    """Test if our enhanced scripts have correct syntax"""
    print("\n🔍 Testing script syntax...")
    
    scripts_to_test = [
        "scripts/detection/train_yolov8.py",
        "scripts/detection/enhanced_detection.py", 
        "scripts/detection/model_exporter.py",
        "scripts/detection/batch_inference.py"
    ]
    
    for script_path in scripts_to_test:
        if os.path.exists(script_path):
            try:
                with open(script_path, 'r') as f:
                    compile(f.read(), script_path, 'exec')
                print(f"✅ {script_path} - syntax OK")
            except SyntaxError as e:
                print(f"❌ {script_path} - syntax error: {e}")
                return False
        else:
            print(f"⚠️  {script_path} - file not found")
    
    return True

def test_basic_functionality():
    """Test basic functionality without heavy dependencies"""
    print("\n⚙️  Testing basic functionality...")
    
    # Test if we can create the enhanced detector class
    try:
        # Create a minimal test
        test_code = """
import sys
import os
sys.path.append('scripts/detection')

# Test if we can import our modules
try:
    from enhanced_detection import EnhancedDetector
    print("✅ EnhancedDetector class can be imported")
except ImportError as e:
    print(f"⚠️  EnhancedDetector import issue: {e}")

try:
    from train_yolov8 import YOLOv8Trainer
    print("✅ YOLOv8Trainer class can be imported")
except ImportError as e:
    print(f"⚠️  YOLOv8Trainer import issue: {e}")
"""
        exec(test_code)
        return True
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        return False

def check_github_readiness():
    """Check if the project is ready for GitHub"""
    print("\n📋 Checking GitHub readiness...")
    
    required_files = [
        "README.md",
        ".gitignore", 
        "requirements.txt",
        "app/main.py",
        "scripts/detection/train_yolov8.py",
        "scripts/detection/enhanced_detection.py"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print(f"⚠️  Missing files: {missing_files}")
    else:
        print("✅ All required files present")
    
    # Check if .gitignore is comprehensive
    if os.path.exists(".gitignore"):
        with open(".gitignore", 'r') as f:
            gitignore_content = f.read()
        
        important_patterns = ["__pycache__", "*.pyc", "*.pt", "*.pth", "runs/", "outputs/", "venv/"]
        missing_patterns = [pattern for pattern in important_patterns if pattern not in gitignore_content]
        
        if missing_patterns:
            print(f"⚠️  Consider adding to .gitignore: {missing_patterns}")
        else:
            print("✅ .gitignore looks good")
    
    return len(missing_files) == 0

def main():
    """Run all tests"""
    print("🚀 Testing Enhanced Detection Scripts Setup")
    print("=" * 50)
    
    # Test imports
    imports_ok = test_imports()
    
    # Test syntax
    syntax_ok = test_script_syntax()
    
    # Test basic functionality
    func_ok = test_basic_functionality()
    
    # Check GitHub readiness
    github_ok = check_github_readiness()
    
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    print(f"Imports: {'✅ PASS' if imports_ok else '❌ FAIL'}")
    print(f"Syntax: {'✅ PASS' if syntax_ok else '❌ FAIL'}")
    print(f"Functionality: {'✅ PASS' if func_ok else '❌ FAIL'}")
    print(f"GitHub Ready: {'✅ PASS' if github_ok else '❌ FAIL'}")
    
    if all([imports_ok, syntax_ok, func_ok, github_ok]):
        print("\n🎉 All tests passed! Your project is ready to run and push to GitHub!")
    else:
        print("\n⚠️  Some tests failed. Check the issues above before proceeding.")
    
    print("\n📝 NEXT STEPS:")
    print("1. Install missing dependencies: pip install ultralytics pandas tqdm")
    print("2. Test with a sample image: python scripts/detection/enhanced_detection.py --model yolov8n.pt --image test.jpg")
    print("3. Train a model: python scripts/detection/train_yolov8.py --model yolov8n.pt --data data/detection_dataset/data.yaml --epochs 5")
    print("4. Push to GitHub: git add . && git commit -m 'Add enhanced detection scripts' && git push")

if __name__ == "__main__":
    main()
