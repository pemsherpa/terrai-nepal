import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "@/contexts/AuthContext";
import ProtectedRoute from "@/components/ProtectedRoute";
import Index from "./pages/Index";
import About from "./pages/About";
import Auth from "./pages/Auth";
import NotFound from "./pages/NotFound";
import AppLayout from "./components/app/AppLayout";
import AppDashboard from "./pages/app/AppDashboard";
import MyForests from "./pages/app/MyForests";
import Verification from "./pages/app/Verification";
import Settings from "./pages/app/Settings";
import ProfilePage from "./pages/app/ProfilePage";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <AuthProvider>
      <TooltipProvider>
        <Toaster />
        <Sonner />
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Index />} />
            <Route path="/about" element={<About />} />
            <Route path="/auth" element={<Auth />} />
            <Route path="/app" element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
              <Route index element={<Navigate to="dashboard" replace />} />
              <Route path="dashboard" element={<AppDashboard />} />
              <Route path="forests" element={<MyForests />} />
              <Route path="verification" element={<Verification />} />
              <Route path="settings" element={<Settings />} />
              <Route path="profile" element={<ProfilePage />} />
            </Route>
            <Route path="/dashboard" element={<Navigate to="/app/dashboard" replace />} />
            <Route path="/mrv" element={<Navigate to="/app/dashboard" replace />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </BrowserRouter>
      </TooltipProvider>
    </AuthProvider>
  </QueryClientProvider>
);

export default App;
