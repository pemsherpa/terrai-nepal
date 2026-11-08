import { BarChart3, TreePine, FileCheck, Settings, Home, User, LogOut, Network, GitCompare, ScanSearch, Database, ExternalLink } from "lucide-react";
import { NavLink } from "@/components/NavLink";
import { useLocation } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@/components/ui/sidebar";

const navItems = [
  { title: "Dashboard", url: "/app/dashboard", icon: BarChart3 },
  { title: "My Forests", url: "/app/forests", icon: TreePine },
  { title: "Verification", url: "/app/verification", icon: FileCheck },
  { title: "Settings", url: "/app/settings", icon: Settings },
];

const visionItems = [
  { title: "U-Net segmentation", href: "/app/dashboard#unet", icon: ScanSearch, term: "U-Net" },
  { title: "Siamese change detection", href: "/app/dashboard#siamese", icon: GitCompare, term: "Siamese" },
  { title: "Vision Transformer", href: "/app/dashboard#vision-transformer", icon: Network, term: "Swin Transformer" },
];

const datasetItems = [
  { title: "ICIMOD RDS / SERVIR-HKH", href: "https://rds.icimod.org/" },
  { title: "FRTC / NLCMS", href: "https://frtc.gov.np/" },
  { title: "Global Forest Watch", href: "https://www.globalforestwatch.org/" },
  { title: "NASA FIRMS", href: "https://firms.modaps.eosdis.nasa.gov/" },
  { title: "BigEarthNet v2 (S1 + S2)", href: "https://zenodo.org/records/10891137" },
  { title: "EuroSAT (13-band S2)", href: "https://www.tensorflow.org/datasets/catalog/eurosat" },
];

export function AppSidebar() {
  const { state } = useSidebar();
  const collapsed = state === "collapsed";
  const location = useLocation();
  const { user, signOut } = useAuth();

  const isActive = (path: string) => location.pathname === path;

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="p-4">
        <NavLink to="/" className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-sidebar-primary flex items-center justify-center shrink-0">
            <TreePine className="w-4 h-4 text-sidebar-primary-foreground" />
          </div>
          {!collapsed && (
            <span className="font-serif text-lg text-sidebar-foreground tracking-tight">
              TerrAI
            </span>
          )}
        </NavLink>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel className="text-sidebar-foreground/40 text-[10px] uppercase tracking-widest">
            Platform
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {navItems.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton
                    asChild
                    isActive={isActive(item.url)}
                    tooltip={item.title}
                  >
                    <NavLink
                      to={item.url}
                      end
                      className="hover:bg-sidebar-accent/50"
                      activeClassName="bg-sidebar-accent text-sidebar-accent-foreground font-medium"
                    >
                      <item.icon className="h-4 w-4" />
                      {!collapsed && <span>{item.title}</span>}
                    </NavLink>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup>
          <SidebarGroupLabel className="text-sidebar-foreground/40 text-[10px] uppercase tracking-widest">
            Vision models
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {visionItems.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton asChild tooltip={item.title}>
                    <a href={item.href} className="hover:bg-sidebar-accent/50">
                      <item.icon className="h-4 w-4" />
                      {!collapsed && <span>{item.title}</span>}
                    </a>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup>
          <SidebarGroupLabel className="text-sidebar-foreground/40 text-[10px] uppercase tracking-widest">
            Training datasets
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {datasetItems.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton asChild tooltip={item.title}>
                    <a href={item.href} target="_blank" rel="noreferrer" className="hover:bg-sidebar-accent/50">
                      <Database className="h-4 w-4" />
                      {!collapsed && (
                        <>
                          <span className="truncate">{item.title}</span>
                          <ExternalLink className="ml-auto h-3 w-3 shrink-0 opacity-60" />
                        </>
                      )}
                    </a>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="p-3">
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton asChild tooltip="Profile" isActive={isActive("/app/profile")}>
              <NavLink to="/app/profile" className="hover:bg-sidebar-accent/50">
                <User className="h-4 w-4" />
                {!collapsed && <span className="text-sm">{user?.email?.split("@")[0] ?? "Profile"}</span>}
              </NavLink>
            </SidebarMenuButton>
          </SidebarMenuItem>
          <SidebarMenuItem>
            <SidebarMenuButton asChild tooltip="Back to Home">
              <NavLink to="/" className="hover:bg-sidebar-accent/50 text-sidebar-foreground/60">
                <Home className="h-4 w-4" />
                {!collapsed && <span className="text-sm">Back to Home</span>}
              </NavLink>
            </SidebarMenuButton>
          </SidebarMenuItem>
          <SidebarMenuItem>
            <SidebarMenuButton tooltip="Sign Out" onClick={signOut} className="hover:bg-sidebar-accent/50 text-sidebar-foreground/60 cursor-pointer">
              <LogOut className="h-4 w-4" />
              {!collapsed && <span className="text-sm">Sign Out</span>}
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  );
}
