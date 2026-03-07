import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Shield, CheckCircle, AlertTriangle, FileText, ListChecks } from "lucide-react";

// Demo data — ready to replace with API response
const reportData = {
  title: "AI Due Diligence Report",
  subtitle: "Chitwan National Park — Forest Carbon Credit Assessment",
  date: "March 7, 2026",
  executiveSummary:
    "Satellite analysis of the Chitwan National Park buffer zone (250 ha) indicates stable-to-improving forest health over the 2024–2025 assessment period. NDVI increased by 4.5%, suggesting net biomass growth consistent with active conservation efforts. Carbon stock estimates align with regional ICIMOD benchmarks, supporting the viability of this area for REDD+ carbon credit issuance.",
  keyFindings: [
    "NDVI increased from 0.66 to 0.69 (+4.5%) between baseline and comparison years.",
    "No significant deforestation or degradation events detected via change analysis.",
    "Estimated carbon stock of 22,440 tonnes C (82,250 tonnes CO₂e) across 250 hectares.",
    "Above-ground biomass density (167 t/ha) is consistent with subtropical broadleaf benchmarks.",
    "Seasonal NDVI patterns show expected monsoon-driven fluctuations with no anomalies.",
  ],
  riskLevel: "LOW" as "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",
  riskDetails: [
    { factor: "Deforestation Risk", level: "LOW", note: "No encroachment detected in buffer zone" },
    { factor: "Data Quality", level: "LOW", note: "Cloud-free Sentinel-2 composites with <5% cloud cover" },
    { factor: "Permanence Risk", level: "MEDIUM", note: "Flood-prone areas in southern quadrant require monitoring" },
    { factor: "Leakage Risk", level: "LOW", note: "Adjacent protected areas reduce displacement probability" },
  ],
  recommendations: [
    "Proceed with carbon credit registration under VCS/Verra methodology VM0015.",
    "Establish three ground-truth validation plots for field calibration of remote sensing estimates.",
    "Implement quarterly NDVI monitoring to detect early-warning degradation signals.",
    "Engage local community forestry user groups (CFUGs) for long-term stewardship agreements.",
    "Consider biodiversity co-benefits certification under CCB Standards.",
  ],
};

const riskColorMap: Record<string, string> = {
  LOW: "bg-accent text-accent-foreground",
  MEDIUM: "bg-terrai-gold text-accent-foreground",
  HIGH: "bg-destructive text-destructive-foreground",
  CRITICAL: "bg-destructive text-destructive-foreground",
};

const MRVReport = () => {
  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      {/* Report Header */}
      <div className="text-center py-8">
        <div className="inline-flex items-center gap-2 bg-muted px-3 py-1 rounded-full text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-4">
          <Shield className="w-3.5 h-3.5" /> AI-Generated Report
        </div>
        <h1 className="font-serif text-3xl text-foreground">{reportData.title}</h1>
        <p className="text-muted-foreground mt-2">{reportData.subtitle}</p>
        <p className="text-xs text-muted-foreground/60 mt-1">{reportData.date}</p>
      </div>

      {/* Executive Summary */}
      <Card className="p-8 shadow-card">
        <div className="flex items-center gap-2 mb-4">
          <FileText className="w-5 h-5 text-accent" />
          <h2 className="font-serif text-xl text-foreground">Executive Summary</h2>
        </div>
        <Separator className="mb-4" />
        <p className="text-sm text-muted-foreground leading-relaxed">{reportData.executiveSummary}</p>
      </Card>

      {/* Key Findings */}
      <Card className="p-8 shadow-card">
        <div className="flex items-center gap-2 mb-4">
          <ListChecks className="w-5 h-5 text-accent" />
          <h2 className="font-serif text-xl text-foreground">Key Findings</h2>
        </div>
        <Separator className="mb-4" />
        <ul className="space-y-3">
          {reportData.keyFindings.map((finding, i) => (
            <li key={i} className="flex items-start gap-3">
              <CheckCircle className="w-4 h-4 text-accent mt-0.5 shrink-0" />
              <span className="text-sm text-muted-foreground leading-relaxed">{finding}</span>
            </li>
          ))}
        </ul>
      </Card>

      {/* Risk Assessment */}
      <Card className="p-8 shadow-card">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-accent" />
            <h2 className="font-serif text-xl text-foreground">Risk Assessment</h2>
          </div>
          <Badge className={`${riskColorMap[reportData.riskLevel]} text-xs px-3 py-1 font-bold`}>
            Overall: {reportData.riskLevel}
          </Badge>
        </div>
        <Separator className="mb-4" />
        <div className="space-y-3">
          {reportData.riskDetails.map((risk, i) => (
            <div key={i} className="flex items-center justify-between py-3 border-b border-border last:border-0">
              <div className="flex-1">
                <span className="text-sm font-medium text-foreground">{risk.factor}</span>
                <p className="text-xs text-muted-foreground mt-0.5">{risk.note}</p>
              </div>
              <Badge className={`${riskColorMap[risk.level]} text-[10px] px-2.5 py-0.5 font-bold shrink-0 ml-4`}>
                {risk.level}
              </Badge>
            </div>
          ))}
        </div>
      </Card>

      {/* Recommendations */}
      <Card className="p-8 shadow-card border-l-4 border-l-accent">
        <h2 className="font-serif text-xl text-foreground mb-4">Recommendations</h2>
        <Separator className="mb-4" />
        <ol className="space-y-3 list-decimal list-inside">
          {reportData.recommendations.map((rec, i) => (
            <li key={i} className="text-sm text-muted-foreground leading-relaxed pl-1">
              {rec}
            </li>
          ))}
        </ol>
      </Card>

      {/* Footer */}
      <div className="text-center py-6">
        <p className="text-xs text-muted-foreground/40 italic">
          This report was generated by TerrAI's AI engine using satellite imagery and geospatial analysis.
          Results should be validated with ground-truth data before making investment decisions.
        </p>
      </div>
    </div>
  );
};

export default MRVReport;
