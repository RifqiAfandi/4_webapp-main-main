# counter/yolo_model.py
from functools import lru_cache
from ultralytics import YOLO
import cv2
import os
import numpy as np
import tifffile as tiff


@lru_cache(maxsize=1)
def get_model():
    model_path = "counter/semangka.pt"
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model {model_path} tidak ditemukan!")
    return YOLO(model_path)


def detect_semangka(image_path, conf=0.15):
    model = get_model()

    print(f"📸 Baca gambar: {image_path}")
    img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    if img is None:
        # fallback khusus TIFF
        print("⚠️ cv2.imread gagal, coba tifffile...")
        img = tiff.imread(image_path)
        img = np.array(img)

    # Kalau 2D (grayscale) → jadikan 3 channel
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    elif img.ndim == 3 and img.shape[2] == 4:
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    elif img.ndim == 3 and img.shape[2] > 4:
        # Ambil 3 channel pertama saja untuk YOLO
        img = img[:, :, :3]

    # Normalisasi ke uint8 kalau 16‑bit / lebih
    if img.dtype != np.uint8:
        img = img.astype(np.float32)
        img = img / img.max() * 255.0
        img = img.astype(np.uint8)

    print("🔍 Deteksi YOLO...")
    results = model.predict(source=img, iou=0.5, conf=conf, imgsz=1280, verbose=False)
    r0 = results[0]
    boxes = r0.boxes
    bboxes = boxes.xyxy.cpu().numpy().tolist() if boxes is not None else []

    out_dir = "media/orthophoto_boxes"
    os.makedirs(out_dir, exist_ok=True)

    base_name = os.path.basename(image_path)
    name, ext = os.path.splitext(base_name)
    out_name = f"{name}_detected{ext}"  # tambah _detected
    out_path = os.path.join(out_dir, out_name)

    for (x1, y1, x2, y2) in bboxes:
        cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 3)

    cv2.imwrite(out_path, img)
    print(f"✅ Simpan hasil: {out_path}")

    return len(bboxes), out_path, bboxes, []
