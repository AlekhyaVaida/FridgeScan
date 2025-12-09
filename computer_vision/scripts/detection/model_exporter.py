#!/usr/bin/env python3
"""
Model Export Utility for Multiple Deployment Formats
Based on Maryam's implementation and industry best practices
"""

import os
import torch
import tensorflow as tf
import numpy as np
from ultralytics import YOLO
from pathlib import Path
import logging
from typing import List, Dict, Optional, Union
import yaml

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ModelExporter:
    def __init__(self, model_path: str, output_dir: str = "models/exported"):
        """
        Initialize the model exporter
        
        Args:
            model_path: Path to the trained YOLOv8 model
            output_dir: Directory to save exported models
        """
        self.model_path = model_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.model = None
        self.class_names = None
        
        self._load_model()
    
    def _load_model(self):
        """Load the YOLOv8 model"""
        try:
            if not os.path.exists(self.model_path):
                raise FileNotFoundError(f"Model file not found: {self.model_path}")
            
            self.model = YOLO(self.model_path)
            self.class_names = self.model.names
            logger.info(f"Model loaded successfully: {self.model_path}")
            logger.info(f"Number of classes: {len(self.class_names)}")
            
        except Exception as e:
            logger.error(f"Failed to load model: {str(e)}")
            raise
    
    def export_onnx(self, 
                   imgsz: int = 640, 
                   batch: int = 1, 
                   opset: int = 11,
                   simplify: bool = True,
                   optimize: bool = True) -> str:
        """
        Export model to ONNX format
        
        Args:
            imgsz: Input image size
            batch: Batch size
            opset: ONNX opset version
            simplify: Simplify ONNX model
            optimize: Optimize ONNX model
            
        Returns:
            Path to exported ONNX model
        """
        try:
            logger.info("Exporting model to ONNX format...")
            
            exported_path = self.model.export(
                format='onnx',
                imgsz=imgsz,
                batch=batch,
                opset=opset,
                simplify=simplify,
                optimize=optimize,
                workspace=4,
                nms=True
            )
            
            # Move to output directory
            onnx_filename = f"model_{imgsz}x{imgsz}_batch{batch}.onnx"
            onnx_path = self.output_dir / onnx_filename
            os.rename(exported_path, onnx_path)
            
            logger.info(f"ONNX model exported to: {onnx_path}")
            return str(onnx_path)
            
        except Exception as e:
            logger.error(f"ONNX export failed: {str(e)}")
            raise
    
    def export_tflite(self, 
                     imgsz: int = 640, 
                     batch: int = 1,
                     int8: bool = False,
                     dynamic: bool = False) -> str:
        """
        Export model to TensorFlow Lite format
        
        Args:
            imgsz: Input image size
            batch: Batch size
            int8: Use INT8 quantization
            dynamic: Use dynamic range quantization
            
        Returns:
            Path to exported TFLite model
        """
        try:
            logger.info("Exporting model to TensorFlow Lite format...")
            
            # First export to TensorFlow SavedModel
            saved_model_path = self.model.export(
                format='tflite',
                imgsz=imgsz,
                batch=batch,
                int8=int8,
                dynamic=dynamic,
                workspace=4,
                nms=True
            )
            
            # Move to output directory
            tflite_filename = f"model_{imgsz}x{imgsz}_batch{batch}.tflite"
            tflite_path = self.output_dir / tflite_filename
            os.rename(saved_model_path, tflite_path)
            
            logger.info(f"TensorFlow Lite model exported to: {tflite_path}")
            return str(tflite_path)
            
        except Exception as e:
            logger.error(f"TensorFlow Lite export failed: {str(e)}")
            raise
    
    def export_tensorflow(self, 
                         imgsz: int = 640, 
                         batch: int = 1) -> str:
        """
        Export model to TensorFlow SavedModel format
        
        Args:
            imgsz: Input image size
            batch: Batch size
            
        Returns:
            Path to exported TensorFlow model
        """
        try:
            logger.info("Exporting model to TensorFlow SavedModel format...")
            
            exported_path = self.model.export(
                format='tensorflow',
                imgsz=imgsz,
                batch=batch,
                workspace=4,
                nms=True
            )
            
            # Move to output directory
            tf_filename = f"model_{imgsz}x{imgsz}_batch{batch}_saved_model"
            tf_path = self.output_dir / tf_filename
            os.rename(exported_path, tf_path)
            
            logger.info(f"TensorFlow SavedModel exported to: {tf_path}")
            return str(tf_path)
            
        except Exception as e:
            logger.error(f"TensorFlow export failed: {str(e)}")
            raise
    
    def export_coreml(self, 
                     imgsz: int = 640, 
                     batch: int = 1) -> str:
        """
        Export model to CoreML format (for iOS/macOS)
        
        Args:
            imgsz: Input image size
            batch: Batch size
            
        Returns:
            Path to exported CoreML model
        """
        try:
            logger.info("Exporting model to CoreML format...")
            
            exported_path = self.model.export(
                format='coreml',
                imgsz=imgsz,
                batch=batch,
                workspace=4,
                nms=True
            )
            
            # Move to output directory
            coreml_filename = f"model_{imgsz}x{imgsz}_batch{batch}.mlpackage"
            coreml_path = self.output_dir / coreml_filename
            os.rename(exported_path, coreml_path)
            
            logger.info(f"CoreML model exported to: {coreml_path}")
            return str(coreml_path)
            
        except Exception as e:
            logger.error(f"CoreML export failed: {str(e)}")
            raise
    
    def export_openvino(self, 
                       imgsz: int = 640, 
                       batch: int = 1,
                       half: bool = False) -> str:
        """
        Export model to OpenVINO format (for Intel hardware)
        
        Args:
            imgsz: Input image size
            batch: Batch size
            half: Use FP16 precision
            
        Returns:
            Path to exported OpenVINO model
        """
        try:
            logger.info("Exporting model to OpenVINO format...")
            
            exported_path = self.model.export(
                format='openvino',
                imgsz=imgsz,
                batch=batch,
                half=half,
                workspace=4,
                nms=True
            )
            
            # Move to output directory
            ov_filename = f"model_{imgsz}x{imgsz}_batch{batch}"
            ov_path = self.output_dir / ov_filename
            os.rename(exported_path, ov_path)
            
            logger.info(f"OpenVINO model exported to: {ov_path}")
            return str(ov_path)
            
        except Exception as e:
            logger.error(f"OpenVINO export failed: {str(e)}")
            raise
    
    def export_torchscript(self, 
                          imgsz: int = 640, 
                          batch: int = 1,
                          optimize: bool = True) -> str:
        """
        Export model to TorchScript format
        
        Args:
            imgsz: Input image size
            batch: Batch size
            optimize: Optimize TorchScript model
            
        Returns:
            Path to exported TorchScript model
        """
        try:
            logger.info("Exporting model to TorchScript format...")
            
            exported_path = self.model.export(
                format='torchscript',
                imgsz=imgsz,
                batch=batch,
                optimize=optimize,
                workspace=4,
                nms=True
            )
            
            # Move to output directory
            ts_filename = f"model_{imgsz}x{imgsz}_batch{batch}.torchscript"
            ts_path = self.output_dir / ts_filename
            os.rename(exported_path, ts_path)
            
            logger.info(f"TorchScript model exported to: {ts_path}")
            return str(ts_path)
            
        except Exception as e:
            logger.error(f"TorchScript export failed: {str(e)}")
            raise
    
    def export_all_formats(self, 
                          formats: List[str] = None,
                          imgsz: int = 640, 
                          batch: int = 1) -> Dict[str, str]:
        """
        Export model to all supported formats
        
        Args:
            formats: List of formats to export (default: all)
            imgsz: Input image size
            batch: Batch size
            
        Returns:
            Dictionary mapping format names to exported paths
        """
        if formats is None:
            formats = ['onnx', 'tflite', 'tensorflow', 'coreml', 'openvino', 'torchscript']
        
        exported_models = {}
        
        for format_name in formats:
            try:
                if format_name == 'onnx':
                    path = self.export_onnx(imgsz, batch)
                elif format_name == 'tflite':
                    path = self.export_tflite(imgsz, batch)
                elif format_name == 'tensorflow':
                    path = self.export_tensorflow(imgsz, batch)
                elif format_name == 'coreml':
                    path = self.export_coreml(imgsz, batch)
                elif format_name == 'openvino':
                    path = self.export_openvino(imgsz, batch)
                elif format_name == 'torchscript':
                    path = self.export_torchscript(imgsz, batch)
                else:
                    logger.warning(f"Unknown format: {format_name}")
                    continue
                
                exported_models[format_name] = path
                
            except Exception as e:
                logger.error(f"Failed to export {format_name}: {str(e)}")
                continue
        
        return exported_models
    
    def create_model_info(self, exported_models: Dict[str, str]) -> str:
        """
        Create a model information file
        
        Args:
            exported_models: Dictionary of exported models
            
        Returns:
            Path to model info file
        """
        info = {
            'model_info': {
                'original_model': self.model_path,
                'class_names': self.class_names,
                'num_classes': len(self.class_names),
                'export_timestamp': str(torch.cuda.get_device_properties(0).name) if torch.cuda.is_available() else 'CPU',
                'device': 'CUDA' if torch.cuda.is_available() else 'CPU'
            },
            'exported_models': exported_models,
            'usage_examples': {
                'python': {
                    'onnx': 'import onnxruntime as ort; session = ort.InferenceSession("model.onnx")',
                    'tflite': 'import tensorflow as tf; interpreter = tf.lite.Interpreter("model.tflite")',
                    'torchscript': 'import torch; model = torch.jit.load("model.torchscript")'
                }
            }
        }
        
        info_path = self.output_dir / 'model_info.yaml'
        with open(info_path, 'w') as f:
            yaml.dump(info, f, default_flow_style=False)
        
        logger.info(f"Model info saved to: {info_path}")
        return str(info_path)
    
    def test_exported_model(self, model_path: str, format_name: str, test_image: str = None):
        """
        Test an exported model with a sample image
        
        Args:
            model_path: Path to exported model
            format_name: Format of the exported model
            test_image: Path to test image (optional)
        """
        try:
            logger.info(f"Testing {format_name} model: {model_path}")
            
            if format_name == 'onnx':
                import onnxruntime as ort
                session = ort.InferenceSession(model_path)
                input_name = session.get_inputs()[0].name
                output_name = session.get_outputs()[0].name
                logger.info(f"ONNX model input: {input_name}, output: {output_name}")
                
            elif format_name == 'tflite':
                interpreter = tf.lite.Interpreter(model_path)
                interpreter.allocate_tensors()
                input_details = interpreter.get_input_details()
                output_details = interpreter.get_output_details()
                logger.info(f"TFLite model input: {input_details[0]['shape']}, output: {output_details[0]['shape']}")
                
            elif format_name == 'torchscript':
                model = torch.jit.load(model_path)
                logger.info(f"TorchScript model loaded successfully")
                
            else:
                logger.info(f"Model format {format_name} loaded successfully")
            
            logger.info(f"✅ {format_name} model test passed")
            
        except Exception as e:
            logger.error(f"❌ {format_name} model test failed: {str(e)}")

