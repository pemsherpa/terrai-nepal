import { Card } from "@/components/ui/card";
import { Settings as SettingsIcon, User, Bell, Shield } from "lucide-react";

const Settings = () => {
  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="font-serif text-2xl text-foreground">Settings</h1>
        <p className="text-sm text-muted-foreground mt-1">Manage your account and preferences</p>
      </div>

      <div className="space-y-4">
        {[
          { icon: User, title: "Profile", desc: "Update your name, email, and organization details" },
          { icon: Bell, title: "Notifications", desc: "Configure alerts for verification updates" },
          { icon: Shield, title: "Security", desc: "Manage password and two-factor authentication" },
        ].map((s) => (
          <Card key={s.title} className="p-5 shadow-card flex items-center gap-4">
            <div className="w-10 h-10 rounded-lg bg-muted flex items-center justify-center shrink-0">
              <s.icon className="w-5 h-5 text-muted-foreground" />
            </div>
            <div>
              <h3 className="font-medium text-foreground">{s.title}</h3>
              <p className="text-sm text-muted-foreground">{s.desc}</p>
            </div>
          </Card>
        ))}
      </div>

      <p className="text-xs text-muted-foreground text-center pt-4">
        Settings functionality coming soon. Authentication required.
      </p>
    </div>
  );
};

export default Settings;
