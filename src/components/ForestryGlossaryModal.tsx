import React, { useState, useMemo } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Search, BookOpen, Info, Sparkles, CheckCircle2 } from "lucide-react";
import { FORESTRY_TERMS, ForestryTerm } from "@/data/forestryTerms";

export const ForestryGlossaryModal: React.FC<{ trigger?: React.ReactNode }> = ({ trigger }) => {
  const [search, setSearch] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("All");

  const termsList = useMemo(() => Object.values(FORESTRY_TERMS), []);

  const categories = useMemo(() => {
    const set = new Set<string>();
    termsList.forEach((t) => set.add(t.category));
    return ["All", ...Array.from(set)];
  }, [termsList]);

  const filteredTerms = useMemo(() => {
    return termsList.filter((t) => {
      const matchCat = selectedCategory === "All" || t.category === selectedCategory;
      const q = search.toLowerCase().trim();
      if (!q) return matchCat;
      const matchText =
        t.term.toLowerCase().includes(q) ||
        (t.abbreviation && t.abbreviation.toLowerCase().includes(q)) ||
        t.name.toLowerCase().includes(q) ||
        t.definition.toLowerCase().includes(q) ||
        (t.nepalContext && t.nepalContext.toLowerCase().includes(q));
      return matchCat && matchText;
    });
  }, [termsList, search, selectedCategory]);

  return (
    <Dialog>
      <DialogTrigger asChild>
        {trigger ?? (
          <Button
            variant="outline"
            size="sm"
            className="gap-2 h-9 border-dashed border-accent/40 bg-accent/5 hover:bg-accent/15 text-accent-foreground text-xs"
          >
            <div className="w-4 h-4 rounded-full bg-accent/20 flex items-center justify-center text-[10px] font-serif font-bold italic text-accent-foreground">
              i
            </div>
            <span>Forestry & Carbon Terms Guide</span>
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="max-w-3xl max-h-[85vh] flex flex-col p-6 overflow-hidden">
        <DialogHeader className="pb-3 border-b border-border/70">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-accent/20 flex items-center justify-center text-accent-foreground">
              <BookOpen className="w-4 h-4 text-accent" />
            </div>
            <div>
              <DialogTitle className="font-serif text-xl">Forestry & Carbon Terms Guide</DialogTitle>
              <p className="text-xs text-muted-foreground mt-0.5">
                Simple, plain-English explanations for remote sensing, biomass, carbon credits, and Nepal community forestry
              </p>
            </div>
          </div>
        </DialogHeader>

        <div className="space-y-3 pt-3">
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search terms, abbreviations (e.g. NDVI, AGB, CFUG, CO2e)…"
              className="pl-9 h-10 text-sm"
            />
          </div>

          <div className="flex flex-wrap gap-1.5">
            {categories.map((c) => (
              <button
                key={c}
                type="button"
                onClick={() => setSelectedCategory(c)}
                className={`text-xs px-2.5 py-1 rounded-full transition-colors font-medium ${
                  selectedCategory === c
                    ? "bg-accent text-accent-foreground"
                    : "bg-muted hover:bg-muted/80 text-muted-foreground"
                }`}
              >
                {c}
              </button>
            ))}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto pr-1 space-y-4 pt-3 mt-1">
          {filteredTerms.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <Info className="w-8 h-8 mx-auto mb-2 opacity-40" />
              <p className="text-sm">No terms match your search.</p>
            </div>
          ) : (
            filteredTerms.map((t) => (
              <div
                key={t.term}
                className="p-4 rounded-xl border border-border bg-card hover:border-accent/40 transition-colors space-y-2"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-serif font-bold text-base text-foreground">
                        {t.abbreviation ? `${t.abbreviation} — ` : ""}
                        {t.name}
                      </span>
                    </div>
                  </div>
                  <Badge variant="outline" className="text-[10px] shrink-0 font-medium">
                    {t.category}
                  </Badge>
                </div>

                <p className="text-sm text-foreground/90 leading-relaxed bg-muted/40 p-2.5 rounded-lg border border-border/40">
                  {t.definition}
                </p>

                <div className="grid md:grid-cols-2 gap-3 text-xs pt-1 text-muted-foreground">
                  <div>
                    <span className="font-semibold text-foreground/80 flex items-center gap-1 mb-0.5">
                      <Sparkles className="w-3 h-3 text-accent" /> Why it matters:
                    </span>
                    <p>{t.whyItMatters}</p>
                  </div>
                  {t.nepalContext && (
                    <div>
                      <span className="font-semibold text-foreground/80 flex items-center gap-1 mb-0.5">
                        <span className="text-sm">🇳🇵</span> Nepal context:
                      </span>
                      <p>{t.nepalContext}</p>
                    </div>
                  )}
                </div>

                {t.typicalValue && (
                  <div className="flex items-center gap-2 text-xs bg-accent/5 p-2 rounded-md border border-accent/15 text-foreground/90 font-mono">
                    <CheckCircle2 className="w-3.5 h-3.5 text-accent shrink-0" />
                    <span>Typical values / formula: {t.typicalValue}</span>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default ForestryGlossaryModal;
