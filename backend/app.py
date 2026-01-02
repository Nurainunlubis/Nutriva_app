# app.py
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import cv2, os, uuid
import numpy as np

from services.ocr import run_ocr_from_array
from services.extract import extract_nutrition
from services.yolo import YoloService

app = FastAPI(title="API Deteksi Tabel Gizi", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/ping")
def ping():
    return {"ok": True, "message": "backend tersambung"}

YOLO_MODEL_PATH = "runs/detect/train6/weights/best.pt"
yolo = YoloService(
    model_path=YOLO_MODEL_PATH,
    imgsz=960,      # naikin biar box lebih presisi
    conf=0.25,
    iou=0.5,
    max_det=3
)

UPLOAD_DIR = "uploaded_images"
CROP_DIR = "cropped_images"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(CROP_DIR, exist_ok=True)

@app.post("/detect")
async def detect(file: UploadFile = File(...)):
    try:
        ext = os.path.splitext(file.filename)[1].lower()
        fname = f"{uuid.uuid4()}{ext}"
        fpath = os.path.join(UPLOAD_DIR, fname)

        contents = await file.read()
        with open(fpath, "wb") as f:
            f.write(contents)

        img = cv2.imread(fpath)
        if img is None:
            raise HTTPException(status_code=400, detail="File bukan gambar valid")

        det = yolo.detect_best_box(img)
        if det is None:
            return JSONResponse(content={
                "ok": False,
                "message": "Tabel gizi tidak terdeteksi",
                "texts": [],
                "nutrition": {}
            })

        box, score = det
        crop, padded_box = yolo.crop_with_padding(img, box, pad_ratio=0.10)

        crop_path = os.path.join(CROP_DIR, f"{uuid.uuid4()}.png")
        cv2.imwrite(crop_path, crop)

        texts = run_ocr_from_array(crop)

        # ✅ kalau extract_nutrition kamu support debug
        nutrition, debug = extract_nutrition(texts, return_debug=True)

        return JSONResponse(content={
            "ok": True,
            "yolo_conf": score,
            "box": padded_box,
            "crop_path": crop_path,
            "texts": texts,
            "debug": debug,
            "nutrition": nutrition
        })

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))