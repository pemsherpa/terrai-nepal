import { Satellite, Leaf, TrendingUp, FileText, MapPin, Brain } from "lucide-react";

const features = [
  {
    icon: Satellite,
    title: "Sentinel-2 Imagery",
    desc: "10-meter resolution multispectral data with cloud-masked composites, updated every 5 days.",
  },
  {
    icon: Leaf,
    title: "NDVI Analysis",
    desc: "Normalized Difference Vegetation Index computed from near-infrared and red bands for canopy health.",
  },
  {
    icon: TrendingUp,
    title: "Multi-Year Trends",
    desc: "Annual NDVI tracking from 2019 to present with linear regression and degradation alerts.",
  },
  {
    icon: Brain,
    title: "AI Due Diligence",
    desc: "LLM-powered reports covering vegetation analysis, carbon implications, and risk assessment.",
  },
  {
    icon: MapPin,
    title: "GeoJSON Boundaries",
    desc: "Upload your exact community forest boundary or project AOI for precise area-based analysis.",
  },
  {
    icon: FileText,
    title: "PDF Export",
    desc: "Professional reports ready for NGO donors, VERRA documentation, and ART-TREES submissions.",
  },
];

const FeaturesSection = () => (
  <section className="py-24 bg-background">
    <div className="container mx-auto px-4">
      <div className="text-center max-w-xl mx-auto mb-16">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-accent mb-3">Capabilities</p>
        <h2 className="font-serif text-3xl md:text-4xl text-foreground mb-4">Everything You Need for Forest MRV</h2>
        <p className="text-muted-foreground leading-relaxed">
          From satellite data acquisition to carbon stock estimation — a complete digital toolkit for Nepal's forests.
        </p>
      </div>

      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
        {features.map((f) => (
          <div
            key={f.title}
            className="group p-7 rounded-xl border border-border bg-card hover:shadow-elevated transition-all duration-300 hover:-translate-y-1"
          >
            <div className="w-12 h-12 rounded-xl bg-gradient-hero flex items-center justify-center mb-5 group-hover:scale-110 transition-transform">
              <f.icon className="w-6 h-6 text-accent-foreground" />
            </div>
            <h3 className="font-serif text-lg text-card-foreground mb-2">{f.title}</h3>
            <p className="text-sm text-muted-foreground leading-relaxed">{f.desc}</p>
          </div>
        ))}
      </div>
    </div>
  </section>
);

export default FeaturesSection;
