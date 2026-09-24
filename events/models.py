import secrets
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.urls import reverse
from django.utils import timezone

CHECKIN_EARLY = timedelta(minutes=30)


def new_token():
    return secrets.token_urlsafe(16)


class Event(models.Model):
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    venue = models.CharField(max_length=150)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    capacity = models.PositiveIntegerField(null=True, blank=True, help_text="Leave empty for unlimited.")
    checkin_open = models.BooleanField(default=False)
    checkin_token = models.CharField(max_length=32, unique=True, default=new_token, editable=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="events_created"
    )

    class Meta:
        ordering = ["starts_at"]

    def __str__(self):
        return f"{self.title} ({timezone.localtime(self.starts_at):%d %b %Y})"

    def clean(self):
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValidationError({"ends_at": "The event must end after it starts."})

    def get_absolute_url(self):
        return reverse("events:detail", args=[self.pk])

    def regenerate_token(self):
        self.checkin_token = new_token()
        self.save(update_fields=["checkin_token"])

    @property
    def is_full(self):
        return self.capacity is not None and self.attendances.count() >= self.capacity

    def can_check_in(self, user, now=None):
        """Return (ok, reason). reason is a short, member-facing message when not ok."""
        now = now or timezone.now()
        if not self.checkin_open:
            return False, "Check-in is closed for this event."
        if now < self.starts_at - CHECKIN_EARLY:
            return False, "Check-in has not started yet. It opens 30 minutes before the event."
        if now > self.ends_at:
            return False, "This event has ended."
        if not user.is_active_member:
            return False, "Your membership is not active. Please talk to the committee."
        if self.is_full and not self.attendances.filter(member=user).exists():
            return False, "This event is full."
        return True, ""

    def check_in(self, user, now=None):
        """Return (attendance or None, created, reason)."""
        with transaction.atomic():
            # Lock the event row so two people cannot both take the last spot (PostgreSQL).
            event = Event.objects.select_for_update().get(pk=self.pk)
            ok, reason = event.can_check_in(user, now)
            if not ok:
                return None, False, reason
            attendance, created = Attendance.objects.get_or_create(event=event, member=user)
        return attendance, created, ""


class Attendance(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="attendances")
    member = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="attendances")
    checked_in_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("event", "member")]
        ordering = ["-checked_in_at"]
        verbose_name_plural = "attendance"

    def __str__(self):
        return f"{self.member.full_name} at {self.event.title}"
