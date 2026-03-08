import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";
import type { Database } from "@/integrations/supabase/types";

type VerificationReport = Database["public"]["Tables"]["verification_reports"]["Row"];
type ReportInsert = Database["public"]["Tables"]["verification_reports"]["Insert"];

export const useVerificationReports = (projectId: string | undefined) =>
  useQuery({
    queryKey: ["verification_reports", projectId],
    enabled: !!projectId,
    queryFn: async () => {
      const { data, error } = await supabase
        .from("verification_reports")
        .select("*")
        .eq("project_id", projectId!)
        .order("created_at", { ascending: false });
      if (error) throw error;
      return data as VerificationReport[];
    },
  });

export const useCreateVerificationReport = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (report: ReportInsert) => {
      const { data, error } = await supabase.from("verification_reports").insert(report).select().single();
      if (error) throw error;
      return data as VerificationReport;
    },
    onSuccess: (_, variables) =>
      qc.invalidateQueries({ queryKey: ["verification_reports", variables.project_id] }),
  });
};

export const useUpdateVerificationReport = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...updates }: { id: string } & Partial<VerificationReport>) => {
      const { data, error } = await supabase.from("verification_reports").update(updates).eq("id", id).select().single();
      if (error) throw error;
      return data as VerificationReport;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["verification_reports"] }),
  });
};
