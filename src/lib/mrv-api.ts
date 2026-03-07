const API_BASE = "http://localhost:8000";

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

export interface AnalyzeResponse {
  ndvi_year1: number;
  ndvi_year2: number;
  change_percent: number;
  area_ha: number;
  agb_ha: number;
  bgb_ha: number;
  total_carbon: number;
  total_co2e: number;
  ndvi_trend: Array<{ year: number; ndvi: number }>;
  monthly_ndvi: Array<{ month: string; ndvi: number }>;
  [key: string]: unknown;
}

export interface ReportResponse {
  title: string;
  subtitle: string;
  date: string;
  executive_summary: string;
  key_findings: string[];
  risk_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  risk_details: Array<{ factor: string; level: string; note: string }>;
  recommendations: string[];
  [key: string]: unknown;
}

export async function analyzeForest(body: AnalyzeRequest): Promise<AnalyzeResponse> {
  const res = await fetch(`${API_BASE}/api/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Analysis failed: ${res.statusText}`);
  return res.json();
}

export async function generateReport(analysisData: Record<string, unknown>): Promise<ReportResponse> {
  const res = await fetch(`${API_BASE}/api/report/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(analysisData),
  });
  if (!res.ok) throw new Error(`Report generation failed: ${res.statusText}`);
  return res.json();
}

export async function downloadPdf(analysisData: Record<string, unknown>): Promise<void> {
  const res = await fetch(`${API_BASE}/api/export/pdf`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(analysisData),
  });
  if (!res.ok) throw new Error(`PDF export failed: ${res.statusText}`);
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
