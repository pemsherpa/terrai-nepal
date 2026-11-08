from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BiomassHistoryViewSet, ProjectViewSet, VerificationReportViewSet

router = DefaultRouter()
router.register("projects", ProjectViewSet, basename="project")
router.register("biomass-history", BiomassHistoryViewSet, basename="biomass-history")
router.register("verification-reports", VerificationReportViewSet, basename="verification-report")

urlpatterns = [
    path("", include(router.urls)),
]
