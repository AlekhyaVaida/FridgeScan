#!/usr/bin/env python3
"""
Enhanced YOLOv8 Training Script
Based on best practices from Maryam's implementation and industry standards
"""

import os
import yaml
import torch
from ultralytics import YOLO
import argparse
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class YOLOv8Trainer:
    def __init__(self, config_path=None):
        self.config = self._load_config(config_path)
        self.model = None
        
    def _load_config(self, config_path):
        """Load training configuration from YAML file"""
        default_config = {
            'model': 'yolov8n.pt',  # Start with nano for speed
            'data': 'data/detection_dataset/data.yaml',
            'epochs': 50,
            'batch': 16,
            'imgsz': 640,
            'workers': 8,
            'device': None,  # Auto-detect
            'project': 'runs/detect',
            'name': 'fridge_detection',
            'patience': 50,
            'save_period': 10,
            'cache': True,
            'augment': True,
            'cos_lr': True,
            'close_mosaic': 10,
            'mixup': 0.15,
            'copy_paste': 0.3,
            'degrees': 10.0,
            'translate': 0.1,
            'scale': 0.5,
            'shear': 2.0,
            'perspective': 0.0,
            'flipud': 0.0,
            'fliplr': 0.5,
            'mosaic': 1.0,
            'hsv_h': 0.015,
            'hsv_s': 0.7,
            'hsv_v': 0.4,
            'lr0': 0.01,
            'lrf': 0.01,
            'momentum': 0.937,
            'weight_decay': 0.0005,
            'warmup_epochs': 3.0,
            'warmup_momentum': 0.8,
            'warmup_bias_lr': 0.1,
            'box': 7.5,
            'cls': 0.5,
            'dfl': 1.5,
            'conf': 0.001,
            'iou': 0.7,
            'max_det': 300,
            'half': False,
            'dnn': False,
            'plots': True,
            'val': True,
            'split': 'val',
            'save_json': False,
            'save_txt': False,
            'save_conf': False,
            'save_crop': False,
            'show_labels': True,
            'show_conf': True,
            'show_boxes': True,
            'verbose': True,
            'seed': 42,
            'deterministic': True,
            'single_cls': False,
            'rect': False,
            'resume': False,
            'amp': True,
            'fraction': 1.0,
            'profile': False,
            'freeze': None,
            'multi_scale': False,
            'overlap_mask': True,
            'mask_ratio': 4,
            'dropout': 0.0,
            'agnostic_nms': False,
            'classes': None,
            'retina_masks': False,
            'embed': None,
            'show': False,
            'save_frames': False,
            'vid_stride': 1,
            'stream_buffer': False,
            'visualize': False,
            'source': None,
            'format': 'torchscript',
            'keras': False,
            'optimize': False,
            'int8': False,
            'dynamic': False,
            'simplify': True,
            'opset': None,
            'workspace': None,
            'nms': False,
            'pose': 12.0,
            'kobj': 1.0,
            'nbs': 64,
            'bgr': 0.0,
            'auto_augment': 'randaugment',
            'erasing': 0.4,
            'cfg': None,
            'tracker': 'botsort.yaml'
        }
        
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r') as f:
                user_config = yaml.safe_load(f)
                default_config.update(user_config)
        
        return default_config
    
    def prepare_data(self):
        """Prepare and validate dataset"""
        data_yaml = self.config['data']
        
        if not os.path.exists(data_yaml):
            raise FileNotFoundError(f"Data YAML file not found: {data_yaml}")
        
        # Load and validate data.yaml
        with open(data_yaml, 'r') as f:
            data_config = yaml.safe_load(f)
        
        # Check if paths exist
        for split in ['train', 'val', 'test']:
            if split in data_config:
                path = data_config[split]
                if not os.path.exists(path):
                    logger.warning(f"Path for {split} does not exist: {path}")
        
        logger.info(f"Dataset configuration loaded: {data_yaml}")
        logger.info(f"Number of classes: {data_config.get('nc', 'Unknown')}")
        logger.info(f"Class names: {data_config.get('names', 'Unknown')}")
        
        return data_config
    
    def load_model(self):
        """Load YOLOv8 model"""
        model_path = self.config['model']
        
        if not os.path.exists(model_path) and not model_path.startswith('yolov8'):
            raise FileNotFoundError(f"Model file not found: {model_path}")
        
        self.model = YOLO(model_path)
        logger.info(f"Model loaded: {model_path}")
        
        return self.model
    
    def train(self):
        """Train the YOLOv8 model"""
        if self.model is None:
            self.load_model()
        
        # Prepare data
        self.prepare_data()
        
        # Create output directory
        os.makedirs(self.config['project'], exist_ok=True)
        
        logger.info("Starting YOLOv8 training...")
        logger.info(f"Configuration: {self.config}")
        
        try:
            # Train the model
            results = self.model.train(
                data=self.config['data'],
                epochs=self.config['epochs'],
                batch=self.config['batch'],
                imgsz=self.config['imgsz'],
                workers=self.config['workers'],
                device=self.config['device'],
                project=self.config['project'],
                name=self.config['name'],
                exist_ok=True,
                patience=self.config['patience'],
                save_period=self.config['save_period'],
                cache=self.config['cache'],
                augment=self.config['augment'],
                cos_lr=self.config['cos_lr'],
                close_mosaic=self.config['close_mosaic'],
                mixup=self.config['mixup'],
                copy_paste=self.config['copy_paste'],
                degrees=self.config['degrees'],
                translate=self.config['translate'],
                scale=self.config['scale'],
                shear=self.config['shear'],
                perspective=self.config['perspective'],
                flipud=self.config['flipud'],
                fliplr=self.config['fliplr'],
                mosaic=self.config['mosaic'],
                hsv_h=self.config['hsv_h'],
                hsv_s=self.config['hsv_s'],
                hsv_v=self.config['hsv_v'],
                lr0=self.config['lr0'],
                lrf=self.config['lrf'],
                momentum=self.config['momentum'],
                weight_decay=self.config['weight_decay'],
                warmup_epochs=self.config['warmup_epochs'],
                warmup_momentum=self.config['warmup_momentum'],
                warmup_bias_lr=self.config['warmup_bias_lr'],
                box=self.config['box'],
                cls=self.config['cls'],
                dfl=self.config['dfl'],
                conf=self.config['conf'],
                iou=self.config['iou'],
                max_det=self.config['max_det'],
                half=self.config['half'],
                dnn=self.config['dnn'],
                plots=self.config['plots'],
                val=self.config['val'],
                split=self.config['split'],
                save_json=self.config['save_json'],
                save_txt=self.config['save_txt'],
                save_conf=self.config['save_conf'],
                save_crop=self.config['save_crop'],
                show_labels=self.config['show_labels'],
                show_conf=self.config['show_conf'],
                show_boxes=self.config['show_boxes'],
                verbose=self.config['verbose'],
                seed=self.config['seed'],
                deterministic=self.config['deterministic'],
                single_cls=self.config['single_cls'],
                rect=self.config['rect'],
                resume=self.config['resume'],
                amp=self.config['amp'],
                fraction=self.config['fraction'],
                profile=self.config['profile'],
                freeze=self.config['freeze'],
                multi_scale=self.config['multi_scale'],
                overlap_mask=self.config['overlap_mask'],
                mask_ratio=self.config['mask_ratio'],
                dropout=self.config['dropout'],
                agnostic_nms=self.config['agnostic_nms'],
                classes=self.config['classes'],
                retina_masks=self.config['retina_masks'],
                embed=self.config['embed'],
                show=self.config['show'],
                save_frames=self.config['save_frames'],
                vid_stride=self.config['vid_stride'],
                stream_buffer=self.config['stream_buffer'],
                visualize=self.config['visualize'],
                source=self.config['source'],
                format=self.config['format'],
                keras=self.config['keras'],
                optimize=self.config['optimize'],
                int8=self.config['int8'],
                dynamic=self.config['dynamic'],
                simplify=self.config['simplify'],
                opset=self.config['opset'],
                workspace=self.config['workspace'],
                nms=self.config['nms'],
                pose=self.config['pose'],
                kobj=self.config['kobj'],
                nbs=self.config['nbs'],
                bgr=self.config['bgr'],
                auto_augment=self.config['auto_augment'],
                erasing=self.config['erasing'],
                cfg=self.config['cfg'],
                tracker=self.config['tracker']
            )
            
            logger.info("Training completed successfully!")
            return results
            
        except Exception as e:
            logger.error(f"Training failed: {str(e)}")
            raise
    
    def evaluate(self, split='val'):
        """Evaluate the trained model"""
        if self.model is None:
            raise ValueError("Model not loaded. Please train or load a model first.")
        
        logger.info(f"Evaluating model on {split} split...")
        
        results = self.model.val(
            data=self.config['data'],
            split=split,
            imgsz=self.config['imgsz'],
            batch=self.config['batch'],
            conf=self.config['conf'],
            iou=self.config['iou'],
            max_det=self.config['max_det'],
            half=self.config['half'],
            dnn=self.config['dnn'],
            plots=self.config['plots'],
            save_json=self.config['save_json'],
            save_txt=self.config['save_txt'],
            save_conf=self.config['save_conf'],
            save_crop=self.config['save_crop'],
            show_labels=self.config['show_labels'],
            show_conf=self.config['show_conf'],
            show_boxes=self.config['show_boxes'],
            verbose=self.config['verbose'],
            agnostic_nms=self.config['agnostic_nms'],
            classes=self.config['classes'],
            retina_masks=self.config['retina_masks'],
            embed=self.config['embed'],
            show=self.config['show'],
            save_frames=self.config['save_frames'],
            vid_stride=self.config['vid_stride'],
            stream_buffer=self.config['stream_buffer'],
            visualize=self.config['visualize'],
            source=self.config['source'],
            format=self.config['format'],
            keras=self.config['keras'],
            optimize=self.config['optimize'],
            int8=self.config['int8'],
            dynamic=self.config['dynamic'],
            simplify=self.config['simplify'],
            opset=self.config['opset'],
            workspace=self.config['workspace'],
            nms=self.config['nms'],
            pose=self.config['pose'],
            kobj=self.config['kobj'],
            nbs=self.config['nbs'],
            bgr=self.config['bgr'],
            auto_augment=self.config['auto_augment'],
            erasing=self.config['erasing'],
            cfg=self.config['cfg'],
            tracker=self.config['tracker']
        )
        
        # Log evaluation results
        if hasattr(results, 'box'):
            logger.info(f"mAP50: {results.box.map50:.4f}")
            logger.info(f"mAP50-95: {results.box.map:.4f}")
            logger.info(f"Precision: {results.box.p:.4f}")
            logger.info(f"Recall: {results.box.r:.4f}")
        
        return results
    
    def export_model(self, formats=['onnx', 'tflite']):
        """Export model to different formats"""
        if self.model is None:
            raise ValueError("Model not loaded. Please train or load a model first.")
        
        exported_models = {}
        
        for format_type in formats:
            try:
                logger.info(f"Exporting model to {format_type.upper()}...")
                exported_path = self.model.export(format=format_type)
                exported_models[format_type] = exported_path
                logger.info(f"Model exported to: {exported_path}")
            except Exception as e:
                logger.error(f"Failed to export to {format_type}: {str(e)}")
        
        return exported_models

