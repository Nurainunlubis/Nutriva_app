# backend/services/yolo.py
from ultralytics import YOLO
import numpy as np
import cv2

class YoloService:
    def __init__(self, model_path: str, imgsz: int = 640, conf: float = 0.4, iou: float = 0.5, max_det: int = 1):
        self.model = YOLO(model_path)
        self.imgsz = imgsz
        self.conf = conf
        self.iou = iou
        self.max_det = max_det

    def detect_best_box(self, bgr_img: np.ndarray):
        """
        Return best bbox [x1,y1,x2,y2] (int) based on highest confidence.
        """
        results = self.model.predict(
            source=bgr_img,
            imgsz=self.imgsz,
            conf=self.conf,
            iou=self.iou,
            max_det=self.max_det,
            verbose=False
        )
        r0 = results[0]
        if r0.boxes is None or len(r0.boxes) == 0:
            return None

        xyxy = r0.boxes.xyxy.cpu().numpy()   # (N,4)
        conf = r0.boxes.conf.cpu().numpy()   # (N,)
        best_i = int(np.argmax(conf))
        box = xyxy[best_i].astype(int).tolist()
        score = float(conf[best_i])
        return box, score

    def crop_with_padding(self, bgr_img: np.ndarray, box, pad_ratio: float = 0.06):
        """
        Crop bbox with padding. Returns (crop_bgr, padded_box)
        """
        H, W = bgr_img.shape[:2]
        x1, y1, x2, y2 = map(int, box)
        w, h = x2 - x1, y2 - y1
        pad = int(pad_ratio * max(w, h))

        x1p = max(0, x1 - pad)
        y1p = max(0, y1 - pad)
        x2p = min(W, x2 + pad)
        y2p = min(H, y2 + pad)

        crop = bgr_img[y1p:y2p, x1p:x2p]
        return crop, [x1p, y1p, x2p, y2p]