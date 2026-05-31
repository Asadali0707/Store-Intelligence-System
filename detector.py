"""
vision/detector.py — YOLOv8n person detector via ONNX Runtime
"""
import numpy as np
import cv2
import onnxruntime as ort
from dataclasses import dataclass
from typing import List


@dataclass
class Detection:
    bbox: tuple[float, float, float, float]  # x1,y1,x2,y2
    confidence: float
    class_id: int


class PersonDetector:
    """
    Wraps YOLOv8n ONNX model for person-only detection.
    Runs on CPU via ONNX Runtime — no GPU required.
    """

    PERSON_CLASS = 0
    INPUT_SIZE = (640, 640)

    def __init__(
        self,
        model_path: str = "models/yolov8n.onnx",
        conf_threshold: float = 0.45,
        iou_threshold: float = 0.5,
    ):
        self.conf_thresh = conf_threshold
        self.iou_thresh = iou_threshold
        self.session = ort.InferenceSession(
            model_path,
            providers=["CPUExecutionProvider"],
        )
        self.input_name = self.session.get_inputs()[0].name

    def preprocess(self, frame: np.ndarray) -> np.ndarray:
        """Resize, normalize, and add batch dimension."""
        img = cv2.resize(frame, self.INPUT_SIZE)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = img.astype(np.float32) / 255.0
        img = np.transpose(img, (2, 0, 1))  # HWC → CHW
        return np.expand_dims(img, 0)        # add batch dim

    def postprocess(self, output: np.ndarray, orig_shape: tuple) -> List[Detection]:
        """Apply NMS and filter to person class only."""
        h, w = orig_shape[:2]
        sx = w / self.INPUT_SIZE[0]
        sy = h / self.INPUT_SIZE[1]

        # YOLOv8 output: [1, 84, 8400] → transpose → [8400, 84]
        preds = np.squeeze(output[0]).T
        detections = []

        for pred in preds:
            scores = pred[4:]
            class_id = int(np.argmax(scores))
            conf = float(scores[class_id])
            if class_id != self.PERSON_CLASS or conf < self.conf_thresh:
                continue
            cx, cy, bw, bh = pred[:4]
            x1 = (cx - bw / 2) * sx
            y1 = (cy - bh / 2) * sy
            x2 = (cx + bw / 2) * sx
            y2 = (cy + bh / 2) * sy
            detections.append(Detection((x1, y1, x2, y2), conf, class_id))

        # Apply NMS
        boxes  = [list(d.bbox) for d in detections]
        scores = [d.confidence for d in detections]
        idxs   = cv2.dnn.NMSBoxes(boxes, scores, self.conf_thresh, self.iou_thresh)
        return [detections[i] for i in idxs.flatten()] if len(idxs) > 0 else []

    def detect(self, frame: np.ndarray) -> List[Detection]:
        inp = self.preprocess(frame)
        out = self.session.run(None, {self.input_name: inp})
        return self.postprocess(out, frame.shape)
