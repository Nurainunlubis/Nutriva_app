import cv2

def detect_table(image_path):
    """
    Deteksi kotak tabel sederhana pakai OpenCV.
    Mengembalikan list kotak (x1, y1, x2, y2)
    """
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    boxes = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        boxes.append({"x1": x, "y1": y, "x2": x+w, "y2": y+h})

    return boxes
