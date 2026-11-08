from django.conf import settings
from django.db import models


class Organization(models.Model):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class OrganizationMembership(models.Model):
    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        MANAGER = "manager", "Manager"
        MEMBER = "member", "Member"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="org_memberships",
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "user"],
                name="unique_org_membership",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "role"]),
            models.Index(fields=["organization", "role"]),
        ]

    def __str__(self) -> str:
        return f"{self.user_id}@{self.organization.slug}:{self.role}"

    @classmethod
    def org_ids_for_user(cls, user, roles=None):
        qs = cls.objects.filter(user=user)
        if roles:
            qs = qs.filter(role__in=roles)
        return list(qs.values_list("organization_id", flat=True))

    @classmethod
    def can_manage_org(cls, user, organization_id) -> bool:
        return cls.objects.filter(
            user=user,
            organization_id=organization_id,
            role__in=[cls.Role.OWNER, cls.Role.MANAGER],
        ).exists()


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="profile",
    )
    full_name = models.CharField(max_length=255, blank=True, default="")
    # Legacy free-text label kept for display; prefer OrganizationMembership
    organization = models.CharField(max_length=255, blank=True, default="")
    primary_organization = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="primary_profiles",
    )
    avatar_url = models.URLField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.full_name or self.user.email
