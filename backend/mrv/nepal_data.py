"""
Nepal eco-zonal reference data for TerrAI MRV.

Physiographic zones follow the five belts used by Nepal's Forest Research and
Training Centre (FRTC) / Department of Forests and ICIMOD regional profiles:

  Terai → Siwaliks (Churia) → Middle Mountains → High Mountains → High Himal

AGB ceilings are conservative mature-canopy caps (t dry matter / ha) anchored to
FRTC Forest Resource Assessment ranges and ICIMOD Himalayan canopy profiles.
They are used to stop NDVI-driven over-crediting once tropical/subtropical
canopies saturate (especially Terai sites such as Chitwan).
"""

from __future__ import annotations

import math
from typing import Any

# Nepal geographic centre (for map defaults)
NEPAL_CENTER = {"lat": 28.3949, "lon": 84.1240, "zoom": 7}

# ---------------------------------------------------------------------------
# Five physiological / physiographic ecological zones
# ---------------------------------------------------------------------------
# elevation_m: indicative FRTC belts (m a.s.l.)
# regional_key: NEPAL_REGIONAL_PARAMS forest stratum
# shorthand: localized eco-zonal label for UI / reports

ECO_ZONES: dict[str, dict[str, Any]] = {
    "terai": {
        "name": "Terai",
        "shorthand": "TR",
        "elevation_m": (0, 300),
        "regional_key": "terai_sal",
        "notes": "Tropical moist plains; rapid NDVI saturation — apply strict AGB cap.",
        "sources": ("FRTC FRA", "ICIMOD Terai canopy profiles"),
    },
    "siwaliks": {
        "name": "Siwaliks",
        "shorthand": "SW",
        "elevation_m": (300, 1000),
        "regional_key": "siwalik_mixed",
        "notes": "Churia foothills; subtropical deciduous / mixed hardwood.",
        "sources": ("FRTC Churia", "ICIMOD Siwalik profiles"),
    },
    "middle_mountains": {
        "name": "Middle Mountains",
        "shorthand": "MM",
        "elevation_m": (1000, 3000),
        "regional_key": "midhill_broadleaf",
        "notes": "Mid-hill broadleaf and mixed forests.",
        "sources": ("FRTC Mid-hills", "ICIMOD regional profiles"),
    },
    "high_mountains": {
        "name": "High Mountains",
        "shorthand": "HM",
        "elevation_m": (3000, 4000),
        "regional_key": "high_mountain_conifer",
        "notes": "Upper montane conifer / mixed stands.",
        "sources": ("FRTC High Mountains", "ICIMOD"),
    },
    "high_himal": {
        "name": "High Himal",
        "shorthand": "HH",
        "elevation_m": (4000, 8849),
        "regional_key": "high_himal_scrub",
        "notes": "Alpine scrub / sparse woody biomass — low AGB ceiling.",
        "sources": ("FRTC High Himal", "ICIMOD alpine profiles"),
    },
}

# Localized forest-type strata (FRTC / ICIMOD-anchored). Prefer these over generic NEPAL_CARBON.
# scale_mode: 'log' | 'evi_like' | 'linear' — non-linear near dense tropical canopies.
NEPAL_REGIONAL_PARAMS: dict[str, dict[str, Any]] = {
    "terai_sal": {
        "label": "Terai Sal / moist tropical",
        "baseline_agb": 245.0,  # FRTC mature Sal-range mid (200–300 t/ha)
        "root_shoot": 0.20,
        "cf": 0.47,
        "ndvi_max_saturation": 0.82,
        "max_agb_t_ha": 280.0,
        "scale_mode": "log",
        "legacy_ftype": "tropical_broadleaf",
    },
    "siwalik_mixed": {
        "label": "Siwalik / Churia mixed hardwood",
        "baseline_agb": 185.0,
        "root_shoot": 0.24,
        "cf": 0.47,
        "ndvi_max_saturation": 0.78,
        "max_agb_t_ha": 220.0,
        "scale_mode": "log",
        "legacy_ftype": "subtropical_broadleaf",
    },
    "midhill_broadleaf": {
        "label": "Middle Mountain broadleaf",
        "baseline_agb": 155.0,
        "root_shoot": 0.28,
        "cf": 0.47,
        "ndvi_max_saturation": 0.80,
        "max_agb_t_ha": 190.0,
        "scale_mode": "evi_like",
        "legacy_ftype": "temperate_broadleaf",
    },
    "high_mountain_conifer": {
        "label": "High Mountain conifer",
        "baseline_agb": 120.0,  # 100–150 t/ha FRTC/ICIMOD
        "root_shoot": 0.26,
        "cf": 0.51,
        "ndvi_max_saturation": 0.68,
        "max_agb_t_ha": 150.0,
        "scale_mode": "evi_like",
        "legacy_ftype": "conifer",
    },
    "high_himal_scrub": {
        "label": "High Himal scrub / sparse woody",
        "baseline_agb": 55.0,
        "root_shoot": 0.30,
        "cf": 0.47,
        "ndvi_max_saturation": 0.55,
        "max_agb_t_ha": 75.0,
        "scale_mode": "linear",
        "legacy_ftype": "conifer",
    },
}

