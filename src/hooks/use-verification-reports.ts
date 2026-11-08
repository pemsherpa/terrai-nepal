import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch, unwrapList, type Paginated } from "@/lib/api";

export interface VerificationReport {
  id: string;
  project_id: string;
  project_name?: string;
  verifier_id: number | null;
  status: "pending" | "approved" | "rejected";
  pdf_url: string | null;
  integrity_seal_hash: string | null;
  created_at: string;
  updated_at: string;
}

type ReportInsert = Pick<VerificationReport, "project_id"> & {
  status?: VerificationReport["status"];
  pdf_url?: string | null;
  integrity_seal_hash?: string | null;
};

export const useVerificationReports = (projectId?: string) =>
  useQuery({
    queryKey: ["verification_reports", projectId ?? "all"],
    queryFn: async () => {
      const url = projectId
        ? `/api/verification-reports/?project_id=${projectId}`
        : "/api/verification-reports/";
      const data = await apiFetch<Paginated<VerificationReport> | VerificationReport[]>(url);
      return unwrapList(data);
    },
  });

export const useCreateVerificationReport = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (report: ReportInsert) =>
      apiFetch<VerificationReport>("/api/verification-reports/", {
        method: "POST",
        body: JSON.stringify(report),
      }),
    onSuccess: (_, variables) => {
      qc.invalidateQueries({ queryKey: ["verification_reports", variables.project_id] });
      qc.invalidateQueries({ queryKey: ["verification_feed"] });
    },
  });
};

export const useUpdateVerificationReport = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...updates }: { id: string } & Partial<VerificationReport>) =>
      apiFetch<VerificationReport>(`/api/verification-reports/${id}/`, {
        method: "PATCH",
        body: JSON.stringify(updates),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["verification_reports"] });
      qc.invalidateQueries({ queryKey: ["verification_feed"] });
    },
  });
};

export const useVerificationFeed = () =>
  useQuery({
    queryKey: ["verification_feed"],
    queryFn: () =>
      apiFetch<
        Array<{
          id: string;
          status: VerificationReport["status"];
          created_at: string;
          project_id: string;
          project_name: string;
        }>
      >("/api/verification-reports/feed/"),
    refetchInterval: 30_000,
  });
