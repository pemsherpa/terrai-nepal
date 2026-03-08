import { useEffect, useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Activity, CheckCircle, Clock, XCircle } from "lucide-react";
import { formatDistanceToNow } from "date-fns";

interface FeedItem {
  id: string;
  status: "pending" | "approved" | "rejected";
  created_at: string;
  project_name: string;
}

const statusConfig = {
  pending: { icon: Clock, label: "Pending", className: "bg-terrai-gold/20 text-terrai-gold border-terrai-gold/30" },
  approved: { icon: CheckCircle, label: "Approved", className: "bg-accent/20 text-accent border-accent/30" },
  rejected: { icon: XCircle, label: "Rejected", className: "bg-destructive/20 text-destructive border-destructive/30" },
};

export function CarbonFeed() {
  const [items, setItems] = useState<FeedItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchFeed = async () => {
      const { data } = await supabase
        .from("verification_reports")
        .select("id, status, created_at, project_id, projects(name)")
        .order("created_at", { ascending: false })
        .limit(20);

      if (data) {
        setItems(
          data.map((r: any) => ({
            id: r.id,
            status: r.status,
            created_at: r.created_at,
            project_name: r.projects?.name ?? "Unknown Project",
          }))
        );
      }
      setLoading(false);
    };

    fetchFeed();

    const channel = supabase
      .channel("carbon-feed")
      .on(
        "postgres_changes",
        { event: "*", schema: "public", table: "verification_reports" },
        () => {
          fetchFeed();
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, []);

  return (
    <Card className="shadow-card">
      <div className="p-5 border-b border-border">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-accent animate-pulse-dot" />
          <h3 className="font-serif text-base text-foreground">Global Carbon Feed</h3>
        </div>
        <p className="text-xs text-muted-foreground mt-1">Real-time verification activity across Nepal</p>
      </div>

      <div className="max-h-80 overflow-y-auto divide-y divide-border">
        {loading ? (
          <div className="p-8 text-center text-muted-foreground text-sm">Loading feed…</div>
        ) : items.length === 0 ? (
          <div className="p-8 text-center">
            <Activity className="w-8 h-8 mx-auto text-muted-foreground/30 mb-2" />
            <p className="text-sm text-muted-foreground">No verifications yet. Activity will appear here in real-time.</p>
          </div>
        ) : (
          items.map((item) => {
            const config = statusConfig[item.status];
            const Icon = config.icon;
            return (
              <div key={item.id} className="px-5 py-3 flex items-center gap-3 hover:bg-muted/50 transition-colors">
                <Icon className="w-4 h-4 shrink-0 text-muted-foreground" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-foreground truncate">{item.project_name}</p>
                  <p className="text-xs text-muted-foreground">
                    {formatDistanceToNow(new Date(item.created_at), { addSuffix: true })}
                  </p>
                </div>
                <Badge variant="outline" className={config.className}>
                  {config.label}
                </Badge>
              </div>
            );
          })
        )}
      </div>
    </Card>
  );
}
