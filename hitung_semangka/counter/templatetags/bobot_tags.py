# counter/templatetags/bobot_tags.py
from django import template
from counter.models import BobotResult

register = template.Library()


@register.inclusion_tag("counter/_live_bobot.html", takes_context=True)
def live_bobot_terbaru(context):
    request = context.get('request')
    if request and request.user and request.user.is_authenticated:
        all_results = BobotResult.objects.filter(user=request.user).order_by("-created_at")
    else:
        all_results = BobotResult.objects.none()
    return {
        "total_ortho_bobot": all_results.count(),
        "total_deteksi_bobot": sum(r.total_terdeteksi for r in all_results),
        "latest_bobot": all_results[:1],
        "all_bobot_list": all_results,
    }


@register.simple_tag(takes_context=True)
def get_latest_bobot(context):
    request = context.get('request')
    if request and request.user and request.user.is_authenticated:
        return BobotResult.objects.filter(user=request.user).order_by("-created_at").first()
    return None