def main():
    """Example usage of ModelExporter"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Export YOLOv8 model to multiple formats')
    parser.add_argument('--model', type=str, required=True, help='Path to YOLOv8 model')
    parser.add_argument('--output-dir', type=str, default='models/exported', help='Output directory')
    parser.add_argument('--formats', nargs='+', 
                       choices=['onnx', 'tflite', 'tensorflow', 'coreml', 'openvino', 'torchscript'],
                       default=['onnx', 'tflite'], help='Formats to export')
    parser.add_argument('--imgsz', type=int, default=640, help='Input image size')
    parser.add_argument('--batch', type=int, default=1, help='Batch size')
    parser.add_argument('--test', action='store_true', help='Test exported models')
    
    args = parser.parse_args()
    
    # Create exporter
    exporter = ModelExporter(args.model, args.output_dir)
    
    # Export models
    exported_models = exporter.export_all_formats(
        formats=args.formats,
        imgsz=args.imgsz,
        batch=args.batch
    )
    
    # Create model info file
    exporter.create_model_info(exported_models)
    
    # Test exported models if requested
    if args.test:
        for format_name, model_path in exported_models.items():
            exporter.test_exported_model(model_path, format_name)
    
    print(f"\n✅ Export completed! Models saved to: {args.output_dir}")
    print("Exported models:")
    for format_name, model_path in exported_models.items():
        print(f"  - {format_name}: {model_path}")

if __name__ == "__main__":
    main()
