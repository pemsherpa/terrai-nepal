from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .models import Organization, OrganizationMembership
from .serializers import (
    AddMemberSerializer,
    MembershipSerializer,
    OrganizationCreateSerializer,
    OrganizationSerializer,
    ProfileSerializer,
    RegisterSerializer,
)
from .token_serializers import EmailTokenObtainPairSerializer


class RegisterView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                "id": user.id,
                "email": user.email,
                "full_name": user.profile.full_name,
                "primary_organization_id": user.profile.primary_organization_id,
            },
            status=status.HTTP_201_CREATED,
        )


class ProfileMeView(generics.RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer

    def get_object(self):
        profile, _ = self.request.user.profile.__class__.objects.select_related(
            "user", "primary_organization"
        ).get_or_create(user=self.request.user)
        return profile


class LoginView(TokenObtainPairView):
    permission_classes = [permissions.AllowAny]
    serializer_class = EmailTokenObtainPairSerializer


class RefreshView(TokenRefreshView):
    permission_classes = [permissions.AllowAny]


class OrganizationListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        orgs = Organization.objects.filter(memberships__user=request.user).distinct()
        return Response(OrganizationSerializer(orgs, many=True, context={"request": request}).data)

    def post(self, request):
        ser = OrganizationCreateSerializer(data=request.data, context={"request": request})
        ser.is_valid(raise_exception=True)
        org = ser.save()
        return Response(
            OrganizationSerializer(org, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class OrganizationDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        org = get_object_or_404(
            Organization.objects.filter(memberships__user=request.user),
            pk=pk,
        )
        return Response(OrganizationSerializer(org, context={"request": request}).data)


class OrganizationMembersView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        org = get_object_or_404(
            Organization.objects.filter(memberships__user=request.user),
            pk=pk,
        )
        members = org.memberships.select_related("user", "user__profile")
        return Response(MembershipSerializer(members, many=True).data)

    def post(self, request, pk):
        org = get_object_or_404(Organization, pk=pk)
        if not OrganizationMembership.can_manage_org(request.user, org.id) and not request.user.is_staff:
            raise PermissionDenied("Only owners/managers can add members")
        ser = AddMemberSerializer(data=request.data, context={"organization": org})
        ser.is_valid(raise_exception=True)
        membership = ser.save()
        return Response(MembershipSerializer(membership).data, status=status.HTTP_201_CREATED)
