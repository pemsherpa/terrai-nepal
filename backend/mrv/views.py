import os

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .cache_utils import (
    DAILY_NDVI_TTL,
    PASS_DATES_TTL,
    analyze_cache_key,
    cache_get_or_set,
    daily_ndvi_cache_key,
    get_baselines_cached,
    get_cached_analyze,
    pass_dates_cache_key,
)
from .models import AnalysisJob
from .pdf_report import build_pdf, monthly_chart, trend_chart
from .science import (
    DISTRICT_BASELINE,
    call_groq,
    daily_ndvi,
    list_pass_dates,
)
from .tasks import enqueue_analysis_job, execute_analysis_job


class VisionInferenceView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        required = ("lat", "lon", "baseline_date", "comparison_date")
        missing = [key for key in required if request.data.get(key) in (None, "")]
        if missing:
            return Response({"detail": f"Missing required fields: {', '.join(missing)}"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            from .vision_inference import run_live_inference

            buf_val = request.data.get("buf_km")
            buf_km = float(buf_val) if buf_val not in (None, "", 0, "0", 0.0) else 5.0
            result = run_live_inference(
                lat=float(request.data["lat"]),
                lon=float(request.data["lon"]),
                buf_km=buf_km,
                geojson=request.data.get("geojson"),
                baseline_date=str(request.data["baseline_date"]),
                comparison_date=str(request.data["comparison_date"]),
            )
            return Response(result)
        except (FileNotFoundError, ImportError) as exc:
            return Response({"detail": str(exc), "code": "vision_runtime_unavailable"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception as exc:
            return Response({"detail": f"Vision inference failed: {exc}", "code": "vision_inference_failed"}, status=status.HTTP_502_BAD_GATEWAY)


def _normalize_analyze_payload(data) -> dict:
    return {
        "lat": float(data["lat"]) if data.get("lat") is not None else None,
        "lon": float(data["lon"]) if data.get("lon") is not None else None,
        "geojson": data.get("geojson"),
        "buf_km": float(data.get("buf_km", 5)),
        "year1": int(data["year1"]) if data.get("year1") is not None else None,
        "year2": int(data["year2"]) if data.get("year2") is not None else None,
        "start_month": int(data.get("start_month", 1)),
        "end_month": int(data.get("end_month", 3)),
        "start_day": int(data.get("start_day", 1)),
        "end_day": int(data["end_day"]) if data.get("end_day") is not None else None,
        "baseline_date": data.get("baseline_date") or data.get("baseline_start"),
        "comparison_date": data.get("comparison_date") or data.get("comparison_start"),
        "baseline_start": data.get("baseline_start"),
        "baseline_end": data.get("baseline_end"),
        "comparison_start": data.get("comparison_start"),
        "comparison_end": data.get("comparison_end"),
        "forest_type": data.get("forest_type", "default"),
        "run_multiyear": bool(data.get("run_multiyear", False)),
        "run_monthly": bool(data.get("run_monthly", True)),
        "run_hotspot": bool(data.get("run_hotspot", True)),
        "project_id": data.get("project_id"),
        "calibration_coefficient": (
            float(data["calibration_coefficient"])
            if data.get("calibration_coefficient") is not None
            else None
        ),
        "field_baseline_agb_t_ha": (
            float(data["field_baseline_agb_t_ha"])
            if data.get("field_baseline_agb_t_ha") is not None
            else None
        ),
    }


class AnalyzeView(APIView):
    """
    Async GEE analysis.
    POST → { job_id, status, cache_hit? }  (202)
    Optional ?sync=1 for legacy blocking (dev only).
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        payload = _normalize_analyze_payload(request.data)
        cache_key = analyze_cache_key(payload)

        # Instant return if identical AOI/params already computed
        cached = get_cached_analyze(cache_key)
        if cached is not None:
            job = AnalysisJob.objects.create(
                user=request.user,
                status=AnalysisJob.Status.CACHED,
                request_payload=payload,
                cache_key=cache_key,
                result=cached,
                cache_hit=True,
                finished_at=timezone.now(),
            )
            return Response(
                {
                    "job_id": str(job.id),
                    "status": job.status,
                    "cache_hit": True,
                    "result": cached,
                },
                status=status.HTTP_200_OK,
            )

        job = AnalysisJob.objects.create(
            user=request.user,
            status=AnalysisJob.Status.PENDING,
            request_payload=payload,
            cache_key=cache_key,
        )

        # Dev escape hatch: block until done
        if str(request.query_params.get("sync", "")).lower() in ("1", "true", "yes"):
            try:
                result = execute_analysis_job(str(job.id))
                job.refresh_from_db()
                return Response(
                    {"job_id": str(job.id), "status": job.status, "cache_hit": job.cache_hit, "result": result}
                )
            except Exception as exc:
                job.refresh_from_db()
                return Response(
                    {"job_id": str(job.id), "status": job.status, "detail": str(exc)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        mode = enqueue_analysis_job(str(job.id))
        return Response(
            {
                "job_id": str(job.id),
                "status": AnalysisJob.Status.PENDING,
                "queue": mode,
                "poll_url": f"/api/analyze/jobs/{job.id}/",
            },
            status=status.HTTP_202_ACCEPTED,
        )


class AnalyzeJobDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, job_id):
        job = get_object_or_404(AnalysisJob, pk=job_id, user=request.user)
        body = {
            "job_id": str(job.id),
            "status": job.status,
            "cache_hit": job.cache_hit,
            "created_at": job.created_at.isoformat(),
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        }
        if job.status in (AnalysisJob.Status.SUCCESS, AnalysisJob.Status.CACHED):
            body["result"] = job.result
        if job.status == AnalysisJob.Status.FAILED:
            body["detail"] = job.error
        return Response(body)


class GenerateReportView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        data = request.data
        groq_key = os.environ.get("GROQ_API_KEY", "")
        if not groq_key:
            return Response({"detail": "GROQ_API_KEY not configured"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        date_note = data.get("date_note") or ""
        b = data.get("baseline_date") or data.get("baseline_start")
        c = data.get("comparison_date") or data.get("comparison_start")
        if not date_note and b and c:
            date_note = f"{b} vs {c}"

        report_data, err = call_groq(
            groq_key,
            data.get("location", "Unknown"),
            float(data.get("lat") or 0.0),
            float(data.get("lon") or 0.0),
            int(data.get("year1") or 0),
            int(data.get("year2") or 0),
            int(data.get("start_month", 1)),
            int(data.get("end_month", 3)),
            data.get("ndvi_year1"),
            data.get("ndvi_year2"),
            float(data.get("change_pct", 0)),
            data.get("monthly_series") or [],
            data.get("carbon_estimate"),
            data.get("trend_data") or [],
            date_note=date_note,
        )
        if err:
            return Response({"detail": f"Report failed: {err}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(report_data)


class ExportPdfView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        data = request.data
        location = data.get("location", "Unknown")
        monthly_series = data.get("monthly_series") or []
        trend_data = data.get("trend_data") or []
        year2 = int(data.get("year2") or 2024)
        monthly_fig = monthly_chart(monthly_series, f"Monthly NDVI {year2} — {location}") if monthly_series else None
        trend_fig = trend_chart(trend_data, location) if len(trend_data) >= 2 else None

        try:
            pdf_bytes = build_pdf(
                data.get("report_data") or {},
                location,
                float(data.get("lat") or 0.0),
                float(data.get("lon") or 0.0),
                float(data.get("buf_km", 5)),
                float(data.get("area_ha", 0)),
                int(data.get("year1") or 2022),
                year2,
                int(data.get("start_month", 1)),
                int(data.get("end_month", 3)),
                data.get("ndvi_year1"),
                data.get("ndvi_year2"),
                float(data.get("change_pct", 0)),
                data.get("carbon_estimate"),
                trend_data,
                monthly_series,
                monthly_fig=monthly_fig,
                trend_fig=trend_fig,
            )
        except Exception as exc:
            return Response({"detail": f"PDF generation failed: {exc}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in location)
        return HttpResponse(
            pdf_bytes,
            content_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="TerrAI_{safe_name}_{year2}.pdf"'},
        )


class PassDatesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        data = dict(request.data)
        key = pass_dates_cache_key(data)
        try:
            result = cache_get_or_set(
                key,
                PASS_DATES_TTL,
                lambda: list_pass_dates(
                    lat=float(data["lat"]) if data.get("lat") is not None else None,
                    lon=float(data["lon"]) if data.get("lon") is not None else None,
                    geojson=data.get("geojson"),
                    buf_km=float(data.get("buf_km", 5)),
                    year=int(data["year"]),
                    month=int(data["month"]),
                ),
            )
            return Response(result)
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DailyNdviView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        data = dict(request.data)
        key = daily_ndvi_cache_key(data)
        try:
            result = cache_get_or_set(
                key,
                DAILY_NDVI_TTL,
                lambda: daily_ndvi(
                    lat=float(data["lat"]) if data.get("lat") is not None else None,
                    lon=float(data["lon"]) if data.get("lon") is not None else None,
                    geojson=data.get("geojson"),
                    buf_km=float(data.get("buf_km", 5)),
                    date=data.get("date"),
                ),
            )
            return Response(result)
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class BaselinesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(get_baselines_cached(lambda: DISTRICT_BASELINE))