# Map legacy UI forest_type keys → regional strata when user picks explicitly
LEGACY_FTYPE_TO_REGIONAL = {
    "tropical_broadleaf": "terai_sal",
    "subtropical_broadleaf": "siwalik_mixed",
    "temperate_broadleaf": "midhill_broadleaf",
    "conifer": "high_mountain_conifer",
    "default": None,
}

# Aliases for UI / API (physiological spellings included)
ECO_ZONE_ALIASES = {
    "terai": "terai",
    "siwalik": "siwaliks",
    "siwaliks": "siwaliks",
    "churia": "siwaliks",
    "middle_mountains": "middle_mountains",
    "middle mountains": "middle_mountains",
    "mid-hills": "middle_mountains",
    "midhills": "middle_mountains",
    "high_mountains": "high_mountains",
    "high mountains": "high_mountains",
    "high_himal": "high_himal",
    "high himal": "high_himal",
    "himalaya": "high_himal",
}

# District → primary physiographic zone (dominant belt at district centre).
# Chitwan and other Terai/Churia districts get Terai/Siwalik caps explicitly.
DISTRICT_ECO_ZONE: dict[str, str] = {
    # Koshi
    "Jhapa": "terai",
    "Morang": "terai",
    "Sunsari": "terai",
    "Udayapur": "siwaliks",
    "Ilam": "middle_mountains",
    "Dhankuta": "middle_mountains",
    "Panchthar": "middle_mountains",
    "Terhathum": "middle_mountains",
    "Bhojpur": "middle_mountains",
    "Khotang": "middle_mountains",
    "Okhaldhunga": "middle_mountains",
    "Sankhuwasabha": "high_mountains",
    "Solukhumbu": "high_himal",
    "Taplejung": "high_mountains",
    # Madhesh
    "Bara": "terai",
    "Dhanusha": "terai",
    "Mahottari": "terai",
    "Parsa": "terai",
    "Rautahat": "terai",
    "Saptari": "terai",
    "Sarlahi": "terai",
    "Siraha": "terai",
    # Bagmati
    "Chitwan": "terai",  # tropical NDVI saturation risk — Terai AGB cap
    "Makwanpur": "siwaliks",
    "Sindhuli": "siwaliks",
    "Bhaktapur": "middle_mountains",
    "Kathmandu": "middle_mountains",
    "Lalitpur": "middle_mountains",
    "Kavrepalanchok": "middle_mountains",
    "Dhading": "middle_mountains",
    "Nuwakot": "middle_mountains",
    "Ramechhap": "middle_mountains",
    "Dolakha": "high_mountains",
    "Sindhupalchok": "high_mountains",
    "Rasuwa": "high_mountains",
    # Gandaki
    "Nawalpur": "terai",
    "Tanahun": "middle_mountains",
    "Tanahu": "middle_mountains",
    "Syangja": "middle_mountains",
    "Kaski": "middle_mountains",
    "Lamjung": "middle_mountains",
    "Gorkha": "middle_mountains",
    "Parbat": "middle_mountains",
    "Baglung": "middle_mountains",
    "Myagdi": "high_mountains",
    "Manang": "high_himal",
    "Mustang": "high_himal",
    # Lumbini
    "Kapilvastu": "terai",
    "Rupandehi": "terai",
    "Parasi": "terai",
    "Banke": "terai",
    "Bardiya": "terai",
    "Dang": "siwaliks",
    "Palpa": "middle_mountains",
    "Arghakhanchi": "middle_mountains",
    "Gulmi": "middle_mountains",
    "Pyuthan": "middle_mountains",
    "Rolpa": "middle_mountains",
    "Rukum East": "high_mountains",
    # Karnali
    "Surkhet": "middle_mountains",
    "Salyan": "middle_mountains",
    "Dailekh": "middle_mountains",
    "Jajarkot": "middle_mountains",
    "Rukum West": "high_mountains",
    "Jumla": "high_mountains",
    "Kalikot": "high_mountains",
    "Mugu": "high_himal",
    "Dolpa": "high_himal",
    "Humla": "high_himal",
    # Sudurpashchim
    "Kailali": "terai",
    "Kanchanpur": "terai",
    "Dadeldhura": "middle_mountains",
    "Doti": "middle_mountains",
    "Achham": "middle_mountains",
    "Baitadi": "middle_mountains",
    "Bajhang": "high_mountains",
    "Bajura": "high_mountains",
    "Darchula": "high_mountains",
}

