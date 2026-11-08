# TerrAI Nepal: Explainable Vision MRV Guide

## What this project does

TerrAI Nepal is a forest **MRV** (Measurement, Reporting, and Verification)
platform. It combines Sentinel-2 optical imagery, Sentinel-1 **SAR** radar
imagery, vegetation indices, Nepal ecological-zone parameters, field
calibration, maps, reports, and project records.

The existing scientific path is the auditable baseline:

1. Select an **AOI** (Area of Interest).
2. Build cloud-masked Sentinel-2 composites and use Sentinel-1 as a radar
   complement when appropriate.
3. Calculate NDVI, EVI, and RVI for baseline and comparison periods.
4. Estimate biomass and CO2e using Nepal regional parameters.
5. Show the imagery, change hotspot, trend, and report.

The advanced vision models are an additional evidence layer. They must not
silently replace the carbon calculation until they have Nepal labels, an
independent test set, and documented validation.

## Model sections

### U-Net segmentation

**U-Net** is an encoder-decoder segmentation network. The encoder learns
image features and the decoder restores them to the original map resolution.
Its output is a class for each pixel.

Recommended TerrAI classes:

- healthy or intact forest
- degraded forest
- deforested or cleared land
- agriculture
- road or settlement
- water
- bare soil
- fire or burn scar
- cloud and cloud shadow

U-Net is used here because MRV needs to answer *where* a disturbance is, not
only whether an entire project changed. U-Net outputs can become map layers,
affected-area calculations, field-verification targets, and evidence for the
LLM report.

### Siamese change detection

A **Siamese** network sends the baseline and comparison images through
weight-sharing feature extractors. The feature representations are compared
and a decoder produces a pixel-level change map.

Recommended inputs:

- aligned Sentinel-2 baseline and comparison composites
- Sentinel-1 VV/VH bands
- NDVI, EVI, NBR, and terrain features
- cloud and shadow masks

Recommended outputs:

- persistent canopy loss
- regrowth
- fire damage
- new roads or clearings
- seasonal/no-change class

This is the most directly useful model for the current dashboard because the
application already compares two dates and displays an NDVI hotspot layer.

### Vision Transformer / Swin Transformer

A **Vision Transformer** divides an image into patches and learns relationships
between them using attention. **Swin Transformer** uses local windows that are
merged hierarchically, making it more practical for large satellite scenes.

It is useful for landscape context: a suspected clearing can be interpreted
alongside roads, farms, rivers, fragmentation, terrain, and neighboring
canopy. A pretrained Earth-observation encoder should be fine-tuned rather
than trained from zero.

The Prithvi-EO-1.0 model is a suitable starting point:

<https://huggingface.co/ibm-nasa-geospatial/Prithvi-EO-1.0-100M>

It was pretrained on HLS imagery from the contiguous United States, so it is
not Nepal ground truth. Nepal fine-tuning and independent Nepal evaluation
remain mandatory.

### ConvLSTM temporal model

**ConvLSTM** combines convolution with recurrent memory. It keeps spatial
structure while learning a monthly or annual sequence. It is suitable for
distinguishing persistent degradation from a one-season anomaly.

Use it after the first segmentation and change-detection baseline is stable.

## Nepal data strategy

### Primary label sources

1. **ICIMOD Regional Database System and SERVIR-HKH**  
   <https://rds.icimod.org/>  
   Use for localized LULC, forest fragmentation, and historical disturbance
   layers. Confirm licences, layer versions, resolution, and class definitions.

2. **FRTC / Nepal Land Cover Monitoring System (NLCMS)**  
   <https://frtc.gov.np/>  
   Use as the national annual land-cover and forest-change reference. Obtain
   the authoritative downloadable release and metadata directly from FRTC;
   do not treat web map tiles as training labels.

### Supplementary disturbance sources

3. **Global Forest Watch**  
   <https://www.globalforestwatch.org/>  
   Use tree-cover loss and disturbance alerts to generate candidate samples
   and for independent cross-checking. Alerts are not definitive ground truth.

4. **NASA FIRMS**  
   <https://firms.modaps.eosdis.nasa.gov/>  
   Use active-fire detections to find candidate fire events. Create final burn
   masks from higher-resolution imagery and manual review.

### Pretraining and benchmarking

5. **BigEarthNet v2**  
   <https://zenodo.org/records/10891137>  
   Sentinel-1 and Sentinel-2 paired patches with pixel reference maps. Good
   for general remote-sensing pretraining and benchmarking, but mostly Europe.

6. **EuroSAT**  
   <https://www.tensorflow.org/datasets/catalog/eurosat>  
   13-band Sentinel-2 classification data. Useful for an initial multispectral
   pipeline, not Nepal-specific forest validation.

## Label construction protocol

1. Freeze a Sentinel-2/Sentinel-1 acquisition window and preprocessing version.
2. Reproject all labels to a common CRS and raster grid.
3. Intersect labels with cloud, shadow, snow, and no-data masks.
4. Resolve conflicts using the authoritative source priority:
   FRTC/NLCMS, ICIMOD/SERVIR-HKH, reviewed imagery, then alerts.
