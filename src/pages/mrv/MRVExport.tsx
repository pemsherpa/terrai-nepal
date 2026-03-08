import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Download, FileText, MapPin, Leaf, Calendar, CheckCircle, TreePine } from "lucide-react";
import { useState } from "react";
import { useMRV } from "@/contexts/MRVContext";
import { downloadPdf } from "@/lib/mrv-api";
import { useToast } from "@/hooks/use-toast";

const MRVExport = () => {
  const [downloading, setDownloading] = useState(false);
  const [downloaded, setDownloaded] = useState(false);
  const { analysisData, reportData, reportLoading, requestBody } = useMRV();
  const { toast } = useToast();

  if (!analysisData) {
    return (
      <div className="p-6 max-w-3xl mx-auto text-center py-20">
        <TreePine className="w-16 h-16 mx-auto text-muted-foreground/20 mb-4" />
        <p className="text-muted-foreground">Run an analysis on the <strong>Dashboard</strong> first to export a report.</p>
      </div>
    );
  }

  const d = analysisData;

  const handleDownload = async () => {
    setDownloading(true);
    setDownloaded(false);
    try {
      await downloadPdf({ ...requestBody, ...d } as Record<string, unknown>);
      setDownloaded(true);
    } catch (err) {
      toast({
        title: "PDF Export Failed",
        description: err instanceof Error ? err.message : "Could not reach backend.",
        variant: "destructive",
      });
    } finally {
      setDownloading(false);
    }
  };

  const summaryItems = [
    { icon: MapPin, label: "Coordinates", value: `${requestBody?.lat ?? "—"}°N, ${requestBody?.lon ?? "—"}°E` },
    { icon: Leaf, label: "Forest Type", value: String(requestBody?.forest_type ?? "—") },
    { icon: Calendar, label: "Period", value: `${requestBody?.year1 ?? "—"} → ${requestBody?.year2 ?? "—"}` },
    { icon: Leaf, label: "NDVI Change", value: `${d.change_percent > 0 ? "+" : ""}${d.change_percent?.toFixed(1) ?? "—"}%` },
    { icon: Leaf, label: "Total Carbon", value: `${(d.total_carbon ?? 0).toLocaleString()} tonnes C` },
    { icon: Leaf, label: "CO₂ Equivalent", value: `${(d.total_co2e ?? 0).toLocaleString()} tonnes CO₂e` },
    { icon: MapPin, label: "Area", value: `${d.area_ha ?? "—"} hectares` },
  ];

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="font-serif text-2xl text-foreground">Export Center</h1>
        <p className="text-sm text-muted-foreground mt-1">Download your analysis as a formal PDF report</p>
      </div>

      <Card className="p-6 shadow-card">
        <h2 className="font-serif text-lg text-foreground mb-4 flex items-center gap-2">
          <FileText className="w-5 h-5 text-accent" /> Analysis Summary
        </h2>
        <Separator className="mb-5" />
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {summaryItems.map((item) => (
            <div key={item.label} className="flex items-start gap-3 py-2">
              <item.icon className="w-4 h-4 text-muted-foreground mt-0.5 shrink-0" />
              <div>
                <div className="text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">{item.label}</div>
                <div className="text-sm text-foreground font-medium">{item.value}</div>
              </div>
            </div>
          ))}
        </div>
      </Card>

      <Card className="p-8 shadow-card text-center">
        <div className="w-16 h-16 rounded-2xl bg-muted flex items-center justify-center mx-auto mb-5">
          <Download className="w-8 h-8 text-muted-foreground" />
        </div>
        <h2 className="font-serif text-xl text-foreground mb-2">Official PDF Report</h2>
        <p className="text-sm text-muted-foreground mb-6 max-w-md mx-auto">
          Generate a comprehensive, boardroom-ready PDF containing satellite analysis, carbon estimates, risk assessment, and AI-generated recommendations.
        </p>
        <Button
          onClick={handleDownload}
          disabled={downloading || reportLoading || !reportData}
          size="lg"
          className="bg-primary text-primary-foreground hover:bg-primary/90 px-10 text-base"
        >
          {downloading ? (
            <span className="flex items-center gap-2">
              <span className="w-5 h-5 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
              Generating PDF…
            </span>
          ) : downloaded ? (
            <span className="flex items-center gap-2">
              <CheckCircle className="w-5 h-5" /> Download Ready
            </span>
          ) : (
            <span className="flex items-center gap-2">
              <Download className="w-5 h-5" /> Download Official PDF Report
            </span>
          )}
        </Button>
        {downloaded && (
          <p className="text-xs text-accent mt-3 animate-fade-in-up">✓ Your report has been generated successfully.</p>
        )}
        {(reportLoading || !reportData) && !downloading && (
          <p className="text-xs text-muted-foreground mt-3">Waiting for AI report to finish generating…</p>
        )}
      </Card>

      <p className="text-xs text-center text-muted-foreground/40 italic">
        Reports include TerrAI branding and are formatted for investor and regulatory submission.
      </p>
    </div>
  );
};

export default MRVExport;
