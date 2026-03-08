import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Leaf, TrendingUp, TrendingDown, MapPin, TreePine, Activity, Layers, Loader2 } from "lucide-react";
import { useState } from "react";
import {
  AreaChart, Area, BarChart, Bar, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";
import { useMRV } from "@/contexts/MRVContext";
import { analyzeForest, generateReport } from "@/lib/mrv-api";
import { useToast } from "@/hooks/use-toast";
import { useCreateBiomassEntry } from "@/hooks/use-biomass-history";
import { useProjects } from "@/hooks/use-projects";
import { useAuth } from "@/contexts/AuthContext";
import { NepalMap } from "@/components/app/NepalMap";

const FOREST_TYPES: Record<string, string> = {
  "Tropical Moist": "tropical_moist",
  "Subtropical Broadleaf": "subtropical_broadleaf",
  "Temperate Conifer": "temperate_conifer",
  "Alpine Scrub": "alpine_scrub",
};

const MRVDashboard = () => {
  const [lat, setLat] = useState("27.5");
  const [lon, setLon] = useState("84.3");
  const [forestType, setForestType] = useState("Tropical Moist");
  const [baselineYear, setBaselineYear] = useState("2022");
  const [comparisonYear, setComparisonYear] = useState("2024");
  const [loading, setLoading] = useState(false);
  const { analysisData, setAnalysisData, setReportData, setRequestBody, reportLoading, setReportLoading } = useMRV();
  const { toast } = useToast();
  const createBiomass = useCreateBiomassEntry();
  const { user } = useAuth();
  const { data: projects } = useProjects();
  const [selectedProjectId, setSelectedProjectId] = useState<string>("");

  const handleAnalyse = async () => {
    setLoading(true);
    const body = {
      lat: parseFloat(lat),
      lon: parseFloat(lon),
      buf_km: 5,
      year1: parseInt(baselineYear),
      year2: parseInt(comparisonYear),
      start_month: 1,
      end_month: 3,
      forest_type: FOREST_TYPES[forestType] || "tropical_moist",
      run_multiyear: true,
    };

    try {
      const data = await analyzeForest(body);
      setAnalysisData(data);
      setRequestBody(body as unknown as Record<string, unknown>);

      // Save to DB if a project is selected
      if (selectedProjectId && user) {
        try {
          await createBiomass.mutateAsync({
            project_id: selectedProjectId,
            carbon_density: data.total_carbon / (data.area_ha || 1),
            health_score: data.ndvi_year2 * 100,
          });
          toast({ title: "Analysis saved", description: "Results stored to your project." });
        } catch {
          // Non-blocking — analysis still succeeded
        }
      }

      // Trigger report generation in background
      setReportLoading(true);
      generateReport(data as unknown as Record<string, unknown>)
        .then(setReportData)
        .catch(() => {})
        .finally(() => setReportLoading(false));
    } catch (err) {
      toast({
        title: "Analysis Failed",
        description: err instanceof Error ? err.message : "Could not reach backend. Is it running on localhost:8000?",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const d = analysisData;
  const changePercent = d?.change_percent ?? 0;
  const isPositive = changePercent > 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-serif text-2xl text-foreground">Forest Health Dashboard</h1>
        <p className="text-sm text-muted-foreground mt-1">Analyse satellite-derived vegetation indices and carbon stocks</p>
      </div>

      {/* Input Form */}
      <Card className="p-6 shadow-card">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 items-end">
          <div className="space-y-1.5">
            <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Latitude</Label>
            <Input value={lat} onChange={(e) => setLat(e.target.value)} placeholder="27.5" />
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Longitude</Label>
            <Input value={lon} onChange={(e) => setLon(e.target.value)} placeholder="84.3" />
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Forest Type</Label>
            <Select value={forestType} onValueChange={setForestType}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {Object.keys(FOREST_TYPES).map((f) => <SelectItem key={f} value={f}>{f}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Baseline Year</Label>
            <Select value={baselineYear} onValueChange={setBaselineYear}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {[2020, 2021, 2022, 2023, 2024].map((y) => <SelectItem key={y} value={String(y)}>{y}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Comparison Year</Label>
            <Select value={comparisonYear} onValueChange={setComparisonYear}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {[2022, 2023, 2024, 2025].map((y) => <SelectItem key={y} value={String(y)}>{y}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
        </div>
        {/* Project selector for saving */}
        {projects && projects.length > 0 && (
          <div className="mt-4 space-y-1.5">
            <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Save to Project</Label>
            <Select value={selectedProjectId} onValueChange={setSelectedProjectId}>
              <SelectTrigger className="max-w-xs"><SelectValue placeholder="Select a project (optional)" /></SelectTrigger>
              <SelectContent>
                {projects.map((p) => <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
        )}
        <div className="mt-5 flex justify-end">
          <Button
            onClick={handleAnalyse}
            disabled={loading}
            className="bg-primary text-primary-foreground hover:bg-primary/90 px-8"
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <span className="w-4 h-4 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
                Analysing…
              </span>
            ) : (
              <span className="flex items-center gap-2">
                <Leaf className="w-4 h-4" /> Analyse Forest
              </span>
            )}
          </Button>
        </div>
      </Card>

      {loading ? (
        <div className="space-y-6 animate-fade-in-up">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Card key={i} className="p-5 shadow-card space-y-3">
                <Skeleton className="h-3 w-20" />
                <Skeleton className="h-8 w-24" />
              </Card>
            ))}
          </div>
          <Skeleton className="h-64 w-full rounded-lg" />
          <Skeleton className="h-48 w-full rounded-lg" />
        </div>
      ) : !d ? (
        <div className="text-center py-20">
          <TreePine className="w-16 h-16 mx-auto text-muted-foreground/20 mb-4" />
          <p className="text-muted-foreground">Enter coordinates and click <strong>Analyse Forest</strong> to begin.</p>
        </div>
      ) : (
        <div className="space-y-6 animate-fade-in-up">
          {/* Report generating indicator */}
          {reportLoading && (
            <Card className="p-4 shadow-card border-accent/30 bg-accent/5 flex items-center gap-3">
              <Loader2 className="w-4 h-4 animate-spin text-accent" />
              <span className="text-sm text-muted-foreground">AI Due Diligence Report is generating in the background…</span>
            </Card>
          )}
          {/* Metrics Row */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { label: `NDVI ${baselineYear}`, value: d.ndvi_year1?.toFixed(4) ?? "—", icon: Activity, color: "text-foreground" },
              { label: `NDVI ${comparisonYear}`, value: d.ndvi_year2?.toFixed(4) ?? "—", icon: Layers, color: "text-foreground" },
              { label: "Change", value: `${isPositive ? "+" : ""}${changePercent.toFixed(1)}%`, icon: isPositive ? TrendingUp : TrendingDown, color: isPositive ? "text-accent" : "text-destructive" },
              { label: "Total Area", value: `${d.area_ha ?? "—"} ha`, icon: MapPin, color: "text-foreground" },
            ].map((m) => (
              <Card key={m.label} className="p-5 shadow-card">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">{m.label}</span>
                  <m.icon className="w-4 h-4 text-muted-foreground" />
                </div>
                <div className={`font-serif text-2xl ${m.color}`}>{m.value}</div>
              </Card>
            ))}
          </div>

          {/* Interactive Nepal Map */}
          <NepalMap
            markers={[{ lat: parseFloat(lat), lon: parseFloat(lon), label: `Analysis Point (${lat}°N, ${lon}°E)` }]}
          />

          {/* Carbon Stock */}
          <Card className="bg-primary p-6 shadow-card border-0">
            <h3 className="font-serif text-lg text-primary-foreground/80 mb-4 flex items-center gap-2">
              <Leaf className="w-5 h-5" /> Carbon Stock Estimate
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {[
                { label: "Above-Ground Biomass", val: `${d.agb_ha ?? "—"}`, unit: "tonnes/ha" },
                { label: "Total Carbon Stock", val: (d.total_carbon ?? 0).toLocaleString(), unit: "tonnes C" },
                { label: "Total CO₂ Equivalent", val: (d.total_co2e ?? 0).toLocaleString(), unit: "tonnes CO₂e" },
                { label: "Area Analysed", val: `${d.area_ha ?? "—"}`, unit: "hectares" },
              ].map((c) => (
                <div key={c.label} className="bg-primary-foreground/10 rounded-lg p-4 text-center">
                  <div className="text-[10px] uppercase tracking-widest text-primary-foreground/50 mb-1 font-semibold">{c.label}</div>
                  <div className="font-serif text-2xl text-primary-foreground">{c.val}</div>
                  <div className="text-xs text-primary-foreground/40 mt-0.5">{c.unit}</div>
                </div>
              ))}
            </div>
            <p className="text-xs text-primary-foreground/30 mt-4 italic">
              ⚠️ Satellite-based estimates · Nepal FAO/ICIMOD literature values · Field calibration required
            </p>
          </Card>

          {/* Charts */}
          {(d.ndvi_trend?.length || d.monthly_ndvi?.length) && (
            <div className="grid lg:grid-cols-2 gap-6">
              {d.ndvi_trend?.length > 0 && (
                <Card className="p-5 shadow-card">
                  <h3 className="font-serif text-base text-foreground mb-4">Multi-Year NDVI Trend</h3>
                  <ResponsiveContainer width="100%" height={260}>
                    <AreaChart data={d.ndvi_trend}>
                      <defs>
                        <linearGradient id="mrvNdviGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="hsl(153,40%,42%)" stopOpacity={0.3} />
                          <stop offset="100%" stopColor="hsl(153,40%,42%)" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(140,25%,88%)" />
                      <XAxis dataKey="year" tick={{ fontSize: 12 }} />
                      <YAxis domain={["auto", "auto"]} tick={{ fontSize: 12 }} />
                      <Tooltip contentStyle={{ borderRadius: 8, fontSize: 13 }} />
                      <Area type="monotone" dataKey="ndvi" stroke="hsl(153,40%,42%)" strokeWidth={2.5} fill="url(#mrvNdviGrad)" dot={{ r: 4, fill: "hsl(153,44%,18%)", stroke: "#fff", strokeWidth: 2 }} />
                    </AreaChart>
                  </ResponsiveContainer>
                </Card>
              )}

              {d.monthly_ndvi?.length > 0 && (
                <Card className="p-5 shadow-card">
                  <h3 className="font-serif text-base text-foreground mb-4">Monthly NDVI ({comparisonYear})</h3>
                  <ResponsiveContainer width="100%" height={260}>
                    <BarChart data={d.monthly_ndvi}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(140,25%,88%)" />
                      <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                      <YAxis domain={["auto", "auto"]} tick={{ fontSize: 12 }} />
                      <Tooltip contentStyle={{ borderRadius: 8, fontSize: 13 }} />
                      <Bar dataKey="ndvi" radius={[4, 4, 0, 0]}>
                        {d.monthly_ndvi.map((entry, i) => (
                          <Cell key={i} fill={entry.ndvi > 0.65 ? "hsl(153,40%,42%)" : entry.ndvi > 0.55 ? "hsl(153,30%,55%)" : "hsl(45,50%,55%)"} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </Card>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default MRVDashboard;
