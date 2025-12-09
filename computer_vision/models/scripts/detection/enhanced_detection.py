#!/usr/bin/env python3
"""
Enhanced Object Detection with Proper Post-Processing
Based on Maryam's implementation and industry best practices
"""

import cv2
import numpy as np
import torch
from ultralytics import YOLO
import os
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Union
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EnhancedDetector:
    def __init__(self, model_path: str, conf_threshold: float = 0.25, iou_threshold: float = 0.45):
        """
        Initialize the enhanced detector
        
        Args:
            model_path: Path to the YOLOv8 model
            conf_threshold: Confidence threshold for detections
            iou_threshold: IoU threshold for NMS
        """
        self.model_path = model_path
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.model = None
        self.class_names = None
        
        self._load_model()
    
    def _load_model(self):
        """Load the YOLOv8 model and class names"""
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
    
    def preprocess_image(self, image: Union[str, np.ndarray], target_size: int = 640) -> Tuple[np.ndarray, Tuple[int, int]]:
        """
        Preprocess image for YOLOv8 inference
        
        Args:
            image: Image path or numpy array
            target_size: Target image size for inference
            
        Returns:
            Preprocessed image and original dimensions
        """
        if isinstance(image, str):
            if not os.path.exists(image):
                raise FileNotFoundError(f"Image file not found: {image}")
            img = cv2.imread(image)
            if img is None:
                raise ValueError(f"Could not load image: {image}")
        else:
            img = image.copy()
        
        # Store original dimensions
        original_h, original_w = img.shape[:2]
        
        # Resize image while maintaining aspect ratio
        img_resized = cv2.resize(img, (target_size, target_size))
        
        # Convert BGR to RGB
        img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)
        
        return img_rgb, (original_h, original_w)
    
    def postprocess_detections(self, 
                             raw_output: np.ndarray, 
                             original_shape: Tuple[int, int],
                             conf_threshold: Optional[float] = None) -> List[Dict]:
        """
        Post-process YOLOv8 raw output with proper NMS
        
        Args:
            raw_output: Raw model output (1, 84, 8400) for YOLOv8n
            original_shape: Original image dimensions (height, width)
            conf_threshold: Confidence threshold (uses instance default if None)
            
        Returns:
            List of detection dictionaries
        """
        if conf_threshold is None:
            conf_threshold = self.conf_threshold
        
        # Remove batch dimension and transpose: (8400, 84)
        raw_output = np.squeeze(raw_output).T
        
        # Extract boxes, objectness, and class probabilities
        boxes = raw_output[:, :4]  # [x_center, y_center, width, height]
        objectness = raw_output[:, 4]  # Objectness score
        class_probs = raw_output[:, 5:]  # Class probabilities
        
        # Apply sigmoid to get probabilities
        objectness_scores = 1 / (1 + np.exp(-objectness))
        class_probabilities = 1 / (1 + np.exp(-class_probs))
        
        # Combine objectness with class probabilities
        scores = objectness_scores[:, np.newaxis] * class_probabilities
        
        # Get best class for each detection
        class_ids = np.argmax(scores, axis=1)
        confidences = np.max(scores, axis=1)
        
        # Filter by confidence threshold
        mask = confidences > conf_threshold
        boxes = boxes[mask]
        confidences = confidences[mask]
        class_ids = class_ids[mask]
        
        if len(boxes) == 0:
            return []
        
        # Convert from center format to corner format
        x_center, y_center, width, height = boxes.T
        x1 = x_center - width / 2
        y1 = y_center - height / 2
        x2 = x_center + width / 2
        y2 = y_center + height / 2
        
        # Scale boxes back to original image size
        orig_h, orig_w = original_shape
        scale_x = orig_w / 640  # Assuming 640x640 input
        scale_y = orig_h / 640
        
        x1 = (x1 * scale_x).astype(int)
        y1 = (y1 * scale_y).astype(int)
        x2 = (x2 * scale_x).astype(int)
        y2 = (y2 * scale_y).astype(int)
        
        # Ensure boxes are within image bounds
        x1 = np.clip(x1, 0, orig_w)
        y1 = np.clip(y1, 0, orig_h)
        x2 = np.clip(x2, 0, orig_w)
        y2 = np.clip(y2, 0, orig_h)
        
        # Apply Non-Maximum Suppression
        boxes_xyxy = np.column_stack([x1, y1, x2, y2])
        indices = cv2.dnn.NMSBoxes(
            boxes_xyxy.tolist(), 
            confidences.tolist(), 
            conf_threshold, 
            self.iou_threshold
        )
        
        if len(indices) == 0:
            return []
        
        # Extract final detections
        detections = []
        for i in indices.flatten():
            detection = {
                'bbox': [int(x1[i]), int(y1[i]), int(x2[i]), int(y2[i])],
                'confidence': float(confidences[i]),
                'class_id': int(class_ids[i]),
                'class_name': self.class_names[class_ids[i]],
                'area': int((x2[i] - x1[i]) * (y2[i] - y1[i]))
            }
            detections.append(detection)
        
        return detections
    
    def detect(self, 
               image: Union[str, np.ndarray], 
               conf_threshold: Optional[float] = None,
               save_crops: bool = False,
               crop_dir: str = 'outputs/crops') -> List[Dict]:
        """
        Detect objects in image with enhanced post-processing
        
        Args:
            image: Image path or numpy array
            conf_threshold: Confidence threshold for detections
            save_crops: Whether to save cropped detections
            crop_dir: Directory to save crops
            
        Returns:
            List of detection dictionaries
        """
        try:
            # Preprocess image
            img_processed, original_shape = self.preprocess_image(image)
            
            # Run inference
            results = self.model(img_processed, verbose=False)
            
            # Extract raw output
            raw_output = results[0].boxes.data.cpu().numpy()
            
            # Post-process detections
            detections = self.postprocess_detections(
                raw_output, 
                original_shape, 
                conf_threshold
            )
            
            # Save crops if requested
            if save_crops and detections:
                self._save_crops(image, detections, crop_dir)
            
            logger.info(f"Detected {len(detections)} objects")
            return detections
            
        except Exception as e:
            logger.error(f"Detection failed: {str(e)}")
            raise
    
    def _save_crops(self, image: Union[str, np.ndarray], detections: List[Dict], crop_dir: str):
        """Save cropped detections to disk"""
        try:
            os.makedirs(crop_dir, exist_ok=True)
            
            if isinstance(image, str):
                img = cv2.imread(image)
            else:
                img = image.copy()
            
            for i, detection in enumerate(detections):
                x1, y1, x2, y2 = detection['bbox']
                crop = img[y1:y2, x1:x2]
                
                if crop.size > 0:  # Ensure crop is not empty
                    crop_filename = f"{detection['class_name']}_{i}_{detection['confidence']:.2f}.jpg"
                    crop_path = os.path.join(crop_dir, crop_filename)
                    cv2.imwrite(crop_path, crop)
                    detection['crop_path'] = crop_path
            
        except Exception as e:
            logger.warning(f"Failed to save crops: {str(e)}")
    
    def visualize_detections(self, 
                           image: Union[str, np.ndarray], 
                           detections: List[Dict],
                           show_conf: bool = True,
                           show_labels: bool = True,
                           thickness: int = 2) -> np.ndarray:
        """
        Visualize detections on image
        
        Args:
            image: Image path or numpy array
            detections: List of detection dictionaries
            show_conf: Whether to show confidence scores
            show_labels: Whether to show class labels
            thickness: Line thickness for bounding boxes
            
        Returns:
            Image with drawn detections
        """
        if isinstance(image, str):
            img = cv2.imread(image)
        else:
            img = image.copy()
        
        # Define colors for different classes
        colors = self._generate_colors(len(self.class_names))
        
        for detection in detections:
            x1, y1, x2, y2 = detection['bbox']
            class_id = detection['class_id']
            confidence = detection['confidence']
            class_name = detection['class_name']
            
            # Get color for this class
            color = colors[class_id % len(colors)]
            
            # Draw bounding box
            cv2.rectangle(img, (x1, y1), (x2, y2), color, thickness)
            
            # Prepare label
            label = ""
            if show_labels:
                label += class_name
            if show_conf:
                if label:
                    label += f" {confidence:.2f}"
                else:
                    label = f"{confidence:.2f}"
            
            # Draw label background
            if label:
                (label_width, label_height), _ = cv2.getTextSize(
                    label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
                )
                cv2.rectangle(
                    img, 
                    (x1, y1 - label_height - 10), 
                    (x1 + label_width, y1), 
                    color, 
                    -1
                )
                
                # Draw label text
                cv2.putText(
                    img, 
                    label, 
                    (x1, y1 - 5), 
                    cv2.FONT_HERSHEY_SIMPLEX, 
                    0.5, 
                    (255, 255, 255), 
                    1
                )
        
        return img
    
    def _generate_colors(self, num_classes: int) -> List[Tuple[int, int, int]]:
        """Generate distinct colors for different classes"""
        colors = []
        for i in range(num_classes):
            hue = int(180 * i / num_classes)
            color = cv2.cvtColor(np.uint8([[[hue, 255, 255]]]), cv2.COLOR_HSV2BGR)[0][0]
            colors.append(tuple(map(int, color)))
        return colors
    
    def get_detection_summary(self, detections: List[Dict]) -> Dict:
        """Get summary statistics of detections"""
        if not detections:
            return {
                'total_detections': 0,
                'unique_classes': 0,
                'avg_confidence': 0.0,
                'class_counts': {},
                'confidence_range': (0.0, 0.0)
            }
        
        class_counts = {}
        confidences = []
        
        for detection in detections:
            class_name = detection['class_name']
            confidence = detection['confidence']
            
            class_counts[class_name] = class_counts.get(class_name, 0) + 1
            confidences.append(confidence)
        
        return {
            'total_detections': len(detections),
            'unique_classes': len(class_counts),
            'avg_confidence': np.mean(confidences),
            'class_counts': class_counts,
            'confidence_range': (min(confidences), max(confidences))
        }

