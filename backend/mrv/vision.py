"""Explainable remote-sensing vision pipeline metadata.

The production carbon estimate remains the auditable NDVI/SAR science path.
This module describes the vision architectures and creates transparent,
feature-based evidence until Nepal-labelled model weights are configured.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


VISION_MODELS = [
    {
        "id": "unet-segmentation",
        "name": "U-Net segmentation decoder",
        "role": "Pixel-level forest, clearing, and disturbance masks",
        "status": "architecture-ready",
        "inputs": "Aligned Sentinel-2, Sentinel-1, NDVI, NBR, elevation",
        "explanation": "An encoder-decoder maps image features back to a class for each pixel.",
    },
    {
        "id": "siamese-change",
        "name": "Siamese change detector",
        "role": "Baseline-versus-comparison change map",
        "status": "architecture-ready",
        "inputs": "Two aligned Sentinel-2/Sentinel-1 dates",
        "explanation": "Shared-weight encoders compare both dates before a U-Net-style decoder maps change to pixels.",
    },
    {
        "id": "vision-transformer",
        "name": "Swin / Vision Transformer encoder",
        "role": "Landscape context and transfer learning",
        "status": "weights-required",
        "inputs": "Multi-spectral and radar image patches",
        "explanation": "Windowed attention captures canopy patterns together with roads, farms, and terrain context.",
    },
    {
        "id": "convlstm-temporal",
        "name": "ConvLSTM temporal model",
        "role": "Multi-date forest health trend and recovery analysis",
        "status": "architecture-ready",
        "inputs": "Monthly optical and SAR feature sequences",
        "explanation": "Convolution preserves geography while recurrent gates learn change through time.",
    },
]

DATASET_SOURCES = [
    {
        "id": "icimod-rds-servir-hkh",
        "name": "ICIMOD Regional Database System & SERVIR-HKH",
        "url": "https://rds.icimod.org/",
        "role": "Primary Nepal land-cover and forest-fragmentation labels",
        "classes": "Forest, degraded forest, agriculture, water, bare soil, fragmentation",
        "priority": "primary",
        "caveat": "Confirm layer licence, version, spatial resolution, and label definitions before training.",
    },
    {
        "id": "frtc-nlcms",
        "name": "FRTC / Nepal Land Cover Monitoring System",
        "url": "https://frtc.gov.np/",
        "role": "National annual land-cover and forest-change reference",
        "classes": "National land-cover classes and annual forest-cover change",
        "priority": "primary",
        "caveat": "Request the authoritative downloadable release and metadata from FRTC; do not scrape map tiles as labels.",
    },
    {
        "id": "global-forest-watch",
        "name": "Global Forest Watch",
        "url": "https://www.globalforestwatch.org/",
        "role": "Disturbance candidate generation and independent cross-check",
        "classes": "Tree-cover loss and disturbance alerts",
        "priority": "supplement",
        "caveat": "Alerts are screening evidence, not definitive Nepal ground truth; validate with imagery or field checks.",
    },
    {
        "id": "nasa-firms",
        "name": "NASA FIRMS",
        "url": "https://firms.modaps.eosdis.nasa.gov/",
        "role": "Fire-event candidate generation",
        "classes": "Active-fire detections and fire-event locations",
        "priority": "supplement",
        "caveat": "Use detections to find candidate fire samples, then create burn masks from higher-resolution imagery.",
    },
]


def _training_metrics() -> dict[str, Any]:
    path = Path(__file__).with_name("artifacts") / "training_metrics.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


def _model_registry() -> list[dict[str, Any]]:
    metrics = _training_metrics().get("tasks", {})
    models = []
    for model in VISION_MODELS:
        item = dict(model)
        task = {
            "unet-segmentation": "unet",
            "siamese-change": "siamese",
            "vision-transformer": "vision_transformer",
            "convlstm-temporal": None,
        }.get(model["id"])
        if task and task in metrics:
            item["status"] = "prototype-trained"
            item["validation"] = metrics[task].get("validation") or {
                "iou": metrics[task].get("validation_iou")
            }
        models.append(item)
    return models


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return round(max(low, min(high, value)), 3)


def build_vision_explanation(
    *,
    ndvi_before: float | None,
    ndvi_after: float | None,
    change_pct: float,
    evi_before: float | None = None,
    evi_after: float | None = None,
    rvi_before: float | None = None,
    rvi_after: float | None = None,
    cloud_free_inputs: bool = True,
) -> dict[str, Any]:
    """Return a truthful, UI-ready explanation of the current analysis.

    This is deliberately not a fake CNN inference result. It uses the same
    measured indices as the audited baseline to provide a labelled proxy until
    trained weights and a Nepal validation set are supplied.
    """
    ndvi_delta = (ndvi_after - ndvi_before) if ndvi_before is not None and ndvi_after is not None else 0.0
    evi_delta = (evi_after - evi_before) if evi_before is not None and evi_after is not None else 0.0
    rvi_delta = (rvi_after - rvi_before) if rvi_before is not None and rvi_after is not None else 0.0
    decline_signal = _clamp(max(0.0, -change_pct / 25))
    recovery_signal = _clamp(max(0.0, change_pct / 25))
    persistence = _clamp(0.45 + abs(ndvi_delta) * 2.5)
    confidence = _clamp(0.55 + (0.15 if cloud_free_inputs else 0) + min(abs(change_pct) / 100, 0.2))

    if decline_signal >= 0.25:
        prediction = "Likely vegetation decline"
        evidence = "The change proxy is driven by a measurable NDVI decrease."
        attention = ["NDVI difference layer", "low-greenness canopy patches", "boundary and disturbance edges"]
    elif recovery_signal >= 0.25:
        prediction = "Likely vegetation recovery"
        evidence = "The change proxy is driven by a measurable NDVI increase."
        attention = ["NDVI difference layer", "new high-greenness canopy patches", "forest interior"]
    else:
        prediction = "No material vegetation change detected"
        evidence = "The measured change is within the current screening tolerance."
        attention = ["stable canopy texture", "seasonal comparison window", "cloud-masked pixels"]

    registry = _model_registry()
    trained = any(model["status"] == "prototype-trained" for model in registry)
    return {
        "pipeline_name": "Explainable forest-change vision pipeline",
        "inference_mode": "transparent-index-proxy",
        "inference_label": (
            "Prototype weights trained — production inference not connected"
            if trained
            else "CNN weights not active — evidence proxy shown"
        ),
        "prediction": prediction,
        "confidence": confidence,
        "persistence_score": persistence,
        "evidence": evidence,
        "attention_regions": attention,
        "feature_evidence": [
            {"feature": "NDVI", "label": "Canopy greenness", "delta": round(ndvi_delta, 4), "weight": _clamp(0.55 + abs(ndvi_delta))},
            {"feature": "EVI", "label": "Dense vegetation signal", "delta": round(evi_delta, 4), "weight": _clamp(0.25 + abs(evi_delta))},
            {"feature": "RVI", "label": "Radar vegetation structure", "delta": round(rvi_delta, 4), "weight": _clamp(0.2 + abs(rvi_delta))},
        ],
        "explainability": {
            "current_visual": "NDVI change hotspot map",
            "learned_visual": "Grad-CAM / Layer-CAM (available after trained weights)",
            "uncertainty_visual": "Cloud, terrain, and model uncertainty mask (requires trained weights)",
        },
        "models": registry,
        "dataset_sources": DATASET_SOURCES,
        "limitations": [
            "A trained CNN requires Nepal-labelled image patches and independent validation.",
            "The current prediction is a transparent screening proxy, not a learned CNN prediction.",
            "Carbon numbers remain calculated by the regional science and field-calibration pathway.",
        ],
    }
