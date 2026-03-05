import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { Card } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Leaf, TrendingUp, TreePine, AlertTriangle, CheckCircle, Activity } from "lucide-react";
import { useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  AreaChart, Area, BarChart, Bar, Cell,
} from "recharts";

// Demo data
const LOCATIONS = ["Chitwan National Park", "Langtang Valley", "Bardiya District", "Gorkha Community Forest"];

const ndviTrend = [
  { year: 2019, ndvi: 0.62 },
  { year: 2020, ndvi: 0.65 },
  { year: 2021, ndvi: 0.64 },
  { year: 2022, ndvi: 0.68 },
  { year: 2023, ndvi: 0.66 },
  { year: 2024, ndvi: 0.71 },
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
  agb_ha: 167, bgb_ha: 47, co2e_ha: 329, total_co2e: 82250, total_carbon: 22440, area_ha: 250,
};

const ndviScale = [
  { range: "0.8–1.0", label: "Very Dense", color: "hsl(153,50%,25%)" },
  { range: "0.6–0.8", label: "Dense", color: "hsl(153,45%,38%)" },
  { range: "0.4–0.6", label: "Moderate", color: "hsl(45,60%,50%)" },
  { range: "0.2–0.4", label: "Sparse", color: "hsl(25,60%,55%)" },
  { range: "0.0–0.2", label: "Bare", color: "hsl(0,50%,50%)" },
];

