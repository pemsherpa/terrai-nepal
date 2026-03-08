import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Button } from "@/components/ui/button";
import { Shield, CheckCircle, AlertTriangle, FileText, ListChecks, Loader2 } from "lucide-react";
import { useMRV } from "@/contexts/MRVContext";
import { generateReport, type ReportRequest } from "@/lib/mrv-api";
import { useState } from "react";
import { useToast } from "@/hooks/use-toast";

const riskColorMap: Record<string, string> = {
  LOW: "bg-accent text-accent-foreground",
  MEDIUM: "bg-terrai-gold text-accent-foreground",
  HIGH: "bg-destructive text-destructive-foreground",
  CRITICAL: "bg-destructive text-destructive-foreground",
};

const MRVReport = () => {
  const { analysisData, reportData, setReportData, requestBody, locationName } = useMRV();
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();

  const handleGenerate = async () => {
    if (!analysisData || !requestBody) return;
    setLoading(true);
    try {
      const body: ReportRequest = {
        location: locationName,
        lat: requestBody.lat,
        lon: requestBody.lon,
        year1: requestBody.year1,
        year2: requestBody.year2,
        start_month: requestBody.start_month,
        end_month: requestBody.end_month,
        ndvi_year1: analysisData.ndvi_year1,
        ndvi_year2: analysisData.ndvi_year2,
        change_pct: analysisData.change_pct,
        carbon_estimate: analysisData.carbon_estimate,
        trend_data: analysisData.trend_data,
        monthly_series: analysisData.monthly_series,
      };
      const data = await generateReport(body);
      setReportData(data);
    } catch (err) {
      toast({
        title: "Report Generation Failed",
        description: err instanceof Error ? err.message : "Could not reach backend.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  if (!analysisData) {
    return (
      <div className="p-6 max-w-4xl mx-auto text-center py-20">
        <Shield className="w-16 h-16 mx-auto text-muted-foreground/20 mb-4" />
        <p className="text-muted-foreground">Run an analysis on the <strong>Dashboard</strong> first to generate a report.</p>
      </div>
    );
  }

  if (!reportData) {
    return (
      <div className="p-6 max-w-4xl mx-auto text-center py-20">
        <Shield className="w-16 h-16 mx-auto text-muted-foreground/20 mb-4" />
        <p className="text-muted-foreground mb-6">Analysis data is ready. Generate your AI Due Diligence Report.</p>
        <Button onClick={handleGenerate} disabled={loading} className="bg-primary text-primary-foreground hover:bg-primary/90 px-8">
          {loading ? (
            <span className="flex items-center gap-2"><Loader2 className="w-4 h-4 animate-spin" /> Generating…</span>
          ) : (
            "Generate Report"
          )}
        </Button>
      </div>
    );
  }

  const r = reportData;

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      {/* Report Header */}
      <div className="text-center py-8">
        <div className="inline-flex items-center gap-2 bg-muted px-3 py-1 rounded-full text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-4">
          <Shield className="w-3.5 h-3.5" /> AI-Generated Report
        </div>
        <h1 className="font-serif text-3xl text-foreground">{r.title}</h1>
        <p className="text-muted-foreground mt-2">{r.subtitle}</p>
        <p className="text-xs text-muted-foreground/60 mt-1">{r.date}</p>
      </div>

      {/* Executive Summary */}
      <Card className="p-8 shadow-card">
        <div className="flex items-center gap-2 mb-4">
          <FileText className="w-5 h-5 text-accent" />
          <h2 className="font-serif text-xl text-foreground">Executive Summary</h2>
        </div>
        <Separator className="mb-4" />
        <p className="text-sm text-muted-foreground leading-relaxed">{r.executive_summary}</p>
      </Card>

      {/* Key Findings */}
      {r.key_findings?.length > 0 && (
        <Card className="p-8 shadow-card">
          <div className="flex items-center gap-2 mb-4">
            <ListChecks className="w-5 h-5 text-accent" />
            <h2 className="font-serif text-xl text-foreground">Key Findings</h2>
          </div>
          <Separator className="mb-4" />
          <ul className="space-y-3">
            {r.key_findings.map((finding, i) => (
              <li key={i} className="flex items-start gap-3">
                <CheckCircle className="w-4 h-4 text-accent mt-0.5 shrink-0" />
                <span className="text-sm text-muted-foreground leading-relaxed">{finding}</span>
              </li>
            ))}
          </ul>
        </Card>
      )}

      {/* Risk Assessment */}
      <Card className="p-8 shadow-card">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-accent" />
            <h2 className="font-serif text-xl text-foreground">Risk Assessment</h2>
          </div>
          <Badge className={`${riskColorMap[r.risk_level] || "bg-muted"} text-xs px-3 py-1 font-bold`}>
            Overall: {r.risk_level}
          </Badge>
        </div>
        <Separator className="mb-4" />
        {r.risk_details?.length > 0 && (
          <div className="space-y-3">
            {r.risk_details.map((risk, i) => (
              <div key={i} className="flex items-center justify-between py-3 border-b border-border last:border-0">
                <div className="flex-1">
                  <span className="text-sm font-medium text-foreground">{risk.factor}</span>
                  <p className="text-xs text-muted-foreground mt-0.5">{risk.note}</p>
                </div>
                <Badge className={`${riskColorMap[risk.level] || "bg-muted"} text-[10px] px-2.5 py-0.5 font-bold shrink-0 ml-4`}>
                  {risk.level}
                </Badge>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Recommendations */}
      {r.recommendations?.length > 0 && (
        <Card className="p-8 shadow-card border-l-4 border-l-accent">
          <h2 className="font-serif text-xl text-foreground mb-4">Recommendations</h2>
          <Separator className="mb-4" />
          <ol className="space-y-3 list-decimal list-inside">
            {r.recommendations.map((rec, i) => (
              <li key={i} className="text-sm text-muted-foreground leading-relaxed pl-1">{rec}</li>
            ))}
          </ol>
        </Card>
      )}

      <div className="text-center py-6">
        <p className="text-xs text-muted-foreground/40 italic">
          This report was generated by TerrAI's AI engine using satellite imagery and geospatial analysis.
        </p>
      </div>
    </div>
  );
};

export default MRVReport;
