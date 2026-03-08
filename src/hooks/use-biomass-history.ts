import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";
import type { Database } from "@/integrations/supabase/types";

type BiomassHistory = Database["public"]["Tables"]["biomass_history"]["Row"];
type BiomassInsert = Database["public"]["Tables"]["biomass_history"]["Insert"];

export const useBiomassHistory = (projectId: string | undefined) =>
  useQuery({
    queryKey: ["biomass_history", projectId],
    enabled: !!projectId,
    queryFn: async () => {
      const { data, error } = await supabase
        .from("biomass_history")
        .select("*")
        .eq("project_id", projectId!)
        .order("recorded_at", { ascending: true });
      if (error) throw error;
      return data as BiomassHistory[];
    },
  });

export const useCreateBiomassEntry = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (entry: BiomassInsert) => {
      const { data, error } = await supabase.from("biomass_history").insert(entry).select().single();
      if (error) throw error;
      return data as BiomassHistory;
    },
    onSuccess: (_, variables) =>
      qc.invalidateQueries({ queryKey: ["biomass_history", variables.project_id] }),
  });
};
