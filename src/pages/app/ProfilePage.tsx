import { useState, useEffect } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useProfile, useUpdateProfile } from "@/hooks/use-profile";
import { useAuth } from "@/contexts/AuthContext";
import { useToast } from "@/hooks/use-toast";
import { User, Building, Mail, Save } from "lucide-react";

const ProfilePage = () => {
  const { user, signOut } = useAuth();
  const { data: profile, isLoading } = useProfile();
  const updateProfile = useUpdateProfile();
  const { toast } = useToast();
  const [fullName, setFullName] = useState("");
  const [organization, setOrganization] = useState("");

  useEffect(() => {
    if (profile) {
      setFullName(profile.full_name ?? "");
      setOrganization(profile.organization ?? "");
    }
  }, [profile]);

  const handleSave = async () => {
    try {
      await updateProfile.mutateAsync({ full_name: fullName, organization });
      toast({ title: "Profile updated", description: "Your changes have been saved." });
    } catch {
      toast({ title: "Update failed", variant: "destructive" });
    }
  };

  if (isLoading) {
    return (
      <div className="p-6 flex items-center justify-center">
        <div className="w-6 h-6 border-2 border-accent/30 border-t-accent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="p-6 max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="font-serif text-2xl text-foreground">Profile</h1>
        <p className="text-sm text-muted-foreground mt-1">Manage your personal information</p>
      </div>

      <Card className="p-6 shadow-card space-y-5">
        <div className="flex items-center gap-4 pb-4 border-b border-border">
          <div className="w-16 h-16 rounded-full bg-accent/20 flex items-center justify-center">
            <User className="w-8 h-8 text-accent" />
          </div>
          <div>
            <p className="font-medium text-foreground">{fullName || "No name set"}</p>
            <p className="text-sm text-muted-foreground">{user?.email}</p>
          </div>
        </div>

        <div className="space-y-4">
          <div className="space-y-1.5">
            <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <User className="w-3.5 h-3.5" /> Full Name
            </Label>
            <Input value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Your full name" />
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <Mail className="w-3.5 h-3.5" /> Email
            </Label>
            <Input value={user?.email ?? ""} disabled className="opacity-60" />
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <Building className="w-3.5 h-3.5" /> Organization
            </Label>
            <Input value={organization} onChange={(e) => setOrganization(e.target.value)} placeholder="Your organization" />
          </div>
        </div>

        <div className="flex gap-3 pt-2">
          <Button onClick={handleSave} disabled={updateProfile.isPending}>
            <Save className="w-4 h-4 mr-2" />
            {updateProfile.isPending ? "Saving…" : "Save Changes"}
          </Button>
          <Button variant="outline" onClick={signOut}>
            Sign Out
          </Button>
        </div>
      </Card>

      <p className="text-xs text-muted-foreground text-center">
        Member since {profile?.created_at ? new Date(profile.created_at).toLocaleDateString() : "—"}
      </p>
    </div>
  );
};

export default ProfilePage;
