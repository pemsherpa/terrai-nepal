"""Core forest-health science shared with the Streamlit prototype."""

from __future__ import annotations

import json
import math
import os
from calendar import monthrange
from datetime import datetime

import ee

from .gee_utils import (
    calculate_ndvi_timeseries,
    compute_daily_ndvi,
    create_aoi_from_point,
    get_ndvi_diff_visualization_params,
    get_ndvi_visualization_params,
    get_sentinel2_acquisition_dates,
    get_sentinel_day_image,
    hybrid_vegetation_metrics,
    month_end_date,
)
from .nepal_data import (
    apply_agb_saturation_cap,
    apply_field_calibration,
    resolve_regional_params,
    vegetation_scale,
)
from .vision import build_vision_explanation

# Legacy keys retained for PDF/UI labels; live math uses NEPAL_REGIONAL_PARAMS.
NEPAL_CARBON = {
    "tropical_broadleaf": {"agb": 180, "bgb_r": 0.26, "cf": 0.47},
    "subtropical_broadleaf": {"agb": 150, "bgb_r": 0.28, "cf": 0.47},
    "temperate_broadleaf": {"agb": 120, "bgb_r": 0.30, "cf": 0.47},
    "conifer": {"agb": 100, "bgb_r": 0.32, "cf": 0.51},
    "default": {"agb": 140, "bgb_r": 0.28, "cf": 0.47},
}
CO2_FACTOR = 3.667

# Strong current Groq model (llama3-70b-8192 decommissioned; llama-3.3-70b also sunsetting)
DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"

MN = {
    1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June",
    7: "July", 8: "August", 9: "September", 10: "October", 11: "November", 12: "December",
}
MS = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
    7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
}

DISTRICT_BASELINE = {
    "Dolakha": {"ndvi": 0.62, "forest_cover_pct": 48},
    "Sindhupalchok": {"ndvi": 0.58, "forest_cover_pct": 45},
    "Rasuwa": {"ndvi": 0.66, "forest_cover_pct": 62},
    "Nuwakot": {"ndvi": 0.55, "forest_cover_pct": 41},
    "Kavrepalanchok": {"ndvi": 0.54, "forest_cover_pct": 39},
    "Makwanpur": {"ndvi": 0.60, "forest_cover_pct": 52},
    "Chitwan": {"ndvi": 0.57, "forest_cover_pct": 44},
    "Nawalpur": {"ndvi": 0.52, "forest_cover_pct": 37},
    "Palpa": {"ndvi": 0.59, "forest_cover_pct": 49},
    "Gorkha": {"ndvi": 0.63, "forest_cover_pct": 55},
    "Lamjung": {"ndvi": 0.61, "forest_cover_pct": 53},
    "Kaski": {"ndvi": 0.64, "forest_cover_pct": 58},
    "Tanahu": {"ndvi": 0.56, "forest_cover_pct": 43},
    "Syangja": {"ndvi": 0.57, "forest_cover_pct": 44},
    "Parbat": {"ndvi": 0.60, "forest_cover_pct": 51},
    "Myagdi": {"ndvi": 0.65, "forest_cover_pct": 60},
    "Baglung": {"ndvi": 0.61, "forest_cover_pct": 54},
    "Dang": {"ndvi": 0.54, "forest_cover_pct": 38},
    "Banke": {"ndvi": 0.50, "forest_cover_pct": 34},
    "Bardiya": {"ndvi": 0.55, "forest_cover_pct": 41},
    "Kailali": {"ndvi": 0.51, "forest_cover_pct": 36},
    "Kanchanpur": {"ndvi": 0.49, "forest_cover_pct": 33},
    "Ilam": {"ndvi": 0.68, "forest_cover_pct": 63},
    "Taplejung": {"ndvi": 0.70, "forest_cover_pct": 66},
    "Panchthar": {"ndvi": 0.66, "forest_cover_pct": 60},
    "Dhankuta": {"ndvi": 0.64, "forest_cover_pct": 57},
    "Solukhumbu": {"ndvi": 0.55, "forest_cover_pct": 42},
    "Nepal (National Avg)": {"ndvi": 0.58, "forest_cover_pct": 45},
}

