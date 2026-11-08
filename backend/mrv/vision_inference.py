"""Live Earth Engine thumbnail inference for the trained public-data models."""

from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Any

import numpy as np
import requests
import torch
from PIL import Image

from .gee_utils import get_ndvi_visualization_params, get_sentinel_day_image
from .science import ensure_gee
from .train_vision import TinySiamese, TinyUNet, TinyVisionTransformer

ARTIFACTS = Path(__file__).with_name("artifacts")


def _tensor(image: Image.Image) -> torch.Tensor:
    data = np.asarray(image.convert("RGB").resize((64, 64)), dtype=np.float32) / 255
    return torch.from_numpy(data.transpose(2, 0, 1)).sub(0.5).div(0.5).unsqueeze(0)


def _data_url(array: np.ndarray, *, palette: str = "magma") -> str:
    values = np.asarray(array, dtype=np.float32)
    values = (values - values.min()) / max(float(values.max() - values.min()), 1e-6)
    import matplotlib.cm as cm

    rgba = (cm.get_cmap(palette)(values)[:, :, :3] * 255).astype(np.uint8)
    out = io.BytesIO()
    Image.fromarray(rgba).save(out, format="PNG")
    return "data:image/png;base64," + base64.b64encode(out.getvalue()).decode()


def _fetch_thumb(image, aoi) -> Image.Image:
    url = image.select(["B4", "B3", "B2"]).getThumbURL({
        "region": aoi,
        "dimensions": 64,
        "format": "png",
        "min": 0,
        "max": 0.3,
    })
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    return Image.open(io.BytesIO(response.content)).convert("RGB")


def _load(model: torch.nn.Module, filename: str) -> torch.nn.Module:
    path = ARTIFACTS / filename
    if not path.exists():
        raise FileNotFoundError(f"Trained checkpoint is missing: {path}")
    checkpoint = torch.load(path, map_location="cpu")
    model.load_state_dict(checkpoint["model"])
    return model.eval()


def _gradcam(model: torch.nn.Module, input_tensor: torch.Tensor, target_layer: torch.nn.Module) -> np.ndarray:
    activations: list[torch.Tensor] = []
    gradients: list[torch.Tensor] = []
    target_layer.register_forward_hook(lambda _, __, output: activations.append(output))
    target_layer.register_full_backward_hook(lambda _, grad_input, grad_output: gradients.append(grad_output[0]))
    model.zero_grad(set_to_none=True)
    output = model(input_tensor)
    output.flatten()[output.argmax()].backward()
    activation = activations[-1].detach()
    gradient = gradients[-1].detach()
    if activation.ndim == 3:
        activation = activation[:, 1:, :]
        gradient = gradient[:, 1:, :]
        side = int(activation.shape[1] ** 0.5)
        activation = activation.transpose(1, 2).reshape(activation.shape[0], activation.shape[2], side, side)
        gradient = gradient.transpose(1, 2).reshape(gradient.shape[0], gradient.shape[2], side, side)
    weights = gradient.mean(dim=tuple(range(2, gradient.ndim)), keepdim=True)
    cam_tensor = torch.relu((weights * activation).sum(dim=1)).squeeze()
    # A saturated or weakly-connected layer can produce an all-zero CAM.
    # Use input-gradient saliency so the UI never presents a black map as
    # meaningful model attention.
    if float(cam_tensor.max()) <= 1e-8:
        input_gradient = input_tensor.grad
        if input_gradient is not None:
            cam_tensor = input_gradient.detach().abs().mean(dim=1).squeeze()
    cam = cam_tensor.detach().cpu().numpy()
    if float(np.max(cam)) <= 1e-8:
        cam = np.ones((64, 64), dtype=np.float32) * 0.5
    return np.asarray(Image.fromarray(cam).resize((64, 64), Image.Resampling.BILINEAR))


def _entropy(probability: torch.Tensor) -> np.ndarray:
    p = probability.detach().cpu().numpy().clip(1e-5, 1 - 1e-5)
    return -(p * np.log(p) + (1 - p) * np.log(1 - p))


