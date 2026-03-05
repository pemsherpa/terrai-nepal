import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";

const CTASection = () => (
  <section className="py-24">
    <div className="container mx-auto px-4">
      <div className="bg-gradient-hero rounded-2xl p-12 md:p-16 text-center relative overflow-hidden">
        <div className="absolute inset-0 opacity-10" style={{ backgroundImage: "radial-gradient(circle at 20% 50%, white 1px, transparent 1px)", backgroundSize: "30px 30px" }} />
        <div className="relative z-10">
          <h2 className="font-serif text-3xl md:text-4xl text-accent-foreground mb-4">
            Start Monitoring Your Forests Today
          </h2>
          <p className="text-accent-foreground/70 max-w-md mx-auto mb-8 leading-relaxed">
            Try the interactive demo with real satellite data from Nepal's community forests — no account required.
          </p>
          <Button size="lg" className="bg-accent-foreground text-primary hover:bg-accent-foreground/90 px-10 h-12 text-base" asChild>
            <Link to="/dashboard">
              Launch Dashboard <ArrowRight className="w-4 h-4 ml-2" />
            </Link>
          </Button>
        </div>
      </div>
    </div>
  </section>
);

export default CTASection;
