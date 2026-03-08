import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Index from "./pages/Index";
import About from "./pages/About";
import NotFound from "./pages/NotFound";
import AppLayout from "./components/app/AppLayout";
import AppDashboard from "./pages/app/AppDashboard";
import MyForests from "./pages/app/MyForests";
import Verification from "./pages/app/Verification";
import Settings from "./pages/app/Settings";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Index />} />
          <Route path="/about" element={<About />} />
          <Route path="/app" element={<AppLayout />}>
            <Route index element={<Navigate to="dashboard" replace />} />
            <Route path="dashboard" element={<AppDashboard />} />
            <Route path="forests" element={<MyForests />} />
            <Route path="verification" element={<Verification />} />
            <Route path="settings" element={<Settings />} />
          </Route>
          <Route path="/dashboard" element={<Navigate to="/app/dashboard" replace />} />
          <Route path="/mrv" element={<Navigate to="/app/dashboard" replace />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
