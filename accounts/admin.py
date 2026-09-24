from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from config.exports import csv_response

from .models import User

# Only a superuser may grant access. Without this, anyone with change_user
# (the Committee group) could tick is_superuser on their own account.
ACCESS_FIELDS = ("is_superuser", "is_staff", "groups", "user_permissions")


@admin.action(description="Export members to CSV")
def export_members_csv(modeladmin, request, queryset):
    rows = (
        (u.student_id, u.full_name, u.get_faculty_display(), u.email, u.phone, u.joined_on,
         "Yes" if u.is_active_member else "No")
        for u in queryset
    )
    return csv_response(
        "members.csv",
        ["Student ID", "Full name", "Faculty", "Email", "Phone", "Joined", "Active member"],
        rows,
    )


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ["student_id", "full_name", "faculty", "email", "is_active_member", "is_staff", "joined_on"]
    list_filter = ["faculty", "is_active_member", "is_staff", "groups"]
    search_fields = ["student_id", "full_name", "email", "username"]
    ordering = ["full_name"]
    actions = [export_members_csv]
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Member", {"fields": ("student_id", "full_name", "faculty", "phone", "is_active_member")}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("Member", {"fields": ("student_id", "full_name", "faculty", "email")}),
    )

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser:
            readonly += ACCESS_FIELDS
        return readonly

    def has_change_permission(self, request, obj=None):
        # Committee members may edit regular members and themselves, but not other
        # staff accounts. This also covers the admin "change password" page.
        if obj is not None and not request.user.is_superuser:
            if obj.is_staff and obj.pk != request.user.pk:
                return False
        return super().has_change_permission(request, obj)
