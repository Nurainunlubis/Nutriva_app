import cv2
import numpy as np
import pytesseract
import re
from typing import List, Dict, Optional, Tuple

# -----------------------------
# OCR PREPROCESS (boleh tetap)
# -----------------------------
def preprocess_for_ocr(image_bgr: np.ndarray) -> np.ndarray:
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


# ---------------------------------------------------------
# OCR: JANGAN BUANG TOKEN ANGKA MESKI CONF KECIL
# ---------------------------------------------------------
def run_ocr_from_array(image_bgr: np.ndarray) -> List[str]:
    proc = preprocess_for_ocr(image_bgr)

    config = r"--oem 3 --psm 6"
    data = pytesseract.image_to_data(
        proc, lang="eng", config=config, output_type=pytesseract.Output.DICT
    )

    lines_map = {}  # key: (block, par, line) -> list of (left, text)
    n = len(data["text"])

    for i in range(n):
        txt = (data["text"][i] or "").strip()
        if not txt:
            continue

        conf_raw = data["conf"][i]
        try:
            conf = float(conf_raw)
        except:
            conf = -1

        # KEEP token kalau:
        # - confidence cukup (>=20), ATAU
        # - token ada digit (biasanya angka gizi conf kecil)
        has_digit = any(ch.isdigit() for ch in txt)
        if conf < 20 and not has_digit:
            continue

        b = data.get("block_num", [0]*n)[i]
        p = data.get("par_num", [0]*n)[i]
        l = data.get("line_num", [0]*n)[i]
        left = data.get("left", [0]*n)[i]

        key = (b, p, l)
        lines_map.setdefault(key, []).append((left, txt))

    lines = []
    for key in sorted(lines_map.keys()):
        parts = [t for _, t in sorted(lines_map[key], key=lambda x: x[0])]
        line = " ".join(parts)
        line = re.sub(r"\s+", " ", line).strip()
        if line:
            lines.append(line)

    return lines