import uuid

from django.conf import settings
from django.db import models


class AnalysisJob(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"
        CACHED = "cached", "Cached"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="analysis_jobs",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    request_payload = models.JSONField(default=dict)
    cache_key = models.CharField(max_length=128, blank=True, default="", db_index=True)
    result = models.JSONField(null=True, blank=True)
    error = models.TextField(blank=True, default="")
    cache_hit = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self) -> str:
        return f"AnalysisJob {self.id} ({self.status})"