from pathlib import Path

_GEE_READY = False


def ensure_gee() -> None:
    global _GEE_READY
    if _GEE_READY:
        return
    pid = os.environ.get("GEE_PROJECT_ID", "himalayacarbon")
    if not pid:
        raise RuntimeError("GEE_PROJECT_ID is not configured in environment variables.")

    # 1. Service account JSON provided in environment
    sa_json = os.environ.get("EE_SERVICE_ACCOUNT_JSON") or os.environ.get("EARTHENGINE_SERVICE_ACCOUNT_JSON")
    if sa_json:
        try:
            key_data = json.loads(sa_json)
            credentials = ee.ServiceAccountCredentials(
                key_data["client_email"],
                key_data=key_data,
            )
            ee.Initialize(credentials=credentials, project=pid)
            _GEE_READY = True
            return
        except Exception:
            pass

    # 2. OAuth user credentials JSON string provided in environment (e.g. on Render)
    ee_creds = (
        os.environ.get("EE_CREDENTIALS_JSON")
        or os.environ.get("EARTHENGINE_CREDENTIALS")
        or os.environ.get("EARTHENGINE_TOKEN")
    )
    if ee_creds:
        try:
            creds_path = Path.home() / ".config" / "earthengine" / "credentials"
            creds_path.parent.mkdir(parents=True, exist_ok=True)
            creds_path.write_text(ee_creds.strip())
        except Exception:
            pass

    ee.Initialize(project=pid)
    _GEE_READY = True


def parse_geojson(data: dict):
    geom, name = None, "Drawn Boundary"
    t = data.get("type")
    if t == "FeatureCollection":
        feats = data.get("features", [])
        if not feats:
            raise ValueError("Empty FeatureCollection")
        geom = feats[0].get("geometry")
        props = feats[0].get("properties", {}) or {}
        name = props.get("name") or props.get("NAME") or name
    elif t == "Feature":
        geom = data.get("geometry")
        props = data.get("properties", {}) or {}
        name = props.get("name") or props.get("NAME") or name
    elif t in ("Polygon", "MultiPolygon"):
        geom = data
    else:
        raise ValueError(f"Unsupported GeoJSON type: {t}")
    if not geom:
        raise ValueError("No geometry found")
    aoi = ee.Geometry(geom)
    c = aoi.centroid(maxError=1).coordinates().getInfo()
    area = aoi.area(maxError=1).getInfo() / 10000
    return aoi, c[1], c[0], area, name


