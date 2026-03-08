import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { BarChart3, FileCheck, Download } from "lucide-react";
import { MRVProvider } from "@/contexts/MRVContext";
import MRVDashboard from "@/pages/mrv/MRVDashboard";
import MRVReport from "@/pages/mrv/MRVReport";
import MRVExport from "@/pages/mrv/MRVExport";

const Dashboard = () => {
  return (
    <MRVProvider>
      <div className="min-h-screen bg-background">
        <Navbar />
        <div className="pt-20 pb-16">
          {/* Header */}
          <div className="bg-gradient-hero py-10">
            <div className="container mx-auto px-4">
              <h1 className="font-serif text-3xl text-accent-foreground mb-1">MRV Platform</h1>
              <p className="text-accent-foreground/60 text-sm">
                Measurement, Reporting & Verification — powered by satellite imagery and AI
              </p>
            </div>
          </div>

          <div className="container mx-auto px-4 -mt-6">
            <Tabs defaultValue="dashboard" className="w-full">
              <TabsList className="bg-card shadow-card border border-border mb-6 h-12 p-1">
                <TabsTrigger value="dashboard" className="gap-2 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
                  <BarChart3 className="w-4 h-4" /> Dashboard
                </TabsTrigger>
                <TabsTrigger value="report" className="gap-2 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
                  <FileCheck className="w-4 h-4" /> AI Due Diligence
                </TabsTrigger>
                <TabsTrigger value="export" className="gap-2 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
                  <Download className="w-4 h-4" /> Export Center
                </TabsTrigger>
              </TabsList>

              <TabsContent value="dashboard">
                <MRVDashboard />
              </TabsContent>
              <TabsContent value="report">
                <MRVReport />
              </TabsContent>
              <TabsContent value="export">
                <MRVExport />
              </TabsContent>
            </Tabs>
          </div>
        </div>
        <Footer />
      </div>
    </MRVProvider>
  );
};

export default Dashboard;
