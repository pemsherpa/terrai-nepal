"""Shared cache helpers for GEE analysis results and baselines."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from django.core.cache import cache

# Metrics/results: reuse across users for identical AOI+params
ANALYZE_TTL = 60 * 60 * 24 * 7  # 7 days
# GEE map tile URLs expire; keep shorter
TILE_TTL = 60 * 60 * 6  # 6 hours
BASELINE_TTL = 60 * 60 * 24 * 30  # 30 days
PASS_DATES_TTL = 60 * 60 * 12
DAILY_NDVI_TTL = 60 * 60 * 24


def _stable_dumps(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))


def analyze_cache_key(payload: dict) -> str:
    """Fingerprint of analysis inputs — identical forests share one GEE hit."""
    relevant = {
        "lat": round(float(payload["lat"]), 5) if payload.get("lat") is not None else None,
        "lon": round(float(payload["lon"]), 5) if payload.get("lon") is not None else None,
        "geojson": payload.get("geojson"),
        "buf_km": round(float(payload.get("buf_km", 5)), 2),
        "year1": payload.get("year1"),
        "year2": payload.get("year2"),
        "start_month": payload.get("start_month"),
        "end_month": payload.get("end_month"),
        "start_day": payload.get("start_day"),
        "end_day": payload.get("end_day"),
        "baseline_date": payload.get("baseline_date") or payload.get("baseline_start"),
        "comparison_date": payload.get("comparison_date") or payload.get("comparison_start"),
        "forest_type": payload.get("forest_type", "default"),
        "run_multiyear": bool(payload.get("run_multiyear", False)),
        "run_monthly": bool(payload.get("run_monthly", True)),
        "run_hotspot": bool(payload.get("run_hotspot", True)),
        "project_id": str(payload.get("project_id") or ""),
        "calibration_coefficient": payload.get("calibration_coefficient"),
    }
    digest = hashlib.sha256(_stable_dumps(relevant).encode()).hexdigest()[:40]
    return f"mrv:analyze:{digest}"


def get_cached_analyze(key: str) -> dict | None:
    return cache.get(key)


def set_cached_analyze(key: str, result: dict) -> None:
    # Split: store full result; tiles also get shorter dedicated keys if present
    cache.set(key, result, ANALYZE_TTL)
    tiles = {
        k: result.get(k)
        for k in ("tile_url", "tile_url_year1", "tile_url_year2", "tile_url_hotspot")
        if result.get(k)
    }
    if tiles:
        cache.set(f"{key}:tiles", tiles, TILE_TTL)


def get_baselines_cached(fetcher) -> dict:
    key = "mrv:baselines:v1"
    data = cache.get(key)
    if data is not None:
        return data
    data = fetcher()
    cache.set(key, data, BASELINE_TTL)
    return data


def pass_dates_cache_key(payload: dict) -> str:
    blob = {
        "lat": payload.get("lat"),
        "lon": payload.get("lon"),
        "geojson": payload.get("geojson"),
        "buf_km": payload.get("buf_km"),
        "year": payload.get("year"),
        "month": payload.get("month"),
    }
    digest = hashlib.sha256(_stable_dumps(blob).encode()).hexdigest()[:32]
    return f"mrv:pass:{digest}"


def daily_ndvi_cache_key(payload: dict) -> str:
    blob = {
        "lat": payload.get("lat"),
        "lon": payload.get("lon"),
        "geojson": payload.get("geojson"),
        "buf_km": payload.get("buf_km"),
        "date": payload.get("date"),
    }
    digest = hashlib.sha256(_stable_dumps(blob).encode()).hexdigest()[:32]
    return f"mrv:daily:{digest}"


def cache_get_or_set(key: str, ttl: int, producer) -> Any:
    hit = cache.get(key)
    if hit is not None:
        return hit
    value = producer()
    cache.set(key, value, ttl)
    return value