def carbon_estimate(
    veg_index,
    area_ha,
    ftype="default",
    change_pct=None,
    *,
    lat=None,
    lon=None,
    district=None,
    elevation_m=None,
    eco_zone=None,
    calibration_coefficient=None,
    field_baseline_agb_t_ha=None,
    index_source=None,
):
    if veg_index is None or area_ha <= 0:
        return None

    params = resolve_regional_params(
        lat=lat,
        lon=lon,
        district=district,
        elevation_m=elevation_m,
        eco_zone=eco_zone,
        forest_type=ftype,
    )
    sat = float(params["ndvi_sat"])
    sc = vegetation_scale(float(veg_index), sat, params["scale_mode"])
    agb_raw = float(params["baseline_agb"]) * sc
    agb, was_capped, ceiling = apply_agb_saturation_cap(agb_raw, veg_index, params)
    agb, coeff, calib_applied = apply_field_calibration(
        agb,
        calibration_coefficient=calibration_coefficient,
        field_baseline_agb_t_ha=field_baseline_agb_t_ha,
    )
    # Re-cap after calibration so field bias cannot explode credits past FRTC ceiling * 1.25
    hard_ceiling = ceiling * 1.25 if calib_applied else ceiling
    if agb > hard_ceiling:
        agb = hard_ceiling
        was_capped = True

    bgb = agb * float(params["root_shoot"])
    bio = agb + bgb
    c_ha = bio * float(params["cf"])
    co2_ha = c_ha * CO2_FACTOR
    ftype_out = params["default_forest_type"]
    res = dict(
        agb_ha=round(agb, 1),
        bgb_ha=round(bgb, 1),
        bio_ha=round(bio, 1),
        c_ha=round(c_ha, 1),
        co2_ha=round(co2_ha, 1),
        total_c=round(c_ha * area_ha),
        total_co2=round(co2_ha * area_ha),
        area_ha=round(area_ha, 1),
        ftype=ftype_out,
        regional_key=params["regional_key"],
        regional_label=params["regional_label"],
        eco_zone=params["zone_key"],
        eco_zone_name=params["zone_name"],
        eco_zone_shorthand=params["shorthand"],
        max_agb_t_ha=ceiling,
        baseline_agb=params["baseline_agb"],
        agb_capped=was_capped,
        ndvi_sat=sat,
        scale_mode=params["scale_mode"],
        vegetation_scale=round(sc, 4),
        veg_index=round(float(veg_index), 4),
        index_source=index_source,
        zone_resolved_via=params["resolved_via"],
        zone_district=params.get("district"),
        calibration_coefficient=round(coeff, 4),
        calibration_applied=calib_applied,
        field_baseline_agb_t_ha=field_baseline_agb_t_ha,
        suggested_calibration_coefficient=(
            round(float(field_baseline_agb_t_ha) / agb_raw, 4)
            if field_baseline_agb_t_ha and agb_raw > 0
            else None
        ),
    )
    if change_pct is not None:
        delta = res["total_co2"] * change_pct / 100
        res["co2_delta"] = round(delta)
        res["change_pct"] = round(change_pct, 1)
    return res


def annual_ndvi_series(aoi, start_m, end_m, start_yr=2019, start_day=1, end_day=28):
    """Batched annual Max-NDVI (+ SAR fallback metrics computed per year sequentially if needed)."""
    from .gee_utils import get_sentinel_composite, compute_mean_ndvi_many

    named = {}
    for yr in range(start_yr, datetime.now().year + 1):
        last = monthrange(yr, end_m)[1]
        ed = min(end_day, last)
        sd = min(start_day, monthrange(yr, start_m)[1])
        start = f"{yr}-{start_m:02d}-{sd:02d}"
        end = f"{yr}-{end_m:02d}-{ed:02d}"
        named[str(yr)] = get_sentinel_composite(aoi, start, _exclusive_end(end), reducer="max")

    if not named:
        return []
    try:
        values = compute_mean_ndvi_many(named, aoi)
    except Exception:
        return []

    results = []
    for yr in sorted(named.keys(), key=int):
        v = values.get(yr)
        if v is not None:
            results.append({"year": int(yr), "ndvi": round(float(v), 4)})
    return results


def _exclusive_end(date_str: str) -> str:
    """Earth Engine filterDate end is exclusive; bump inclusive YYYY-MM-DD by one day."""
    d = datetime.strptime(date_str, "%Y-%m-%d")
    from datetime import timedelta

    return (d.replace(hour=0) + timedelta(days=1)).strftime("%Y-%m-%d")


def trend_stats(data):
    if len(data) < 2:
        return 0, "stable"
    xs = [d["year"] for d in data]
    ys = [d["ndvi"] for d in data]
    xm, ym = sum(xs) / len(xs), sum(ys) / len(ys)
    num = sum((xs[i] - xm) * (ys[i] - ym) for i in range(len(xs)))
    den = sum((xs[i] - xm) ** 2 for i in range(len(xs)))
    slope = num / den if den else 0
    direction = "improving" if slope > 0.001 else ("declining" if slope < -0.001 else "stable")
    return slope, direction


