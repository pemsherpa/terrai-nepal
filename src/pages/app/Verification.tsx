import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useVerificationReports } from "@/hooks/use-verification-reports";
import { useProjects } from "@/hooks/use-projects";
import { FileCheck, Download, CheckCircle, Clock, XCircle, FileText } from "lucide-react";
import { formatDistanceToNow } from "date-fns";

const statusConfig = {
  pending: { icon: Clock, label: "Pending Review", className: "bg-terrai-gold/20 text-terrai-gold border-terrai-gold/30" },
  approved: { icon: CheckCircle, label: "Approved", className: "bg-accent/20 text-accent border-accent/30" },
  rejected: { icon: XCircle, label: "Rejected", className: "bg-destructive/20 text-destructive border-destructive/30" },
};

const Verification = () => {
  const { data: projects } = useProjects();
  const { data: reports = [], isLoading: loading } = useVerificationReports();

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div>
        <h1 className="font-serif text-2xl text-foreground">Verification Reports</h1>
        <p className="text-sm text-muted-foreground mt-1">Track the status of your carbon credit verifications</p>
      </div>

      {loading ? (
        <div className="text-center py-16 text-muted-foreground">Loading reports…</div>
      ) : !reports.length ? (
        <div className="text-center py-20">
          <FileCheck className="w-16 h-16 mx-auto text-muted-foreground/20 mb-4" />
          <p className="text-muted-foreground">No verification reports yet. Run an analysis and submit for verification.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {reports.map((r) => {
            const config = statusConfig[r.status];
            const Icon = config.icon;
            const projectName =
              r.project_name ??
              projects?.find((p) => p.id === r.project_id)?.name ??
              "Unknown";
            return (
              <Card key={r.id} className="p-5 shadow-card">
                <div className="flex flex-col sm:flex-row sm:items-center gap-4">
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    <div className="w-10 h-10 rounded-lg bg-muted flex items-center justify-center shrink-0">
                      <FileText className="w-5 h-5 text-muted-foreground" />
                    </div>
                    <div className="min-w-0">
                      <p className="font-medium text-foreground truncate">{projectName}</p>
                      <p className="text-xs text-muted-foreground">
                        Submitted {formatDistanceToNow(new Date(r.created_at), { addSuffix: true })}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <Badge variant="outline" className={config.className}>
                      <Icon className="w-3 h-3 mr-1" />
                      {config.label}
                    </Badge>
                    {r.pdf_url && (
                      <Button variant="outline" size="sm" asChild>
                        <a href={r.pdf_url} target="_blank" rel="noopener noreferrer" className="gap-1.5">
                          <Download className="w-3.5 h-3.5" /> PDF
                        </a>
                      </Button>
                    )}
                  </div>
                </div>
                {r.integrity_seal_hash && (
                  <p className="text-[10px] text-muted-foreground/60 mt-3 font-mono truncate">
                    Seal: {r.integrity_seal_hash}
                  </p>
                )}
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default Verification;
