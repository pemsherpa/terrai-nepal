from django.contrib import admin

from .models import BiomassHistory, Project, UserRole, VerificationReport


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ("user", "role")
    list_filter = ("role",)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "owner",
        "area_hectares",
        "field_baseline_agb_t_ha",
        "calibration_coefficient",
        "created_at",
    )
    list_select_related = ("owner", "organization")
    readonly_fields = ("calibration_updated_at",)


@admin.register(BiomassHistory)
class BiomassHistoryAdmin(admin.ModelAdmin):
    list_display = ("project", "carbon_density", "health_score", "recorded_at")
    list_select_related = ("project",)


@admin.register(VerificationReport)
class VerificationReportAdmin(admin.ModelAdmin):
    list_display = ("project", "status", "verifier", "created_at")
    list_select_related = ("project", "verifier")
