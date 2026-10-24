"""
Color Detector Module for Intelligent Industrial Robot Sorter (Phase 4)
Captures raw camera frames from /InspectionCamera in CoppeliaSim via ZeroMQ Remote API
and performs robust pixel-based HSV color classification (Red, Green, Blue) with OpenCV.
"""

import os
import math
from typing import Tuple, Dict, Any, Optional
from dataclasses import dataclass

import numpy as np
import cv2

import config.settings as cfg


@dataclass
class DetectionResult:
    """Encapsulates the vision detection outcome for an object."""
    detected: bool
    color: str                      # 'red', 'green', 'blue', 'unknown', or 'none'
    confidence: float               # 0.0 to 1.0
    contour_area: float             # Area in pixels
    center: Tuple[int, int]         # (cx, cy) pixel coordinates
    bbox: Tuple[int, int, int, int] # (x, y, w, h)
    aspect_ratio: float             # min(w,h) / max(w,h)
    purity: float                   # Color pixel purity within bbox
    annotated_frame: Optional[np.ndarray] = None


class ColorDetector:
    """
    Vision-based object detector and color classifier using OpenCV.
    Connects to the CoppeliaSim /InspectionCamera vision sensor.
    """

    # Calibrated OpenCV HSV thresholds [H: 0-180, S: 0-255, V: 0-255]
    # Rejects conveyor belts (S < 30, V ~ 70) and amber/yellow rails (H ~ 20-35)
    HSV_RANGES = {
        "red": [
            (np.array([0, 110, 70], dtype=np.uint8), np.array([10, 255, 255], dtype=np.uint8)),
            (np.array([170, 110, 70], dtype=np.uint8), np.array([180, 255, 255], dtype=np.uint8)),
        ],
        "green": [
            (np.array([45, 110, 70], dtype=np.uint8), np.array([85, 255, 255], dtype=np.uint8)),
        ],
        "blue": [
            (np.array([100, 110, 70], dtype=np.uint8), np.array([135, 255, 255], dtype=np.uint8)),
        ],
    }

    # BGR Display colors for visual annotations
    ANNOTATION_COLORS = {
        "red": (0, 0, 255),
        "green": (0, 220, 0),
        "blue": (255, 80, 0),
        "unknown": (0, 255, 255),
        "none": (180, 180, 180),
    }

    # Expected full-view block area in 128x128 resolution (~19x19 px = ~342 px)
    EXPECTED_BLOCK_AREA = 340.0
    MIN_CONTOUR_AREA = 120.0
    MAX_CONTOUR_AREA = 800.0

    def __init__(
        self,
        client: Any,
        sim: Any,
        camera_path: str = "/InspectionCamera",
        roi_bounds: Optional[Tuple[int, int, int, int]] = None,
    ):
        """
        Initializes the color detector.
        
        Args:
            client: RemoteAPIClient instance.
            sim: CoppeliaSim sim module.
            camera_path: Scene path to camera model or vision sensor.
            roi_bounds: Optional (xmin, ymin, xmax, ymax) pixel bounds for inspection zone.
                        Default: (15, 20, 95, 110) in 128x128 frame.
        """
        self.client = client
        self.sim = sim
        self.camera_path = camera_path
        self.sensor_handle = self._resolve_sensor_handle(camera_path)
        
        # Default ROI focused on the pickup station before the bumper
        # Excludes conveyor edges, background, and upstream trailing blocks
        self.roi_bounds = roi_bounds if roi_bounds is not None else (50, 20, 92, 110)

    def _resolve_sensor_handle(self, camera_path: str) -> int:
        """Resolves the actual vision sensor child within the camera hierarchy."""
        try:
            model_handle = self.sim.getObject(camera_path)
        except Exception as e:
            raise RuntimeError(f"Failed to find camera object at '{camera_path}': {e}")

        # Check if the model handle itself is a vision sensor
        if self.sim.getObjectType(model_handle) == self.sim.object_visionsensor_type:
            return model_handle

        # Search for vision sensor child (typically named 'camera')
        try:
            sensor = self.sim.getObject("./camera", {"proxy": model_handle})
            return sensor
        except Exception:
            # Fall back to searching objects in tree
            for obj in self.sim.getObjectsInTree(model_handle):
                if self.sim.getObjectType(obj) == self.sim.object_visionsensor_type:
                    return obj

        raise RuntimeError(f"No vision sensor found inside camera hierarchy at '{camera_path}'")

    def capture_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Captures an image frame from the CoppeliaSim vision sensor.
        
        Returns:
            (success, bgr_image): BGR image as uint8 NumPy array of shape (H, W, 3),
                                  or (False, None) on failure.
        """
        try:
            img_bytes, [w, h] = self.sim.getVisionSensorImg(self.sensor_handle)
            if not img_bytes or w <= 0 or h <= 0:
                return False, None

            raw_arr = np.frombuffer(img_bytes, dtype=np.uint8)
            expected_size = w * h * 3
            if raw_arr.size != expected_size:
                return False, None

            # Reshape buffer
            rgb_arr = raw_arr.reshape((h, w, 3))

            # CoppeliaSim stores images bottom-to-top; flip vertically
            rgb_flipped = np.flipud(rgb_arr)

            # Convert RGB to OpenCV BGR format
            bgr_frame = cv2.cvtColor(rgb_flipped, cv2.COLOR_RGB2BGR)
            return True, bgr_frame

        except Exception as err:
            print(f"[!] ColorDetector capture error: {err}")
            return False, None

    def get_color_mask(self, hsv_frame: np.ndarray, color_name: str) -> np.ndarray:
        """Computes a binary mask for the specified color name."""
        if color_name not in self.HSV_RANGES:
            raise ValueError(f"Unknown color '{color_name}'. Available: {list(self.HSV_RANGES.keys())}")

        mask = np.zeros(hsv_frame.shape[:2], dtype=np.uint8)
        for lower, upper in self.HSV_RANGES[color_name]:
            mask = cv2.bitwise_or(mask, cv2.inRange(hsv_frame, lower, upper))

        # Morphological opening to eliminate isolated noise pixels
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)
        return mask

    def detect_color(
        self,
        frame: Optional[np.ndarray] = None,
        annotate: bool = True,
    ) -> DetectionResult:
        """
        Performs robust color detection and classification on a camera frame.
        If frame is None, captures a fresh frame from the vision sensor.
        
        Returns:
            DetectionResult dataclass with classification, confidence, and metadata.
        """
        if frame is None:
            ok, frame = self.capture_frame()
            if not ok or frame is None:
                return DetectionResult(
                    detected=False,
                    color="none",
                    confidence=0.0,
                    contour_area=0.0,
                    center=(0, 0),
                    bbox=(0, 0, 0, 0),
                    aspect_ratio=0.0,
                    purity=0.0,
                    annotated_frame=None,
                )

        h, w = frame.shape[:2]

        # Apply ROI mask to restrict analysis to pickup station
        roi_mask = np.zeros((h, w), dtype=np.uint8)
        xmin, ymin, xmax, ymax = self.roi_bounds
        xmin, xmax = max(0, xmin), min(w, xmax)
        ymin, ymax = max(0, ymin), min(h, ymax)
        roi_mask[ymin:ymax, xmin:xmax] = 255

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        color_candidates: Dict[str, Dict[str, Any]] = {}

        for color_name in self.HSV_RANGES:
            full_mask = self.get_color_mask(hsv, color_name)
            masked = cv2.bitwise_and(full_mask, full_mask, mask=roi_mask)

            contours, _ = cv2.findContours(masked, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            valid_contours = [
                c for c in contours
                if self.MIN_CONTOUR_AREA <= cv2.contourArea(c) <= self.MAX_CONTOUR_AREA
            ]

            if valid_contours:
                best_c = max(valid_contours, key=cv2.contourArea)
                area = cv2.contourArea(best_c)
                bx, by, bw, bh = cv2.boundingRect(best_c)
                
                # Center from image moments
                M = cv2.moments(best_c)
                if M["m00"] > 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                else:
                    cx, cy = bx + bw // 2, by + bh // 2

                # Aspect ratio
                aspect = min(bw, bh) / max(1, max(bw, bh))

                # Color purity in bounding box
                bbox_mask_roi = masked[by : by + bh, bx : bx + bw]
                purity = float(np.count_nonzero(bbox_mask_roi)) / max(1, bw * bh)

                # Composite confidence score
                area_score = min(1.0, area / (self.EXPECTED_BLOCK_AREA * 0.75))
                conf = float(0.40 * area_score + 0.30 * purity + 0.30 * aspect)

                color_candidates[color_name] = {
                    "contour": best_c,
                    "area": area,
                    "bbox": (bx, by, bw, bh),
                    "center": (cx, cy),
                    "aspect_ratio": aspect,
                    "purity": purity,
                    "confidence": conf,
                }

        # Evaluate candidate colors
        if not color_candidates:
            # No color detected
            annotated = self._draw_annotation(frame, None) if annotate else None
            return DetectionResult(
                detected=False,
                color="none",
                confidence=0.0,
                contour_area=0.0,
                center=(0, 0),
                bbox=(0, 0, 0, 0),
                aspect_ratio=0.0,
                purity=0.0,
                annotated_frame=annotated,
            )

        # Check for ambiguity: if multiple colors have high confidence (> 0.6)
        sorted_candidates = sorted(
            color_candidates.items(),
            key=lambda item: item[1]["confidence"],
            reverse=True,
        )
        best_color, best_data = sorted_candidates[0]

        if len(sorted_candidates) > 1:
            second_color, second_data = sorted_candidates[1]
            if second_data["confidence"] > 0.65 and abs(best_data["confidence"] - second_data["confidence"]) < 0.15:
                # Ambiguous detection
                annotated = self._draw_annotation(frame, None, status_text="AMBIGUOUS") if annotate else None
                return DetectionResult(
                    detected=True,
                    color="unknown",
                    confidence=best_data["confidence"],
                    contour_area=best_data["area"],
                    center=best_data["center"],
                    bbox=best_data["bbox"],
                    aspect_ratio=best_data["aspect_ratio"],
                    purity=best_data["purity"],
                    annotated_frame=annotated,
                )

        annotated = self._draw_annotation(frame, (best_color, best_data)) if annotate else None

        return DetectionResult(
            detected=True,
            color=best_color,
            confidence=round(best_data["confidence"], 3),
            contour_area=round(best_data["area"], 1),
            center=best_data["center"],
            bbox=best_data["bbox"],
            aspect_ratio=round(best_data["aspect_ratio"], 3),
            purity=round(best_data["purity"], 3),
            annotated_frame=annotated,
        )

    def _draw_annotation(
        self,
        frame: np.ndarray,
        detection: Optional[Tuple[str, Dict[str, Any]]],
        status_text: Optional[str] = None,
    ) -> np.ndarray:
        """Renders bounding box, center dot, ROI boundary, and label on frame."""
        annotated = frame.copy()
        h, w = annotated.shape[:2]

        # Draw subtle ROI rectangle
        xmin, ymin, xmax, ymax = self.roi_bounds
        cv2.rectangle(annotated, (xmin, ymin), (xmax, ymax), (80, 80, 80), 1)

        if detection is not None:
            color_name, data = detection
            draw_color = self.ANNOTATION_COLORS.get(color_name, (0, 255, 255))
            bx, by, bw, bh = data["bbox"]
            cx, cy = data["center"]

            # Draw bounding box
            cv2.rectangle(annotated, (bx, by), (bx + bw, by + bh), draw_color, 2)
            # Draw centroid marker
            cv2.circle(annotated, (cx, cy), 3, (0, 255, 255), -1)

            label = f"{color_name.upper()} {int(data['confidence']*100)}%"
            cv2.putText(
                annotated,
                label,
                (bx, max(12, by - 4)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.35,
                draw_color,
                1,
                cv2.LINE_AA,
            )
        else:
            text = status_text if status_text else "EMPTY"
            cv2.putText(
                annotated,
                text,
                (xmin + 4, ymin + 14),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.35,
                (120, 120, 120),
                1,
                cv2.LINE_AA,
            )

        return annotated

    @staticmethod
    def save_image(img: np.ndarray, filepath: str) -> bool:
        """Saves an image frame to the filesystem."""
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        return cv2.imwrite(filepath, img)
