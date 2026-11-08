import { apiFetch, apiFetchBlob } from "@/lib/api";

export interface AnalyzeRequest {
  lat?: number;
  lon?: number;
  geojson?: Record<string, unknown>;
  buf_km: number;
  year1: number;
  year2: number;
  start_month: number;
  end_month: number;
  start_day?: number;
  end_day?: number;
  baseline_date?: string;
  comparison_date?: string;
  baseline_start?: string;
  baseline_end?: string;
  comparison_start?: string;
  comparison_end?: string;
  forest_type: string;
  run_multiyear: boolean;
  run_monthly?: boolean;
  run_hotspot?: boolean;
  project_id?: string;
  calibration_coefficient?: number;
  field_baseline_agb_t_ha?: number;
}

export interface CarbonEstimate {
  agb_ha: number;
  bgb_ha: number;
  bio_ha: number;
  c_ha: number;
  co2_ha: number;
  total_c: number;
  total_co2: number;
  area_ha: number;
  ftype: string;
  co2_delta?: number;
  change_pct?: number;
  regional_key?: string;
  regional_label?: string;
  eco_zone?: string;
  eco_zone_name?: string;
  eco_zone_shorthand?: string;
  max_agb_t_ha?: number;
  baseline_agb?: number;
  agb_capped?: boolean;
  ndvi_sat?: number;
  scale_mode?: string;
  calibration_coefficient?: number;
  calibration_applied?: boolean;
  field_baseline_agb_t_ha?: number | null;
  suggested_calibration_coefficient?: number | null;
  zone_resolved_via?: string;
  zone_district?: string | null;
}

export interface AnalyzeResponse {
  ndvi_year1: number | null;
  ndvi_year2: number | null;
  change_pct: number;
  carbon_estimate: CarbonEstimate | null;
  trend_data: Array<{ year: number; ndvi: number }>;
  monthly_series: Array<{ month: string; ndvi: number }>;
  area_ha: number;
  tile_url?: string | null;
  tile_url_year1?: string | null;
  tile_url_year2?: string | null;
  tile_url_hotspot?: string | null;
  lat?: number;
  lon?: number;
  buf_km?: number;
  trend_slope?: number;
  trend_direction?: string;
  baseline_date?: string;
  comparison_date?: string;
  baseline_start?: string;
  baseline_end?: string;
  comparison_start?: string;
  comparison_end?: string;
  year1?: number;
  year2?: number;
  vision_explanation?: VisionExplanation;
  [key: string]: unknown;
}

export interface VisionExplanation {
  pipeline_name: string;
  inference_mode: string;
  inference_label: string;
  prediction: string;
  confidence: number;
  persistence_score: number;
  evidence: string;
  attention_regions: string[];
  feature_evidence: Array<{ feature: string; label: string; delta: number; weight: number }>;
  explainability: {
    current_visual: string;
    learned_visual: string;
    uncertainty_visual: string;
  };
  models: Array<{
    id: string;
    name: string;
    role: string;
    status: string;
    inputs: string;
    explanation: string;
    validation?: { accuracy?: number; iou?: number };
  }>;
  dataset_sources: Array<{
    id: string;
    name: string;
    url: string;
    role: string;
    classes: string;
    priority: string;
    caveat: string;
  }>;
  limitations: string[];
}

export interface VisionInferenceResponse {
  status: string;
  dataset: string;
  model_input: string;
  prediction: { class: string; confidence: number };
  segmentation: { positive_fraction: number; mask: string; grad_cam: string; uncertainty: string };
  change_detection: { changed_fraction: number; mask: string; grad_cam: string; uncertainty: string };
  vision_transformer: { grad_cam: string; uncertainty: number };
  tile_url: string;
  dates: { baseline: string; comparison: string };
  limitations: string[];
}

export async function inferVision(body: {
  lat: number;
  lon: number;
  buf_km: number;
  geojson?: any;
  baseline_date: string;
  comparison_date: string;
}): Promise<VisionInferenceResponse> {
  return apiFetch<VisionInferenceResponse>("/api/vision/infer/", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export interface ReportRequest {
  location: string;
  lat: number;
  lon: number;
  year1: number;
  year2: number;
  start_month: number;
  end_month: number;
  ndvi_year1: number | null;
  ndvi_year2: number | null;
  change_pct: number;
  carbon_estimate: CarbonEstimate | null;
  trend_data: Array<{ year: number; ndvi: number }>;
  monthly_series: Array<{ month: string; ndvi: number }>;
  date_note?: string;
  baseline_date?: string;
  comparison_date?: string;
  baseline_start?: string;
  baseline_end?: string;
  comparison_start?: string;
  comparison_end?: string;
}

export interface ReportResponse {
  executive_summary: string;
  key_findings: string[];
  vegetation_analysis: string;
  carbon_implications: string;
  risk_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  risk_assessment: string;
  recommendations: string[];
  data_confidence: string;
  next_monitoring: string;
  [key: string]: unknown;
}

export interface PdfRequest extends ReportRequest {
  report_data: ReportResponse;
  buf_km: number;
  area_ha: number;
}

export async function analyzeForest(body: AnalyzeRequest): Promise<AnalyzeResponse> {
  const started = await apiFetch<AnalyzeJobResponse>("/api/analyze/", {
    method: "POST",
    body: JSON.stringify(body),
  });

  if (started.result && (started.status === "success" || started.status === "cached")) {
    return started.result;
  }

  const jobId = started.job_id;
  if (!jobId) {
    throw new Error("Analysis did not return a job id");
  }

  const deadline = Date.now() + 5 * 60 * 1000;
  while (Date.now() < deadline) {
    await new Promise((r) => setTimeout(r, 1500));
    const job = await apiFetch<AnalyzeJobResponse>(`/api/analyze/jobs/${jobId}/`);
    if (job.status === "success" || job.status === "cached") {
      if (!job.result) throw new Error("Job finished without a result payload");
      return job.result;
    }
    if (job.status === "failed") {
      throw new Error(job.detail || "Analysis job failed");
    }
  }
  throw new Error("Analysis timed out — try again or check the worker");
}

export interface AnalyzeJobResponse {
  job_id: string;
  status: "pending" | "running" | "success" | "failed" | "cached";
  cache_hit?: boolean;
  queue?: string;
  poll_url?: string;
  result?: AnalyzeResponse;
  detail?: string;
}

export async function generateReport(body: ReportRequest): Promise<ReportResponse> {
  return apiFetch<ReportResponse>("/api/report/generate/", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function downloadPdf(body: PdfRequest): Promise<void> {
  const blob = await apiFetchBlob("/api/export/pdf/", {
    method: "POST",
    body: JSON.stringify(body),
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `TerrAI_${body.location.replace(/\s+/g, "_")}_${body.year2}.pdf`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export async function fetchPassDates(body: {
  lat?: number;
  lon?: number;
  geojson?: Record<string, unknown>;
  buf_km: number;
  year: number;
  month: number;
}): Promise<{ dates: string[] }> {
  return apiFetch("/api/pass-dates/", { method: "POST", body: JSON.stringify(body) });
}

export async function fetchDailyNdvi(body: {
  lat?: number;
  lon?: number;
  geojson?: Record<string, unknown>;
  buf_km: number;
  date: string;
}): Promise<{ ndvi: number | null; cloud_pct: number | null; tile_url: string | null; quality: string; date: string }> {
  return apiFetch("/api/daily-ndvi/", { method: "POST", body: JSON.stringify(body) });
}

export async function fetchBaselines(): Promise<Record<string, { ndvi: number; forest_cover_pct: number }>> {
  return apiFetch("/api/baselines/");
}
