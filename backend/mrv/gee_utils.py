"""
GEE utilities for TerrAI forest health monitoring.

Optical path: Sentinel-2 SR + QA60 + S2_CLOUD_PROBABILITY (≤20%).
Temporal path: Max-NDVI composites to skip monsoon cloud dropouts.
Radar path: Sentinel-1 GRD RVI as monsoon / cloud fallback.
"""

from __future__ import annotations

from calendar import monthrange
from datetime import datetime, timedelta

import ee

# Pixels with cloud probability above this are masked (user requirement: >20%).
CLOUD_PROB_MAX = 20
# Scene-level cloudy metadata filter (pre-join; per-pixel mask is stricter).
SCENE_CLOUDY_PCT_MAX = 70


def mask_s2_clouds(image):
    """Legacy QA60-only mask (kept for callers that already divided/scaled)."""
    qa = image.select("QA60")
    cloud_bit_mask = 1 << 10
    cirrus_bit_mask = 1 << 11
    mask = qa.bitwiseAnd(cloud_bit_mask).eq(0).And(qa.bitwiseAnd(cirrus_bit_mask).eq(0))
    return image.updateMask(mask).divide(10000).copyProperties(image, ["system:time_start"])


def _mask_joined_s2(image, cloud_prob_max=CLOUD_PROB_MAX):
    """QA60 + COPERNICUS/S2_CLOUD_PROBABILITY per-pixel mask, then scale to reflectance."""
    qa = image.select("QA60")
    cloud_bit_mask = 1 << 10
    cirrus_bit_mask = 1 << 11
    qa_clear = qa.bitwiseAnd(cloud_bit_mask).eq(0).And(qa.bitwiseAnd(cirrus_bit_mask).eq(0))
    clouds = ee.Image(image.get("s2cloud")).select("probability")
    clear = qa_clear.And(clouds.lt(cloud_prob_max))
    return (
        image.updateMask(clear)
        .divide(10000)
        .copyProperties(image, ["system:time_start"])
    )


def s2_sr_collection(aoi, start_date, end_date, cloudy_pct=SCENE_CLOUDY_PCT_MAX):
    """Sentinel-2 SR joined to S2_CLOUD_PROBABILITY and cloud-masked."""
    s2 = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(aoi)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", cloudy_pct))
    )
    s2c = (
        ee.ImageCollection("COPERNICUS/S2_CLOUD_PROBABILITY")
        .filterBounds(aoi)
        .filterDate(start_date, end_date)
    )
    joined = ee.ImageCollection(
        ee.Join.saveFirst("s2cloud").apply(
            primary=s2,
            secondary=s2c,
            condition=ee.Filter.equals(leftField="system:index", rightField="system:index"),
        )
    )
    return joined.map(_mask_joined_s2)


def calculate_ndvi(image):
    ndvi = image.normalizedDifference(["B8", "B4"]).rename("NDVI")
    return image.addBands(ndvi)


def calculate_evi(image):
    """Enhanced Vegetation Index — less saturated than NDVI in dense canopies."""
    evi = image.expression(
        "2.5 * ((NIR - RED) / (NIR + 6 * RED - 7.5 * BLUE + 1))",
        {
            "NIR": image.select("B8"),
            "RED": image.select("B4"),
            "BLUE": image.select("B2"),
        },
    ).rename("EVI")
    return image.addBands(evi)


def get_sentinel_composite(aoi, start_date, end_date, reducer="median"):
    """
    Seasonal S2 composite with strict cloud masking.
    reducer: 'median' | 'max' — Max-NDVI skips transient cloud NDVI dropouts
    (pre-/post-monsoon peak greenness over a multi-month window).
    """
    collection = s2_sr_collection(aoi, start_date, end_date).map(calculate_ndvi).map(calculate_evi)
    ndvi = collection.select("NDVI")
    evi = collection.select("EVI")
    if reducer == "max":
        ndvi_img = ndvi.max().clip(aoi)
        evi_img = evi.max().clip(aoi)
    else:
        ndvi_img = ndvi.median().clip(aoi)
        evi_img = evi.median().clip(aoi)
    # Keep a reflectance band set for map tiles (median RGB-ish from masked stack)
    rgb = collection.select(["B4", "B3", "B2", "B8"]).median().clip(aoi)
    return rgb.addBands(ndvi_img).addBands(evi_img)


def get_max_ndvi_composite(aoi, start_date, end_date):
    """Peak-greenness composite — preferred for cloudy Nepal seasons."""
    return get_sentinel_composite(aoi, start_date, end_date, reducer="max")


def _db_to_linear(band):
    return ee.Image(10).pow(band.divide(10))