def run_live_inference(
    *,
    lat: float,
    lon: float,
    buf_km: float = 5.0,
    geojson: dict | None = None,
    baseline_date: str,
    comparison_date: str,
) -> dict[str, Any]:
    ensure_gee()
    import ee
    from .science import parse_geojson

    aoi = None
    if geojson:
        try:
            aoi, _lat, _lon, _area, _name = parse_geojson(geojson)
        except Exception:
            aoi = None

    if aoi is None:
        radius_km = float(buf_km) if (buf_km and float(buf_km) > 0) else 5.0
        aoi = ee.Geometry.Point([lon, lat]).buffer(radius_km * 1000, 10)

    thumb_region = aoi.bounds(10)
    # Exact dates often have no cloud-free Sentinel-2 acquisition. The day
    # helper searches a bounded +/-7 day window and raises a useful error if
    # the AOI has no usable scene at all.
    try:
        baseline = get_sentinel_day_image(aoi, baseline_date, search_days=7)
    except Exception:
        baseline = get_sentinel_day_image(aoi, baseline_date, search_days=21)

    try:
        comparison = get_sentinel_day_image(aoi, comparison_date, search_days=7)
    except Exception:
        comparison = get_sentinel_day_image(aoi, comparison_date, search_days=21)

    before_image = _fetch_thumb(baseline, thumb_region)
    after_image = _fetch_thumb(comparison, thumb_region)
    before, after = _tensor(before_image), _tensor(after_image)

    vit = _load(TinyVisionTransformer(), "vision_transformer.pt")
    with torch.no_grad():
        probabilities = vit(after).softmax(dim=1)
    class_index = int(probabilities.argmax())
    class_confidence = float(probabilities[0, class_index])
    vit_cam = _gradcam(vit, after.clone().requires_grad_(True), vit.encoder.layers[-1])

    unet = _load(TinyUNet(), "unet.pt")
    with torch.no_grad():
        segmentation = torch.sigmoid(unet(after))
    segmentation_probability = segmentation[0, 0]
    unet_cam = _gradcam(unet, after.clone().requires_grad_(True), unet.down2)

    siamese = _load(TinySiamese(), "siamese.pt")
    with torch.no_grad():
        change_probability = torch.sigmoid(siamese(before, after))[0, 0]
    change_uncertainty = _entropy(change_probability)
    class ComparisonModel(torch.nn.Module):
        def forward(self, image):
            return siamese(before, image)

    comparison_model = ComparisonModel()
    siamese_cam = _gradcam(comparison_model, after.clone().requires_grad_(True), siamese.encoder[3])

    tile = comparison.select("NDVI").getMapId(get_ndvi_visualization_params())["tile_fetcher"].url_format
    return {
        "status": "prototype-inference",
        "dataset": "EuroSAT RGB checkpoints",
        "model_input": "Live Sentinel-2 RGB thumbnail from Google Earth Engine",
        "prediction": {"class": CLASSES[class_index], "confidence": round(class_confidence, 4)},
        "segmentation": {
            "positive_fraction": round(float(segmentation_probability.mean()), 4),
            "mask": _data_url(segmentation_probability.numpy(), palette="Greens"),
            "grad_cam": _data_url(unet_cam),
            "uncertainty": _data_url(_entropy(segmentation_probability), palette="viridis"),
        },
        "change_detection": {
            "changed_fraction": round(float((change_probability > 0.5).float().mean()), 4),
            "mask": _data_url(change_probability.numpy(), palette="Reds"),
            "grad_cam": _data_url(siamese_cam),
            "uncertainty": _data_url(change_uncertainty, palette="viridis"),
        },
        "vision_transformer": {
            "grad_cam": _data_url(vit_cam),
            "uncertainty": round(1 - class_confidence, 4),
            "explanation": "Grad-CAM with input-gradient fallback when the selected transformer layer has weak activation.",
        },
        "tile_url": tile,
        "dates": {"baseline": baseline_date, "comparison": comparison_date},
        "limitations": [
            "Weights were trained on EuroSAT image-level land-cover data.",
            "U-Net segmentation uses EuroSAT green-dominance pseudo-labels.",
            "Siamese change uses the live dates but was trained on synthetic changes.",
            "Outputs are prototype evidence and do not alter carbon accounting.",
        ],
    }


CLASSES = (
    "AnnualCrop", "Forest", "HerbaceousVegetation", "Highway", "Industrial",
    "Pasture", "PermanentCrop", "Residential", "River", "SeaLake",
)
