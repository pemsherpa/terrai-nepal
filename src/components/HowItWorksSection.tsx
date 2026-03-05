const steps = [
  { num: "01", title: "Select Location", desc: "Choose a Nepal district, community forest, enter coordinates, or upload a GeoJSON boundary." },
  { num: "02", title: "Configure Analysis", desc: "Set comparison years, season window, and forest type for accurate carbon estimation." },
  { num: "03", title: "Analyse & Report", desc: "Get NDVI maps, multi-year trends, carbon estimates, and AI-powered due diligence reports." },
];

const HowItWorksSection = () => (
  <section className="py-24 bg-muted/40">
    <div className="container mx-auto px-4">
      <div className="text-center max-w-xl mx-auto mb-16">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-accent mb-3">How It Works</p>
        <h2 className="font-serif text-3xl md:text-4xl text-foreground mb-4">Three Steps to Forest Intelligence</h2>
      </div>

      <div className="grid md:grid-cols-3 gap-8 max-w-4xl mx-auto">
        {steps.map((s, i) => (
          <div key={s.num} className="relative text-center">
            {i < steps.length - 1 && (
              <div className="hidden md:block absolute top-10 left-[60%] w-[80%] h-px bg-border" />
            )}
            <div className="w-20 h-20 rounded-2xl bg-gradient-hero mx-auto mb-6 flex items-center justify-center">
              <span className="font-serif text-2xl text-accent-foreground">{s.num}</span>
            </div>
            <h3 className="font-serif text-xl text-foreground mb-2">{s.title}</h3>
            <p className="text-sm text-muted-foreground leading-relaxed max-w-xs mx-auto">{s.desc}</p>
          </div>
        ))}
      </div>
    </div>
  </section>
);

export default HowItWorksSection;