NEPAL_DISTRICTS = {
    "Bhojpur": {"lat": 27.1767, "lon": 87.0508},
    "Dhankuta": {"lat": 26.9826, "lon": 87.3469},
    "Ilam": {"lat": 26.9093, "lon": 87.9264},
    "Jhapa": {"lat": 26.5455, "lon": 87.8942},
    "Khotang": {"lat": 27.0217, "lon": 86.8425},
    "Morang": {"lat": 26.6650, "lon": 87.4628},
    "Okhaldhunga": {"lat": 27.3145, "lon": 86.5006},
    "Panchthar": {"lat": 27.1321, "lon": 87.7567},
    "Sankhuwasabha": {"lat": 27.3517, "lon": 87.2017},
    "Solukhumbu": {"lat": 27.7909, "lon": 86.6617},
    "Sunsari": {"lat": 26.6544, "lon": 87.1780},
    "Taplejung": {"lat": 27.3512, "lon": 87.6698},
    "Terhathum": {"lat": 27.1267, "lon": 87.5517},
    "Udayapur": {"lat": 26.9333, "lon": 86.5167},
    "Bara": {"lat": 27.0167, "lon": 85.0000},
    "Dhanusha": {"lat": 26.8333, "lon": 85.9167},
    "Mahottari": {"lat": 26.8667, "lon": 85.7667},
    "Parsa": {"lat": 27.1333, "lon": 84.8667},
    "Rautahat": {"lat": 27.0000, "lon": 85.2667},
    "Saptari": {"lat": 26.6333, "lon": 86.7333},
    "Sarlahi": {"lat": 26.9833, "lon": 85.5667},
    "Siraha": {"lat": 26.6533, "lon": 86.2178},
    "Bhaktapur": {"lat": 27.6710, "lon": 85.4298},
    "Chitwan": {"lat": 27.5291, "lon": 84.3542},
    "Dhading": {"lat": 27.8667, "lon": 84.9167},
    "Dolakha": {"lat": 27.7833, "lon": 86.0667},
    "Kathmandu": {"lat": 27.7172, "lon": 85.3240},
    "Kavrepalanchok": {"lat": 27.5500, "lon": 85.5500},
    "Lalitpur": {"lat": 27.6667, "lon": 85.3167},
    "Makwanpur": {"lat": 27.4167, "lon": 85.0333},
    "Nuwakot": {"lat": 27.9000, "lon": 85.1667},
    "Ramechhap": {"lat": 27.5333, "lon": 86.0833},
    "Rasuwa": {"lat": 28.0833, "lon": 85.3833},
    "Sindhuli": {"lat": 27.2500, "lon": 85.9667},
    "Sindhupalchok": {"lat": 27.9500, "lon": 85.7000},
    "Baglung": {"lat": 28.2667, "lon": 83.5833},
    "Gorkha": {"lat": 28.0000, "lon": 84.6333},
    "Kaski": {"lat": 28.2096, "lon": 83.9856},
    "Lamjung": {"lat": 28.2833, "lon": 84.3500},
    "Manang": {"lat": 28.5500, "lon": 84.0167},
    "Mustang": {"lat": 28.9983, "lon": 83.8500},
    "Myagdi": {"lat": 28.5500, "lon": 83.4667},
    "Nawalpur": {"lat": 27.6500, "lon": 84.1000},
    "Parbat": {"lat": 28.2000, "lon": 83.6833},
    "Syangja": {"lat": 28.0833, "lon": 83.8667},
    "Tanahun": {"lat": 27.9333, "lon": 84.2500},
    "Arghakhanchi": {"lat": 27.9333, "lon": 83.1167},
    "Banke": {"lat": 28.0600, "lon": 81.6300},
    "Bardiya": {"lat": 28.4167, "lon": 81.4167},
    "Dang": {"lat": 28.1167, "lon": 82.3000},
    "Gulmi": {"lat": 28.0833, "lon": 83.2667},
    "Kapilvastu": {"lat": 27.5500, "lon": 83.0500},
    "Palpa": {"lat": 27.8667, "lon": 83.5500},
    "Parasi": {"lat": 27.5000, "lon": 83.6667},
    "Pyuthan": {"lat": 28.1000, "lon": 82.8500},
    "Rolpa": {"lat": 28.3667, "lon": 82.6500},
    "Rukum East": {"lat": 28.5500, "lon": 82.5167},
    "Rupandehi": {"lat": 27.4833, "lon": 83.4333},
    "Dailekh": {"lat": 28.8500, "lon": 81.7000},
    "Dolpa": {"lat": 29.0833, "lon": 82.8667},
    "Humla": {"lat": 29.9667, "lon": 81.8500},
    "Jajarkot": {"lat": 28.7167, "lon": 82.1833},
    "Jumla": {"lat": 29.2833, "lon": 82.1833},
    "Kalikot": {"lat": 29.1333, "lon": 81.6167},
    "Mugu": {"lat": 29.5000, "lon": 82.0833},
    "Rukum West": {"lat": 28.6167, "lon": 82.3333},
    "Salyan": {"lat": 28.3833, "lon": 82.1667},
    "Surkhet": {"lat": 28.6000, "lon": 81.6167},
    "Achham": {"lat": 29.0500, "lon": 81.2500},
    "Baitadi": {"lat": 29.5167, "lon": 80.4167},
    "Bajhang": {"lat": 29.5333, "lon": 81.1833},
    "Bajura": {"lat": 29.4500, "lon": 81.4833},
    "Dadeldhura": {"lat": 29.3000, "lon": 80.5667},
    "Darchula": {"lat": 29.8500, "lon": 80.5500},
    "Doti": {"lat": 29.2667, "lon": 80.9500},
    "Kailali": {"lat": 28.8000, "lon": 80.8833},
    "Kanchanpur": {"lat": 28.8500, "lon": 80.3167},
}


