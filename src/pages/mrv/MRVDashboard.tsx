import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Leaf, TrendingUp, TrendingDown, MapPin, TreePine, Activity, Layers, Loader2 } from "lucide-react";
import { useState } from "react";
import {
  AreaChart, Area, BarChart, Bar, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";
import { useMRV } from "@/contexts/MRVContext";
import { analyzeForest, generateReport, type AnalyzeRequest, type ReportRequest } from "@/lib/mrv-api";
import { useToast } from "@/hooks/use-toast";
import { useCreateBiomassEntry } from "@/hooks/use-biomass-history";
import { useProjects } from "@/hooks/use-projects";
import { useAuth } from "@/contexts/AuthContext";
import { NepalMap } from "@/components/app/NepalMap";
import { DrawMap } from "@/components/app/DrawMap";
import { NEPAL_DISTRICTS, COMMUNITY_FORESTS } from "@/lib/nepal-locations";

const FOREST_TYPES: Record<string, string> = {
  "Tropical Moist": "tropical_moist",
  "Subtropical Broadleaf": "subtropical_broadleaf",
  "Temperate Conifer": "temperate_conifer",
  "Alpine Scrub": "alpine_scrub",
};

type LocationSource = "district" | "community" | "custom" | "draw";

type LoadingStep = "idle" | "analyzing" | "reporting";

const LOADING_MESSAGES: Record<LoadingStep, string> = {
  idle: "",
  analyzing: "Fetching satellite data & computing NDVI…",
  reporting: "Llama 3 is generating due diligence report…",
};

const MRVDashboard = () => {
  const [locationSource, setLocationSource] = useState<LocationSource>("district");
  const [selectedLocation, setSelectedLocation] = useState("");
  const [customLat, setCustomLat] = useState("27.5");
  const [customLon, setCustomLon] = useState("84.3");
  const [forestType, setForestType] = useState("Tropical Moist");
  const [baselineYear, setBaselineYear] = useState("2022");
  const [comparisonYear, setComparisonYear] = useState("2024");
  const [bufKm, setBufKm] = useState(5);
  const [loadingStep, setLoadingStep] = useState<LoadingStep>("idle");
  const [customGeojson, setCustomGeojson] = useState<GeoJSON.GeoJSON | null>(null);
  const { analysisData, setAnalysisData, setReportData, setRequestBody, setLocationName, setReportLoading } = useMRV();
  const { toast } = useToast();
  const createBiomass = useCreateBiomassEntry();
  const { user } = useAuth();
  const { data: projects } = useProjects();
  const [selectedProjectId, setSelectedProjectId] = useState<string>("");

  const isLoading = loadingStep !== "idle";

  const getCoordinates = (): { lat: number; lon: number; name: string } | null => {
    if (locationSource === "draw") return null;
    if (locationSource === "district" && selectedLocation) {
      const loc = NEPAL_DISTRICTS[selectedLocation];
      return { lat: loc.lat, lon: loc.lon, name: selectedLocation };
    }
    if (locationSource === "community" && selectedLocation) {
      const loc = COMMUNITY_FORESTS[selectedLocation];
      return { lat: loc.lat, lon: loc.lon, name: selectedLocation };
    }
    return { lat: parseFloat(customLat), lon: parseFloat(customLon), name: `${customLat}°N, ${customLon}°E` };
  };

  const handleAnalyse = async () => {
    const coords = getCoordinates();
    const isDraw = locationSource === "draw";

    if (isDraw && !customGeojson) {
      toast({ title: "No polygon drawn", description: "Please draw a polygon on the map first.", variant: "destructive" });
      return;
    }

    // Step 1: Analyse
    setLoadingStep("analyzing");
    const body: AnalyzeRequest = {
      year1: parseInt(baselineYear),
      year2: parseInt(comparisonYear),
      start_month: 1,
      end_month: 3,
      forest_type: FOREST_TYPES[forestType] || "tropical_moist",
      run_multiyear: true,
      ...(isDraw
        ? { geojson: customGeojson! }
        : { lat: coords!.lat, lon: coords!.lon, buf_km: bufKm }),
    };

    try {
      const data = await analyzeForest(body);
      setAnalysisData(data);
      setRequestBody(body);
      const locName = isDraw ? "Custom Polygon" : coords!.name;
      setLocationName(locName);

      // Save to DB if a project is selected
      if (selectedProjectId && user) {
        try {
          const ce = data.carbon_estimate;
          await createBiomass.mutateAsync({
            project_id: selectedProjectId,
            carbon_density: ce ? ce.c_ha : 0,
            health_score: (data.ndvi_year2 ?? 0) * 100,
          });
          toast({ title: "Analysis saved", description: "Results stored to your project." });
        } catch {
          // Non-blocking
        }
      }

      // Step 2: Generate report
      setLoadingStep("reporting");
      const reportBody: ReportRequest = {
        location: locName,
        lat: coords?.lat ?? 0,
        lon: coords?.lon ?? 0,
        year1: body.year1,
        year2: body.year2,
        start_month: body.start_month,
        end_month: body.end_month,
        ndvi_year1: data.ndvi_year1,
        ndvi_year2: data.ndvi_year2,
        change_pct: data.change_pct,
        carbon_estimate: data.carbon_estimate,
        trend_data: data.trend_data,
        monthly_series: data.monthly_series,
      };

      try {
        const report = await generateReport(reportBody);
        setReportData(report);
      } catch {
        toast({ title: "Report generation failed", description: "Analysis succeeded but the AI report could not be generated.", variant: "destructive" });
      }
    } catch (err) {
      toast({
        title: "Analysis Failed",
        description: err instanceof Error ? err.message : "Could not reach backend.",
        variant: "destructive",
      });
    } finally {
      setLoadingStep("idle");
    }
  };

  const d = analysisData;
  const changePct = d?.change_pct ?? 0;
  const isPositive = changePct > 0;
  const ce = d?.carbon_estimate;
  const coords = getCoordinates();

  const locationOptions = locationSource === "district"
    ? Object.keys(NEPAL_DISTRICTS)
    : locationSource === "community"
    ? Object.keys(COMMUNITY_FORESTS)
    : [];

  const canAnalyse =
    !isLoading &&
    (locationSource === "draw"
      ? !!customGeojson
      : locationSource === "custom"
      ? true
      : !!selectedLocation);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-serif text-2xl text-foreground">Forest Health Dashboard</h1>
        <p className="text-sm text-muted-foreground mt-1">Analyse satellite-derived vegetation indices and carbon stocks</p>
      </div>

      {/* Input Form */}
      <Card className="p-6 shadow-card space-y-4">
        {/* Location source selector */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
          <div className="space-y-1.5">
            <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Location Source</Label>
            <Select value={locationSource} onValueChange={(v) => { setLocationSource(v as LocationSource); setSelectedLocation(""); setCustomGeojson(null); }}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="district">Nepal District</SelectItem>
                <SelectItem value="community">Community Forest</SelectItem>
                <SelectItem value="custom">Custom Coordinates</SelectItem>
                <SelectItem value="draw">Draw on Map</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {locationSource === "draw" ? (
            <div className="md:col-span-2 flex items-center gap-2 text-xs text-muted-foreground bg-muted/50 rounded-md px-3 py-2">
              <MapPin className="w-3.5 h-3.5 shrink-0" />
              <span>{customGeojson ? "✓ Polygon drawn — ready to analyse" : "Use the drawing tools on the map below to define your AOI"}</span>
            </div>
          ) : locationSource !== "custom" ? (
            <div className="space-y-1.5 md:col-span-2">
              <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                {locationSource === "district" ? "District" : "Community Forest"}
              </Label>
              <Select value={selectedLocation} onValueChange={setSelectedLocation}>
                <SelectTrigger><SelectValue placeholder={`Select a ${locationSource === "district" ? "district" : "community forest"}…`} /></SelectTrigger>
                <SelectContent className="max-h-64">
                  {locationOptions.map((name) => (
                    <SelectItem key={name} value={name}>{name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          ) : (
            <>
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Latitude</Label>
                <Input value={customLat} onChange={(e) => setCustomLat(e.target.value)} placeholder="27.5" />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Longitude</Label>
                <Input value={customLon} onChange={(e) => setCustomLon(e.target.value)} placeholder="84.3" />
              </div>
            </>
          )}
        </div>

        {/* Radius + Analysis params */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
          {locationSource !== "draw" && (
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Radius: {bufKm} km
              </Label>
              <Slider
                value={[bufKm]}
                onValueChange={([v]) => setBufKm(v)}
                min={1}
                max={20}
                step={1}
              />
            </div>
          )}
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
          <div className="space-y-1.5">
            <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Save to Project</Label>
            <Select value={selectedProjectId} onValueChange={setSelectedProjectId}>
              <SelectTrigger className="max-w-xs"><SelectValue placeholder="Select a project (optional)" /></SelectTrigger>
              <SelectContent>
                {projects.map((p) => <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
        )}

        {/* Selected location preview */}
        {(locationSource !== "custom" && locationSource !== "draw" && selectedLocation) && coords && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground bg-muted/50 rounded-md px-3 py-2">
            <MapPin className="w-3.5 h-3.5" />
            <span>{selectedLocation} — {coords.lat.toFixed(4)}°N, {coords.lon.toFixed(4)}°E</span>
          </div>
        )}

        <div className="flex justify-end">
          <Button
            onClick={handleAnalyse}
            disabled={!canAnalyse}
            className="bg-primary text-primary-foreground hover:bg-primary/90 px-8"
          >
            {isLoading ? (
              <span className="flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin" />
                {LOADING_MESSAGES[loadingStep]}
              </span>
            ) : (
              <span className="flex items-center gap-2">
                <Leaf className="w-4 h-4" /> Analyse Forest
              </span>
            )}
          </Button>
        </div>
      </Card>

      {/* Drawing map – separate, with labeled forests */}
      {locationSource === "draw" && (
        <DrawMap onPolygonCreated={setCustomGeojson} height="h-96" />
      )}

      {/* Results / AOI map */}
      {locationSource !== "draw" && coords && (
        <NepalMap
          markers={[{ lat: coords.lat, lon: coords.lon, label: coords.name }]}
          circleCenter={[coords.lat, coords.lon]}
          circleRadiusKm={bufKm}
          tileUrl={d?.tile_url}
        />
      )}

      {isLoading ? (
        <div className="space-y-6 animate-fade-in-up">
          {/* Loading step indicator */}
          <Card className="p-4 shadow-card border-accent/30 bg-accent/5 flex items-center gap-3">
            <Loader2 className="w-5 h-5 animate-spin text-accent" />
            <div>
              <p className="text-sm font-medium text-foreground">{LOADING_MESSAGES[loadingStep]}</p>
              <p className="text-xs text-muted-foreground mt-0.5">
                Step {loadingStep === "analyzing" ? "1/2" : "2/2"}
              </p>
            </div>
          </Card>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Card key={i} className="p-5 shadow-card space-y-3">
                <Skeleton className="h-3 w-20" />
                <Skeleton className="h-8 w-24" />
              </Card>
            ))}
          </div>
          <Skeleton className="h-48 w-full rounded-lg" />
        </div>
      ) : !d ? (
        <div className="text-center py-20">
          <TreePine className="w-16 h-16 mx-auto text-muted-foreground/20 mb-4" />
          <p className="text-muted-foreground">Select a location and click <strong>Analyse Forest</strong> to begin.</p>
        </div>
      ) : (
        <div className="space-y-6 animate-fade-in-up">
          {/* Metrics Row */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { label: `NDVI ${baselineYear}`, value: d.ndvi_year1?.toFixed(4) ?? "—", icon: Activity, color: "text-foreground" },
              { label: `NDVI ${comparisonYear}`, value: d.ndvi_year2?.toFixed(4) ?? "—", icon: Layers, color: "text-foreground" },
              { label: "Change", value: `${isPositive ? "+" : ""}${changePct.toFixed(1)}%`, icon: isPositive ? TrendingUp : TrendingDown, color: isPositive ? "text-accent" : "text-destructive" },
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

          {/* Carbon Stock */}
          {ce && (
            <Card className="bg-primary p-6 shadow-card border-0">
              <h3 className="font-serif text-lg text-primary-foreground/80 mb-4 flex items-center gap-2">
                <Leaf className="w-5 h-5" /> Carbon Stock Estimate
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {[
                  { label: "Above-Ground Biomass", val: `${ce.agb_ha?.toFixed(1) ?? "—"}`, unit: "tonnes/ha" },
                  { label: "Total Carbon Stock", val: (ce.total_c ?? 0).toLocaleString(), unit: "tonnes C" },
                  { label: "Total CO₂ Equivalent", val: (ce.total_co2 ?? 0).toLocaleString(), unit: "tonnes CO₂e" },
                  { label: "Area Analysed", val: `${ce.area_ha ?? "—"}`, unit: "hectares" },
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
          )}

          {/* Charts */}
          {(d.trend_data?.length > 0 || d.monthly_series?.length > 0) && (
            <div className="grid lg:grid-cols-2 gap-6">
              {d.trend_data?.length > 0 && (
                <Card className="p-5 shadow-card">
                  <h3 className="font-serif text-base text-foreground mb-4">Multi-Year NDVI Trend</h3>
                  <ResponsiveContainer width="100%" height={260}>
                    <AreaChart data={d.trend_data}>
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

              {d.monthly_series?.length > 0 && (
                <Card className="p-5 shadow-card">
                  <h3 className="font-serif text-base text-foreground mb-4">Monthly NDVI ({comparisonYear})</h3>
                  <ResponsiveContainer width="100%" height={260}>
                    <BarChart data={d.monthly_series}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(140,25%,88%)" />
                      <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                      <YAxis domain={["auto", "auto"]} tick={{ fontSize: 12 }} />
                      <Tooltip contentStyle={{ borderRadius: 8, fontSize: 13 }} />
                      <Bar dataKey="ndvi" radius={[4, 4, 0, 0]}>
                        {d.monthly_series.map((_entry, i) => (
                          <Cell key={i} fill={_entry.ndvi > 0.65 ? "hsl(153,40%,42%)" : _entry.ndvi > 0.55 ? "hsl(153,30%,55%)" : "hsl(45,50%,55%)"} />
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
