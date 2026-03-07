import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Leaf, TrendingUp, TrendingDown, MapPin, TreePine, Activity, Layers } from "lucide-react";
import { useState } from "react";
import {
  AreaChart, Area, BarChart, Bar, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";

const FOREST_TYPES = ["Tropical Moist", "Subtropical Broadleaf", "Temperate Conifer", "Alpine Scrub"];

const ndviTrend = [
  { year: 2019, ndvi: 0.62 }, { year: 2020, ndvi: 0.65 }, { year: 2021, ndvi: 0.64 },
  { year: 2022, ndvi: 0.68 }, { year: 2023, ndvi: 0.66 }, { year: 2024, ndvi: 0.71 },
  { year: 2025, ndvi: 0.69 },
];

const monthlyNdvi = [
  { month: "Jan", ndvi: 0.52 }, { month: "Feb", ndvi: 0.58 },
  { month: "Mar", ndvi: 0.63 }, { month: "Apr", ndvi: 0.69 },
  { month: "May", ndvi: 0.72 }, { month: "Jun", ndvi: 0.68 },
  { month: "Jul", ndvi: 0.65 }, { month: "Aug", ndvi: 0.61 },
  { month: "Sep", ndvi: 0.67 }, { month: "Oct", ndvi: 0.70 },
  { month: "Nov", ndvi: 0.66 }, { month: "Dec", ndvi: 0.55 },
];

const carbonData = {
  agb_ha: 167, bgb_ha: 47, total_carbon: 22440, total_co2e: 82250, area_ha: 250,
};

const MRVDashboard = () => {
  const [lat, setLat] = useState("27.5");
  const [lon, setLon] = useState("84.3");
  const [forestType, setForestType] = useState(FOREST_TYPES[0]);
  const [analyzed, setAnalyzed] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleAnalyse = () => {
    setLoading(true);
    setTimeout(() => {
      setAnalyzed(true);
      setLoading(false);
    }, 1200);
  };

  const changePercent = 4.5;
  const isPositive = changePercent > 0;

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Page Header */}
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
                {FOREST_TYPES.map((f) => <SelectItem key={f} value={f}>{f}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Baseline Year</Label>
            <Select defaultValue="2024">
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {[2022, 2023, 2024].map((y) => <SelectItem key={y} value={String(y)}>{y}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Comparison Year</Label>
            <Select defaultValue="2025">
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {[2023, 2024, 2025].map((y) => <SelectItem key={y} value={String(y)}>{y}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
        </div>
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

      {!analyzed ? (
        <div className="text-center py-20">
          <TreePine className="w-16 h-16 mx-auto text-muted-foreground/20 mb-4" />
          <p className="text-muted-foreground">Enter coordinates and click <strong>Analyse Forest</strong> to begin.</p>
        </div>
      ) : (
        <div className="space-y-6 animate-fade-in-up">
          {/* Metrics Row */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { label: "NDVI 2024", value: "0.6600", icon: Activity, color: "text-foreground" },
              { label: "NDVI 2025", value: "0.6900", icon: Layers, color: "text-foreground" },
              { label: "Change", value: `${isPositive ? "+" : ""}${changePercent}%`, icon: isPositive ? TrendingUp : TrendingDown, color: isPositive ? "text-accent" : "text-destructive" },
              { label: "Total Area", value: "250 ha", icon: MapPin, color: "text-foreground" },
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

          {/* Map Placeholder */}
          <Card className="shadow-card overflow-hidden">
            <div className="bg-muted h-80 flex items-center justify-center relative">
              <div className="absolute inset-0 opacity-10" style={{
                backgroundImage: "radial-gradient(circle at 30% 40%, hsl(var(--accent)) 0%, transparent 50%), radial-gradient(circle at 70% 60%, hsl(var(--primary)) 0%, transparent 50%)"
              }} />
              <div className="text-center z-10">
                <MapPin className="w-10 h-10 mx-auto text-muted-foreground/40 mb-2" />
                <p className="text-sm text-muted-foreground font-medium">Interactive Satellite Map</p>
                <p className="text-xs text-muted-foreground/60 mt-1">
                  {lat}°N, {lon}°E · Leaflet/Mapbox integration ready
                </p>
              </div>
            </div>
          </Card>

          {/* Carbon Stock */}
          <Card className="bg-primary p-6 shadow-card border-0">
            <h3 className="font-serif text-lg text-primary-foreground/80 mb-4 flex items-center gap-2">
              <Leaf className="w-5 h-5" /> Carbon Stock Estimate
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {[
                { label: "Above-Ground Biomass", val: `${carbonData.agb_ha}`, unit: "tonnes/ha" },
                { label: "Total Carbon Stock", val: carbonData.total_carbon.toLocaleString(), unit: "tonnes C" },
                { label: "Total CO₂ Equivalent", val: carbonData.total_co2e.toLocaleString(), unit: "tonnes CO₂e" },
                { label: "Area Analysed", val: `${carbonData.area_ha}`, unit: "hectares" },
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
          <div className="grid lg:grid-cols-2 gap-6">
            <Card className="p-5 shadow-card">
              <h3 className="font-serif text-base text-foreground mb-4">Multi-Year NDVI Trend</h3>
              <ResponsiveContainer width="100%" height={260}>
                <AreaChart data={ndviTrend}>
                  <defs>
                    <linearGradient id="mrvNdviGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="hsl(153,40%,42%)" stopOpacity={0.3} />
                      <stop offset="100%" stopColor="hsl(153,40%,42%)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(140,25%,88%)" />
                  <XAxis dataKey="year" tick={{ fontSize: 12 }} />
                  <YAxis domain={[0.5, 0.8]} tick={{ fontSize: 12 }} />
                  <Tooltip contentStyle={{ borderRadius: 8, fontSize: 13 }} />
                  <Area type="monotone" dataKey="ndvi" stroke="hsl(153,40%,42%)" strokeWidth={2.5} fill="url(#mrvNdviGrad)" dot={{ r: 4, fill: "hsl(153,44%,18%)", stroke: "#fff", strokeWidth: 2 }} />
                </AreaChart>
              </ResponsiveContainer>
            </Card>

            <Card className="p-5 shadow-card">
              <h3 className="font-serif text-base text-foreground mb-4">Monthly NDVI (2025)</h3>
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={monthlyNdvi}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(140,25%,88%)" />
                  <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                  <YAxis domain={[0.4, 0.8]} tick={{ fontSize: 12 }} />
                  <Tooltip contentStyle={{ borderRadius: 8, fontSize: 13 }} />
                  <Bar dataKey="ndvi" radius={[4, 4, 0, 0]}>
                    {monthlyNdvi.map((entry, i) => (
                      <Cell key={i} fill={entry.ndvi > 0.65 ? "hsl(153,40%,42%)" : entry.ndvi > 0.55 ? "hsl(153,30%,55%)" : "hsl(45,50%,55%)"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
};

export default MRVDashboard;
