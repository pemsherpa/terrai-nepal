import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { MRVSidebar } from "./MRVSidebar";
import { Outlet } from "react-router-dom";

const MRVLayout = () => {
  return (
    <SidebarProvider>
      <div className="min-h-screen flex w-full bg-background">
        <MRVSidebar />
        <div className="flex-1 flex flex-col min-w-0">
          <header className="h-14 flex items-center border-b border-border bg-card px-4 gap-3 shrink-0">
            <SidebarTrigger />
            <div className="flex items-center gap-2">
              <span className="font-serif text-lg text-primary">TerrAI</span>
              <span className="text-xs text-muted-foreground font-medium tracking-wider uppercase">MRV Platform</span>
            </div>
          </header>
          <main className="flex-1 overflow-auto">
            <Outlet />
          </main>
        </div>
      </div>
    </SidebarProvider>
  );
};

export default MRVLayout;
