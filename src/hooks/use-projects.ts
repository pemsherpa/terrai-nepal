import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";
import type { Database } from "@/integrations/supabase/types";

type Project = Database["public"]["Tables"]["projects"]["Row"];
type ProjectInsert = Database["public"]["Tables"]["projects"]["Insert"];

export const useProjects = () =>
  useQuery({
    queryKey: ["projects"],
    queryFn: async () => {
      const { data, error } = await supabase.from("projects").select("*").order("created_at", { ascending: false });
      if (error) throw error;
      return data as Project[];
    },
  });

export const useProject = (id: string | undefined) =>
  useQuery({
    queryKey: ["projects", id],
    enabled: !!id,
    queryFn: async () => {
      const { data, error } = await supabase.from("projects").select("*").eq("id", id!).single();
      if (error) throw error;
      return data as Project;
    },
  });

export const useCreateProject = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (project: Omit<ProjectInsert, "owner_id">) => {
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) throw new Error("Not authenticated");
      const { data, error } = await supabase.from("projects").insert({ ...project, owner_id: user.id }).select().single();
      if (error) throw error;
      return data as Project;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["projects"] }),
  });
};

export const useUpdateProject = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...updates }: { id: string } & Partial<ProjectInsert>) => {
      const { data, error } = await supabase.from("projects").update(updates).eq("id", id).select().single();
      if (error) throw error;
      return data as Project;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["projects"] }),
  });
};

export const useDeleteProject = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { error } = await supabase.from("projects").delete().eq("id", id);
      if (error) throw error;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["projects"] }),
  });
};
