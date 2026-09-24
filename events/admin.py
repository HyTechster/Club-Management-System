from django.contrib import admin, messages
from django.db.models import Count
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html

from config.exports import csv_response

from .models import Attendance, Event


class AttendanceInline(admin.TabularInline):
    model = Attendance
    extra = 0
    autocomplete_fields = ["member"]
    readonly_fields = ["checked_in_at"]


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ["title", "starts_at", "venue", "checkin_open", "attendance_count", "qr_link"]
    list_filter = ["checkin_open", "starts_at"]
    search_fields = ["title", "venue"]
    date_hierarchy = "starts_at"
    readonly_fields = ["qr_link", "created_by"]
    inlines = [AttendanceInline]
    actions = ["open_checkin", "close_checkin", "regenerate_token", "export_attendance_csv"]
    fields = ["title", "description", "venue", "starts_at", "ends_at", "capacity",
              "checkin_open", "qr_link", "created_by"]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_attendance=Count("attendances"))

    @admin.display(description="Attended", ordering="_attendance")
    def attendance_count(self, obj):
        return obj._attendance

    @admin.display(description="QR page")
    def qr_link(self, obj):
        if not obj.pk:
            return "Save the event first."
        return format_html('<a href="{}" target="_blank">Open QR display</a>', reverse("events:qr", args=[obj.pk]))

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    @admin.action(description="Open check-in", permissions=["change"])
    def open_checkin(self, request, queryset):
        n = queryset.update(checkin_open=True)
        self.message_user(request, f"Check-in opened for {n} event(s).", messages.SUCCESS)

    @admin.action(description="Close check-in", permissions=["change"])
    def close_checkin(self, request, queryset):
        n = queryset.update(checkin_open=False)
        self.message_user(request, f"Check-in closed for {n} event(s).", messages.SUCCESS)

    @admin.action(description="Regenerate check-in token", permissions=["change"])
    def regenerate_token(self, request, queryset):
        for event in queryset:
            event.regenerate_token()
        self.message_user(request, f"New QR codes made for {queryset.count()} event(s). Old ones no longer work.",
                          messages.SUCCESS)

    @admin.action(description="Export attendance to CSV")
    def export_attendance_csv(self, request, queryset):
        rows = (Attendance.objects.filter(event__in=queryset)
                .select_related("event", "member").order_by("event__starts_at", "checked_in_at"))
        return csv_response(
            "attendance.csv",
            ["Event", "Event date", "Student ID", "Full name", "Faculty", "Checked in at"],
            ((a.event.title,
              timezone.localtime(a.event.starts_at).strftime("%Y-%m-%d %H:%M"),
              a.member.student_id,
              a.member.full_name,
              a.member.get_faculty_display(),
              timezone.localtime(a.checked_in_at).strftime("%Y-%m-%d %H:%M")) for a in rows),
        )


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ["member", "event", "checked_in_at"]
    list_filter = ["event", "checked_in_at"]
    search_fields = ["member__student_id", "member__full_name", "event__title"]
    autocomplete_fields = ["member", "event"]
    list_select_related = ["member", "event"]
