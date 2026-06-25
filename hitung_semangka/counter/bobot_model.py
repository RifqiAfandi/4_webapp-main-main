# counter/bobot_model.py
from functools import lru_cache
from ultralytics import YOLO
import cv2
import os
import numpy as np
import tifffile as tiff

# ── Robust Mapping kelas / range berat ke info standar ────────────────────────
BOBOT_MAP = {
    # Format 1: Model mengembalikan nama kelas 'kelas1', 'kelas2', dst. (seperti plan/best.pt)
    "kelas1": {"id": 1, "range": "< 2.0 kg", "warna_marker": "Ungu", "warna_bgr": (182, 89, 155)},
    "kelas2": {"id": 2, "range": "2.0 - 2.5 kg", "warna_marker": "Tosca", "warna_bgr": (180, 200, 0)},
    "kelas3": {"id": 3, "range": "2.6 - 3.0 kg", "warna_marker": "Orange", "warna_bgr": (0, 165, 255)},
    "kelas4": {"id": 4, "range": "3.1 - 4.0 kg", "warna_marker": "Putih", "warna_bgr": (220, 220, 220)},
    "kelas5": {"id": 5, "range": "4.1 - 5.0 kg", "warna_marker": "Biru Navy", "warna_bgr": (128, 0, 0)},
    "kelas6": {"id": 6, "range": "5.1 - 6.0 kg", "warna_marker": "Merah", "warna_bgr": (0, 0, 200)},
    "kelas7": {"id": 7, "range": "6.1 - 7.5 kg", "warna_marker": "Kuning", "warna_bgr": (0, 215, 255)},
    "kelas8": {"id": 8, "range": "> 7.5 kg", "warna_marker": "Hitam", "warna_bgr": (0, 0, 0)},
    
    # Format 2: Model mengembalikan string berat langsung (seperti counter/bobot.pt)
    "<2.0 kg": {"id": 1, "range": "< 2.0 kg", "warna_marker": "Ungu", "warna_bgr": (182, 89, 155)},
    "< 2.0 kg": {"id": 1, "range": "< 2.0 kg", "warna_marker": "Ungu", "warna_bgr": (182, 89, 155)},
    "< 2,0 kg": {"id": 1, "range": "< 2.0 kg", "warna_marker": "Ungu", "warna_bgr": (182, 89, 155)},
    "2.0-2.5 kg": {"id": 2, "range": "2.0 - 2.5 kg", "warna_marker": "Tosca", "warna_bgr": (180, 200, 0)},
    "2,0 - 2,5 kg": {"id": 2, "range": "2.0 - 2.5 kg", "warna_marker": "Tosca", "warna_bgr": (180, 200, 0)},
    "2.6-3.0 kg": {"id": 3, "range": "2.6 - 3.0 kg", "warna_marker": "Orange", "warna_bgr": (0, 165, 255)},
    "2,6 - 3,0 kg": {"id": 3, "range": "2.6 - 3.0 kg", "warna_marker": "Orange", "warna_bgr": (0, 165, 255)},
    "3.1-4.0 kg": {"id": 4, "range": "3.1 - 4.0 kg", "warna_marker": "Putih", "warna_bgr": (220, 220, 220)},
    "3,1 - 4,0 kg": {"id": 4, "range": "3.1 - 4.0 kg", "warna_marker": "Putih", "warna_bgr": (220, 220, 220)},
    "4.1-5.0 kg": {"id": 5, "range": "4.1 - 5.0 kg", "warna_marker": "Biru Navy", "warna_bgr": (128, 0, 0)},
    "4,1 - 5,0 kg": {"id": 5, "range": "4.1 - 5.0 kg", "warna_marker": "Biru Navy", "warna_bgr": (128, 0, 0)},
    "5.1-6.0 kg": {"id": 6, "range": "5.1 - 6.0 kg", "warna_marker": "Merah", "warna_bgr": (0, 0, 200)},
    "5,1 - 6,0 kg": {"id": 6, "range": "5.1 - 6.0 kg", "warna_marker": "Merah", "warna_bgr": (0, 0, 200)},
    "6.1-7.5 kg": {"id": 7, "range": "6.1 - 7.5 kg", "warna_marker": "Kuning", "warna_bgr": (0, 215, 255)},
    "6,1 - 7,5 kg": {"id": 7, "range": "6.1 - 7.5 kg", "warna_marker": "Kuning", "warna_bgr": (0, 215, 255)},
    ">7.5 kg": {"id": 8, "range": "> 7.5 kg", "warna_marker": "Hitam", "warna_bgr": (0, 0, 0)},
    "> 7.5 kg": {"id": 8, "range": "> 7.5 kg", "warna_marker": "Hitam", "warna_bgr": (0, 0, 0)},
}

