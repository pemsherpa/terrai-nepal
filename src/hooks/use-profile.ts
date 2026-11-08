import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch, unwrapList } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";

export interface Profile {
  id: number;
  email: string;
  full_name: string | null;
  organization: string | null;
  avatar_url: string | null;
  created_at: string;
  updated_at: string;
}

export const useProfile = () => {
  const { user } = useAuth();
  return useQuery({
    queryKey: ["profile", user?.id],
    enabled: !!user,
    queryFn: () => apiFetch<Profile>("/api/auth/profile/me/"),
  });
};

export const useUpdateProfile = () => {
  const { user } = useAuth();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (updates: { full_name?: string; organization?: string; avatar_url?: string }) =>
      apiFetch<Profile>("/api/auth/profile/me/", {
        method: "PATCH",
        body: JSON.stringify(updates),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["profile", user?.id] }),
  });
};