5. Record source, date, class, resolution, licence, and confidence for every
   polygon or raster tile.
6. Split by geography, not random pixels. Keep entire districts or spatial
   blocks out of training so nearby pixels cannot leak into validation.
7. Hold out Nepal regions across Terai, Siwalik, Middle Mountains, High
   Mountains, and High Himal.
8. Have forestry reviewers inspect a sample of every class before training.

## Explainability

The current app labels its result as:

> CNN weights not active — evidence proxy shown

That is intentional. The current proxy uses measured NDVI/EVI/RVI evidence and
the existing hotspot map. It is not a fabricated neural-network prediction.

After validated weights are available, add:

- Grad-CAM or Layer-CAM for classification/change decisions
- segmentation confidence and entropy maps
- occlusion tests for important regions
- cloud, terrain, and out-of-distribution warnings
- model version, dataset version, and input dates in every report

## LLM responsibilities

The LLM should explain structured, verified outputs; it should not invent
measurements or be the primary pixel classifier. Its input should include:

```json
{
  "model": "Siamese U-Net v1",
  "model_status": "validated",
  "affected_area_ha": 12.4,
  "change_confidence": 0.87,
  "uncertainty": 0.11,
  "ndvi_change": -0.18,
  "top_evidence": ["canopy loss", "road-edge disturbance"],
  "field_checks": ["north boundary", "road crossing"]
}
```

The report should state the evidence, confidence, uncertainty, limitations,
and field-verification recommendation.

## Training the public-data prototype

Install the optional training dependencies:

```bash
python3 -m pip install -r backend/requirements-vision.txt
python3 backend/mrv/train_vision.py --limit 3000 --epochs 3
```

The command downloads EuroSAT through `torchvision`, trains all three
prototype models, writes metrics to
`backend/mrv/artifacts/training_metrics.json`, and writes local checkpoints.
The default run is intentionally CPU/MPS-friendly. Increase `--limit` and
`--epochs` for a serious benchmark.

EuroSAT has real image-level land-cover labels. It does **not** contain
pixel-level forest masks or date-paired change labels. Consequently, the
Vision Transformer metric is a real EuroSAT validation accuracy, while the
U-Net IoU and Siamese IoU are proxy-task metrics. They are useful for checking
that the training code works, but they are not deployment quality or Nepal
forest performance.

The completed local run used Apple MPS, 3,000 EuroSAT RGB images, and 3
epochs. It measured 1.0000 Vision Transformer validation accuracy, 0.7873
U-Net proxy IoU, and 0.9738 Siamese synthetic-change IoU. The unusually high
classification score is a small, easy benchmark subset result; it is not a
claim of generalization to Nepal. The dashboard reports these as
`prototype-trained` and keeps production inference as the transparent-index
proxy.

## Live inference API

After authenticating, send the selected AOI and two dates to:

```text
POST /api/vision/infer/
{
  "lat": 27.7,
  "lon": 85.3,
  "buf_km": 5,
  "baseline_date": "2022-01-15",
  "comparison_date": "2024-01-15"
}
```

The endpoint fetches two 64x64 Sentinel-2 RGB thumbnails from Earth Engine,
runs the local Vision Transformer, U-Net, and Siamese checkpoints, and returns
the predicted class, masks, Grad-CAM images, uncertainty images, and the
current NDVI map tile URL. It returns an explicit 503 when checkpoints or
vision dependencies are unavailable, and a 502 when Earth Engine or inference
fails.

The dashboard's **Run vision models** action calls this endpoint. Configure
`GEE_PROJECT_ID` and Earth Engine authentication before using it.

The live endpoint is production-wired but the checkpoints remain public-data
prototypes: only the Vision Transformer has real EuroSAT class labels. The
U-Net and Siamese checkpoint labels are proxy labels, so their live outputs
must remain screening evidence until real segmentation and date-paired
change labels are trained.

## Current implementation status

Implemented:

- Existing Sentinel-2/Sentinel-1 hybrid science path
- NDVI/EVI/RVI change results and hotspot map
- Labelled U-Net, Siamese, Swin/Vision Transformer, and ConvLSTM registry
- Transparent evidence proxy with explicit non-CNN status
- Model roles, inputs, limitations, and explainability labels in the dashboard
- Sidebar sections linking to each model and public dataset source
- Hover glossary for technical terms
- Backend unit test and frontend build/test coverage for the integration
- Reproducible EuroSAT training harness and explicit proxy-label accounting

Still required for real learned inference:

- Obtain and license ICIMOD and FRTC/NLCMS data
- Build the Nepal label catalogue and spatially separated splits
- Collect field-reviewed samples for forest condition and disturbance
- Implement raster tile extraction and model training
- Train and validate U-Net segmentation
- Train and validate Siamese change detection
- Fine-tune and compare a Prithvi/Swin encoder
- Add temporal ConvLSTM experiments
- Serve versioned weights and prediction tiles
- Add real Grad-CAM, uncertainty, and out-of-distribution checks
- Independent forestry review before carbon-credit use

The application is therefore complete as an explainable MRV prototype and
model-ready integration, but learned model deployment is not complete until
the Nepal data, training, validation, and serving steps above are performed.