# Untuk backward compatibility (jika ada kode lain yang mengakses dictionary lama secara langsung)
WARNA_KELAS = {k: v["warna_bgr"] for k, v in BOBOT_MAP.items() if "warna_bgr" in v}
WARNA_MARKER = {k: v["warna_marker"] for k, v in BOBOT_MAP.items() if "warna_marker" in v}


@lru_cache(maxsize=1)
def get_bobot_model():
    candidates = [
        "counter/bobot.pt",
        os.path.join(os.path.dirname(__file__), "bobot.pt"),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "bobot.pt"),
        "bobot.pt"
    ]
    model_path = None
    for path in candidates:
        if os.path.exists(path):
            model_path = path
            break
    if not model_path:
        raise FileNotFoundError(f"Model bobot.pt tidak ditemukan di kandidat lokasi: {candidates}")
    return YOLO(model_path)


def _load_image(image_path: str) -> np.ndarray:
    """Baca gambar, tangani TIFF, grayscale, BGRA, 16-bit secara robust."""
    img = None
    try:
        # PENTING: ultralytics memodifikasi cv2.imread secara internal,
        # sehingga cv2.imread dapat memicu ValueError saat membaca TIFF multiband/multiframe.
        img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    except Exception as e:
        print(f"⚠️ cv2.imread gagal atau memicu exception: {e}. Menggunakan fallback.")

    if img is None:
        try:
            print("Trying tiff.imread fallback...")
            img = tiff.imread(image_path)
            img = np.array(img)
        except Exception as e2:
            print(f"⚠️ tifffile gagal: {e2}. Menggunakan fallback PIL.Image.")
            from PIL import Image
            img = Image.open(image_path)
            img = np.array(img)

    if img.ndim == 3 and img.shape[0] < 10 and img.shape[1] > img.shape[0]:
        img = np.stack([img[0], img[1], img[2]], axis=-1)

    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    elif img.ndim == 3 and img.shape[2] == 1:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    elif img.ndim == 3 and img.shape[2] == 4:
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    elif img.ndim == 3 and img.shape[2] > 4:
        img = img[:, :, :3]

    if img.dtype != np.uint8:
        img = img.astype(np.float32)
        max_val = img.max()
        if max_val > 0:
            img = (img - img.min()) / (max_val - img.min()) * 255
        img = img.astype(np.uint8)

    return img


def _annotate(img: np.ndarray, detections: list) -> np.ndarray:
    """Gambar bbox + label (range berat + confidence) di gambar."""
    img_out = img.copy()
    for det in detections:
        x1, y1, x2, y2 = [int(v) for v in det["bbox"]]
        
        # Ambil info warna dari kelas atau fallback
        kelas_raw = det["kelas"]
        info = BOBOT_MAP.get(kelas_raw, {
            "warna_bgr": (0, 255, 0)
        })
        warna = info.get("warna_bgr", (0, 255, 0))
        label = f"{det['range_bobot']}  {det['conf']}"

        # Bbox
        cv2.rectangle(img_out, (x1, y1), (x2, y2), warna, 3)

        # Ukuran teks
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)

        # Posisi background label (di atas bbox, tidak keluar frame)
        lx1 = x1
        ly1 = max(y1 - th - 10, 0)
        lx2 = x1 + tw + 6
        ly2 = max(y1, th + 10)

        # Background filled
        cv2.rectangle(img_out, (lx1, ly1), (lx2, ly2), warna, -1)

        # Teks putih
        cv2.putText(img_out, label,
                    (lx1 + 3, ly2 - 4),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, (255, 255, 255), 2)

    return img_out


