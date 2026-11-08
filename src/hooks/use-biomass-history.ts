import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch, unwrapList, type Paginated } from "@/lib/api";

export interface BiomassHistory {
  id: string;
  project_id: string;
  recorded_at: string;
  carbon_density: number;
  health_score: number;
  source_url: string | null;
  created_at: string;
}

type BiomassInsert = Pick<BiomassHistory, "project_id" | "carbon_density" | "health_score"> & {
  source_url?: string | null;
};

export const useBiomassHistory = (projectId: string | undefined) =>
  useQuery({
    queryKey: ["biomass_history", projectId],
    enabled: !!projectId,
    queryFn: async () => {
      const data = await apiFetch<Paginated<BiomassHistory> | BiomassHistory[]>(
        `/api/biomass-history/?project_id=${projectId}`,
      );
      return unwrapList(data);
    },
  });

export const useCreateBiomassEntry = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (entry: BiomassInsert) =>
      apiFetch<BiomassHistory>("/api/biomass-history/", {
        method: "POST",
        body: JSON.stringify(entry),
      }),
    onSuccess: (_, variables) =>
      qc.invalidateQueries({ queryKey: ["biomass_history", variables.project_id] }),
  });
};
