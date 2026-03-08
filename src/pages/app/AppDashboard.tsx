import MRVDashboard from "@/pages/mrv/MRVDashboard";
import { CarbonFeed } from "@/components/app/CarbonFeed";

const AppDashboard = () => {
  return (
    <div className="space-y-6 p-6 max-w-7xl mx-auto">
      <MRVDashboard />
      <CarbonFeed />
    </div>
  );
};

export default AppDashboard;