def ndvi_quality_label(ndvi):
    if ndvi is None:
        return "N/A"
    if ndvi >= 0.6:
        return "Dense Forest"
    if ndvi >= 0.4:
        return "Moderate Vegetation"
    if ndvi >= 0.2:
        return "Sparse Vegetation"
    return "Bare / Degraded"


def _resolve_windows(data_like: dict):
    """
    Resolve date windows for baseline (year1) and comparison (year2).

    Modes:
    - Single dates: baseline_date + comparison_date (YYYY-MM-DD) — one day each
    - Legacy aliases: baseline_start / comparison_start used as those single dates
    - Season months on years: year1/year2 + start_month/end_month (+ optional start_day/end_day)
    """
    y1 = int(data_like.get("year1") or datetime.now().year - 2)
    y2 = int(data_like.get("year2") or datetime.now().year)
    sm = int(data_like.get("start_month") or 1)
    em = int(data_like.get("end_month") or 3)
    sd = int(data_like.get("start_day") or 1)
    ed = int(data_like.get("end_day") or monthrange(y1, em)[1])

    # One date for baseline, one for comparison
    b_date = data_like.get("baseline_date") or data_like.get("baseline_start")
    c_date = data_like.get("comparison_date") or data_like.get("comparison_start")
    # If legacy end fields were sent alone, ignore range — single date mode only
    if b_date and c_date:
        y1 = int(str(b_date)[:4])
        y2 = int(str(c_date)[:4])
        return b_date, b_date, c_date, c_date, y1, y2, sm, em, sd, ed

    # Apply day-of-month window to each year
    sd1 = min(sd, monthrange(y1, sm)[1])
    ed1 = min(ed, monthrange(y1, em)[1])
    sd2 = min(sd, monthrange(y2, sm)[1])
    ed2 = min(ed, monthrange(y2, em)[1])
    return (
        f"{y1}-{sm:02d}-{sd1:02d}",
        f"{y1}-{em:02d}-{ed1:02d}",
        f"{y2}-{sm:02d}-{sd2:02d}",
        f"{y2}-{em:02d}-{ed2:02d}",
        y1,
        y2,
        sm,
        em,
        sd,
        ed,
    )