def normalize_zone_key(zone: str | None) -> str | None:
    if not zone:
        return None
    key = ECO_ZONE_ALIASES.get(zone.strip().lower().replace("-", "_"))
    if key:
        return key
    compact = zone.strip().lower().replace(" ", "_").replace("-", "_")
    return compact if compact in ECO_ZONES else None


def nearest_district(lat: float, lon: float) -> str | None:
    best_name, best_d = None, float("inf")
    for name, coords in NEPAL_DISTRICTS.items():
        d = (coords["lat"] - lat) ** 2 + (coords["lon"] - lon) ** 2
        if d < best_d:
            best_d, best_name = d, name
    return best_name


def zone_from_elevation(elevation_m: float | None) -> str | None:
    if elevation_m is None:
        return None
    for key, z in ECO_ZONES.items():
        lo, hi = z["elevation_m"]
        if lo <= elevation_m < hi or (key == "high_himal" and elevation_m >= lo):
            return key
    return None


def resolve_eco_zone(
    *,
    lat: float | None = None,
    lon: float | None = None,
    district: str | None = None,
    elevation_m: float | None = None,
    zone: str | None = None,
) -> dict[str, Any]:
    """
    Resolve the FRTC physiographic zone for an AOI.
    Priority: explicit zone → elevation → district name → nearest district → lat heuristic.
    """
    key = normalize_zone_key(zone)
    source = "explicit"

    if not key and elevation_m is not None:
        key = zone_from_elevation(elevation_m)
        source = "elevation"

    if not key and district and district in DISTRICT_ECO_ZONE:
        key = DISTRICT_ECO_ZONE[district]
        source = "district"

    if not key and lat is not None and lon is not None:
        near = nearest_district(lat, lon)
        if near and near in DISTRICT_ECO_ZONE:
            key = DISTRICT_ECO_ZONE[near]
            district = district or near
            source = "nearest_district"

    if not key and lat is not None:
        # Coarse south→north fallback when no district match
        if lat < 27.2:
            key = "terai"
        elif lat < 27.7:
            key = "siwaliks"
        elif lat < 28.6:
            key = "middle_mountains"
        elif lat < 29.4:
            key = "high_mountains"
        else:
            key = "high_himal"
        source = "latitude_heuristic"

    key = key or "middle_mountains"
    z = ECO_ZONES[key]
    regional_key = z["regional_key"]
    rp = NEPAL_REGIONAL_PARAMS[regional_key]
    return {
        "zone_key": key,
        "zone_name": z["name"],
        "shorthand": z["shorthand"],
        "regional_key": regional_key,
        "regional_label": rp["label"],
        "max_agb_t_ha": rp["max_agb_t_ha"],
        "ndvi_sat": rp["ndvi_max_saturation"],
        "baseline_agb": rp["baseline_agb"],
        "root_shoot": rp["root_shoot"],
        "cf": rp["cf"],
        "scale_mode": rp["scale_mode"],
        "default_forest_type": rp["legacy_ftype"],
        "notes": z["notes"],
        "sources": list(z["sources"]),
        "district": district,
        "resolved_via": source,
        "elevation_m": elevation_m,
    }


