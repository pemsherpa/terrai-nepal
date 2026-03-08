const API_BASE = "https://busy-parks-shout.loca.lt";

// ── Request / Response interfaces ──────────────────────────────

export interface AnalyzeRequest {
  lat: number;
  lon: number;
  buf_km: number;
  year1: number;
  year2: number;
  start_month: number;
  end_month: number;
  forest_type: string;
  run_multiyear: boolean;
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
}

export interface AnalyzeResponse {
  ndvi_year1: number | null;
  ndvi_year2: number | null;
  change_pct: number;
  carbon_estimate: CarbonEstimate | null;
  trend_data: Array<{ year: number; ndvi: number }>;
  monthly_series: Array<{ month: string; ndvi: number }>;
  area_ha: number;
  [key: string]: unknown;
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
}

export interface ReportResponse {
  title: string;
  subtitle: string;
  date: string;
  executive_summary: string;
  key_findings: string[];
  vegetation_analysis: string;
  carbon_implications: string;
  risk_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  risk_assessment: string;
  risk_details: Array<{ factor: string; level: string; note: string }>;
  recommendations: string[];
  data_confidence: string;
  next_monitoring: string;
  [key: string]: unknown;
}

export interface PdfRequest extends ReportRequest {
  report_data: {
    executive_summary: string;
    key_findings: string[];
    vegetation_analysis: string;
    carbon_implications: string;
    risk_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
    risk_assessment: string;
    recommendations: string[];
    data_confidence: string;
    next_monitoring: string;
  };
  buf_km: number;
  area_ha: number;
}

// ── API functions ──────────────────────────────────────────────

export async function analyzeForest(body: AnalyzeRequest): Promise<AnalyzeResponse> {
  const res = await fetch(`${API_BASE}/api/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.text().catch(() => res.statusText);
    throw new Error(`Analysis failed: ${err}`);
  }
  return res.json();
}

export async function generateReport(body: ReportRequest): Promise<ReportResponse> {
  const res = await fetch(`${API_BASE}/api/report/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.text().catch(() => res.statusText);
    throw new Error(`Report generation failed: ${err}`);
  }
  return res.json();
}

export async function downloadPdf(body: PdfRequest): Promise<void> {
  const res = await fetch(`${API_BASE}/api/export/pdf`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.text().catch(() => res.statusText);
    throw new Error(`PDF export failed: ${err}`);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "TerrAI_Report.pdf";
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
