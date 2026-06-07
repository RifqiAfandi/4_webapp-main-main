from celery import shared_task
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models import Sum
from .models import Orthophoto
from .yolo_model import detect_semangka

def push(payload: dict):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "dashboard",
        {"type": "dashboard.event", "payload": payload},
    )

@shared_task(bind=True)
def run_detection(self, orthophoto_id: int):
    ortho = Orthophoto.objects.get(id=orthophoto_id)
    ortho.status = "processing"
    ortho.task_id = self.request.id
    ortho.save(update_fields=["status", "task_id"])

    push({"type": "status", "id": ortho.id, "status": "processing"})

    count, out_path, *_ = detect_semangka(ortho.image.path, conf=0.25)

    # simpan relative untuk ImageField
    ortho.status = "processed"
    ortho.detected_count = count
    ortho.image_with_boxes.name = out_path.replace("media/", "")
    ortho.save(update_fields=["status", "detected_count", "image_with_boxes"])

    total_ortho = Orthophoto.objects.count()
    total_detected = Orthophoto.objects.aggregate(s=Sum("detected_count"))["s"] or 0

    push({
        "type": "done",
        "id": ortho.id,
        "filename": ortho.image.name.split("/")[-1],
        "lahan": ortho.lahan,
        "status": ortho.status,
        "detected_count": ortho.detected_count,
        "image_with_boxes_url": ortho.image_with_boxes.url,
        "total_orthophoto": total_ortho,
        "total_detected": total_detected,
    })
