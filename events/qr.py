import segno
from django.urls import reverse
from django.utils.safestring import mark_safe


def checkin_url(request, event):
    return request.build_absolute_uri(reverse("events:checkin", args=[event.checkin_token]))


def qr_svg(data):
    """Inline SVG that scales to its container. Always dark on light so phones read it reliably."""
    qr = segno.make(data, error="m")
    return mark_safe(qr.svg_inline(scale=10, border=2, omitsize=True, dark="#111111", light="#ffffff"))