def get_sentinel1_rvi(aoi, start_date, end_date):
    """
    Sentinel-1 IW dual-pol Radar Vegetation Index:
        RVI = 4 * VH / (VV + VH)   (linear power domain)
    Penetrates monsoon cloud cover; sensitive to canopy structure/moisture.
    """
    s1 = (
        ee.ImageCollection("COPERNICUS/S1_GRD")
        .filterBounds(aoi)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.eq("instrumentMode", "IW"))
        .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
        .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VH"))
        .filter(ee.Filter.eq("resolution_meters", 10))
        .select(["VV", "VH"])
    )

    def add_rvi(img):
        vv = _db_to_linear(img.select("VV"))
        vh = _db_to_linear(img.select("VH"))
        rvi = vh.multiply(4).divide(vv.add(vh).max(1e-6)).rename("RVI")
        return rvi.copyProperties(img, ["system:time_start"])

    col = s1.map(add_rvi)
    return col.median().clip(aoi).rename("RVI")


def rvi_to_ndvi_proxy(rvi_mean: float | None) -> float | None:
    """Map typical forest RVI (~0.3–0.9) onto an NDVI-like [0.1, 0.85] scale."""
    if rvi_mean is None:
        return None
    r = max(0.0, min(1.2, float(rvi_mean)))
    return round(max(0.1, min(0.85, 0.15 + 0.75 * r)), 4)


def is_monsoon_window(start_date: str, end_date: str) -> bool:
    """Nepal monsoon roughly June–September."""
    try:
        s = datetime.strptime(str(start_date)[:10], "%Y-%m-%d")
        e = datetime.strptime(str(end_date)[:10], "%Y-%m-%d")
    except ValueError:
        return False
    months = set()
    cur = s
    while cur <= e and len(months) < 12:
        months.add(cur.month)
        cur += timedelta(days=20)
    return bool(months & {6, 7, 8, 9})


def compute_mean_band(image, aoi, band: str, scale=30):
    stats = image.select(band).reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=aoi,
        scale=scale,
        maxPixels=1e9,
    )
    val = stats.get(band).getInfo()
    return float(val) if val is not None else None


def compute_mean_ndvi(ndvi_image, aoi):
    return compute_mean_band(ndvi_image, aoi, "NDVI")


def compute_mean_ndvi_many(named_images: dict, aoi) -> dict:
    """One getInfo for many band means — prefers NDVI, falls back to first band."""
    payload = {}
    for key, img in named_images.items():
        band = "NDVI"
        payload[key] = img.select(band).reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=aoi,
            scale=30,
            maxPixels=1e9,
        ).get(band)
    return ee.Dictionary(payload).getInfo()


def hybrid_vegetation_metrics(aoi, start_date, end_date, *, prefer_max_ndvi=True):
    """
    Dual-informed optical + SAR metrics for one window.

    Returns dict with ndvi, evi, rvi, index (value used for biomass), source.
    During monsoon or when optical NDVI is missing, blends / substitutes S1 RVI.
    """
    use_max = prefer_max_ndvi or is_monsoon_window(start_date, end_date)
    reducer = "max" if use_max else "median"
    optical = get_sentinel_composite(aoi, start_date, end_date, reducer=reducer)

    # Batch optical means
    opt_means = ee.Dictionary(
        {
            "ndvi": optical.select("NDVI")
            .reduceRegion(ee.Reducer.mean(), aoi, 30, maxPixels=1e9)
            .get("NDVI"),
            "evi": optical.select("EVI")
            .reduceRegion(ee.Reducer.mean(), aoi, 30, maxPixels=1e9)
            .get("EVI"),
        }
    ).getInfo()

    ndvi = opt_means.get("ndvi")
    evi = opt_means.get("evi")
    if ndvi is not None:
        ndvi = float(ndvi)
    if evi is not None:
        evi = float(evi)

    rvi = None
    try:
        rvi_img = get_sentinel1_rvi(aoi, start_date, end_date)
        rvi = compute_mean_band(rvi_img, aoi, "RVI", scale=20)
    except Exception:
        rvi = None

    monsoon = is_monsoon_window(start_date, end_date)
    rvi_proxy = rvi_to_ndvi_proxy(rvi)

    if ndvi is None and rvi_proxy is not None:
        index, source = rvi_proxy, "sar_rvi"
    elif monsoon and ndvi is not None and rvi_proxy is not None:
        # Dual-informed: optical peak greenness + structural radar
        index = round(0.55 * ndvi + 0.45 * rvi_proxy, 4)
        source = "dual_optical_sar"
    elif ndvi is not None and evi is not None and ndvi >= 0.7:
        # Dense canopy: prefer EVI (less saturated) mapped toward NDVI range
        index = round(max(ndvi * 0.35 + float(evi) * 0.65, evi), 4)
        source = "evi_dense_canopy"
    elif ndvi is not None:
        index, source = ndvi, "optical_max_ndvi" if use_max else "optical_median"
    else:
        index, source = None, "none"

    return {
        "image": optical,
        "ndvi": ndvi,
        "evi": evi,
        "rvi": round(rvi, 4) if rvi is not None else None,
        "index": index,
        "source": source,
        "monsoon": monsoon,
        "reducer": reducer,
    }


