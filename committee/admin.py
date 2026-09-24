from django.contrib import admin

from .models import CommitteeRole, Term


class CommitteeRoleInline(admin.TabularInline):
    model = CommitteeRole
    extra = 1
    autocomplete_fields = ["member"]


@admin.register(Term)
class TermAdmin(admin.ModelAdmin):
    list_display = ["name", "starts_on", "ends_on", "is_current"]
    list_filter = ["is_current"]
    search_fields = ["name"]
    inlines = [CommitteeRoleInline]


@admin.register(CommitteeRole)
class CommitteeRoleAdmin(admin.ModelAdmin):
    list_display = ["member", "title", "term"]
    list_filter = ["term", "title"]
    search_fields = ["member__student_id", "member__full_name"]
    autocomplete_fields = ["member"]
    list_select_related = ["member", "term"]
