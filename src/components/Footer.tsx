import { TreePine } from "lucide-react";
import { Link } from "react-router-dom";

const Footer = () => (
  <footer className="bg-primary text-primary-foreground">
    <div className="container mx-auto px-4 py-12">
      <div className="grid md:grid-cols-4 gap-8">
        <div className="md:col-span-2">
          <div className="flex items-center gap-2.5 mb-4">
            <div className="w-8 h-8 rounded-lg bg-accent flex items-center justify-center">
              <TreePine className="w-4 h-4 text-accent-foreground" />
            </div>
            <span className="font-serif text-xl">TerrAI</span>
          </div>
          <p className="text-primary-foreground/70 text-sm max-w-sm leading-relaxed">
            Digital MRV platform for satellite-based forest health monitoring, carbon stock estimation, and due diligence reporting in Nepal.
          </p>
        </div>
        <div>
          <h4 className="font-semibold text-sm uppercase tracking-wider mb-4 text-primary-foreground/50">Platform</h4>
          <div className="space-y-2.5">
            <Link to="/dashboard" className="block text-sm text-primary-foreground/70 hover:text-primary-foreground transition-colors">Dashboard</Link>
            <Link to="/about" className="block text-sm text-primary-foreground/70 hover:text-primary-foreground transition-colors">About</Link>
          </div>
        </div>
        <div>
          <h4 className="font-semibold text-sm uppercase tracking-wider mb-4 text-primary-foreground/50">Technology</h4>
          <div className="space-y-2.5 text-sm text-primary-foreground/70">
            <p>Sentinel-2 (10m)</p>
            <p>Google Earth Engine</p>
            <p>FAO/ICIMOD Data</p>
          </div>
        </div>
      </div>
      <div className="border-t border-primary-foreground/10 mt-10 pt-6 flex flex-col md:flex-row justify-between items-center gap-4">
        <p className="text-xs text-primary-foreground/40">© 2025 TerrAI. Built in Nepal 🇳🇵</p>
        <p className="text-xs text-primary-foreground/40">Satellite-based estimates · Field calibration required</p>
      </div>
    </div>
  </footer>
);

export default Footer;