def month_end_date(year: int, month: int) -> str:
    last = monthrange(year, month)[1]
    return f"{year}-{month:02d}-{last:02d}"


def calculate_ndvi_timeseries(aoi, year, start_month=1, end_month=12):
    """Monthly Max-NDVI with a single batched getInfo."""
    named = {}
    for month in range(start_month, end_month + 1):
        start_date = f"{year}-{month:02d}-01"
        if month == 12:
            end_date = f"{year + 1}-01-01"
        else:
            end_date = f"{year}-{month + 1:02d}-01"
        named[f"{year}-{month:02d}"] = get_sentinel_composite(
            aoi, start_date, end_date, reducer="max"
        )

    if not named:
        return []

    try:
        values = compute_mean_ndvi_many(named, aoi)
    except Exception:
        return []

    results = []
    for key in sorted(named.keys()):
        v = values.get(key)
        if v is not None:
            results.append({"month": key, "ndvi": round(float(v), 4)})
    return results


def get_ndvi_visualization_params():
    return {
        "min": 0,
        "max": 0.8,
        "palette": ["#d73027", "#fc8d59", "#fee08b", "#d9ef8b", "#91cf60", "#1a9850"],
    }


def get_ndvi_diff_visualization_params():
    return {
        "min": -0.3,
        "max": 0.3,
        "palette": ["#d73027", "#fc8d59", "#ffffbf", "#91cf60", "#1a9850"],
    }


def create_aoi_from_point(lat, lon, buffer_km=5):
    buf = float(buffer_km) if buffer_km and float(buffer_km) > 0 else 5.0
    return ee.Geometry.Point([lon, lat]).buffer(buf * 1000, 10)


def get_sentinel2_acquisition_dates(aoi, year, month):
    try:
        start = f"{year}-{month:02d}-01"
        end = f"{year + 1}-01-01" if month == 12 else f"{year}-{month + 1:02d}-01"
        col = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(aoi)
            .filterDate(start, end)
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 80))
        )
        dates_list = col.aggregate_array("system:time_start").getInfo() or []
        seen, dates = set(), []
        for ts in sorted(dates_list):
            d = datetime.utcfromtimestamp(ts / 1000).strftime("%Y-%m-%d")
            if d not in seen:
                seen.add(d)
                dates.append(d)
        return dates
    except Exception:
        return []


def get_sentinel_day_image(aoi, date_str: str, search_days: int = 7):
    """
    Best-effort single-day (or nearest) S2 image with cloud-prob mask + NDVI/EVI.
    """
    d = datetime.strptime(date_str, "%Y-%m-%d")
    d_next = (d + timedelta(days=1)).strftime("%Y-%m-%d")

    def _build(start, end):
        col = s2_sr_collection(aoi, start, end, cloudy_pct=90)
        return col

    col = _build(date_str, d_next)
    if col.size().eq(0).getInfo():
        start = (d - timedelta(days=search_days)).strftime("%Y-%m-%d")
        end = (d + timedelta(days=search_days + 1)).strftime("%Y-%m-%d")
        col = _build(start, end)
        if col.size().eq(0).getInfo():
            raise ValueError(
                f"No Sentinel-2 scenes near {date_str} (±{search_days}d) for this AOI. "
                "Pick another date from Pass Dates, or use a seasonal window."
            )
        target_ms = ee.Date(date_str).millis()
        with_dist = col.map(
            lambda im: im.set(
                "abs_dt", ee.Number(im.get("system:time_start")).subtract(target_ms).abs()
            )
        )
        img = ee.Image(with_dist.sort("abs_dt").first()).clip(aoi)
    else:
        img = col.median().clip(aoi)

    img = calculate_ndvi(img)
    img = calculate_evi(img)
    return img


def compute_daily_ndvi(aoi, date_str):
    try:
        ndvi_img = get_sentinel_day_image(aoi, date_str).select("NDVI")
        d = datetime.strptime(date_str, "%Y-%m-%d")
        d_next = (d + timedelta(days=1)).strftime("%Y-%m-%d")
        col = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(aoi)
            .filterDate(date_str, d_next)
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 80))
        )
        mean_val = ndvi_img.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=aoi,
            scale=20,
            maxPixels=1e9,
        ).get("NDVI").getInfo()
        cloud_pct = col.first().get("CLOUDY_PIXEL_PERCENTAGE").getInfo()
        vis = get_ndvi_visualization_params()
        tile_url = ndvi_img.getMapId(vis)["tile_fetcher"].url_format
        return {
            "ndvi": round(mean_val, 4) if mean_val is not None else None,
            "cloud_pct": round(cloud_pct, 1) if cloud_pct is not None else None,
            "tile_url": tile_url,
            "date": date_str,
        }
    except Exception:
        return {"ndvi": None, "cloud_pct": None, "tile_url": None, "date": date_str}
