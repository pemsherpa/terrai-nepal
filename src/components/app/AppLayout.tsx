import { Outlet } from "react-router-dom";
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { AppSidebar } from "./AppSidebar";
import { MRVProvider } from "@/contexts/MRVContext";

export default function AppLayout() {
  return (
    <MRVProvider>
      <SidebarProvider>
        <div className="min-h-screen flex w-full">
          <AppSidebar />
          <div className="flex-1 flex flex-col min-w-0">
            <header className="h-14 flex items-center border-b border-border bg-background/80 backdrop-blur-sm px-4 shrink-0">
              <SidebarTrigger className="mr-3" />
              <span className="text-sm font-medium text-muted-foreground">MRV Platform</span>
            </header>
            <main className="flex-1 overflow-auto">
              <Outlet />
            </main>
          </div>
        </div>
      </SidebarProvider>
    </MRVProvider>
  );
}
