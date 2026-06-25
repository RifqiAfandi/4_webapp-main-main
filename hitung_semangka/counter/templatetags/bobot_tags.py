# counter/templatetags/bobot_tags.py
from django import template
from counter.models import BobotResult

register = template.Library()


@register.inclusion_tag("counter/_live_bobot.html")
def live_bobot_terbaru():
    all_results = BobotResult.objects.all().order_by("-created_at")
    return {
        "total_ortho_bobot": all_results.count(),
        "total_deteksi_bobot": sum(r.total_terdeteksi for r in all_results),
        "latest_bobot": all_results[:1],
        "all_bobot_list": all_results,
    }


@register.simple_tag
def get_latest_bobot():
    return BobotResult.objects.all().order_by("-created_at").first()
