import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import {
  Leaf, TrendingUp, TrendingDown, MapPin, TreePine, Activity, Layers,
  Loader2, Download, Pentagon, Eraser, AlertTriangle, CheckCircle2, FileText,
  ChevronDown, Satellite, Upload,
  BrainCircuit, Eye, ShieldCheck,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import {
  AreaChart, Area, BarChart, Bar, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer,
} from "recharts";
import { useMRV } from "@/contexts/MRVContext";
import {
  analyzeForest, generateReport, downloadPdf, fetchPassDates, fetchDailyNdvi, fetchBaselines,
  inferVision,
  type AnalyzeRequest, type ReportRequest,
} from "@/lib/mrv-api";
import { useToast } from "@/hooks/use-toast";
import { useCreateBiomassEntry } from "@/hooks/use-biomass-history";
import { useProjects } from "@/hooks/use-projects";
import { useAuth } from "@/contexts/AuthContext";
import { NepalMap, type LatLon } from "@/components/app/NepalMap";
import { NEPAL_DISTRICTS, COMMUNITY_FORESTS } from "@/lib/nepal-locations";
import { TermInfo } from "@/components/TermInfo";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

const FOREST_TYPES: Record<string, string> = {
  "Tropical Broadleaf": "tropical_broadleaf",
  "Subtropical Broadleaf": "subtropical_broadleaf",
  "Temperate Broadleaf": "temperate_broadleaf",
  "Conifer": "conifer",
  "Default (Mixed)": "default",
};

const MONTHS = [
  { v: 1, l: "Jan" }, { v: 2, l: "Feb" }, { v: 3, l: "Mar" }, { v: 4, l: "Apr" },
  { v: 5, l: "May" }, { v: 6, l: "Jun" }, { v: 7, l: "Jul" }, { v: 8, l: "Aug" },
  { v: 9, l: "Sep" }, { v: 10, l: "Oct" }, { v: 11, l: "Nov" }, { v: 12, l: "Dec" },
];

type LocationSource = "district" | "community" | "custom" | "draw" | "geojson";
type DateMode = "season" | "exact";
type MapLayer = "year1" | "year2" | "hotspot" | "daily";

function statusFromChange(changePct: number) {
  if (changePct < -10) return { label: "Degradation Alert", detail: "CRITICAL — NDVI declined more than 10%", tone: "destructive" as const };
  if (changePct < -5) return { label: "Moderate Change", detail: "WARNING — NDVI declined 5–10%", tone: "warn" as const };
  if (changePct >= 0) return { label: "Forest Healthy", detail: "Vegetation stable or improving", tone: "good" as const };
  return { label: "Minor Variation", detail: "Small NDVI decline within seasonal noise", tone: "neutral" as const };
}

function daysInMonth(year: number, month: number) {
  return new Date(year, month, 0).getDate();
}

const MRVDashboard = () => {
  const [locationSource, setLocationSource] = useState<LocationSource>("district");
  const [selectedLocation, setSelectedLocation] = useState("");
  const [locationFilter, setLocationFilter] = useState("");
  const [customLat, setCustomLat] = useState("");
  const [customLon, setCustomLon] = useState("");
  const [forestType, setForestType] = useState("Subtropical Broadleaf");
  const [baselineYear, setBaselineYear] = useState("2022");
  const [comparisonYear, setComparisonYear] = useState("2024");
  const [startMonth, setStartMonth] = useState("1");
  const [endMonth, setEndMonth] = useState("3");
  const [startDay, setStartDay] = useState("1");
  const [endDay, setEndDay] = useState("28");
  const [dateMode, setDateMode] = useState<DateMode>("exact");
  const [baselineDate, setBaselineDate] = useState("2022-01-15");
  const [comparisonDate, setComparisonDate] = useState("2024-01-15");
  const [bufKm, setBufKm] = useState(5);
  const [drawPoints, setDrawPoints] = useState<LatLon[]>([]);
  const [geojsonText, setGeojsonText] = useState("");
  const [runMultiyear, setRunMultiyear] = useState(false);
  const [runMonthly, setRunMonthly] = useState(true);
  const [runHotspot, setRunHotspot] = useState(true);
  const [runAiReport, setRunAiReport] = useState(true);
  const [mapLayer, setMapLayer] = useState<MapLayer>("year2");
  const [loading, setLoading] = useState(false);
  const [pdfLoading, setPdfLoading] = useState(false);
  const [benchDistrict, setBenchDistrict] = useState("Nepal (National Avg)");
  const [baselines, setBaselines] = useState<Record<string, { ndvi: number; forest_cover_pct: number }>>({});

  // Daily explorer
  const [dailyYear, setDailyYear] = useState("2024");
  const [dailyMonth, setDailyMonth] = useState("1");
  const [passDates, setPassDates] = useState<string[]>([]);
  const [selectedPass, setSelectedPass] = useState("");
  const [dailyLoading, setDailyLoading] = useState(false);
  const [visionLoading, setVisionLoading] = useState(false);
  const [visionResult, setVisionResult] = useState<Awaited<ReturnType<typeof inferVision>> | null>(null);
  const [dailyResult, setDailyResult] = useState<{
    ndvi: number | null; cloud_pct: number | null; tile_url: string | null; quality: string; date: string;
  } | null>(null);

  const {
    analysisData, setAnalysisData, reportData, setReportData,
    setRequestBody, setLocationName, reportLoading, setReportLoading, locationName, requestBody,
  } = useMRV();
  const { toast } = useToast();
  const createBiomass = useCreateBiomassEntry();
  const { user } = useAuth();
  const { data: projects } = useProjects();
  const [selectedProjectId, setSelectedProjectId] = useState<string>("");

  useEffect(() => {
    fetchBaselines().then(setBaselines).catch(() => {});
  }, []);

  useEffect(() => {
    const y = parseInt(baselineYear, 10);
    const m = parseInt(endMonth, 10);
    setEndDay(String(daysInMonth(y, m)));
  }, [baselineYear, endMonth]);

  const parsedGeojson = useMemo(() => {
    if (locationSource !== "geojson" || !geojsonText.trim()) return null;
    try {
      return JSON.parse(geojsonText) as Record<string, unknown>;
    } catch {
      return null;
    }
  }, [locationSource, geojsonText]);

  const getCoordinates = (): { lat: number; lon: number; name: string } | null => {
    if (locationSource === "district" && selectedLocation) {
      const loc = NEPAL_DISTRICTS[selectedLocation];
      return { lat: loc.lat, lon: loc.lon, name: selectedLocation };
    }
    if (locationSource === "community" && selectedLocation) {
      const loc = COMMUNITY_FORESTS[selectedLocation];
      return { lat: loc.lat, lon: loc.lon, name: selectedLocation };
    }
    if (locationSource === "custom") {
      const lat = parseFloat(customLat);
      const lon = parseFloat(customLon);
      if (Number.isNaN(lat) || Number.isNaN(lon)) return null;
      return { lat, lon, name: `${lat.toFixed(4)}°N, ${lon.toFixed(4)}°E` };
    }
    if (locationSource === "draw" && drawPoints.length >= 3) {
      const lat = drawPoints.reduce((s, p) => s + p.lat, 0) / drawPoints.length;
      const lon = drawPoints.reduce((s, p) => s + p.lon, 0) / drawPoints.length;
      return { lat, lon, name: "Drawn Polygon AOI" };
    }
    if (locationSource === "geojson" && parsedGeojson) {
      return { lat: 28.0, lon: 84.0, name: "Uploaded Boundary" };
    }
    return null;
  };

  const buildGeojson = (): Record<string, unknown> | null => {
    if (locationSource === "geojson") return parsedGeojson;
    if (locationSource !== "draw" || drawPoints.length < 3) return null;
    const ring = drawPoints.map((p) => [p.lon, p.lat] as [number, number]);
    const first = ring[0];
    const last = ring[ring.length - 1];
    if (first[0] !== last[0] || first[1] !== last[1]) ring.push([...first]);
    return {
      type: "Feature",
      properties: { name: "Drawn Polygon AOI" },
      geometry: { type: "Polygon", coordinates: [ring] },
    };
  };

  const canAnalyse = useMemo(() => {
    if (locationSource === "draw") return drawPoints.length >= 3;
    if (locationSource === "custom") return Boolean(customLat && customLon);
    if (locationSource === "geojson") return Boolean(parsedGeojson);
    return Boolean(selectedLocation);
  }, [locationSource, drawPoints.length, customLat, customLon, selectedLocation, parsedGeojson]);

  const handleAnalyse = async () => {
    const coords = getCoordinates();
    if (!coords && locationSource !== "geojson") {
      toast({ title: "Location required", description: "Select a location or draw at least 3 points.", variant: "destructive" });
      return;
    }

    setLoading(true);
    setDailyResult(null);
    setMapLayer("year2");
    const geojson = buildGeojson();
    const y1 = parseInt(baselineYear, 10);
    const y2 = parseInt(comparisonYear, 10);
    const body: AnalyzeRequest = {
      lat: geojson ? undefined : coords!.lat,
      lon: geojson ? undefined : coords!.lon,
      geojson: geojson ?? undefined,
      buf_km: geojson ? 0 : bufKm,
      year1: y1,
      year2: y2,
      start_month: parseInt(startMonth, 10),
      end_month: parseInt(endMonth, 10),
      start_day: parseInt(startDay, 10),
      end_day: parseInt(endDay, 10),
      forest_type: FOREST_TYPES[forestType] || "default",
      run_multiyear: runMultiyear,
      run_monthly: runMonthly,
      run_hotspot: runHotspot,
      ...(selectedProjectId ? { project_id: selectedProjectId } : {}),
    };

    if (dateMode === "exact") {
      body.baseline_date = baselineDate;
      body.comparison_date = comparisonDate;
      body.year1 = parseInt(baselineDate.slice(0, 4), 10);
      body.year2 = parseInt(comparisonDate.slice(0, 4), 10);
    }

    try {
      const data = await analyzeForest(body);
      const name = data.aoi_name ? String(data.aoi_name) : (coords?.name || "AOI");
      setAnalysisData(data);
      setRequestBody({
        ...body,
        lat: data.lat ?? coords?.lat,
        lon: data.lon ?? coords?.lon,
        buf_km: data.buf_km ?? body.buf_km,
        year1: data.year1 ?? body.year1,
        year2: data.year2 ?? body.year2,
      });
      setLocationName(name);
      if (selectedLocation && NEPAL_DISTRICTS[selectedLocation] && baselines[selectedLocation]) {
        setBenchDistrict(selectedLocation);
      }

      if (selectedProjectId && user) {
        try {
          const ce = data.carbon_estimate;
          await createBiomass.mutateAsync({
            project_id: selectedProjectId,
            carbon_density: ce ? ce.c_ha : 0,
            health_score: Math.min(1, Math.max(0, data.ndvi_year2 ?? 0)),
          });
          toast({ title: "Analysis saved", description: "Results stored to your project." });
        } catch { /* non-blocking */ }
      }

      if (runAiReport) {
        const reportBody: ReportRequest = {
          location: name,
          lat: data.lat ?? coords!.lat,
          lon: data.lon ?? coords!.lon,
          year1: data.year1 ?? body.year1,
          year2: data.year2 ?? body.year2,
          start_month: body.start_month,
          end_month: body.end_month,
          ndvi_year1: data.ndvi_year1,
          ndvi_year2: data.ndvi_year2,
          change_pct: data.change_pct,
          carbon_estimate: data.carbon_estimate,
          trend_data: data.trend_data,
          monthly_series: data.monthly_series,
          baseline_date: data.baseline_date ? String(data.baseline_date) : undefined,
          comparison_date: data.comparison_date ? String(data.comparison_date) : undefined,
          baseline_start: data.baseline_start,
          baseline_end: data.baseline_end,
          comparison_start: data.comparison_start,
          comparison_end: data.comparison_end,
          date_note: data.single_date_mode
            ? `${data.baseline_date ?? data.baseline_start} vs ${data.comparison_date ?? data.comparison_start}`
            : `${data.baseline_start} → ${data.baseline_end} vs ${data.comparison_start} → ${data.comparison_end}`,
        };
        setReportLoading(true);
        generateReport(reportBody)
          .then(setReportData)
          .catch((err) => {
            toast({
              title: "Report generation failed",
              description: err instanceof Error ? err.message : "Could not generate AI report.",
              variant: "destructive",
            });
          })
          .finally(() => setReportLoading(false));
      } else {
        setReportData(null);
      }
    } catch (err) {
      toast({
        title: "Analysis Failed",
        description: err instanceof Error ? err.message : "Could not reach analysis backend.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadPdf = async () => {
    if (!analysisData || !requestBody || !reportData) {
      toast({ title: "Report not ready", description: "Wait for the AI report before downloading PDF.", variant: "destructive" });
      return;
    }
    setPdfLoading(true);
    try {
      await downloadPdf({
        location: locationName,
        lat: requestBody.lat!,
        lon: requestBody.lon!,
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
        report_data: reportData,
        buf_km: requestBody.buf_km,
        area_ha: analysisData.area_ha,
      });
    } catch (err) {
      toast({
        title: "PDF export failed",
        description: err instanceof Error ? err.message : "Could not download PDF.",
        variant: "destructive",
      });
    } finally {
      setPdfLoading(false);
    }
  };

  const aoiPayload = () => {
    const coords = getCoordinates();
    const geojson = buildGeojson();
    return {
      lat: geojson ? undefined : coords?.lat,
      lon: geojson ? undefined : coords?.lon,
      geojson: geojson ?? undefined,
      buf_km: geojson ? 0 : bufKm,
    };
  };

  const handleLoadPassDates = async () => {
    setDailyLoading(true);
    try {
      const res = await fetchPassDates({
        ...aoiPayload(),
        year: parseInt(dailyYear, 10),
        month: parseInt(dailyMonth, 10),
      });
      setPassDates(res.dates);
      setSelectedPass(res.dates[0] || "");
      if (!res.dates.length) {
        toast({ title: "No scenes found", description: "No Sentinel-2 passes for that month/AOI (cloud filter < 80%).", variant: "destructive" });
      }
    } catch (err) {
      toast({ title: "Pass dates failed", description: err instanceof Error ? err.message : "Request failed", variant: "destructive" });
    } finally {
      setDailyLoading(false);
    }
  };

  const handleDailyNdvi = async () => {
    if (!selectedPass) return;
    setDailyLoading(true);
    try {
      const res = await fetchDailyNdvi({ ...aoiPayload(), date: selectedPass });
      setDailyResult(res);
      setMapLayer("daily");
    } catch (err) {
      toast({ title: "Daily NDVI failed", description: err instanceof Error ? err.message : "Request failed", variant: "destructive" });
    } finally {
      setDailyLoading(false);
    }
  };

  const handleVisionInference = async () => {
    const coords = getCoordinates();
    if (!coords) return;
    setVisionLoading(true);
    try {
      const result = await inferVision({
        lat: d?.lat ?? coords.lat,
        lon: d?.lon ?? coords.lon,
        buf_km: (d?.buf_km && Number(d.buf_km) > 0) ? Number(d.buf_km) : (bufKm > 0 ? bufKm : 5),
        geojson: selectedGeojson ?? (d as any)?.geojson ?? undefined,
        baseline_date: d?.baseline_date ?? baselineDate,
        comparison_date: d?.comparison_date ?? comparisonDate,
      });
      setVisionResult(result);
      toast({ title: "Vision inference complete", description: "Live Sentinel-2 thumbnails were evaluated by the prototype models." });
    } catch (err) {
      toast({ title: "Vision inference failed", description: err instanceof Error ? err.message : "Could not run vision models.", variant: "destructive" });
    } finally {
      setVisionLoading(false);
    }
  };

  const d = analysisData;
  const changePct = d?.change_pct ?? 0;
  const isPositive = changePct > 0;
  const ce = d?.carbon_estimate;
  const coords = getCoordinates();
  const mapCenter = d?.lat != null && d?.lon != null
    ? { lat: Number(d.lat), lon: Number(d.lon) }
    : coords && coords.lat !== 28.0
      ? coords
      : d?.lat != null
        ? { lat: Number(d.lat), lon: Number(d.lon) }
        : coords;
  const status = d ? statusFromChange(changePct) : null;

  const activeTile =
    mapLayer === "year1" ? d?.tile_url_year1 :
    mapLayer === "year2" ? (d?.tile_url_year2 || d?.tile_url) :
    mapLayer === "hotspot" ? d?.tile_url_hotspot :
    dailyResult?.tile_url;

  const locationOptions = useMemo(() => {
    const keys = locationSource === "district" ? Object.keys(NEPAL_DISTRICTS) : Object.keys(COMMUNITY_FORESTS);
    const q = locationFilter.trim().toLowerCase();
    return q ? keys.filter((k) => k.toLowerCase().includes(q)) : keys;
  }, [locationSource, locationFilter]);

  const years = Array.from({ length: new Date().getFullYear() - 2018 }, (_, i) => 2019 + i);
  const startDayOptions = Array.from({ length: daysInMonth(parseInt(baselineYear, 10), parseInt(startMonth, 10)) }, (_, i) => i + 1);
  const endDayOptions = Array.from({ length: daysInMonth(parseInt(baselineYear, 10), parseInt(endMonth, 10)) }, (_, i) => i + 1);

  const bench = baselines[benchDistrict];
  const forestNdvi = d?.ndvi_year2 ?? null;
  const benchDiff = forestNdvi != null && bench ? forestNdvi - bench.ndvi : null;

  const yoyRows = useMemo(() => {
    if (!d?.trend_data || d.trend_data.length < 2) return [];
    return d.trend_data.map((row, i) => {
      if (i === 0) return { ...row, yoy: null as number | null };
      const prev = d.trend_data[i - 1].ndvi;
      const yoy = prev ? ((row.ndvi - prev) / prev) * 100 : null;
      return { ...row, yoy };
    });
  }, [d?.trend_data]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-serif text-2xl text-foreground">Forest Health Dashboard</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Live Sentinel-2 NDVI, carbon stocks, dual-year maps, and due-diligence reports
        </p>
      </div>

      <Collapsible defaultOpen>
        <Card className="p-4 border-accent/25 bg-accent/[0.03]">
          <CollapsibleTrigger className="flex w-full items-center justify-between text-left">
            <div>
              <div className="font-medium">How to use TerrAI</div>
              <div className="text-xs text-muted-foreground mt-1">A quick guide from selecting a forest to interpreting the results.</div>
            </div>
            <ChevronDown className="w-4 h-4 shrink-0" />
          </CollapsibleTrigger>
          <CollapsibleContent className="pt-4">
            <ol className="grid md:grid-cols-2 lg:grid-cols-5 gap-3 text-sm">
              {[
                ["1. Choose an area", "Select a Nepal district/community forest, enter coordinates, draw a polygon, or paste GeoJSON."],
                ["2. Choose dates", "Use Exact dates for a clean two-scene comparison, or Season window to reduce cloud and seasonal noise."],
                ["3. Run analysis", "Analyse Forest calculates NDVI, EVI, SAR/RVI, change, area, biomass, and CO₂e using the auditable science path."],
                ["4. Read the map", "Switch between baseline, comparison, hotspot, and daily-pass layers. Red hotspot areas indicate vegetation decline."],
                ["5. Review evidence", "Use the report, charts, PDF, and prototype vision outputs. Confirm uncertain or high-risk areas in the field."],
              ].map(([title, description]) => (
                <li key={title} className="rounded-lg border border-border/70 bg-background/70 p-3">
                  <div className="font-medium">{title}</div>
                  <p className="text-xs text-muted-foreground leading-relaxed mt-1">{description}</p>
                </li>
              ))}
            </ol>
            <p className="text-xs text-muted-foreground mt-3">
              The trained U-Net, Siamese, and Vision Transformer are public-data prototypes. Their masks, Grad-CAM, and uncertainty views support screening; they do not replace field verification or the carbon science calculation.
            </p>
          </CollapsibleContent>
        </Card>
      </Collapsible>

      <Card className="p-6 shadow-card space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
          <div className="space-y-1.5">
            <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Location Source</Label>
            <Select
              value={locationSource}
              onValueChange={(v) => {
                setLocationSource(v as LocationSource);
                setSelectedLocation("");
                if (v !== "draw") setDrawPoints([]);
              }}
            >
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="district">Nepal District</SelectItem>
                <SelectItem value="community">Community Forest</SelectItem>
                <SelectItem value="custom">Custom Coordinates</SelectItem>
                <SelectItem value="draw">Draw Area on Map</SelectItem>
                <SelectItem value="geojson">Upload GeoJSON</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {(locationSource === "district" || locationSource === "community") && (
            <div className="space-y-1.5 md:col-span-2">
              <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Search / Select
              </Label>
              <div className="flex gap-2">
                <Input
                  value={locationFilter}
                  onChange={(e) => setLocationFilter(e.target.value)}
                  placeholder="Filter locations…"
                  className="max-w-[10rem]"
                />
                <Select value={selectedLocation} onValueChange={setSelectedLocation}>
                  <SelectTrigger className="flex-1"><SelectValue placeholder="Select…" /></SelectTrigger>
                  <SelectContent className="max-h-64">
                    {locationOptions.map((name) => (
                      <SelectItem key={name} value={name}>{name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          )}

          {locationSource === "custom" && (
            <>
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Latitude</Label>
                <Input value={customLat} onChange={(e) => setCustomLat(e.target.value)} placeholder="e.g. 27.7172" />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Longitude</Label>
                <Input value={customLon} onChange={(e) => setCustomLon(e.target.value)} placeholder="e.g. 85.3240" />
              </div>
            </>
          )}

          {locationSource === "draw" && (
            <div className="md:col-span-2 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
              <Pentagon className="w-4 h-4 text-accent" />
              Click map to add points ({drawPoints.length}). Need ≥ 3.
              <Button type="button" variant="outline" size="sm" onClick={() => setDrawPoints([])} disabled={!drawPoints.length}>
                <Eraser className="w-3.5 h-3.5 mr-1" /> Clear
              </Button>
              {drawPoints.length > 0 && (
                <Button type="button" variant="outline" size="sm" onClick={() => setDrawPoints((p) => p.slice(0, -1))}>Undo</Button>
              )}
            </div>
          )}

          {locationSource === "geojson" && (
            <div className="md:col-span-2 space-y-1.5">
              <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1">
                <Upload className="w-3.5 h-3.5" /> GeoJSON
              </Label>
              <textarea
                className="w-full min-h-[88px] rounded-md border border-input bg-background px-3 py-2 text-xs font-mono"
                placeholder='Paste Feature / FeatureCollection / Polygon JSON…'
                value={geojsonText}
                onChange={(e) => setGeojsonText(e.target.value)}
              />
              {geojsonText && !parsedGeojson && (
                <p className="text-xs text-destructive">Invalid JSON</p>
              )}
            </div>
          )}
        </div>

        {locationSource !== "draw" && locationSource !== "geojson" && (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Analysis Radius</Label>
              <span className="text-sm font-medium">{bufKm} km</span>
            </div>
            <Slider value={[bufKm]} min={1} max={20} step={0.5} onValueChange={(v) => setBufKm(v[0] ?? 5)} />
          </div>
        )}

        <div className="flex flex-wrap gap-2">
          <Button type="button" size="sm" variant={dateMode === "season" ? "default" : "outline"} onClick={() => setDateMode("season")}>
            Season window
          </Button>
          <Button type="button" size="sm" variant={dateMode === "exact" ? "default" : "outline"} onClick={() => setDateMode("exact")}>
            Exact dates (1 + 1)
          </Button>
        </div>

        {dateMode === "season" ? (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 items-end">
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Baseline Year</Label>
              <Select value={baselineYear} onValueChange={setBaselineYear}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>{years.map((y) => <SelectItem key={y} value={String(y)}>{y}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Comparison Year</Label>
              <Select value={comparisonYear} onValueChange={setComparisonYear}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>{years.map((y) => <SelectItem key={y} value={String(y)}>{y}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Start Month</Label>
              <Select value={startMonth} onValueChange={setStartMonth}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>{MONTHS.map((m) => <SelectItem key={m.v} value={String(m.v)}>{m.l}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Start Day</Label>
              <Select value={startDay} onValueChange={setStartDay}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>{startDayOptions.map((d) => <SelectItem key={d} value={String(d)}>{d}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">End Month</Label>
              <Select value={endMonth} onValueChange={setEndMonth}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>{MONTHS.map((m) => <SelectItem key={m.v} value={String(m.v)}>{m.l}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">End Day</Label>
              <Select value={endDay} onValueChange={setEndDay}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>{endDayOptions.map((d) => <SelectItem key={d} value={String(d)}>{d}</SelectItem>)}</SelectContent>
              </Select>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Baseline date</Label>
              <Input type="date" value={baselineDate} onChange={(e) => setBaselineDate(e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Comparison date</Label>
              <Input type="date" value={comparisonDate} onChange={(e) => setComparisonDate(e.target.value)} />
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-end">
          <div className="space-y-1.5">
            <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Forest Type</Label>
            <Select value={forestType} onValueChange={setForestType}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {Object.keys(FOREST_TYPES).map((f) => <SelectItem key={f} value={f}>{f}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          {projects && projects.length > 0 && (
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Save to Project</Label>
              <Select value={selectedProjectId} onValueChange={setSelectedProjectId}>
                <SelectTrigger><SelectValue placeholder="Optional project…" /></SelectTrigger>
                <SelectContent>
                  {projects.map((p) => <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          )}
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3 pt-1">
          {[
            { id: "monthly", label: "Monthly NDVI series", checked: runMonthly, set: setRunMonthly },
            { id: "multi", label: "Multi-year trend (slower)", checked: runMultiyear, set: setRunMultiyear },
            { id: "hot", label: "Change hotspot map", checked: runHotspot, set: setRunHotspot },
            { id: "ai", label: "AI due-diligence report", checked: runAiReport, set: setRunAiReport },
          ].map((opt) => (
            <label key={opt.id} className="flex items-center justify-between gap-2 rounded-md border border-border px-3 py-2 text-sm">
              <span>{opt.label}</span>
              <Switch checked={opt.checked} onCheckedChange={opt.set} />
            </label>
          ))}
        </div>

        <div className="flex flex-wrap justify-end gap-2">
          {reportData && (
            <Button variant="outline" onClick={handleDownloadPdf} disabled={pdfLoading}>
              {pdfLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
              Download PDF
            </Button>
          )}
          <Button onClick={handleAnalyse} disabled={loading || !canAnalyse} className="bg-primary text-primary-foreground hover:bg-primary/90 px-8">
            {loading ? (
              <span className="flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin" /> Queued / analysing Sentinel-2…
              </span>
            ) : (
              <span className="flex items-center gap-2"><Leaf className="w-4 h-4" /> Analyse Forest</span>
            )}
          </Button>
        </div>
      </Card>

      {/* Map layer toggles */}
      <div className="space-y-3">
        <div className="flex flex-wrap gap-2 items-center">
          <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mr-1">Map layer</span>
          <Button type="button" size="sm" variant={mapLayer === "year1" ? "default" : "outline"} disabled={!d?.tile_url_year1} onClick={() => setMapLayer("year1")}>
            Baseline {d?.year1 ?? baselineYear}
          </Button>
          <Button type="button" size="sm" variant={mapLayer === "year2" ? "default" : "outline"} disabled={!d?.tile_url_year2 && !d?.tile_url} onClick={() => setMapLayer("year2")}>
            Comparison {d?.year2 ?? comparisonYear}
          </Button>
          <Button type="button" size="sm" variant={mapLayer === "hotspot" ? "default" : "outline"} disabled={!d?.tile_url_hotspot} onClick={() => setMapLayer("hotspot")}>
            Change Hotspot
          </Button>
          <Button type="button" size="sm" variant={mapLayer === "daily" ? "default" : "outline"} disabled={!dailyResult?.tile_url} onClick={() => setMapLayer("daily")}>
            Daily Pass
          </Button>
        </div>
        <NepalMap
          height="h-[28rem]"
          center={mapCenter && Number.isFinite(mapCenter.lat) ? mapCenter : null}
          radiusKm={bufKm}
          showCircle={locationSource !== "draw" && locationSource !== "geojson" && Boolean(mapCenter)}
          drawMode={locationSource === "draw"}
          drawPoints={drawPoints}
          onAddDrawPoint={(p) => setDrawPoints((prev) => [...prev, p])}
          tileUrl={activeTile ? String(activeTile) : null}
          markers={mapCenter && Number.isFinite(mapCenter.lat) ? [{ lat: mapCenter.lat, lon: mapCenter.lon, label: coords?.name || locationName || "AOI" }] : []}
          fitNepal={!mapCenter}
        />
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          <span>NDVI</span>
          <div className="h-2 flex-1 max-w-xs rounded-full" style={{ background: "linear-gradient(90deg,#d73027,#fc8d59,#fee08b,#d9ef8b,#91cf60,#1a9850)" }} />
          <span>0 → 0.8</span>
          {mapLayer === "hotspot" && <span className="ml-2">Hotspot: red = decline, green = gain</span>}
        </div>
      </div>

      {loading ? (
        <div className="space-y-6">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Card key={i} className="p-5 space-y-3"><Skeleton className="h-3 w-20" /><Skeleton className="h-8 w-24" /></Card>
            ))}
          </div>
        </div>
      ) : !d ? (
        <div className="text-center py-12">
          <TreePine className="w-16 h-16 mx-auto text-muted-foreground/20 mb-4" />
          <p className="text-muted-foreground">Select or draw an area, then <strong>Analyse Forest</strong>.</p>
          <p className="text-xs text-muted-foreground mt-2 max-w-lg mx-auto">
            Tip: leave Multi-year off for a faster first run (~few Sentinel composites). Enable it when you need the 2019→now trend.
          </p>
        </div>
      ) : (
        <div className="space-y-6 animate-fade-in-up">
          <Card className="p-4 border-primary/20 bg-primary/[0.03] flex items-center justify-between gap-3 flex-wrap">
            <div>
              <div className="font-medium">Run live vision inference</div>
              <div className="text-xs text-muted-foreground">Uses Sentinel-2 thumbnails from GEE with the trained public-data prototype checkpoints.</div>
            </div>
            <Button variant="outline" onClick={handleVisionInference} disabled={visionLoading}>
              {visionLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <BrainCircuit className="w-4 h-4" />}
              {visionLoading ? "Running models…" : "Run vision models"}
            </Button>
          </Card>

          {visionResult && (
            <Card className="p-5 space-y-4">
              <div className="flex items-center justify-between gap-3 flex-wrap">
                <div>
                  <h3 className="font-serif text-lg">Live model outputs</h3>
                  <p className="text-xs text-muted-foreground">{visionResult.model_input} · {visionResult.dates.baseline} → {visionResult.dates.comparison}</p>
                </div>
                <Badge variant="outline">{visionResult.prediction.class} · {(visionResult.prediction.confidence * 100).toFixed(1)}%</Badge>
              </div>
              <div className="grid md:grid-cols-3 gap-3">
                {[
                  {
                    label: "U-Net mask",
                    image: visionResult.segmentation.mask,
                    uncertainty: visionResult.segmentation.uncertainty,
                    explanation: "Pixels highlighted here are the areas the U-Net prototype classifies as positive vegetation or canopy evidence. It is a screening mask, not a verified forest boundary.",
                  },
                  {
                    label: "Siamese change mask",
                    image: visionResult.change_detection.mask,
                    uncertainty: visionResult.change_detection.uncertainty,
                    explanation: "This compares the baseline and comparison images and highlights pixels that the Siamese prototype considers changed. Seasonal effects and image conditions can create false positives.",
                  },
                  {
                    label: "Vision Transformer Grad-CAM",
                    image: visionResult.vision_transformer.grad_cam,
                    uncertainty: null,
                    explanation: "This heatmap shows the image regions that influenced the Vision Transformer land-cover prediction. It explains attention; it is not a segmentation or damage map.",
                  },
                ].map(({ label, image, uncertainty, explanation }) => (
                  <div key={label} className="space-y-2">
                    <div className="flex items-center justify-between gap-2">
                      <div className="text-sm font-medium">{label}</div>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <button
                            type="button"
                            aria-label={`Explain ${label}`}
                            className="inline-flex h-5 w-5 items-center justify-center rounded-full border border-accent/30 text-[11px] font-bold text-accent-foreground/80 hover:bg-accent hover:text-accent-foreground focus:outline-none focus:ring-2 focus:ring-accent/50"
                          >
                            i
                          </button>
                        </TooltipTrigger>
                        <TooltipContent side="top" className="max-w-xs text-xs leading-relaxed">
                          {explanation}
                        </TooltipContent>
                      </Tooltip>
                    </div>
                    <img src={image} alt={`${label} output`} className="w-full aspect-square rounded-md border object-cover" />
                    {uncertainty && (
                      <div className="space-y-2">
                        <div className="flex items-center justify-between gap-2">
                          <div className="text-xs text-muted-foreground">Uncertainty map</div>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <button
                                type="button"
                                aria-label={`Explain ${label} uncertainty`}
                                className="inline-flex h-4 w-4 items-center justify-center rounded-full border border-accent/30 text-[9px] font-bold text-accent-foreground/80 hover:bg-accent hover:text-accent-foreground focus:outline-none focus:ring-2 focus:ring-accent/50"
                              >
                                i
                              </button>
                            </TooltipTrigger>
                            <TooltipContent side="top" className="max-w-xs text-xs leading-relaxed">
                              Brighter areas indicate lower confidence in this prototype output. Treat them as places that need closer imagery review or field verification.
                            </TooltipContent>
                          </Tooltip>
                        </div>
                        <img src={uncertainty} alt={`${label} uncertainty`} className="w-full aspect-square rounded-md border object-cover" />
                      </div>
                    )}
                  </div>
                ))}
              </div>
              <p className="text-xs text-muted-foreground">{visionResult.limitations.join(" ")}</p>
            </Card>
          )}

          {reportLoading && (
            <Card className="p-4 border-accent/30 bg-accent/5 flex items-center gap-3">
              <Loader2 className="w-4 h-4 animate-spin text-accent" />
              <span className="text-sm text-muted-foreground">AI report generating (openai/gpt-oss-120b)…</span>
            </Card>
          )}

          {status && (
            <Card className={`p-4 border ${
              status.tone === "destructive" ? "border-destructive/40 bg-destructive/5" :
              status.tone === "warn" ? "border-amber-500/40 bg-amber-500/5" :
              status.tone === "good" ? "border-accent/40 bg-accent/5" : "border-border"
            }`}>
              <div className="flex items-start gap-3">
                {status.tone === "good" ? <CheckCircle2 className="w-5 h-5 text-accent mt-0.5" /> : <AlertTriangle className="w-5 h-5 text-amber-600 mt-0.5" />}
                <div>
                  <div className="font-medium">{status.label}</div>
                  <div className="text-sm text-muted-foreground">{status.detail}</div>
                  <div className="text-xs text-muted-foreground mt-1">
                    {d.single_date_mode
                      ? `Dates: ${d.baseline_date ?? d.baseline_start} vs ${d.comparison_date ?? d.comparison_start}`
                      : `Windows: ${d.baseline_start} → ${d.baseline_end} vs ${d.comparison_start} → ${d.comparison_end}`}
                  </div>
                </div>
              </div>
            </Card>
          )}

          {d.vision_explanation && (
            <Card className="p-5 shadow-card border-primary/20 bg-primary/[0.03] space-y-5">
              <div className="flex items-start justify-between gap-3 flex-wrap">
                <div>
                  <h3 className="font-serif text-lg flex items-center gap-2">
                    <BrainCircuit className="w-5 h-5 text-primary" />
                    Explainable vision pipeline
                  </h3>
                  <p className="text-sm text-muted-foreground mt-1">
                    {d.vision_explanation.pipeline_name} — every stage is labelled below.
                  </p>
                </div>
                <Badge variant="outline" className="border-amber-500/40 text-amber-700 dark:text-amber-300">
                  {d.vision_explanation.inference_label}
                </Badge>
              </div>

              <div className="grid md:grid-cols-2 xl:grid-cols-4 gap-3">
                {d.vision_explanation.models.map((model) => (
                  <div
                    key={model.id}
                    id={model.id === "siamese-change" ? "siamese" : model.id === "vision-transformer" ? "vision-transformer" : model.id === "unet-segmentation" ? "unet" : undefined}
                    className="rounded-lg border border-border/70 bg-background/70 p-3 space-y-2 scroll-mt-6"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-medium text-sm">{model.name}</span>
                      <Badge variant="secondary" className="text-[10px]">{model.status}</Badge>
                    </div>
                    <p className="text-xs text-muted-foreground">{model.role}</p>
                    <p className="text-xs leading-relaxed">{model.explanation}</p>
                    {model.validation && (
                      <p className="text-[11px] font-mono text-primary">
                        Validation: {model.validation.accuracy != null
                          ? `${(model.validation.accuracy * 100).toFixed(1)}% accuracy`
                          : `${((model.validation.iou ?? 0) * 100).toFixed(1)}% IoU`}
                      </p>
                    )}
                    <div className="text-[11px] text-muted-foreground">
                      <span className="font-semibold">Inputs: </span>{model.inputs}
                    </div>
                  </div>
                ))}
              </div>

              <div className="grid md:grid-cols-3 gap-4">
                <div className="rounded-lg border border-border/60 p-3">
                  <div className="flex items-center gap-2 text-sm font-medium">
                    <Eye className="w-4 h-4 text-primary" /> Current evidence
                  </div>
                  <p className="text-sm mt-2">{d.vision_explanation.prediction}</p>
                  <p className="text-xs text-muted-foreground mt-1">{d.vision_explanation.evidence}</p>
                </div>
                <div className="rounded-lg border border-border/60 p-3">
                  <div className="flex items-center gap-2 text-sm font-medium">
                    <ShieldCheck className="w-4 h-4 text-primary" /> Confidence screen
                  </div>
                  <p className="text-2xl font-semibold mt-1">{Math.round(d.vision_explanation.confidence * 100)}%</p>
                  <p className="text-xs text-muted-foreground">Evidence quality, not a trained CNN probability.</p>
                </div>
                <div className="rounded-lg border border-border/60 p-3">
                  <div className="text-sm font-medium">Influential evidence areas</div>
                  <ul className="mt-2 space-y-1 text-xs text-muted-foreground">
                    {d.vision_explanation.attention_regions.map((region) => <li key={region}>• {region}</li>)}
                  </ul>
                </div>
              </div>

              <div>
                <div className="text-sm font-medium mb-2">Feature evidence used for this screen</div>
                <div className="grid sm:grid-cols-3 gap-2">
                  {d.vision_explanation.feature_evidence.map((feature) => (
                    <div key={feature.feature} className="rounded-md bg-muted/40 px-3 py-2 text-xs">
                      <div className="font-semibold">
                        <TermInfo term={feature.feature}>{feature.feature}</TermInfo>
                      </div>
                      <div className="text-muted-foreground">{feature.label}: {feature.delta > 0 ? "+" : ""}{feature.delta}</div>
                      <div className="mt-1 h-1.5 rounded-full bg-muted overflow-hidden">
                        <div className="h-full rounded-full bg-primary" style={{ width: `${Math.round(feature.weight * 100)}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-md border border-dashed border-border p-3 text-xs text-muted-foreground">
                <span className="font-semibold text-foreground">How to read this: </span>
                the hotspot map is the current visual explanation. <TermInfo term="Grad-CAM">Grad-CAM</TermInfo> and a learned uncertainty map will appear when labelled Nepal imagery and validated model weights are configured. Carbon remains calculated by the auditable regional science path.
              </div>
            </Card>
          )}

          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { label: `NDVI ${d.year1 ?? baselineYear}`, value: d.ndvi_year1?.toFixed(4) ?? "—", icon: Activity },
              { label: `NDVI ${d.year2 ?? comparisonYear}`, value: d.ndvi_year2?.toFixed(4) ?? "—", icon: Layers },
              { label: "Change", value: `${isPositive ? "+" : ""}${changePct.toFixed(1)}%`, icon: isPositive ? TrendingUp : TrendingDown, color: isPositive ? "text-accent" : "text-destructive" },
              { label: "Total Area", value: `${d.area_ha ?? "—"} ha`, icon: MapPin },
            ].map((m) => (
              <Card key={m.label} className="p-5 shadow-card">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">{m.label}</span>
                  <m.icon className="w-4 h-4 text-muted-foreground" />
                </div>
                <div className={`font-serif text-2xl ${m.color ?? "text-foreground"}`}>{m.value}</div>
              </Card>
            ))}
          </div>

          {ce && (
            <Card className="bg-primary p-6 shadow-card border-0">
              <h3 className="font-serif text-lg text-primary-foreground/80 mb-1 flex items-center gap-2">
                <Leaf className="w-5 h-5" /> Carbon Stock Estimate
              </h3>
              {(ce.eco_zone_name || ce.agb_capped) && (
                <p className="text-xs text-primary-foreground/55 mb-4">
                  {ce.eco_zone_name && (
                    <>
                      Zone {ce.eco_zone_shorthand ?? ""} · {ce.eco_zone_name}
                      {ce.regional_label ? ` · ${ce.regional_label}` : ""}
                      {ce.zone_district ? ` (${ce.zone_district})` : ""}
                      {ce.max_agb_t_ha != null ? ` · AGB ceiling ${ce.max_agb_t_ha} t/ha` : ""}
                      {ce.scale_mode ? ` · ${ce.scale_mode} scale` : ""}
                    </>
                  )}
                  {ce.agb_capped ? " · FRTC/ICIMOD saturation cap applied" : ""}
                  {ce.calibration_applied ? ` · field calib ×${ce.calibration_coefficient}` : ""}
                </p>
              )}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {[
                  { label: "AGB", val: `${ce.agb_ha?.toFixed(1) ?? "—"}`, unit: "t/ha" },
                  { label: "Total Carbon", val: (ce.total_c ?? 0).toLocaleString(), unit: "t C" },
                  { label: "Total CO₂e", val: (ce.total_co2 ?? 0).toLocaleString(), unit: "t CO₂e" },
                  { label: "CO₂e Change", val: ce.co2_delta != null ? `${ce.co2_delta >= 0 ? "+" : ""}${ce.co2_delta.toLocaleString()}` : "—", unit: "t CO₂e" },
                ].map((c) => (
                  <div key={c.label} className="bg-primary-foreground/10 rounded-lg p-4 text-center">
                    <div className="text-[10px] uppercase tracking-widest text-primary-foreground/50 mb-1 font-semibold">{c.label}</div>
                    <div className="font-serif text-2xl text-primary-foreground">{c.val}</div>
                    <div className="text-xs text-primary-foreground/40 mt-0.5">{c.unit}</div>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* District benchmark */}
          {forestNdvi != null && Object.keys(baselines).length > 0 && (
            <Card className="p-5 shadow-card space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h3 className="font-serif text-base">District Benchmark</h3>
                <Select value={benchDistrict} onValueChange={setBenchDistrict}>
                  <SelectTrigger className="w-56"><SelectValue /></SelectTrigger>
                  <SelectContent className="max-h-64">
                    {Object.keys(baselines).map((k) => <SelectItem key={k} value={k}>{k}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              {bench && (
                <div className="grid sm:grid-cols-3 gap-4 text-sm">
                  <div>
                    <div className="text-muted-foreground text-xs uppercase tracking-wider">Your forest NDVI</div>
                    <div className="font-serif text-xl">{forestNdvi.toFixed(4)}</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground text-xs uppercase tracking-wider">{benchDistrict} avg</div>
                    <div className="font-serif text-xl">{bench.ndvi.toFixed(2)}</div>
                    <div className="text-xs text-muted-foreground">Forest cover ~{bench.forest_cover_pct}%</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground text-xs uppercase tracking-wider">Difference</div>
                    <div className={`font-serif text-xl ${(benchDiff ?? 0) >= 0 ? "text-accent" : "text-destructive"}`}>
                      {benchDiff != null ? `${benchDiff >= 0 ? "+" : ""}${benchDiff.toFixed(3)}` : "—"}
                    </div>
                  </div>
                </div>
              )}
            </Card>
          )}

          {(d.trend_data?.length > 0 || d.monthly_series?.length > 0) && (
            <div className="grid lg:grid-cols-2 gap-6">
              {d.trend_data?.length > 0 && (
                <Card className="p-5 shadow-card">
                  <h3 className="font-serif text-base mb-1">Multi-Year NDVI Trend</h3>
                  {d.trend_direction && (
                    <p className="text-xs text-muted-foreground mb-3">
                      Trend: {String(d.trend_direction)}
                      {typeof d.trend_slope === "number" ? ` (slope ${d.trend_slope.toFixed(4)}/yr)` : ""}
                    </p>
                  )}
                  <ResponsiveContainer width="100%" height={240}>
                    <AreaChart data={d.trend_data}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(140,25%,88%)" />
                      <XAxis dataKey="year" tick={{ fontSize: 12 }} />
                      <YAxis domain={[0, 1]} tick={{ fontSize: 12 }} />
                      <RechartsTooltip />
                      <Area type="monotone" dataKey="ndvi" stroke="hsl(153,40%,42%)" strokeWidth={2.5} fill="hsl(153,40%,42%,0.15)" />
                    </AreaChart>
                  </ResponsiveContainer>
                </Card>
              )}
              {d.monthly_series?.length > 0 && (
                <Card className="p-5 shadow-card">
                  <h3 className="font-serif text-base mb-4">Monthly NDVI ({d.year2 ?? comparisonYear})</h3>
                  <ResponsiveContainer width="100%" height={240}>
                    <BarChart data={d.monthly_series}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(140,25%,88%)" />
                      <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                      <YAxis domain={[0, 1]} tick={{ fontSize: 12 }} />
                      <RechartsTooltip />
                      <Bar dataKey="ndvi" radius={[4, 4, 0, 0]}>
                        {d.monthly_series.map((entry, i) => (
                          <Cell key={i} fill={entry.ndvi > 0.65 ? "hsl(153,40%,42%)" : entry.ndvi > 0.55 ? "hsl(153,30%,55%)" : "hsl(45,50%,55%)"} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </Card>
              )}
            </div>
          )}

          {yoyRows.length > 1 && (
            <Collapsible>
              <Card className="p-4 shadow-card">
                <CollapsibleTrigger className="flex w-full items-center justify-between text-sm font-medium">
                  Raw annual NDVI record
                  <ChevronDown className="w-4 h-4" />
                </CollapsibleTrigger>
                <CollapsibleContent className="pt-3 overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-left text-muted-foreground border-b">
                        <th className="py-2 pr-4">Year</th>
                        <th className="py-2 pr-4">NDVI</th>
                        <th className="py-2">YoY %</th>
                      </tr>
                    </thead>
                    <tbody>
                      {yoyRows.map((r) => (
                        <tr key={r.year} className="border-b border-border/50">
                          <td className="py-2 pr-4">{r.year}</td>
                          <td className="py-2 pr-4">{r.ndvi}</td>
                          <td className="py-2">{r.yoy == null ? "—" : `${r.yoy >= 0 ? "+" : ""}${r.yoy.toFixed(1)}%`}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </CollapsibleContent>
              </Card>
            </Collapsible>
          )}

          {/* Daily NDVI Explorer */}
          <Card className="p-5 shadow-card space-y-4">
            <div className="flex items-center justify-between gap-2 flex-wrap">
              <h3 className="font-serif text-base flex items-center gap-2">
                <Satellite className="w-4 h-4" /> Daily NDVI Explorer
              </h3>
              <Badge variant="outline">~5-day Sentinel-2 revisit</Badge>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 items-end">
              <div className="space-y-1.5">
                <Label className="text-xs uppercase tracking-wider text-muted-foreground">Year</Label>
                <Select value={dailyYear} onValueChange={setDailyYear}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>{years.map((y) => <SelectItem key={y} value={String(y)}>{y}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs uppercase tracking-wider text-muted-foreground">Month</Label>
                <Select value={dailyMonth} onValueChange={setDailyMonth}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>{MONTHS.map((m) => <SelectItem key={m.v} value={String(m.v)}>{m.l}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <Button variant="outline" onClick={handleLoadPassDates} disabled={dailyLoading || !canAnalyse}>
                {dailyLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                Load pass dates
              </Button>
              <div className="space-y-1.5">
                <Label className="text-xs uppercase tracking-wider text-muted-foreground">Acquisition date</Label>
                <Select value={selectedPass} onValueChange={setSelectedPass} disabled={!passDates.length}>
                  <SelectTrigger><SelectValue placeholder="Select date…" /></SelectTrigger>
                  <SelectContent>
                    {passDates.map((dt) => <SelectItem key={dt} value={dt}>{dt}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <Button onClick={handleDailyNdvi} disabled={!selectedPass || dailyLoading}>
              Compute NDVI for this date
            </Button>
            {dailyResult && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                <div><div className="text-xs text-muted-foreground">Date</div><div className="font-medium">{dailyResult.date}</div></div>
                <div><div className="text-xs text-muted-foreground">NDVI</div><div className="font-medium">{dailyResult.ndvi?.toFixed(4) ?? "—"}</div></div>
                <div><div className="text-xs text-muted-foreground">Cloud %</div><div className="font-medium">{dailyResult.cloud_pct ?? "—"}</div></div>
                <div><div className="text-xs text-muted-foreground">Vegetation</div><div className="font-medium">{dailyResult.quality}</div></div>
              </div>
            )}
          </Card>

          {reportData && (
            <Card className="p-6 shadow-card space-y-4">
              <div className="flex items-center justify-between gap-3 flex-wrap">
                <h3 className="font-serif text-lg flex items-center gap-2">
                  <FileText className="w-5 h-5" /> Forest Health Due Diligence Report
                </h3>
                <Badge variant="outline">{reportData.risk_level} risk</Badge>
              </div>
              <p className="text-sm text-muted-foreground leading-relaxed">{reportData.executive_summary}</p>
              <div className="grid md:grid-cols-2 gap-4 text-sm">
                <div>
                  <div className="font-medium mb-1">Vegetation Health Analysis</div>
                  <p className="text-muted-foreground">{reportData.vegetation_analysis}</p>
                </div>
                <div>
                  <div className="font-medium mb-1">Carbon Stock Implications</div>
                  <p className="text-muted-foreground">{reportData.carbon_implications}</p>
                </div>
                <div>
                  <div className="font-medium mb-1">Risk Assessment</div>
                  <p className="text-muted-foreground">{reportData.risk_assessment}</p>
                </div>
                <div>
                  <div className="font-medium mb-1">Next Monitoring</div>
                  <p className="text-muted-foreground">{reportData.next_monitoring}</p>
                </div>
              </div>
              {reportData.key_findings?.length > 0 && (
                <div>
                  <div className="font-medium mb-2">Key Findings</div>
                  <ul className="list-disc pl-5 space-y-1 text-sm text-muted-foreground">
                    {reportData.key_findings.map((f) => <li key={f}>{f}</li>)}
                  </ul>
                </div>
              )}
              {reportData.recommendations?.length > 0 && (
                <div>
                  <div className="font-medium mb-2">Recommendations</div>
                  <ol className="list-decimal pl-5 space-y-1 text-sm text-muted-foreground">
                    {reportData.recommendations.map((r) => <li key={r}>{r}</li>)}
                  </ol>
                </div>
              )}
            </Card>
          )}

          <Collapsible>
            <Card className="p-4 shadow-card">
              <CollapsibleTrigger className="flex w-full items-center justify-between text-sm font-medium">
                About NDVI & Carbon Methodology
                <ChevronDown className="w-4 h-4" />
              </CollapsibleTrigger>
              <CollapsibleContent className="pt-3 text-sm text-muted-foreground space-y-2">
                <p><TermInfo term="NDVI">NDVI</TermInfo> = (NIR − Red) / (NIR + Red) from <TermInfo term="Sentinel-2">Sentinel-2</TermInfo> bands B8 and B4, cloud-masked with <TermInfo term="QA60">QA60</TermInfo>.</p>
                <p>Carbon uses FAO/ICIMOD Nepal <TermInfo term="AGB">AGB</TermInfo> baselines scaled by NDVI/0.75, root:shoot ratios, carbon fraction, and CO₂ factor 3.667.</p>
                <p><TermInfo term="U-Net">U-Net</TermInfo>, <TermInfo term="Siamese">Siamese</TermInfo> change detection, <TermInfo term="Swin Transformer">Swin Transformer</TermInfo>, and <TermInfo term="ConvLSTM">ConvLSTM</TermInfo> are the labelled vision architectures planned for trained inference; this run shows the transparent evidence proxy until weights are validated.</p>
                <p>Satellite estimates only — field calibration required before verified credits.</p>
              </CollapsibleContent>
            </Card>
          </Collapsible>
        </div>
      )}
    </div>
  );
};

export default MRVDashboard;
