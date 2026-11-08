from django.contrib import admin

from .models import AnalysisJob


@admin.register(AnalysisJob)
class AnalysisJobAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "status", "cache_hit", "created_at", "finished_at")
    list_filter = ("status", "cache_hit")
    search_fields = ("id", "user__email", "cache_key")
    readonly_fields = ("id", "created_at", "started_at", "finished_at")
