import { useProjects, useCreateProject, useDeleteProject, useUpdateProject } from "@/hooks/use-projects";
import { useOrganizations, useCreateOrganization, useAddOrgMember, useOrgMembers } from "@/hooks/use-organizations";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { TreePine, Plus, MapPin, Ruler, Trash2, Loader2, Building2, UserPlus, FlaskConical } from "lucide-react";
import { useState } from "react";
import { useToast } from "@/hooks/use-toast";
import { formatDistanceToNow } from "date-fns";

const MyForests = () => {
  const { data: projects, isLoading } = useProjects();
  const { data: orgs } = useOrganizations();
  const createProject = useCreateProject();
  const updateProject = useUpdateProject();
  const deleteProject = useDeleteProject();
  const createOrg = useCreateOrganization();
  const { toast } = useToast();
  const [open, setOpen] = useState(false);
  const [orgOpen, setOrgOpen] = useState(false);
  const [memberOpen, setMemberOpen] = useState(false);
  const [calibOpen, setCalibOpen] = useState(false);
  const [calibProjectId, setCalibProjectId] = useState<string>("");
  const [calibForm, setCalibForm] = useState({
    field_baseline_agb_t_ha: "",
    satellite_agb_at_calibration: "",
    calibration_coefficient: "",
    calibration_notes: "",
  });
  const [orgName, setOrgName] = useState("");
  const [memberEmail, setMemberEmail] = useState("");
  const [memberRole, setMemberRole] = useState("member");
  const [selectedOrgId, setSelectedOrgId] = useState<string>("");
  const [form, setForm] = useState({
    name: "",
    latitude: "",
    longitude: "",
    area_hectares: "",
    organization_id: "" as string,
  });

  const manageOrgId = selectedOrgId ? Number(selectedOrgId) : orgs?.[0]?.id;
  const addMember = useAddOrgMember(manageOrgId || 0);
  const { data: members } = useOrgMembers(manageOrgId);

  const handleCreate = async () => {
    if (!form.name || !form.latitude || !form.longitude) return;
    try {
      await createProject.mutateAsync({
        name: form.name,
        latitude: parseFloat(form.latitude),
        longitude: parseFloat(form.longitude),
        area_hectares: parseFloat(form.area_hectares) || 0,
        organization_id: form.organization_id ? Number(form.organization_id) : null,
      });
      setForm({ name: "", latitude: "", longitude: "", area_hectares: "", organization_id: "" });
      setOpen(false);
      toast({ title: "Forest project created" });
    } catch {
      toast({ title: "Failed to create project", variant: "destructive" });
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteProject.mutateAsync(id);
      toast({ title: "Project deleted" });
    } catch {
      toast({ title: "Failed to delete project", variant: "destructive" });
    }
  };

  const handleCreateOrg = async () => {
    if (!orgName.trim()) return;
    try {
      const org = await createOrg.mutateAsync(orgName.trim());
      setOrgName("");
      setOrgOpen(false);
      setSelectedOrgId(String(org.id));
      toast({ title: "Organization created", description: "Invite field team members next." });
    } catch {
      toast({ title: "Failed to create organization", variant: "destructive" });
    }
  };

  const handleAddMember = async () => {
    if (!manageOrgId || !memberEmail.trim()) return;
    try {
      await addMember.mutateAsync({ email: memberEmail.trim(), role: memberRole });
      setMemberEmail("");
      setMemberOpen(false);
      toast({ title: "Team member added" });
    } catch (err) {
      toast({
        title: "Could not add member",
        description: err instanceof Error ? err.message : "User must already have an account.",
        variant: "destructive",
      });
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="font-serif text-2xl text-foreground">My Forests</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Personal and organization projects — NGO managers see the whole field team
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Dialog open={orgOpen} onOpenChange={setOrgOpen}>
            <DialogTrigger asChild>
              <Button variant="outline" className="gap-2">
                <Building2 className="w-4 h-4" /> New Org
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader><DialogTitle>Create organization</DialogTitle></DialogHeader>
              <div className="space-y-3 pt-2">
                <Label>NGO / team name</Label>
                <Input value={orgName} onChange={(e) => setOrgName(e.target.value)} placeholder="e.g. Himalayan CFUG Network" />
                <Button onClick={handleCreateOrg} disabled={createOrg.isPending}>Create</Button>
              </div>
            </DialogContent>
          </Dialog>

          <Dialog open={memberOpen} onOpenChange={setMemberOpen}>
            <DialogTrigger asChild>
              <Button variant="outline" className="gap-2" disabled={!manageOrgId}>
                <UserPlus className="w-4 h-4" /> Invite member
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader><DialogTitle>Add field team member</DialogTitle></DialogHeader>
              <div className="space-y-3 pt-2">
                {orgs && orgs.length > 1 && (
                  <div className="space-y-1.5">
                    <Label>Organization</Label>
                    <Select value={selectedOrgId || String(manageOrgId)} onValueChange={setSelectedOrgId}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {orgs.map((o) => <SelectItem key={o.id} value={String(o.id)}>{o.name}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                )}
                <div className="space-y-1.5">
                  <Label>Member email (must already have an account)</Label>
                  <Input value={memberEmail} onChange={(e) => setMemberEmail(e.target.value)} placeholder="field@ngo.org" />
                </div>
                <div className="space-y-1.5">
                  <Label>Role</Label>
                  <Select value={memberRole} onValueChange={setMemberRole}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="member">Member (field team)</SelectItem>
                      <SelectItem value="manager">Manager</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <Button onClick={handleAddMember} disabled={addMember.isPending}>Add to org</Button>
                {members && members.length > 0 && (
                  <div className="text-xs text-muted-foreground space-y-1 pt-2 border-t">
                    {members.map((m) => (
                      <div key={m.id}>{m.full_name || m.email} · {m.role}</div>
                    ))}
                  </div>
                )}
              </div>
            </DialogContent>
          </Dialog>

          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button className="gap-2">
                <Plus className="w-4 h-4" /> Add Forest
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>New Forest Project</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 pt-2">
                <div className="space-y-1.5">
                  <Label>Project Name</Label>
                  <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="e.g. Chitwan Buffer Zone" />
                </div>
                {orgs && orgs.length > 0 && (
                  <div className="space-y-1.5">
                    <Label>Organization (optional)</Label>
                    <Select
                      value={form.organization_id || "none"}
                      onValueChange={(v) => setForm({ ...form, organization_id: v === "none" ? "" : v })}
                    >
                      <SelectTrigger><SelectValue placeholder="Personal project" /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">Personal (no org)</SelectItem>
                        {orgs.map((o) => <SelectItem key={o.id} value={String(o.id)}>{o.name}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                )}
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1.5">
                    <Label>Latitude</Label>
                    <Input value={form.latitude} onChange={(e) => setForm({ ...form, latitude: e.target.value })} placeholder="27.5" />
                  </div>
                  <div className="space-y-1.5">
                    <Label>Longitude</Label>
                    <Input value={form.longitude} onChange={(e) => setForm({ ...form, longitude: e.target.value })} placeholder="84.3" />
                  </div>
                </div>
                <div className="space-y-1.5">
                  <Label>Area (hectares)</Label>
                  <Input value={form.area_hectares} onChange={(e) => setForm({ ...form, area_hectares: e.target.value })} placeholder="100" />
                </div>
                <Button onClick={handleCreate} disabled={createProject.isPending} className="w-full">
                  {createProject.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : "Create project"}
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {orgs && orgs.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {orgs.map((o) => (
            <Badge key={o.id} variant="outline" className="gap-1">
              <Building2 className="w-3 h-3" /> {o.name} · {o.my_role} · {o.member_count} members
            </Badge>
          ))}
        </div>
      )}

      {isLoading ? (
        <div className="flex justify-center py-20"><Loader2 className="w-6 h-6 animate-spin text-muted-foreground" /></div>
      ) : !projects?.length ? (
        <div className="text-center py-20">
          <TreePine className="w-16 h-16 mx-auto text-muted-foreground/20 mb-4" />
          <p className="text-muted-foreground">No forest projects yet. Create one or join an organization.</p>
        </div>
      ) : (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.map((p) => (
            <Card key={p.id} className="p-5 shadow-card space-y-3">
              <div className="flex items-start justify-between gap-2">
                <h3 className="font-serif text-lg">{p.name}</h3>
                <Button variant="ghost" size="icon" onClick={() => handleDelete(p.id)}>
                  <Trash2 className="w-4 h-4 text-muted-foreground" />
                </Button>
              </div>
              {p.organization_name && (
                <Badge variant="secondary" className="text-xs">{p.organization_name}</Badge>
              )}
              <div className="text-sm text-muted-foreground space-y-1">
                <div className="flex items-center gap-2"><MapPin className="w-3.5 h-3.5" />{p.latitude.toFixed(4)}, {p.longitude.toFixed(4)}</div>
                <div className="flex items-center gap-2"><Ruler className="w-3.5 h-3.5" />{p.area_hectares} ha</div>
                {(p.field_baseline_agb_t_ha != null || (p.calibration_coefficient != null && p.calibration_coefficient !== 1)) && (
                  <div className="flex items-center gap-2 text-xs text-foreground/80">
                    <FlaskConical className="w-3.5 h-3.5" />
                    Field AGB {p.field_baseline_agb_t_ha ?? "—"} t/ha · coeff {p.calibration_coefficient ?? 1}
                  </div>
                )}
                <div className="text-xs">Updated {formatDistanceToNow(new Date(p.updated_at), { addSuffix: true })}</div>
              </div>
              <Button
                variant="outline"
                size="sm"
                className="w-full"
                onClick={() => {
                  setCalibProjectId(p.id);
                  setCalibForm({
                    field_baseline_agb_t_ha: p.field_baseline_agb_t_ha != null ? String(p.field_baseline_agb_t_ha) : "",
                    satellite_agb_at_calibration: "",
                    calibration_coefficient: p.calibration_coefficient != null ? String(p.calibration_coefficient) : "1",
                    calibration_notes: p.calibration_notes || "",
                  });
                  setCalibOpen(true);
                }}
              >
                <FlaskConical className="w-3.5 h-3.5 mr-1.5" /> Field calibration
              </Button>
            </Card>
          ))}
        </div>
      )}

      <Dialog open={calibOpen} onOpenChange={setCalibOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Field inventory calibration</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            Upload a CFUG / consultant AGB baseline (t/ha). Optionally pass the matching satellite AGB to auto-set
            coefficient = field ÷ satellite. Final biomass = satellite × coefficient.
          </p>
          <div className="space-y-3 pt-2">
            <div className="space-y-1.5">
              <Label>Field baseline AGB (t/ha)</Label>
              <Input
                value={calibForm.field_baseline_agb_t_ha}
                onChange={(e) => setCalibForm({ ...calibForm, field_baseline_agb_t_ha: e.target.value })}
                placeholder="e.g. 180"
              />
            </div>
            <div className="space-y-1.5">
              <Label>Satellite AGB at calibration (t/ha, optional)</Label>
              <Input
                value={calibForm.satellite_agb_at_calibration}
                onChange={(e) => setCalibForm({ ...calibForm, satellite_agb_at_calibration: e.target.value })}
                placeholder="From last analyze — auto-computes coefficient"
              />
            </div>
            <div className="space-y-1.5">
              <Label>Calibration coefficient (optional override)</Label>
              <Input
                value={calibForm.calibration_coefficient}
                onChange={(e) => setCalibForm({ ...calibForm, calibration_coefficient: e.target.value })}
                placeholder="1.0"
              />
            </div>
            <div className="space-y-1.5">
              <Label>Notes</Label>
              <Input
                value={calibForm.calibration_notes}
                onChange={(e) => setCalibForm({ ...calibForm, calibration_notes: e.target.value })}
                placeholder="DBH survey date, CFUG name…"
              />
            </div>
            <Button
              className="w-full"
              disabled={updateProject.isPending || !calibProjectId}
              onClick={async () => {
                try {
                  const payload: Record<string, unknown> = {
                    id: calibProjectId,
                    calibration_notes: calibForm.calibration_notes,
                  };
                  if (calibForm.field_baseline_agb_t_ha) {
                    payload.field_baseline_agb_t_ha = parseFloat(calibForm.field_baseline_agb_t_ha);
                  }
                  if (calibForm.satellite_agb_at_calibration) {
                    payload.satellite_agb_at_calibration = parseFloat(calibForm.satellite_agb_at_calibration);
                  }
                  if (calibForm.calibration_coefficient) {
                    payload.calibration_coefficient = parseFloat(calibForm.calibration_coefficient);
                  }
                  await updateProject.mutateAsync(payload as { id: string } & Partial<import("@/hooks/use-projects").Project>);
                  toast({ title: "Calibration saved" });
                  setCalibOpen(false);
                } catch (err) {
                  toast({
                    title: "Calibration failed",
                    description: err instanceof Error ? err.message : "Request failed",
                    variant: "destructive",
                  });
                }
              }}
            >
              {updateProject.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : "Save calibration"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default MyForests;
