from rest_framework import permissions

from accounts.models import OrganizationMembership

from .models import UserRole


class IsOwnerOrOrgMemberOrValidator(permissions.BasePermission):
    """Owners, org members (read), org managers (write), validators (read)."""

    def has_permission(self, request, view) -> bool:
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj) -> bool:
        user = request.user
        is_validator = UserRole.user_has_role(user, UserRole.Role.VALIDATOR)
        project = obj if hasattr(obj, "owner_id") else getattr(obj, "project", None)
        owner = getattr(project, "owner", None)
        org_id = getattr(project, "organization_id", None)

        if request.method in permissions.SAFE_METHODS:
            if owner == user or is_validator or user.is_staff:
                return True
            if org_id:
                return OrganizationMembership.objects.filter(
                    user=user, organization_id=org_id
                ).exists()
            return False

        if owner == user or user.is_staff:
            return True
        if org_id:
            return OrganizationMembership.can_manage_org(user, org_id)
        return False


class IsOwnerOrValidatorRead(IsOwnerOrOrgMemberOrValidator):
    """Back-compat alias."""


class IsValidator(permissions.BasePermission):
    def has_permission(self, request, view) -> bool:
        return UserRole.user_has_role(request.user, UserRole.Role.VALIDATOR) or request.user.is_staff
