import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { Card } from "@/components/ui/card";
import { TreePine, Globe, BarChart3, Shield, Users, Leaf } from "lucide-react";

const About = () => (
  <div className="min-h-screen bg-background">
    <Navbar />
    <div className="pt-16">
      {/* Hero */}
      <div className="bg-gradient-hero py-20">
        <div className="container mx-auto px-4 text-center">
          <h1 className="font-serif text-4xl md:text-5xl text-accent-foreground mb-4">About TerrAI</h1>
          <p className="text-accent-foreground/70 max-w-xl mx-auto leading-relaxed">
            A digital MRV platform leveraging satellite data and AI to protect Nepal's forests and support community-based conservation.
          </p>
        </div>
      </div>

      <div className="container mx-auto px-4 py-16 max-w-4xl space-y-16">
        {/* Mission */}
        <section>
          <h2 className="font-serif text-2xl text-foreground mb-4">Our Mission</h2>
          <p className="text-muted-foreground leading-relaxed mb-4">
            Nepal is home to 6.6 million hectares of forest — nearly 45% of its land area. These forests are critical for biodiversity, carbon sequestration, and the livelihoods of millions. Yet monitoring forest health at scale remains a challenge for community forest user groups (CFUGs), NGOs, and government agencies.
          </p>
          <p className="text-muted-foreground leading-relaxed">
            TerrAI bridges this gap by making satellite-based forest monitoring accessible, affordable, and actionable. We combine Sentinel-2 imagery, NDVI analysis, carbon stock estimation using FAO/ICIMOD data, and AI-powered reporting to deliver professional-grade forest intelligence.
          </p>
        </section>

        {/* What we do */}
        <section>
          <h2 className="font-serif text-2xl text-foreground mb-6">What We Do</h2>
          <div className="grid md:grid-cols-2 gap-5">
            {[
              { icon: Globe, title: "Satellite Monitoring", desc: "10m resolution Sentinel-2 imagery with automated cloud masking and seasonal compositing." },
              { icon: BarChart3, title: "NDVI Trend Analysis", desc: "Multi-year vegetation health tracking from 2019 to present with degradation alerts." },
              { icon: Leaf, title: "Carbon Estimation", desc: "NDVI-scaled biomass converted to CO₂e using Nepal-specific FAO/ICIMOD literature values." },
              { icon: Shield, title: "Due Diligence Reports", desc: "AI-generated analysis with risk assessment, ready for VERRA and ART-TREES documentation." },
            ].map((item) => (
              <Card key={item.title} className="p-6 shadow-card">
                <item.icon className="w-8 h-8 text-accent mb-3" />
                <h3 className="font-serif text-lg text-foreground mb-2">{item.title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{item.desc}</p>
              </Card>
            ))}
          </div>
        </section>

        {/* Technology */}
        <section>
          <h2 className="font-serif text-2xl text-foreground mb-4">Technology Stack</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {["Sentinel-2 SR", "Google Earth Engine", "FAO/ICIMOD Data", "Llama 3 (Groq)"].map((tech) => (
              <div key={tech} className="bg-muted rounded-xl p-4 text-center">
                <p className="text-sm font-medium text-foreground">{tech}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Built in Nepal */}
        <section className="text-center">
          <div className="inline-flex items-center gap-3 bg-muted rounded-full px-6 py-3">
            <TreePine className="w-5 h-5 text-accent" />
            <span className="font-medium text-foreground">Built with ❤️ in Nepal 🇳🇵</span>
          </div>
        </section>
      </div>
    </div>
    <Footer />
  </div>
);

export default About;
