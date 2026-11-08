from django.db.models import Q
from rest_framework import mixins, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.models import OrganizationMembership

from .models import BiomassHistory, Project, UserRole, VerificationReport
from .permissions import IsOwnerOrOrgMemberOrValidator, IsValidator
from .serializers import (
    BiomassHistorySerializer,
    ProjectSerializer,
    VerificationReportSerializer,
)


def _is_validator(user) -> bool:
    return UserRole.user_has_role(user, UserRole.Role.VALIDATOR) or user.is_staff


def _visible_project_q(user, *, via_project: bool = False):
    """Own projects + all projects in orgs where user is owner/manager/member."""
    org_ids = OrganizationMembership.org_ids_for_user(user)
    owner_key = "project__owner" if via_project else "owner"
    org_key = "project__organization_id" if via_project else "organization_id"
    return Q(**{owner_key: user}) | Q(**{f"{org_key}__in": org_ids})


def _can_edit_project(user, project) -> bool:
    if user.is_staff or project.owner_id == user.id:
        return True
    if project.organization_id:
        return OrganizationMembership.can_manage_org(user, project.organization_id)
    return False


class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [IsOwnerOrOrgMemberOrValidator]

    def get_queryset(self):
        qs = Project.objects.select_related("owner", "organization")
        if _is_validator(self.request.user):
            return qs
        return qs.filter(_visible_project_q(self.request.user)).distinct()

    def perform_create(self, serializer):
        org = serializer.validated_data.get("organization")
        if org and not (
            OrganizationMembership.objects.filter(
                user=self.request.user,
                organization=org,
            ).exists()
            or self.request.user.is_staff
        ):
            raise PermissionDenied("You are not a member of this organization")
        serializer.save(owner=self.request.user)

    def perform_update(self, serializer):
        if not _can_edit_project(self.request.user, serializer.instance):
            raise PermissionDenied("Only the owner or org managers can edit this project")
        serializer.save()

    def perform_destroy(self, instance):
        if not _can_edit_project(self.request.user, instance):
            raise PermissionDenied("Only the owner or org managers can delete this project")
        instance.delete()


class BiomassHistoryViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = BiomassHistorySerializer
    permission_classes = [IsOwnerOrOrgMemberOrValidator]

    def get_queryset(self):
        qs = BiomassHistory.objects.select_related("project", "project__owner", "project__organization")
        project_id = self.request.query_params.get("project_id")
        if project_id:
            qs = qs.filter(project_id=project_id)
        if not _is_validator(self.request.user):
            qs = qs.filter(_visible_project_q(self.request.user, via_project=True)).distinct()
        return qs

    def perform_create(self, serializer):
        project = serializer.validated_data["project"]
        if not _can_edit_project(self.request.user, project) and not _is_validator(self.request.user):
            # members can still add biomass to org projects they can see
            if not Project.objects.filter(_visible_project_q(self.request.user), pk=project.pk).exists():
                raise PermissionDenied("Cannot add biomass to this project")
        serializer.save()


class VerificationReportViewSet(viewsets.ModelViewSet):
    serializer_class = VerificationReportSerializer
    permission_classes = [IsOwnerOrOrgMemberOrValidator]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        qs = VerificationReport.objects.select_related(
            "project", "project__owner", "project__organization", "verifier"
        )
        project_id = self.request.query_params.get("project_id")
        if project_id:
            qs = qs.filter(project_id=project_id)
        if not _is_validator(self.request.user):
            qs = qs.filter(_visible_project_q(self.request.user, via_project=True)).distinct()
        return qs

    def get_permissions(self):
        if self.action in ("update", "partial_update"):
            return [IsValidator()]
        return super().get_permissions()

    def perform_update(self, serializer):
        serializer.save(verifier=self.request.user)

    @action(detail=False, methods=["get"], url_path="feed")
    def feed(self, request):
        qs = VerificationReport.objects.select_related("project").only(
            "id",
            "status",
            "created_at",
            "project_id",
            "project__name",
        )
        if not _is_validator(request.user):
            qs = qs.filter(_visible_project_q(request.user, via_project=True)).distinct()
        qs = qs.order_by("-created_at")[:20]

        data = [
            {
                "id": str(r.id),
                "status": r.status,
                "created_at": r.created_at.isoformat(),
                "project_id": str(r.project_id),
                "project_name": r.project.name,
            }
            for r in qs
        ]
        return Response(data)
