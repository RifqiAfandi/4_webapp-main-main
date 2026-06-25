from django.db import models

class Orthophoto(models.Model):
    lahan = models.CharField(max_length=100)
    image = models.ImageField(upload_to="orthophoto/")
    created_at = models.DateTimeField(auto_now_add=True)

    status = models.CharField(max_length=20, default="pending")  # pending|processing|processed|failed
    detected_count = models.IntegerField(default=0)

    image_with_boxes = models.ImageField(upload_to="orthophoto_boxes/", null=True, blank=True)
    task_id = models.CharField(max_length=100, null=True, blank=True)

class DetectionResult(models.Model):
    filename = models.CharField(max_length=255)
    lahan = models.CharField(max_length=100)
    image_path = models.CharField(max_length=500)
    bbox_path = models.CharField(max_length=500)
    count = models.IntegerField(default=0)          
    manual_count = models.IntegerField(default=0)   
    created_at = models.DateTimeField(auto_now_add=True)

class BoundingBox(models.Model):
    result = models.ForeignKey(
        DetectionResult,
        on_delete=models.CASCADE,
        related_name='boxes'
    )
    x1 = models.FloatField()
    y1 = models.FloatField()
    x2 = models.FloatField()
    y2 = models.FloatField()


class BobotResult(models.Model):
    filename = models.CharField(max_length=255)
    lahan = models.CharField(max_length=100)
    image_path = models.CharField(max_length=500)
    bbox_path = models.CharField(max_length=500)
    total_terdeteksi = models.IntegerField(default=0)

    kelas_dominan = models.CharField(max_length=20, blank=True)    # contoh: "kelas3"
    range_dominan = models.CharField(max_length=50, blank=True)    # contoh: "2,6 - 3,0 kg"
    jumlah_dominan = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    def get_rekap(self):
        """Mengembalikan rekap jumlah per kelas untuk hasil bobot ini secara dinamis."""
        from django.db.models import Count
        from counter.bobot_model import BOBOT_MAP

        classes_info = {}
        for k in sorted(BOBOT_MAP.keys()):
            if k.startswith("kelas"):
                info = BOBOT_MAP[k]
                b, g, r = info["warna_bgr"]
                hex_color = f"#{r:02x}{g:02x}{b:02x}"
                classes_info[k] = {
                    "range": info["range"],
                    "warna": info["warna_marker"],
                    "hex": hex_color,
                    "count": 0
                }

        # Hitung deteksi riil di database
        detections = self.detections.values('kelas').annotate(count=Count('id'))
        for det in detections:
            kls = det['kelas']
            if kls in classes_info:
                classes_info[kls]['count'] = det['count']

        # Kembalikan sebagai list of dicts yang diurutkan dari kelas1 ke kelas8
        return [
            {
                "kelas": k,
                "range": v["range"],
                "warna": v["warna"],
                "hex": v["hex"],
                "count": v["count"]
            }
            for k, v in sorted(classes_info.items(), key=lambda x: int(x[0].replace("kelas", "")))
        ]


class BobotDetection(models.Model):
    result = models.ForeignKey(
        BobotResult, on_delete=models.CASCADE, related_name="detections"
    )
    kelas = models.CharField(max_length=20)
    range_bobot = models.CharField(max_length=50)
    warna_marker = models.CharField(max_length=50)
    confidence = models.FloatField(default=0.0)
    x1 = models.FloatField()
    y1 = models.FloatField()
    x2 = models.FloatField()
    y2 = models.FloatField()