def run_analysis(
    *,
    lat=None,
    lon=None,
    geojson=None,
    buf_km=5.0,
    year1=None,
    year2=None,
    start_month=1,
    end_month=3,
    start_day=1,
    end_day=None,
    baseline_date=None,
    comparison_date=None,
    baseline_start=None,
    baseline_end=None,
    comparison_start=None,
    comparison_end=None,
    forest_type="default",
    run_multiyear=False,
    run_monthly=True,
    run_hotspot=True,
    calibration_coefficient=None,
    field_baseline_agb_t_ha=None,
    project_id=None,
):
    ensure_gee()
    name = None
    if geojson:
        aoi, lat, lon, area_ha, name = parse_geojson(geojson)
        buf_km = 0
    else:
        if lat is None or lon is None:
            raise ValueError("Must provide either lat/lon or geojson")
        aoi = create_aoi_from_point(lat, lon, buf_km)
        area_ha = math.pi * (buf_km ** 2) * 100

    # Optional project-level field calibration hook
    if project_id and (calibration_coefficient is None or field_baseline_agb_t_ha is None):
        try:
            from forests.models import Project

            proj = Project.objects.filter(pk=project_id).first()
            if proj:
                if calibration_coefficient is None:
                    calibration_coefficient = proj.calibration_coefficient
                if field_baseline_agb_t_ha is None:
                    field_baseline_agb_t_ha = proj.field_baseline_agb_t_ha
        except Exception:
            pass

    payload = {
        "year1": year1,
        "year2": year2,
        "start_month": start_month,
        "end_month": end_month,
        "start_day": start_day,
        "end_day": end_day or month_end_date(int(year1 or 2022), int(end_month)).split("-")[2],
        "baseline_date": baseline_date or baseline_start,
        "comparison_date": comparison_date or comparison_start,
        "baseline_start": baseline_date or baseline_start,
        "comparison_start": comparison_date or comparison_start,
    }
    b0, b1, c0, c1, y1, y2, sm, em, sd, ed = _resolve_windows(payload)

    single_date = b0 == b1 and c0 == c1
    if single_date:
        # Day images stay optical; SAR fills gaps via hybrid on ±15d window around each date
        c1_img = get_sentinel_day_image(aoi, b0)
        c2_img = get_sentinel_day_image(aoi, c0)
        from datetime import timedelta as _td

        def _day_window(ds: str):
            d = datetime.strptime(ds, "%Y-%m-%d")
            return (d - _td(days=15)).strftime("%Y-%m-%d"), (d + _td(days=16)).strftime("%Y-%m-%d")

        b_s, b_e = _day_window(b0)
        c_s, c_e = _day_window(c0)
        m1 = hybrid_vegetation_metrics(aoi, b_s, b_e, prefer_max_ndvi=True)
        m2 = hybrid_vegetation_metrics(aoi, c_s, c_e, prefer_max_ndvi=True)
        # Prefer day-image NDVI when present; else hybrid index
        from .gee_utils import compute_mean_ndvi_many

        day_means = compute_mean_ndvi_many({"n1": c1_img, "n2": c2_img}, aoi)
        n1 = float(day_means["n1"]) if day_means.get("n1") is not None else m1.get("index")
        n2 = float(day_means["n2"]) if day_means.get("n2") is not None else m2.get("index")
        src1, src2 = m1.get("source"), m2.get("source")
        if day_means.get("n1") is not None:
            src1 = "optical_day"
        if day_means.get("n2") is not None:
            src2 = "optical_day"
        # Use hybrid images for tiles when day optical failed
        if day_means.get("n1") is None:
            c1_img = m1["image"]
        if day_means.get("n2") is None:
            c2_img = m2["image"]
        evi1, evi2 = m1.get("evi"), m2.get("evi")
        rvi1, rvi2 = m1.get("rvi"), m2.get("rvi")
    else:
        m1 = hybrid_vegetation_metrics(aoi, b0, _exclusive_end(b1), prefer_max_ndvi=True)
        m2 = hybrid_vegetation_metrics(aoi, c0, _exclusive_end(c1), prefer_max_ndvi=True)
        c1_img, c2_img = m1["image"], m2["image"]
        n1, n2 = m1.get("index"), m2.get("index")
        src1, src2 = m1.get("source"), m2.get("source")
        evi1, evi2 = m1.get("evi"), m2.get("evi")
        rvi1, rvi2 = m1.get("rvi"), m2.get("rvi")

    dpct = ((n2 - n1) / n1 * 100) if (n1 and n2 and n1 != 0) else 0.0
    cd = carbon_estimate(
        n2,
        area_ha,
        forest_type,
        dpct,
        lat=lat,
        lon=lon,
        calibration_coefficient=calibration_coefficient,
        field_baseline_agb_t_ha=field_baseline_agb_t_ha,
        index_source=src2,
    )

    ts = calculate_ndvi_timeseries(aoi, y2, sm, em) if (run_monthly and not single_date) else []
    trend_data = (
        annual_ndvi_series(aoi, sm, em, start_day=sd, end_day=ed)
        if (run_multiyear and not single_date)
        else []
    )

    vis = get_ndvi_visualization_params()
    tile_url_y1 = c1_img.select("NDVI").getMapId(vis)["tile_fetcher"].url_format
    tile_url_y2 = c2_img.select("NDVI").getMapId(vis)["tile_fetcher"].url_format

    tile_url_hotspot = None
    if run_hotspot:
        diff = c2_img.select("NDVI").subtract(c1_img.select("NDVI")).rename("NDVI_DIFF")
        tile_url_hotspot = diff.getMapId(get_ndvi_diff_visualization_params())["tile_fetcher"].url_format

    slope, direction = trend_stats(trend_data) if trend_data else (0, "stable")
    zone_meta = (cd or {}).get("eco_zone_name") and {
        "eco_zone": cd.get("eco_zone"),
        "eco_zone_name": cd.get("eco_zone_name"),
        "eco_zone_shorthand": cd.get("eco_zone_shorthand"),
        "regional_key": cd.get("regional_key"),
        "regional_label": cd.get("regional_label"),
        "max_agb_t_ha": cd.get("max_agb_t_ha"),
        "agb_capped": cd.get("agb_capped"),
        "scale_mode": cd.get("scale_mode"),
    }
    vision_explanation = build_vision_explanation(
        ndvi_before=n1,
        ndvi_after=n2,
        change_pct=dpct,
        evi_before=evi1,
        evi_after=evi2,
        rvi_before=rvi1,
        rvi_after=rvi2,
    )

    return {
        "ndvi_year1": n1,
        "ndvi_year2": n2,
        "evi_year1": evi1,
        "evi_year2": evi2,
        "rvi_year1": rvi1,
        "rvi_year2": rvi2,
        "index_source_year1": src1,
        "index_source_year2": src2,
        "change_pct": round(dpct, 2),
        "carbon_estimate": cd,
        "eco_zone": zone_meta,
        "trend_data": trend_data,
        "monthly_series": ts,
        "area_ha": round(area_ha, 2),
        "tile_url": tile_url_y2,
        "tile_url_year1": tile_url_y1,
        "tile_url_year2": tile_url_y2,
        "tile_url_hotspot": tile_url_hotspot,
        "lat": lat,
        "lon": lon,
        "buf_km": buf_km,
        "aoi_name": name,
        "trend_slope": slope,
        "trend_direction": direction,
        "baseline_date": b0,
        "comparison_date": c0,
        "baseline_start": b0,
        "baseline_end": b1,
        "comparison_start": c0,
        "comparison_end": c1,
        "year1": y1,
        "year2": y2,
        "single_date_mode": single_date,
        "project_id": str(project_id) if project_id else None,
        "vision_explanation": vision_explanation,
    }


