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