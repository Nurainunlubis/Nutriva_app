import cv2
import numpy as np
import pytesseract
import re
from typing import List

# Kalau di Windows dan tesseract belum masuk PATH, isi ini:
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def preprocess_for_ocr(image_bgr: np.ndarray) -> np.ndarray:
    """
    Preprocess yang cocok buat label gizi:
    - grayscale
    - upscale (biar font kecil kebaca)
    - CLAHE (naikin kontras)
    - adaptive threshold
    - morphology close (rapihin huruf)
    """
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)

    h, w = gray.shape[:2]
    if max(h, w) < 1200:
        gray = cv2.resize(gray, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC)

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)

    gray = cv2.bilateralFilter(gray, 7, 35, 35)

    thr = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31, 9
    )

    k = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    thr = cv2.morphologyEx(thr, cv2.MORPH_CLOSE, k, iterations=1)
    return thr

def run_ocr_from_array(image_bgr: np.ndarray) -> List[str]:
    proc = preprocess_for_ocr(image_bgr)

    config = r"--oem 3 --psm 6"
    data = pytesseract.image_to_data(proc, lang="eng", config=config, output_type=pytesseract.Output.DICT)

    words = []
    n = len(data["text"])
    for i in range(n):
        txt = (data["text"][i] or "").strip()
        conf = float(data["conf"][i]) if str(data["conf"][i]).isdigit() else -1

        # buang noise
        if conf < 35:
            continue
        if len(txt) < 2:
            continue

        txt = re.sub(r"\s+", " ", txt)
        words.append(txt)

    # gabung jadi 1 baris besar (lebih gampang diekstrak)
    return [" ".join(words)]