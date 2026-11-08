import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";

export interface Organization {
  id: number;
  name: string;
  slug: string;
  my_role: "owner" | "manager" | "member" | null;
  member_count: number;
  created_at: string;
  updated_at: string;
}

export interface OrgMember {
  id: number;
  user_id: number;
  email: string;
  full_name: string;
  role: "owner" | "manager" | "member";
  created_at: string;
}

export const useOrganizations = () =>
  useQuery({
    queryKey: ["organizations"],
    queryFn: () => apiFetch<Organization[]>("/api/auth/organizations/"),
  });

export const useCreateOrganization = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (name: string) =>
      apiFetch<Organization>("/api/auth/organizations/", {
        method: "POST",
        body: JSON.stringify({ name }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["organizations"] }),
  });
};

export const useOrgMembers = (orgId: number | undefined) =>
  useQuery({
    queryKey: ["organizations", orgId, "members"],
    enabled: !!orgId,
    queryFn: () => apiFetch<OrgMember[]>(`/api/auth/organizations/${orgId}/members/`),
  });

export const useAddOrgMember = (orgId: number) => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { email: string; role?: string }) =>
      apiFetch<OrgMember>(`/api/auth/organizations/${orgId}/members/`, {
        method: "POST",
        body: JSON.stringify(body),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["organizations", orgId, "members"] }),
  });
};
