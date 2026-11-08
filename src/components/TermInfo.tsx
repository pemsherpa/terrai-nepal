import React, { useState } from "react";
import { Info, BookOpen, Sparkles, CheckCircle2 } from "lucide-react";
import { FORESTRY_TERMS, lookupTerm } from "@/data/forestryTerms";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Badge } from "@/components/ui/badge";

interface TermInfoProps {
  term: string;
  children?: React.ReactNode;
  showLabel?: boolean;
  className?: string;
  badge?: boolean;
}

export const TermInfo: React.FC<TermInfoProps> = ({
  term,
  children,
  showLabel = true,
  className = "",
  badge = false,
}) => {
  const [open, setOpen] = useState(false);
  const info = lookupTerm(term);

  if (!info) {
    return <span>{children ?? term}</span>;
  }

  const categoryColors: Record<string, string> = {
    "Remote Sensing": "bg-sky-500/10 text-sky-700 dark:text-sky-300 border-sky-300/40",
    "Carbon & Biomass": "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-300/40",
    "Nepal Forestry": "bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-300/40",
    "Carbon Standards & Policy": "bg-purple-500/10 text-purple-700 dark:text-purple-300 border-purple-300/40",
  };

  return (
    <span className={`inline-flex items-center gap-1.5 align-baseline ${className}`}>
      {showLabel && (
        <span className={badge ? "font-medium" : ""}>
          {children ?? info.abbreviation ?? info.term}
        </span>
      )}
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
            }}
            title={`Explain "${info.name}"`}
            aria-label={`Learn what ${info.name} means`}
            className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-accent/15 hover:bg-accent hover:text-accent-foreground text-accent-foreground/80 transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-accent/50 text-[10px] font-bold shrink-0 cursor-pointer shadow-xs border border-accent/25 hover:scale-110 active:scale-95"
          >
            <span className="leading-none select-none italic font-serif">i</span>
          </button>
        </PopoverTrigger>
        <PopoverContent
          side="top"
          align="start"
          className="w-84 sm:w-96 p-4 rounded-xl shadow-xl border border-border/80 bg-popover text-popover-foreground z-50 animate-in fade-in zoom-in-95 duration-200"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="space-y-3">
            <div className="flex items-start justify-between gap-2 border-b border-border/60 pb-2.5">
              <div>
                <div className="flex items-center gap-2">
                  <h4 className="font-serif font-bold text-base text-foreground tracking-tight">
                    {info.abbreviation ? `${info.abbreviation} — ` : ""}
                    {info.name}
                  </h4>
                </div>
                <span className={`inline-block mt-1 text-[10px] font-semibold tracking-wider uppercase px-2 py-0.5 rounded-full border ${categoryColors[info.category] || "bg-muted text-muted-foreground"}`}>
                  {info.category}
                </span>
              </div>
            </div>

            <div className="space-y-2.5 text-xs text-muted-foreground leading-relaxed">
              <div className="bg-muted/40 p-2.5 rounded-lg border border-border/40">
                <p className="text-foreground/90 font-medium leading-relaxed">
                  {info.definition}
                </p>
              </div>

              <div>
                <span className="font-semibold text-foreground/80 flex items-center gap-1 mb-1 text-[11px] uppercase tracking-wider">
                  <Sparkles className="w-3 h-3 text-accent" /> Why it matters:
                </span>
                <p className="text-muted-foreground/90">{info.whyItMatters}</p>
              </div>

              {info.nepalContext && (
                <div className="pt-1 border-t border-border/40">
                  <span className="font-semibold text-foreground/80 flex items-center gap-1 mb-1 text-[11px] uppercase tracking-wider">
                    <span className="text-sm">🇳🇵</span> In Nepal:
                  </span>
                  <p className="text-muted-foreground/90">{info.nepalContext}</p>
                </div>
              )}

              {info.typicalValue && (
                <div className="pt-1.5 flex items-start gap-1.5 bg-accent/5 p-2 rounded-md border border-accent/15 text-[11px]">
                  <CheckCircle2 className="w-3.5 h-3.5 text-accent shrink-0 mt-0.5" />
                  <div>
                    <span className="font-semibold text-foreground/80">Benchmark: </span>
                    <span className="font-mono text-foreground/90">{info.typicalValue}</span>
                  </div>
                </div>
              )}
            </div>
          </div>
        </PopoverContent>
      </Popover>
    </span>
  );
};

export default TermInfo;
