import cv2
import numpy as np
from ultralytics import YOLO
from pathlib import Path
from typing import Dict, List

MODEL_PATH = Path("backend/models/yolov8m-pose.pt")

class PoseDetector:
    def __init__(self):
        self.model = None
        self.load_model()

    def load_model(self):
        """Load YOLOv8 pose model"""
        if not MODEL_PATH.exists():
            print(f"Model file not found at {MODEL_PATH}")
            return

        self.model = YOLO(str(MODEL_PATH))

    def detect_pose(self, image_bytes: bytes) -> Dict:
        """Detect pose from image bytes"""
        if self.model is None:
            return {"joints": [], "metrics": {}}

        # Decode image
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if image is None:
            return {"joints": [], "metrics": {}}

        # Run detection
        results = self.model(image, verbose=False)

        if not results or len(results) == 0:
            return {"joints": [], "metrics": {}}

        result = results[0]

        # Get keypoints if detected
        if result.keypoints is None:
            return {"joints": [], "metrics": {}}

        keypoints = result.keypoints.xyn.cpu().numpy()[0]  # Normalized coordinates

        # Convert to joint data
        joints = []
        joint_names = [
            "nose", "left_eye", "right_eye", "left_ear", "right_ear",
            "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
            "left_wrist", "right_wrist", "left_hip", "right_hip",
            "left_knee", "right_knee", "left_ankle", "right_ankle"
        ]

        for i, (x, y, conf) in enumerate(keypoints):
            if conf > 0.5:  # Confidence threshold
                joints.append({
                    "name": joint_names[i],
                    "x": float(x),
                    "y": float(y),
                    "confidence": float(conf)
                })

        # Calculate basic metrics
        metrics = self._calculate_metrics(joints)

        return {"joints": joints, "metrics": metrics}

    def _calculate_metrics(self, joints: List[Dict]) -> Dict:
        """Calculate movement metrics from joints"""
        metrics = {
            "leanAngle": 0.0,
            "limbSpeed": 0.0,
            "rangeOfMotion": 0.0
        }

        # Find key joints
        joints_dict = {j["name"]: j for j in joints}

        if "left_shoulder" in joints_dict and "left_hip" in joints_dict:
            # Calculate body lean angle
            shoulder = joints_dict["left_shoulder"]
            hip = joints_dict["left_hip"]

            # Simple vertical angle from hip to shoulder
            dx = shoulder["x"] - hip["x"]
            dy = shoulder["y"] - hip["y"]

            if dy != 0:
                angle = np.degrees(np.arctan2(dx, dy))
                metrics["leanAngle"] = abs(angle)

        return metrics