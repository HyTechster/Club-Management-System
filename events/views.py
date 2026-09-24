from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.generic import DetailView, ListView

from .models import Event
from .qr import checkin_url, qr_svg


class EventListView(LoginRequiredMixin, ListView):
    template_name = "events/list.html"
    context_object_name = "events"

    def get_queryset(self):
        return (Event.objects.filter(ends_at__gte=timezone.now())
                .annotate(attendee_count=Count("attendances")).order_by("starts_at"))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["attended_ids"] = set(
            self.request.user.attendances.filter(event__in=ctx["events"]).values_list("event_id", flat=True)
        )
        return ctx


class EventDetailView(LoginRequiredMixin, DetailView):
    model = Event
    template_name = "events/detail.html"

    def get_queryset(self):
        return Event.objects.annotate(attendee_count=Count("attendances"))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        event = self.object
        now = timezone.now()
        ctx["attended"] = event.attendances.filter(member=self.request.user).exists()
        ctx["is_past"] = event.ends_at < now
        ctx["is_live"] = event.starts_at <= now <= event.ends_at
        ctx["can_manage"] = self.request.user.has_perm("events.change_event")
        return ctx


@permission_required("events.change_event")
def qr_display(request, pk):
    event = get_object_or_404(Event, pk=pk)
    url = checkin_url(request, event)
    return render(request, "events/qr.html", {
        "event": event,
        "qr": qr_svg(url),
        "checkin_url": url,
        "attendee_count": event.attendances.count(),
    })


@login_required
@require_http_methods(["GET", "POST"])
def checkin(request, token):
    event = Event.objects.filter(checkin_token=token).first()
    if event is None:
        return render(request, "events/checkin.html", {
            "state": "error",
            "reason": "This QR code no longer works. Ask the committee for the current one.",
        }, status=404)

    existing = event.attendances.filter(member=request.user).first()
    if existing:
        return render(request, "events/checkin.html", {"state": "success", "event": event, "attendance": existing})

    if request.method == "GET":
        ok, reason = event.can_check_in(request.user)
        return render(request, "events/checkin.html", {
            "state": "confirm" if ok else "error", "event": event, "reason": reason,
        })

    attendance, _created, reason = event.check_in(request.user)
    if attendance is None:
        return render(request, "events/checkin.html", {"state": "error", "event": event, "reason": reason})
    return render(request, "events/checkin.html", {"state": "success", "event": event, "attendance": attendance})