def resolve_regional_params(
    *,
    lat=None,
    lon=None,
    district=None,
    elevation_m=None,
    eco_zone=None,
    forest_type: str | None = "default",
) -> dict[str, Any]:
    """Resolve eco-zone then apply optional explicit forest_type override."""
    zone_info = resolve_eco_zone(
        lat=lat, lon=lon, district=district, elevation_m=elevation_m, zone=eco_zone
    )
    ftype = (forest_type or "default").strip().lower()
    if ftype in NEPAL_REGIONAL_PARAMS:
        regional_key = ftype
    elif ftype in LEGACY_FTYPE_TO_REGIONAL and LEGACY_FTYPE_TO_REGIONAL[ftype]:
        # Explicit legacy pick overrides zone stratum
        regional_key = LEGACY_FTYPE_TO_REGIONAL[ftype]
    else:
        regional_key = zone_info["regional_key"]

    rp = NEPAL_REGIONAL_PARAMS[regional_key]
    return {
        **zone_info,
        "regional_key": regional_key,
        "regional_label": rp["label"],
        "max_agb_t_ha": rp["max_agb_t_ha"],
        "ndvi_sat": rp["ndvi_max_saturation"],
        "baseline_agb": rp["baseline_agb"],
        "root_shoot": rp["root_shoot"],
        "cf": rp["cf"],
        "scale_mode": rp["scale_mode"],
        "default_forest_type": rp["legacy_ftype"],
    }


def vegetation_scale(index: float, sat: float, mode: str = "linear") -> float:
    """
    Map vegetation index → [0.1, 1.0] biomass scaler.
    Dense tropical/subtropical canopies use log / evi_like so NDVI~0.8 does not
    linearly over-credit biomass past FRTC baselines.
    """
    if sat <= 0:
        return 0.1
    x = max(0.0, min(1.0, float(index) / float(sat)))
    if mode == "log":
        k = 3.0
        return max(0.1, math.log1p(k * x) / math.log1p(k))
    if mode == "evi_like":
        # Concave near saturation (EVI-style)
        return max(0.1, 1.0 - (1.0 - x) ** 2)
    return max(0.1, min(1.0, x))


def apply_agb_saturation_cap(
    agb_t_ha: float,
    ndvi: float | None,
    zone_info: dict[str, Any],
) -> tuple[float, bool, float]:
    """
    Cap AGB to the regional FRTC/ICIMOD ceiling.
    Returns (capped_agb, was_capped, ceiling).
    """
    ceiling = float(zone_info["max_agb_t_ha"])
    ndvi_sat = float(zone_info["ndvi_sat"])
    capped = min(float(agb_t_ha), ceiling)
    if ndvi is not None and ndvi >= ndvi_sat:
        capped = min(capped, ceiling)
    was_capped = capped < float(agb_t_ha) - 1e-9
    return capped, was_capped, ceiling


def apply_field_calibration(
    agb_t_ha: float,
    *,
    calibration_coefficient: float | None = None,
    field_baseline_agb_t_ha: float | None = None,
) -> tuple[float, float, bool]:
    """
    Final Biomass = Satellite Estimate × Local Field Calibration Coefficient.

    If only a field baseline is known, coefficient defaults to 1.0 until the
    consultant sets an explicit coefficient (or we derive one elsewhere).
    Returns (calibrated_agb, coefficient_used, applied).
    """
    coeff = calibration_coefficient
    if coeff is None or coeff <= 0:
        coeff = 1.0
    applied = abs(coeff - 1.0) > 1e-9
    calibrated = float(agb_t_ha) * float(coeff)
    # Soft-bias toward field baseline when both present and coeff==1 (first ingest)
    if (
        not applied
        and field_baseline_agb_t_ha
        and field_baseline_agb_t_ha > 0
        and agb_t_ha > 0
    ):
        # Suggestive blend is NOT applied automatically — keep satellite pure
        # until an explicit coefficient is stored. Expose field baseline only.
        pass
    return calibrated, float(coeff), applied


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))