const Dashboard = () => {
  const [location, setLocation] = useState(LOCATIONS[0]);
  const [analyzed, setAnalyzed] = useState(false);

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <div className="pt-20 pb-16">
        {/* Header */}
        <div className="bg-gradient-hero py-10">
          <div className="container mx-auto px-4">
            <h1 className="font-serif text-3xl text-accent-foreground mb-1">Forest Health Dashboard</h1>
            <p className="text-accent-foreground/60 text-sm">Interactive demo with sample satellite data from Nepal</p>
          </div>
        </div>

        <div className="container mx-auto px-4 -mt-6">
          {/* Controls */}
          <Card className="p-5 mb-6 shadow-card flex flex-col md:flex-row items-end gap-4">
            <div className="flex-1 w-full">
              <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5 block">Location</label>
              <Select value={location} onValueChange={setLocation}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {LOCATIONS.map((l) => <SelectItem key={l} value={l}>{l}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="w-full md:w-36">
              <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5 block">Year 1</label>
              <Select defaultValue="2024"><SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>{[2022,2023,2024].map(y => <SelectItem key={y} value={String(y)}>{y}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div className="w-full md:w-36">
              <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5 block">Year 2</label>
              <Select defaultValue="2025"><SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>{[2023,2024,2025].map(y => <SelectItem key={y} value={String(y)}>{y}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <Button className="bg-gradient-hero text-accent-foreground hover:opacity-90 w-full md:w-auto px-8" onClick={() => setAnalyzed(true)}>
              Analyse
            </Button>
          </Card>

          {!analyzed ? (
            <div className="text-center py-20">
              <TreePine className="w-16 h-16 mx-auto text-muted-foreground/30 mb-4" />
              <p className="text-muted-foreground">Configure parameters above, then click <strong>Analyse</strong> to see results.</p>
            </div>
          ) : (
            <div className="space-y-6 animate-fade-in-up">
              {/* Metric cards */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                {[
                  { label: "NDVI 2024", value: "0.6600", icon: Leaf, change: null },
                  { label: "NDVI 2025", value: "0.6900", icon: Activity, change: null },
                  { label: "Change", value: "+4.5%", icon: TrendingUp, change: "positive" },
                  { label: "Area", value: "250 ha", icon: TreePine, change: null },
                ].map((m) => (
                  <Card key={m.label} className="p-5 shadow-card">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{m.label}</span>
                      <m.icon className="w-4 h-4 text-accent" />
                    </div>
                    <div className={`font-serif text-2xl ${m.change === "positive" ? "text-accent" : "text-foreground"}`}>{m.value}</div>
                  </Card>
                ))}
              </div>

              {/* Status */}
              <Card className="p-5 shadow-card border-l-4 border-l-accent flex items-start gap-4">
                <CheckCircle className="w-8 h-8 text-accent flex-shrink-0 mt-0.5" />
                <div>
                  <h3 className="font-semibold text-foreground mb-1">Forest Healthy — Stable or Improving</h3>
                  <p className="text-sm text-muted-foreground">NDVI increased 4.5%. No significant degradation detected in the analysis period.</p>
                </div>
              </Card>

              {/* Carbon box */}
              <Card className="bg-gradient-hero p-6 shadow-card border-0">
                <h3 className="font-serif text-lg text-accent-foreground/80 mb-4 flex items-center gap-2">
                  <Leaf className="w-5 h-5" /> Carbon Stock Estimate (Satellite-Based)
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {[
                    { label: "Above-Ground Biomass", val: `${carbonData.agb_ha}`, unit: "tonnes/ha" },
                    { label: "Total Carbon Stock", val: `${carbonData.total_carbon.toLocaleString()}`, unit: "tonnes C" },
                    { label: "Total CO₂ Equivalent", val: `${carbonData.total_co2e.toLocaleString()}`, unit: "tonnes CO₂e" },
                    { label: "Area Analysed", val: `${carbonData.area_ha}`, unit: "hectares" },
                  ].map((c) => (
                    <div key={c.label} className="bg-accent-foreground/10 rounded-lg p-4 text-center">
                      <div className="text-[10px] uppercase tracking-widest text-accent-foreground/60 mb-1 font-semibold">{c.label}</div>
                      <div className="font-serif text-2xl text-accent-foreground">{c.val}</div>
                      <div className="text-xs text-accent-foreground/50 mt-0.5">{c.unit}</div>
                    </div>
                  ))}
                </div>
                <p className="text-xs text-accent-foreground/40 mt-4 italic">
                  ⚠️ Satellite-based estimates only · Based on Nepal FAO/ICIMOD literature values · Field calibration required
                </p>
              </Card>

              {/* Charts */}
              <div className="grid lg:grid-cols-2 gap-6">
                <Card className="p-5 shadow-card">
                  <h3 className="font-serif text-lg text-foreground mb-4">Multi-Year NDVI Trend (2019–2025)</h3>
                  <ResponsiveContainer width="100%" height={280}>
                    <AreaChart data={ndviTrend}>
                      <defs>
                        <linearGradient id="ndviGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="hsl(153,40%,42%)" stopOpacity={0.3} />
                          <stop offset="100%" stopColor="hsl(153,40%,42%)" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(140,25%,88%)" />
                      <XAxis dataKey="year" tick={{ fontSize: 12 }} />
                      <YAxis domain={[0, 1]} tick={{ fontSize: 12 }} />
                      <Tooltip contentStyle={{ borderRadius: 8, fontSize: 13 }} />
                      <Area type="monotone" dataKey="ndvi" stroke="hsl(153,40%,42%)" strokeWidth={2.5} fill="url(#ndviGrad)" dot={{ r: 5, fill: "hsl(153,44%,18%)", stroke: "#fff", strokeWidth: 2 }} />
                    </AreaChart>
                  </ResponsiveContainer>
                </Card>

                <Card className="p-5 shadow-card">
                  <h3 className="font-serif text-lg text-foreground mb-4">Monthly NDVI (2025)</h3>
                  <ResponsiveContainer width="100%" height={280}>
                    <BarChart data={monthlyNdvi}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(140,25%,88%)" />
                      <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                      <YAxis domain={[0, 1]} tick={{ fontSize: 12 }} />
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

              {/* NDVI Scale */}
              <Card className="p-5 shadow-card">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">NDVI Scale Reference</h3>
                <div className="flex rounded-lg overflow-hidden h-4 mb-2">
                  {ndviScale.map((s) => (
                    <div key={s.range} className="flex-1" style={{ backgroundColor: s.color }} />
                  ))}
                </div>
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>0.0 · Bare</span><span>0.2</span><span>0.4</span><span>0.6</span><span>0.8</span><span>1.0 · Dense</span>
                </div>
              </Card>
            </div>
          )}
        </div>
      </div>
      <Footer />
    </div>
  );
};

export default Dashboard;
