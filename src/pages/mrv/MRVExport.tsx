import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Download, FileText, MapPin, Leaf, Calendar, CheckCircle } from "lucide-react";
import { useState } from "react";

const summaryData = {
  location: "Chitwan National Park",
  coordinates: "27.5°N, 84.3°E",
  forestType: "Subtropical Broadleaf",
  baselineYear: 2024,
  comparisonYear: 2025,
  ndviChange: "+4.5%",
  totalCarbon: "22,440 tonnes C",
  totalCo2e: "82,250 tonnes CO₂e",
  area: "250 hectares",
  riskLevel: "LOW",
  reportDate: "March 7, 2026",
};

const MRVExport = () => {
  const [downloading, setDownloading] = useState(false);
  const [downloaded, setDownloaded] = useState(false);

  const handleDownload = () => {
    setDownloading(true);
    setDownloaded(false);
    // Simulate PDF generation / API call
    setTimeout(() => {
      setDownloading(false);
      setDownloaded(true);
    }, 2500);
  };

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="font-serif text-2xl text-foreground">Export Center</h1>
        <p className="text-sm text-muted-foreground mt-1">Download your analysis as a formal PDF report</p>
      </div>

      {/* Analysis Summary */}
      <Card className="p-6 shadow-card">
        <h2 className="font-serif text-lg text-foreground mb-4 flex items-center gap-2">
          <FileText className="w-5 h-5 text-accent" /> Analysis Summary
        </h2>
        <Separator className="mb-5" />

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {[
            { icon: MapPin, label: "Location", value: summaryData.location },
            { icon: MapPin, label: "Coordinates", value: summaryData.coordinates },
            { icon: Leaf, label: "Forest Type", value: summaryData.forestType },
            { icon: Calendar, label: "Period", value: `${summaryData.baselineYear} → ${summaryData.comparisonYear}` },
            { icon: Leaf, label: "NDVI Change", value: summaryData.ndviChange },
            { icon: Leaf, label: "Total Carbon", value: summaryData.totalCarbon },
            { icon: Leaf, label: "CO₂ Equivalent", value: summaryData.totalCo2e },
            { icon: MapPin, label: "Area", value: summaryData.area },
          ].map((item) => (
            <div key={item.label} className="flex items-start gap-3 py-2">
              <item.icon className="w-4 h-4 text-muted-foreground mt-0.5 shrink-0" />
              <div>
                <div className="text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">{item.label}</div>
                <div className="text-sm text-foreground font-medium">{item.value}</div>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-4 flex items-center gap-2">
          <span className="text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">Risk Level:</span>
          <Badge className="bg-accent text-accent-foreground text-xs font-bold">{summaryData.riskLevel}</Badge>
        </div>
      </Card>

      {/* Download Section */}
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
          disabled={downloading}
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
          <p className="text-xs text-accent mt-3 animate-fade-in-up">
            ✓ Your report has been generated successfully.
          </p>
        )}
      </Card>

      <p className="text-xs text-center text-muted-foreground/40 italic">
        Reports include TerrAI branding and are formatted for investor and regulatory submission.
      </p>
    </div>
  );
};

export default MRVExport;
