import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class UserRole(models.Model):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        VALIDATOR = "validator", "Validator"
        USER = "user", "User"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="roles",
    )
    role = models.CharField(max_length=20, choices=Role.choices)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "role"], name="unique_user_role"),
        ]
        indexes = [
            models.Index(fields=["user", "role"]),
        ]

    @classmethod
    def user_has_role(cls, user, role: str) -> bool:
        if not user or not user.is_authenticated:
            return False
        return cls.objects.filter(user=user, role=role).exists()


class Project(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    latitude = models.FloatField()
    longitude = models.FloatField()
    area_hectares = models.FloatField(default=0)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="projects",
    )
    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects",
    )
    # Field inventory calibration (CFUG DBH surveys) — not ML, explicit bias hook
    field_baseline_agb_t_ha = models.FloatField(
        null=True,
        blank=True,
        help_text="Actual field inventory AGB (t/ha) from CFUG / consultant survey",
    )
    calibration_coefficient = models.FloatField(
        default=1.0,
        validators=[MinValueValidator(0.1), MaxValueValidator(5.0)],
        help_text="Final Biomass = Satellite Estimate × coefficient",
    )
    calibration_notes = models.TextField(blank=True, default="")
    calibration_updated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["owner"]),
            models.Index(fields=["organization"]),
            models.Index(fields=["-created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.name

    def set_field_calibration(
        self,
        field_baseline_agb_t_ha: float | None = None,
        *,
        satellite_agb_t_ha: float | None = None,
        coefficient: float | None = None,
        notes: str = "",
    ) -> None:
        """
        Store field baseline and/or derive coefficient:
          coefficient = field_baseline / satellite_agb
        """
        from django.utils import timezone

        if field_baseline_agb_t_ha is not None:
            self.field_baseline_agb_t_ha = field_baseline_agb_t_ha
        if coefficient is not None:
            self.calibration_coefficient = coefficient
        elif (
            self.field_baseline_agb_t_ha
            and satellite_agb_t_ha
            and satellite_agb_t_ha > 0
        ):
            self.calibration_coefficient = max(
                0.1, min(5.0, float(self.field_baseline_agb_t_ha) / float(satellite_agb_t_ha))
            )
        if notes:
            self.calibration_notes = notes
        self.calibration_updated_at = timezone.now()
        self.save(
            update_fields=[
                "field_baseline_agb_t_ha",
                "calibration_coefficient",
                "calibration_notes",
                "calibration_updated_at",
                "updated_at",
            ]
        )


class BiomassHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="biomass_entries",
    )
    recorded_at = models.DateTimeField(auto_now_add=True)
    carbon_density = models.FloatField()
    health_score = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
    )
    source_url = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["project"]),
            models.Index(fields=["recorded_at"]),
        ]
        ordering = ["recorded_at"]

    def __str__(self) -> str:
        return f"{self.project.name} @ {self.recorded_at:%Y-%m-%d}"


class VerificationReport(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="verification_reports",
    )
    verifier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_reports",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    pdf_url = models.URLField(blank=True, null=True)
    integrity_seal_hash = models.CharField(max_length=128, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["project"]),
            models.Index(fields=["status"]),
            models.Index(fields=["-created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.project.name} ({self.status})"
