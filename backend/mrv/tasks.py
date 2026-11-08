"""Celery / background tasks for GEE analysis."""

from __future__ import annotations

import logging

from django.utils import timezone as dj_tz

from .cache_utils import get_cached_analyze, set_cached_analyze
from .science import run_analysis

logger = logging.getLogger(__name__)

try:
    from celery import shared_task
except ImportError:  # pragma: no cover - Celery optional for local/thread mode

    def shared_task(*_args, **_kwargs):
        def decorator(fn):
            fn.delay = lambda *a, **k: (_ for _ in ()).throw(
                RuntimeError("Celery is not installed")
            )
            return fn

        if _args and callable(_args[0]) and not _kwargs:
            return decorator(_args[0])
        return decorator


def _payload_for_run(payload: dict) -> dict:
    return {
        "lat": float(payload["lat"]) if payload.get("lat") is not None else None,
        "lon": float(payload["lon"]) if payload.get("lon") is not None else None,
        "geojson": payload.get("geojson"),
        "buf_km": float(payload.get("buf_km", 5)),
        "year1": int(payload["year1"]) if payload.get("year1") is not None else None,
        "year2": int(payload["year2"]) if payload.get("year2") is not None else None,
        "start_month": int(payload.get("start_month", 1)),
        "end_month": int(payload.get("end_month", 3)),
        "start_day": int(payload.get("start_day", 1)),
        "end_day": int(payload["end_day"]) if payload.get("end_day") is not None else None,
        "baseline_date": payload.get("baseline_date") or payload.get("baseline_start"),
        "comparison_date": payload.get("comparison_date") or payload.get("comparison_start"),
        "baseline_start": payload.get("baseline_start"),
        "baseline_end": payload.get("baseline_end"),
        "comparison_start": payload.get("comparison_start"),
        "comparison_end": payload.get("comparison_end"),
        "forest_type": payload.get("forest_type", "default"),
        "run_multiyear": bool(payload.get("run_multiyear", False)),
        "run_monthly": bool(payload.get("run_monthly", True)),
        "run_hotspot": bool(payload.get("run_hotspot", True)),
        "project_id": payload.get("project_id"),
        "calibration_coefficient": payload.get("calibration_coefficient"),
        "field_baseline_agb_t_ha": payload.get("field_baseline_agb_t_ha"),
    }


def execute_analysis_job(job_id: str) -> dict:
    """Run (or cache-hit) an AnalysisJob. Used by Celery and thread fallback."""
    from .models import AnalysisJob

    job = AnalysisJob.objects.get(pk=job_id)
    if job.status in (AnalysisJob.Status.SUCCESS, AnalysisJob.Status.CACHED) and job.result:
        return job.result

    job.status = AnalysisJob.Status.RUNNING
    job.started_at = dj_tz.now()
    job.error = ""
    job.save(update_fields=["status", "started_at", "error"])

    try:
        cached = get_cached_analyze(job.cache_key) if job.cache_key else None
        if cached is not None:
            job.result = cached
            job.cache_hit = True
            job.status = AnalysisJob.Status.CACHED
            job.finished_at = dj_tz.now()
            job.save(update_fields=["result", "cache_hit", "status", "finished_at"])
            return cached

        result = run_analysis(**_payload_for_run(job.request_payload))
        if job.cache_key:
            set_cached_analyze(job.cache_key, result)
        job.result = result
        job.cache_hit = False
        job.status = AnalysisJob.Status.SUCCESS
        job.finished_at = dj_tz.now()
        job.save(update_fields=["result", "cache_hit", "status", "finished_at"])
        return result
    except Exception as exc:
        logger.exception("Analysis job %s failed", job_id)
        job.status = AnalysisJob.Status.FAILED
        job.error = str(exc)
        job.finished_at = dj_tz.now()
        job.save(update_fields=["status", "error", "finished_at"])
        raise


@shared_task(bind=True, name="mrv.run_analysis_job", max_retries=1, soft_time_limit=300, time_limit=360)
def run_analysis_job(self, job_id: str):
    return execute_analysis_job(job_id)


def enqueue_analysis_job(job_id: str) -> str:
    """
    Prefer Celery when a real broker + worker exist.
    memory:// (default without Redis) cannot process tasks without a worker —
    always fall back to a daemon thread so the dashboard does not hang forever.
    Returns 'celery' | 'thread' | 'eager'.
    """
    import threading

    from django.conf import settings

    if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
        execute_analysis_job(job_id)
        return "eager"

    broker = (getattr(settings, "CELERY_BROKER_URL", None) or "").strip().lower()
    # In-process / fake brokers accept .delay() but never execute without a worker.
    ephemeral = (
        not broker
        or broker.startswith("memory://")
        or broker.startswith("cache+")
        or broker.startswith("filesystem://")
    )

    if not ephemeral:
        try:
            run_analysis_job.delay(job_id)
            return "celery"
        except Exception as exc:
            logger.warning("Celery enqueue failed (%s); using background thread", exc)

    t = threading.Thread(target=execute_analysis_job, args=(job_id,), daemon=True)
    t.start()
    return "thread"
