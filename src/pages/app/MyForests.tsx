import { useProjects, useCreateProject, useDeleteProject } from "@/hooks/use-projects";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { TreePine, Plus, MapPin, Ruler, Trash2, Loader2 } from "lucide-react";
import { useState } from "react";
import { useToast } from "@/hooks/use-toast";
import { formatDistanceToNow } from "date-fns";

const MyForests = () => {
  const { data: projects, isLoading } = useProjects();
  const createProject = useCreateProject();
  const deleteProject = useDeleteProject();
  const { toast } = useToast();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ name: "", latitude: "", longitude: "", area_hectares: "" });

  const handleCreate = async () => {
    if (!form.name || !form.latitude || !form.longitude) return;
    try {
      await createProject.mutateAsync({
        name: form.name,
        latitude: parseFloat(form.latitude),
        longitude: parseFloat(form.longitude),
        area_hectares: parseFloat(form.area_hectares) || 0,
      });
      setForm({ name: "", latitude: "", longitude: "", area_hectares: "" });
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

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-serif text-2xl text-foreground">My Forests</h1>
          <p className="text-sm text-muted-foreground mt-1">Manage your forest monitoring projects</p>
        </div>
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
                <Input value={form.area_hectares} onChange={(e) => setForm({ ...form, area_hectares: e.target.value })} placeholder="500" />
              </div>
              <Button onClick={handleCreate} className="w-full" disabled={createProject.isPending}>
                {createProject.isPending ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                Create Project
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {isLoading ? (
        <div className="text-center py-16 text-muted-foreground">Loading projects…</div>
      ) : !projects?.length ? (
        <div className="text-center py-20">
          <TreePine className="w-16 h-16 mx-auto text-muted-foreground/20 mb-4" />
          <p className="text-muted-foreground">No forest projects yet. Click <strong>Add Forest</strong> to get started.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.map((p) => (
            <Card key={p.id} className="p-5 shadow-card hover:shadow-elevated transition-shadow">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-lg bg-accent/10 flex items-center justify-center">
                    <TreePine className="w-4 h-4 text-accent" />
                  </div>
                  <h3 className="font-serif text-lg text-foreground">{p.name}</h3>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-muted-foreground hover:text-destructive"
                  onClick={() => handleDelete(p.id)}
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </Button>
              </div>
              <div className="space-y-2 text-sm">
                <div className="flex items-center gap-2 text-muted-foreground">
                  <MapPin className="w-3.5 h-3.5" />
                  <span>{p.latitude}°N, {p.longitude}°E</span>
                </div>
                <div className="flex items-center gap-2 text-muted-foreground">
                  <Ruler className="w-3.5 h-3.5" />
                  <span>{p.area_hectares} hectares</span>
                </div>
              </div>
              <div className="mt-3 pt-3 border-t border-border">
                <Badge variant="outline" className="text-xs text-muted-foreground">
                  Created {formatDistanceToNow(new Date(p.created_at), { addSuffix: true })}
                </Badge>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};

export default MyForests;
