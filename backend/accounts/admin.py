from django.contrib import admin

from .models import Organization, OrganizationMembership, Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "full_name", "organization", "primary_organization", "created_at")
    search_fields = ("user__email", "full_name", "organization")
    raw_id_fields = ("primary_organization",)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "created_at")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "slug")


@admin.register(OrganizationMembership)
class OrganizationMembershipAdmin(admin.ModelAdmin):
    list_display = ("organization", "user", "role", "created_at")
    list_filter = ("role",)
    search_fields = ("organization__name", "user__email")
