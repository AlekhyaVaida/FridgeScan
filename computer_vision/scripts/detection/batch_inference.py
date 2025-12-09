#!/usr/bin/env python3
"""
Batch Inference Pipeline for Fridge Object Detection
Combines detection, classification, and spoilage detection
"""

import os
import cv2
import json
import time
import argparse
from pathlib import Path
from typing import List, Dict, Optional, Union
import logging
import pandas as pd
from tqdm import tqdm

from enhanced_detection import EnhancedDetector
from app.infer_spoilage import classify_image

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BatchInferencePipeline:
    def __init__(self, 
                 detection_model: str,
                 conf_threshold: float = 0.25,
                 iou_threshold: float = 0.45,
                 spoilage_threshold: float = 0.01):
        """
        Initialize the batch inference pipeline
        
        Args:
            detection_model: Path to YOLOv8 detection model
            conf_threshold: Confidence threshold for detections
            iou_threshold: IoU threshold for NMS
            spoilage_threshold: Threshold for spoilage detection
        """
        self.detector = EnhancedDetector(detection_model, conf_threshold, iou_threshold)
        self.spoilage_threshold = spoilage_threshold
        self.results = []
        
    def process_single_image(self, 
                           image_path: str, 
                           save_crops: bool = False,
                           crop_dir: str = 'outputs/crops') -> Dict:
        """
        Process a single image through the complete pipeline
        
        Args:
            image_path: Path to input image
            save_crops: Whether to save cropped detections
            crop_dir: Directory to save crops
            
        Returns:
            Dictionary containing all results
        """
        try:
            # Object detection
            detections = self.detector.detect(
                image_path, 
                save_crops=save_crops, 
                crop_dir=crop_dir
            )
            
            # Process each detection
            processed_detections = []
            for detection in detections:
                # Check spoilage if crop exists
                spoilage_status = "unknown"
                spoilage_confidence = 0.0
                
                if 'crop_path' in detection and os.path.exists(detection['crop_path']):
                    try:
                        spoilage_status, spoilage_confidence = classify_image(
                            detection['crop_path'], 
                            threshold=self.spoilage_threshold
                        )
                    except Exception as e:
                        logger.warning(f"Spoilage detection failed for {detection['crop_path']}: {str(e)}")
                
                processed_detection = {
                    'class_name': detection['class_name'],
                    'class_id': detection['class_id'],
                    'confidence': detection['confidence'],
                    'bbox': detection['bbox'],
                    'area': detection['area'],
                    'spoilage_status': spoilage_status,
                    'spoilage_confidence': spoilage_confidence,
                    'crop_path': detection.get('crop_path', '')
                }
                processed_detections.append(processed_detection)
            
            # Create result for this image
            result = {
                'image_path': image_path,
                'image_name': os.path.basename(image_path),
                'timestamp': time.time(),
                'num_detections': len(processed_detections),
                'detections': processed_detections,
                'summary': self._create_summary(processed_detections)
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to process image {image_path}: {str(e)}")
            return {
                'image_path': image_path,
                'image_name': os.path.basename(image_path),
                'timestamp': time.time(),
                'error': str(e),
                'num_detections': 0,
                'detections': [],
                'summary': {}
            }
    
    def _create_summary(self, detections: List[Dict]) -> Dict:
        """Create summary statistics for detections"""
        if not detections:
            return {
                'total_items': 0,
                'unique_classes': 0,
                'avg_confidence': 0.0,
                'fresh_items': 0,
                'spoiled_items': 0,
                'unknown_status': 0,
                'class_counts': {},
                'spoilage_breakdown': {}
            }
        
        class_counts = {}
        spoilage_counts = {'fresh': 0, 'spoiled': 0, 'unknown': 0}
        confidences = []
        
        for detection in detections:
            class_name = detection['class_name']
            spoilage_status = detection['spoilage_status']
            confidence = detection['confidence']
            
            class_counts[class_name] = class_counts.get(class_name, 0) + 1
            spoilage_counts[spoilage_status] = spoilage_counts.get(spoilage_status, 0) + 1
            confidences.append(confidence)
        
        return {
            'total_items': len(detections),
            'unique_classes': len(class_counts),
            'avg_confidence': sum(confidences) / len(confidences) if confidences else 0.0,
            'fresh_items': spoilage_counts['fresh'],
            'spoiled_items': spoilage_counts['spoiled'],
            'unknown_status': spoilage_counts['unknown'],
            'class_counts': class_counts,
            'spoilage_breakdown': spoilage_counts
        }
    
    def process_batch(self, 
                     input_path: Union[str, List[str]], 
                     output_dir: str = 'outputs/batch_results',
                     save_crops: bool = True,
                     save_visualizations: bool = True,
                     save_json: bool = True,
                     save_csv: bool = True) -> List[Dict]:
        """
        Process a batch of images
        
        Args:
            input_path: Path to image directory or list of image paths
            output_dir: Directory to save results
            save_crops: Whether to save cropped detections
            save_visualizations: Whether to save visualization images
            save_json: Whether to save results as JSON
            save_csv: Whether to save results as CSV
            
        Returns:
            List of result dictionaries
        """
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Get list of images to process
        if isinstance(input_path, str):
            if os.path.isdir(input_path):
                image_paths = []
                for ext in ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.tiff']:
                    image_paths.extend(Path(input_path).glob(ext))
                    image_paths.extend(Path(input_path).glob(ext.upper()))
                image_paths = [str(p) for p in image_paths]
            else:
                image_paths = [input_path]
        else:
            image_paths = input_path
        
        if not image_paths:
            logger.warning("No images found to process")
            return []
        
        logger.info(f"Processing {len(image_paths)} images...")
        
        # Process each image
        results = []
        crop_dir = str(output_path / 'crops')
        
        for image_path in tqdm(image_paths, desc="Processing images"):
            result = self.process_single_image(
                str(image_path), 
                save_crops=save_crops, 
                crop_dir=crop_dir
            )
            results.append(result)
            
            # Save visualization if requested
            if save_visualizations and 'error' not in result:
                try:
                    vis_img = self.detector.visualize_detections(str(image_path), result['detections'])
                    vis_path = output_path / 'visualizations' / f"vis_{result['image_name']}"
                    vis_path.parent.mkdir(exist_ok=True)
                    cv2.imwrite(str(vis_path), vis_img)
                except Exception as e:
                    logger.warning(f"Failed to save visualization for {image_path}: {str(e)}")
        
        # Save results
        if save_json:
            json_path = output_path / 'results.json'
            with open(json_path, 'w') as f:
                json.dump(results, f, indent=2)
            logger.info(f"Results saved to: {json_path}")
        
        if save_csv:
            self._save_csv_results(results, output_path / 'results.csv')
        
        # Save summary
        self._save_summary(results, output_path / 'summary.json')
        
        self.results = results
        return results
    
    def _save_csv_results(self, results: List[Dict], csv_path: Path):
        """Save results as CSV file"""
        try:
            rows = []
            for result in results:
                if 'error' in result:
                    continue
                
                for detection in result['detections']:
                    row = {
                        'image_name': result['image_name'],
                        'image_path': result['image_path'],
                        'timestamp': result['timestamp'],
                        'class_name': detection['class_name'],
                        'class_id': detection['class_id'],
                        'confidence': detection['confidence'],
                        'bbox_x1': detection['bbox'][0],
                        'bbox_y1': detection['bbox'][1],
                        'bbox_x2': detection['bbox'][2],
                        'bbox_y2': detection['bbox'][3],
                        'area': detection['area'],
                        'spoilage_status': detection['spoilage_status'],
                        'spoilage_confidence': detection['spoilage_confidence'],
                        'crop_path': detection['crop_path']
                    }
                    rows.append(row)
            
            if rows:
                df = pd.DataFrame(rows)
                df.to_csv(csv_path, index=False)
                logger.info(f"CSV results saved to: {csv_path}")
            
        except Exception as e:
            logger.error(f"Failed to save CSV results: {str(e)}")
    
    def _save_summary(self, results: List[Dict], summary_path: Path):
        """Save overall summary statistics"""
        try:
            total_images = len(results)
            successful_images = len([r for r in results if 'error' not in r])
            failed_images = total_images - successful_images
            
            total_detections = sum(r.get('num_detections', 0) for r in results)
            
            # Aggregate statistics
            all_class_counts = {}
            all_spoilage_counts = {'fresh': 0, 'spoiled': 0, 'unknown': 0}
            all_confidences = []
            
            for result in results:
                if 'error' in result:
                    continue
                
                for detection in result['detections']:
                    class_name = detection['class_name']
                    spoilage_status = detection['spoilage_status']
                    confidence = detection['confidence']
                    
                    all_class_counts[class_name] = all_class_counts.get(class_name, 0) + 1
                    all_spoilage_counts[spoilage_status] = all_spoilage_counts.get(spoilage_status, 0) + 1
                    all_confidences.append(confidence)
            
            summary = {
                'processing_info': {
                    'total_images': total_images,
                    'successful_images': successful_images,
                    'failed_images': failed_images,
                    'success_rate': successful_images / total_images if total_images > 0 else 0
                },
                'detection_stats': {
                    'total_detections': total_detections,
                    'avg_detections_per_image': total_detections / successful_images if successful_images > 0 else 0,
                    'unique_classes_detected': len(all_class_counts),
                    'avg_confidence': sum(all_confidences) / len(all_confidences) if all_confidences else 0
                },
                'class_distribution': all_class_counts,
                'spoilage_distribution': all_spoilage_counts,
                'confidence_stats': {
                    'min': min(all_confidences) if all_confidences else 0,
                    'max': max(all_confidences) if all_confidences else 0,
                    'mean': sum(all_confidences) / len(all_confidences) if all_confidences else 0
                }
            }
            
            with open(summary_path, 'w') as f:
                json.dump(summary, f, indent=2)
            
            logger.info(f"Summary saved to: {summary_path}")
            
        except Exception as e:
            logger.error(f"Failed to save summary: {str(e)}")

def main():
    """Example usage of BatchInferencePipeline"""
    parser = argparse.ArgumentParser(description='Batch inference pipeline for fridge detection')
    parser.add_argument('--model', type=str, required=True, help='Path to YOLOv8 model')
    parser.add_argument('--input', type=str, required=True, help='Path to input image or directory')
    parser.add_argument('--output', type=str, default='outputs/batch_results', help='Output directory')
    parser.add_argument('--conf', type=float, default=0.25, help='Confidence threshold')
    parser.add_argument('--iou', type=float, default=0.45, help='IoU threshold for NMS')
    parser.add_argument('--spoilage-threshold', type=float, default=0.01, help='Spoilage detection threshold')
    parser.add_argument('--no-crops', action='store_true', help='Do not save cropped detections')
    parser.add_argument('--no-vis', action='store_true', help='Do not save visualization images')
    parser.add_argument('--no-json', action='store_true', help='Do not save JSON results')
    parser.add_argument('--no-csv', action='store_true', help='Do not save CSV results')
    
    args = parser.parse_args()
    
    # Create pipeline
    pipeline = BatchInferencePipeline(
        detection_model=args.model,
        conf_threshold=args.conf,
        iou_threshold=args.iou,
        spoilage_threshold=args.spoilage_threshold
    )
    
    # Process batch
    results = pipeline.process_batch(
        input_path=args.input,
        output_dir=args.output,
        save_crops=not args.no_crops,
        save_visualizations=not args.no_vis,
        save_json=not args.no_json,
        save_csv=not args.no_csv
    )
    
    # Print summary
    if results:
        successful = len([r for r in results if 'error' not in r])
        total_detections = sum(r.get('num_detections', 0) for r in results)
        
        print(f"\n✅ Batch processing completed!")
        print(f"Images processed: {len(results)}")
        print(f"Successful: {successful}")
        print(f"Failed: {len(results) - successful}")
        print(f"Total detections: {total_detections}")
        print(f"Results saved to: {args.output}")

if __name__ == "__main__":
    main()
