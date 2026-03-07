import { BarChart3, FileCheck, Download, Leaf } from "lucide-react";
import { NavLink } from "@/components/NavLink";
import { useLocation } from "react-router-dom";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarHeader,
  SidebarFooter,
  useSidebar,
} from "@/components/ui/sidebar";

const navItems = [
  { title: "Dashboard", url: "/mrv/dashboard", icon: BarChart3 },
  { title: "AI Due Diligence", url: "/mrv/report", icon: FileCheck },
  { title: "Export Center", url: "/mrv/export", icon: Download },
];

export function MRVSidebar() {
  const { state } = useSidebar();
  const collapsed = state === "collapsed";
  const location = useLocation();

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="p-4">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-sidebar-accent flex items-center justify-center shrink-0">
            <Leaf className="w-4 h-4 text-sidebar-accent-foreground" />
          </div>
          {!collapsed && (
            <div>
              <div className="font-serif text-base text-sidebar-foreground leading-tight">TerrAI</div>
              <div className="text-[10px] uppercase tracking-widest text-sidebar-foreground/50">MRV Platform</div>
            </div>
          )}
        </div>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel className="text-sidebar-foreground/40">Navigation</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {navItems.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton asChild>
                    <NavLink
                      to={item.url}
                      end
                      className="hover:bg-sidebar-accent/60 transition-colors"
                      activeClassName="bg-sidebar-accent text-sidebar-accent-foreground font-medium"
                    >
                      <item.icon className="mr-2 h-4 w-4" />
                      {!collapsed && <span>{item.title}</span>}
                    </NavLink>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="p-4">
        {!collapsed && (
          <NavLink to="/" className="text-xs text-sidebar-foreground/40 hover:text-sidebar-foreground/70 transition-colors">
            ← Back to Home
          </NavLink>
        )}
      </SidebarFooter>
    </Sidebar>
  );
}