def _nms_global(detections: list, iou_threshold: float = 0.5) -> list:
    if not detections:
        return []

    boxes  = np.array([[d["bbox"][0], d["bbox"][1],
                        d["bbox"][2], d["bbox"][3]] for d in detections])
    scores = np.array([d["conf"] for d in detections])
    keep   = []
    idxs   = np.argsort(scores)[::-1]

    while len(idxs) > 0:
        i = idxs[0]
        keep.append(i)
        if len(idxs) == 1:
            break

        x1 = np.maximum(boxes[i][0], boxes[idxs[1:], 0])
        y1 = np.maximum(boxes[i][1], boxes[idxs[1:], 1])
        x2 = np.minimum(boxes[i][2], boxes[idxs[1:], 2])
        y2 = np.minimum(boxes[i][3], boxes[idxs[1:], 3])

        inter     = np.maximum(0, x2 - x1) * np.maximum(0, y2 - y1)
        area_i    = (boxes[i][2]-boxes[i][0]) * (boxes[i][3]-boxes[i][1])
        area_rest = ((boxes[idxs[1:], 2] - boxes[idxs[1:], 0]) *
                     (boxes[idxs[1:], 3] - boxes[idxs[1:], 1]))
        iou  = inter / (area_i + area_rest - inter + 1e-6)
        idxs = idxs[1:][iou < iou_threshold]

    return [detections[i] for i in keep]


def estimate_bobot(image_path: str, conf: float = 0.15,
                   tile_size: int = 1280, overlap: int = 200):
    """
    Deteksi semangka dari orthophoto dengan teknik tiling,
    dan kategorikan berdasarkan kelas marker yang merepresentasikan range berat buah.
    """
    model = get_bobot_model()
    img = _load_image(image_path)
    class_names = model.names
    H, W = img.shape[:2]
    step = tile_size - overlap

    cols = max(1, int(np.ceil((W - overlap) / step)))
    rows = max(1, int(np.ceil((H - overlap) / step)))
    total_tiles = rows * cols
    print(f"🔍 Tiling: {rows} baris × {cols} kolom = {total_tiles} tile")

    detections_raw = []
    tile_count = 0

    for row in range(rows):
        for col in range(cols):
            x1_t = col * step
            y1_t = row * step
            x2_t = min(x1_t + tile_size, W)
            y2_t = min(y1_t + tile_size, H)
            tile = img[y1_t:y2_t, x1_t:x2_t]

            tile_count += 1
            print(f"   Tile {tile_count}/{total_tiles} [x:{x1_t}-{x2_t}, y:{y1_t}-{y2_t}]", end="\r")

            results = model.predict(
                source=tile, iou=0.5, conf=conf,
                imgsz=tile_size, verbose=False
            )
            boxes = results[0].boxes

            if boxes is not None and len(boxes) > 0:
                bboxes  = boxes.xyxy.cpu().numpy().tolist()
                cls_ids = boxes.cls.cpu().numpy().astype(int).tolist()
                confs   = boxes.conf.cpu().numpy().tolist()

                for (bx1, by1, bx2, by2), cls_id, conf_val in zip(bboxes, cls_ids, confs):
                    # Robust Mapping
                    kelas_raw = class_names.get(cls_id, f"kelas{cls_id+1}")
                    info = BOBOT_MAP.get(kelas_raw, {
                        "id": cls_id + 1,
                        "range": kelas_raw,
                        "warna_marker": "Abu-abu",
                        "warna_bgr": (128, 128, 128)
                    })
                    
                    kelas = f"kelas{info['id']}"
                    range_bobot = info["range"]
                    marker = info["warna_marker"]

                    detections_raw.append({
                        "bbox": [bx1+x1_t, by1+y1_t, bx2+x1_t, by2+y1_t],
                        "kelas": kelas,
                        "range_bobot": range_bobot,
                        "warna_marker": marker,
                        "conf": round(conf_val, 3),
                    })

    print(f"\n   Deteksi sebelum NMS : {len(detections_raw)} box")
    detections = _nms_global(detections_raw)
    print(f"   Deteksi setelah NMS : {len(detections)} box")

    # Rekap per kelas
    rekap = {}
    for det in detections:
        kelas = det["kelas"]
        if kelas not in rekap:
            rekap[kelas] = {
                "range_bobot":  det["range_bobot"],
                "warna_marker": det["warna_marker"],
                "jumlah":       0,
            }
        rekap[kelas]["jumlah"] += 1

    # Anotasi & simpan
    img_out = _annotate(img, detections)
    out_dir = "media/orthophoto_bobot"
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.basename(image_path)
    name, ext = os.path.splitext(base)
    out_name = f"{name}_bobot.jpg"  # Selalu jpg agar browser bisa render
    out_path = os.path.join(out_dir, out_name)
    cv2.imwrite(out_path, img_out)
    print(f"✅ Simpan hasil: {out_path}")

    return rekap, out_path, detections
