import { ArrowRight, Satellite, TreePine, BarChart3 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";
import heroImage from "@/assets/hero-forest.jpg";

const HeroSection = () => (
  <section className="relative min-h-[90vh] flex items-center overflow-hidden">
    {/* Background image */}
    <div className="absolute inset-0">
      <img src={heroImage} alt="Aerial view of Nepal forest canopy" className="w-full h-full object-cover" />
      <div className="absolute inset-0 bg-gradient-to-r from-primary/95 via-primary/80 to-primary/40" />
    </div>

    <div className="container mx-auto px-4 relative z-10 pt-20">
      <div className="max-w-2xl">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-accent/20 border border-primary-foreground/20 text-primary-foreground/80 text-xs font-semibold tracking-widest uppercase mb-6 animate-fade-in-up">
          <Satellite className="w-3.5 h-3.5" />
          Sentinel-2 · 10m Resolution
        </div>

        <h1 className="font-serif text-5xl md:text-6xl lg:text-7xl text-primary-foreground leading-[1.1] mb-6 animate-fade-in-up" style={{ animationDelay: "0.1s" }}>
          Monitor Nepal's Forests from Space
        </h1>

        <p className="text-lg md:text-xl text-primary-foreground/75 leading-relaxed mb-8 max-w-lg animate-fade-in-up" style={{ animationDelay: "0.2s" }}>
          Satellite-powered NDVI analysis, carbon stock estimation, and AI-generated due diligence reports — built for Nepal's community forests.
        </p>

        <div className="flex flex-wrap gap-4 animate-fade-in-up" style={{ animationDelay: "0.3s" }}>
          <Button size="lg" className="bg-accent text-accent-foreground hover:bg-accent/90 px-8 h-12 text-base" asChild>
            <Link to="/dashboard">
              Try the Demo <ArrowRight className="w-4 h-4 ml-2" />
            </Link>
          </Button>
          <Button size="lg" variant="outline" className="border-primary-foreground/30 text-primary-foreground hover:bg-primary-foreground/10 px-8 h-12 text-base" asChild>
            <Link to="/about">Learn More</Link>
          </Button>
        </div>

        {/* Mini stats */}
        <div className="grid grid-cols-3 gap-6 mt-14 animate-fade-in-up" style={{ animationDelay: "0.4s" }}>
          {[
            { icon: TreePine, value: "6.6M ha", label: "Forest Cover" },
            { icon: BarChart3, value: "2019–Now", label: "NDVI Trends" },
            { icon: Satellite, value: "5-day", label: "Revisit Cycle" },
          ].map((s) => (
            <div key={s.label} className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-primary-foreground/10 flex items-center justify-center">
                <s.icon className="w-5 h-5 text-terrai-light" />
              </div>
              <div>
                <div className="font-serif text-lg text-primary-foreground">{s.value}</div>
                <div className="text-xs text-primary-foreground/50 uppercase tracking-wider">{s.label}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  </section>
);

export default HeroSection;
