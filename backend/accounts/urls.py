from django.urls import path

from .views import (
    LoginView,
    OrganizationDetailView,
    OrganizationListCreateView,
    OrganizationMembersView,
    ProfileMeView,
    RefreshView,
    RegisterView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("refresh/", RefreshView.as_view(), name="auth-refresh"),
    path("profile/me/", ProfileMeView.as_view(), name="profile-me"),
    path("organizations/", OrganizationListCreateView.as_view(), name="org-list"),
    path("organizations/<int:pk>/", OrganizationDetailView.as_view(), name="org-detail"),
    path("organizations/<int:pk>/members/", OrganizationMembersView.as_view(), name="org-members"),
]
