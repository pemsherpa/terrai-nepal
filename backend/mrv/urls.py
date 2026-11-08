from django.urls import path

from .views import (
    AnalyzeJobDetailView,
    AnalyzeView,
    BaselinesView,
    DailyNdviView,
    ExportPdfView,
    GenerateReportView,
    PassDatesView,
    VisionInferenceView,
)

urlpatterns = [
    path("analyze/", AnalyzeView.as_view(), name="mrv-analyze"),
    path("analyze/jobs/<uuid:job_id>/", AnalyzeJobDetailView.as_view(), name="mrv-analyze-job"),
    path("report/generate/", GenerateReportView.as_view(), name="mrv-report-generate"),
    path("export/pdf/", ExportPdfView.as_view(), name="mrv-export-pdf"),
    path("pass-dates/", PassDatesView.as_view(), name="mrv-pass-dates"),
    path("daily-ndvi/", DailyNdviView.as_view(), name="mrv-daily-ndvi"),
    path("baselines/", BaselinesView.as_view(), name="mrv-baselines"),
    path("vision/infer/", VisionInferenceView.as_view(), name="mrv-vision-infer"),
]
