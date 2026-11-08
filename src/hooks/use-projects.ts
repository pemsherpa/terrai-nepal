import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch, unwrapList, type Paginated } from "@/lib/api";

export interface Project {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
  area_hectares: number;
  owner_id: number;
  organization_id?: number | null;
  organization_name?: string | null;
  field_baseline_agb_t_ha?: number | null;
  calibration_coefficient?: number;
  calibration_notes?: string;
  calibration_updated_at?: string | null;
  created_at: string;
  updated_at: string;
}

type ProjectInsert = Omit<
  Project,
  "id" | "owner_id" | "organization_name" | "created_at" | "updated_at" | "calibration_updated_at"
> & {
  satellite_agb_at_calibration?: number | null;
};

export const useProjects = () =>
  useQuery({
    queryKey: ["projects"],
    queryFn: async () => {
      const data = await apiFetch<Paginated<Project> | Project[]>("/api/projects/");
      return unwrapList(data);
    },
  });

export const useProject = (id: string | undefined) =>
  useQuery({
    queryKey: ["projects", id],
    enabled: !!id,
    queryFn: () => apiFetch<Project>(`/api/projects/${id}/`),
  });

export const useCreateProject = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (project: ProjectInsert) =>
      apiFetch<Project>("/api/projects/", {
        method: "POST",
        body: JSON.stringify(project),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["projects"] }),
  });
};

export const useUpdateProject = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...updates }: { id: string } & Partial<ProjectInsert>) =>
      apiFetch<Project>(`/api/projects/${id}/`, {
        method: "PATCH",
        body: JSON.stringify(updates),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["projects"] }),
  });
};

export const useDeleteProject = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch<void>(`/api/projects/${id}/`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["projects"] }),
  });
};