def main():
    """Example usage of EnhancedDetector"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Enhanced Object Detection')
    parser.add_argument('--model', type=str, required=True, help='Path to YOLOv8 model')
    parser.add_argument('--image', type=str, required=True, help='Path to input image')
    parser.add_argument('--conf', type=float, default=0.25, help='Confidence threshold')
    parser.add_argument('--iou', type=float, default=0.45, help='IoU threshold for NMS')
    parser.add_argument('--save-crops', action='store_true', help='Save cropped detections')
    parser.add_argument('--output', type=str, help='Output image path')
    parser.add_argument('--show', action='store_true', help='Show result image')
    
    args = parser.parse_args()
    
    # Create detector
    detector = EnhancedDetector(args.model, args.conf, args.iou)
    
    # Run detection
    detections = detector.detect(args.image, save_crops=args.save_crops)
    
    # Print results
    print(f"\nDetected {len(detections)} objects:")
    for i, detection in enumerate(detections):
        print(f"{i+1}. {detection['class_name']} (conf: {detection['confidence']:.3f})")
    
    # Get summary
    summary = detector.get_detection_summary(detections)
    print(f"\nSummary:")
    print(f"Total detections: {summary['total_detections']}")
    print(f"Unique classes: {summary['unique_classes']}")
    print(f"Average confidence: {summary['avg_confidence']:.3f}")
    print(f"Class counts: {summary['class_counts']}")
    
    # Visualize and save/show result
    if args.output or args.show:
        result_img = detector.visualize_detections(args.image, detections)
        
        if args.output:
            cv2.imwrite(args.output, result_img)
            print(f"Result saved to: {args.output}")
        
        if args.show:
            cv2.imshow('Detection Result', result_img)
            cv2.waitKey(0)
            cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