def main():
    parser = argparse.ArgumentParser(description='Train YOLOv8 model for fridge object detection')
    parser.add_argument('--config', type=str, help='Path to training configuration YAML file')
    parser.add_argument('--data', type=str, default='data/detection_dataset/data.yaml', help='Path to data YAML file')
    parser.add_argument('--model', type=str, default='yolov8n.pt', help='Path to model file or model name')
    parser.add_argument('--epochs', type=int, default=50, help='Number of training epochs')
    parser.add_argument('--batch', type=int, default=16, help='Batch size')
    parser.add_argument('--imgsz', type=int, default=640, help='Image size')
    parser.add_argument('--device', type=str, default=None, help='Device to use (cpu, cuda, 0, 1, etc.)')
    parser.add_argument('--project', type=str, default='runs/detect', help='Project directory')
    parser.add_argument('--name', type=str, default='fridge_detection', help='Experiment name')
    parser.add_argument('--eval-only', action='store_true', help='Only evaluate, do not train')
    parser.add_argument('--export', action='store_true', help='Export model after training')
    
    args = parser.parse_args()
    
    # Create trainer
    trainer = YOLOv8Trainer(args.config)
    
    # Override config with command line arguments
    if args.data:
        trainer.config['data'] = args.data
    if args.model:
        trainer.config['model'] = args.model
    if args.epochs:
        trainer.config['epochs'] = args.epochs
    if args.batch:
        trainer.config['batch'] = args.batch
    if args.imgsz:
        trainer.config['imgsz'] = args.imgsz
    if args.device:
        trainer.config['device'] = args.device
    if args.project:
        trainer.config['project'] = args.project
    if args.name:
        trainer.config['name'] = args.name
    
    try:
        if not args.eval_only:
            # Train the model
            trainer.train()
        
        # Evaluate the model
        trainer.evaluate('val')
        trainer.evaluate('test')
        
        # Export model if requested
        if args.export:
            trainer.export_model(['onnx', 'tflite'])
        
        logger.info("All tasks completed successfully!")
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise

if __name__ == "__main__":
    main()