def resolve_aoi(lat=None, lon=None, geojson=None, buf_km=5.0):
    ensure_gee()
    if geojson:
        return parse_geojson(geojson)
    if lat is None or lon is None:
        raise ValueError("Must provide either lat/lon or geojson")
    aoi = create_aoi_from_point(lat, lon, buf_km)
    area_ha = math.pi * (buf_km ** 2) * 100
    return aoi, lat, lon, area_ha, None


def list_pass_dates(*, lat=None, lon=None, geojson=None, buf_km=5.0, year=None, month=None):
    aoi, lat, lon, _area, _name = resolve_aoi(lat, lon, geojson, buf_km)
    dates = get_sentinel2_acquisition_dates(aoi, int(year), int(month))
    return {"dates": dates, "lat": lat, "lon": lon}


def daily_ndvi(*, lat=None, lon=None, geojson=None, buf_km=5.0, date=None):
    aoi, lat, lon, _area, _name = resolve_aoi(lat, lon, geojson, buf_km)
    result = compute_daily_ndvi(aoi, date)
    result["quality"] = ndvi_quality_label(result.get("ndvi"))
    result["lat"] = lat
    result["lon"] = lon
    return result


def call_groq(api_key, loc, lat, lon, y1, y2, sm, em, n1, n2, dpct, ts, cd, td, date_note=""):
    try:
        from groq import Groq
    except ImportError:
        return None, "install_groq"
    try:
        client = Groq(api_key=api_key)
        model = os.environ.get("GROQ_MODEL", DEFAULT_GROQ_MODEL)
        status = "CRITICAL" if dpct < -10 else "WARNING" if dpct < -5 else "STABLE" if dpct < 0 else "HEALTHY"
        carbon_str = (
            f"CO2e stock: {cd['co2_ha']} t CO2e/ha, total {cd['total_co2']:,} t CO2e" if cd else ""
        )
        trend_str = "Annual NDVI: " + ", ".join(f"{d['year']}:{d['ndvi']}" for d in td) if td else ""
        period = date_note or f"{MN.get(sm, sm)}-{MN.get(em, em)}, {y1} vs {y2}"
        prompt = f"""Senior environmental scientist specializing in Himalayan forest MRV, Nepal.

DATA:
Location: {loc} ({lat:.4f}N {lon:.4f}E)
Period: {period}
NDVI {y1}: {f'{n1:.4f}' if n1 else 'N/A'} | NDVI {y2}: {f'{n2:.4f}' if n2 else 'N/A'}
Change: {dpct:+.2f}% | Status: {status}
{carbon_str}
{trend_str}

CRITICAL FORMATTING RULES:
- Use standard ASCII characters only.
- For hyphenated words, use plain ASCII hyphen '-' (do NOT use unicode non-breaking hyphens, en-dashes, or em-dashes).
- For units, write 't CO2e/ha', 't CO2e/ha/yr', 'ha^-1', 'yr^-1' (do NOT use unicode superscript characters like ⁻, ¹, ², ³).
- Use plain straight quotes " and '.

Return ONLY valid JSON (no markdown):
{{"executive_summary":"2-3 sentence overview.",
"key_findings":["f1","f2","f3","f4"],
"vegetation_analysis":"paragraph with specific numbers.",
"carbon_implications":"paragraph on CO2e implications.",
"risk_level":"LOW|MEDIUM|HIGH|CRITICAL",
"risk_assessment":"paragraph on risk drivers.",
"recommendations":["r1","r2","r3","r4"],
"data_confidence":"data quality notes.",
"next_monitoring":"timeframe suggestion."}}"""
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.25,
            max_tokens=1400,
        )
        raw = resp.choices[0].message.content.strip().replace("```json", "").replace("```", "").strip()
        # Some reasoning models wrap JSON — extract object if needed
        if not raw.startswith("{"):
            start = raw.find("{")
            end = raw.rfind("}")
            if start >= 0 and end > start:
                raw = raw[start : end + 1]

        def _clean_text(obj):
            if isinstance(obj, str):
                s = obj
                for ch in ["\u2010", "\u2011", "\u2012", "\u00ad", "\u2212"]:
                    s = s.replace(ch, "-")
                s = s.replace("\u2013", "-").replace("\u2014", " - ")
                s = s.replace("ha⁻¹", "ha^-1").replace("ha-1", "ha^-1")
                s = s.replace("yr⁻¹", "yr^-1").replace("yr-1", "yr^-1")
                s = s.replace("⁻¹", "^-1").replace("⁻²", "^-2").replace("⁻³", "^-3")
                s = s.replace("⁻", "-").replace("¹", "1").replace("²", "2").replace("³", "3")
                for sup, digit in [("⁰", "0"), ("⁴", "4"), ("⁵", "5"), ("⁶", "6"), ("⁷", "7"), ("⁸", "8"), ("⁹", "9")]:
                    s = s.replace(sup, digit)
                s = s.replace("\u2018", "'").replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"')
                s = s.replace("\u00a0", " ").replace("\u202f", " ").replace("\u200b", "")
                return s
            if isinstance(obj, list):
                return [_clean_text(item) for item in obj]
            if isinstance(obj, dict):
                return {k: _clean_text(v) for k, v in obj.items()}
            return obj

        return _clean_text(json.loads(raw)), None
    except json.JSONDecodeError as e:
        return None, f"JSON error: {e}"
    except Exception as e:
        return None, str(e)
