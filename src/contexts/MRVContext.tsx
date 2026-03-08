import { createContext, useContext, useState, type ReactNode } from "react";
import type { AnalyzeResponse, ReportResponse, AnalyzeRequest } from "@/lib/mrv-api";

interface MRVContextValue {
  analysisData: AnalyzeResponse | null;
  setAnalysisData: (data: AnalyzeResponse | null) => void;
  reportData: ReportResponse | null;
  setReportData: (data: ReportResponse | null) => void;
  reportLoading: boolean;
  setReportLoading: (loading: boolean) => void;
  requestBody: AnalyzeRequest | null;
  setRequestBody: (body: AnalyzeRequest | null) => void;
  locationName: string;
  setLocationName: (name: string) => void;
}

const MRVContext = createContext<MRVContextValue | null>(null);

export const MRVProvider = ({ children }: { children: ReactNode }) => {
  const [analysisData, setAnalysisData] = useState<AnalyzeResponse | null>(null);
  const [reportData, setReportData] = useState<ReportResponse | null>(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [requestBody, setRequestBody] = useState<AnalyzeRequest | null>(null);
  const [locationName, setLocationName] = useState("");

  return (
    <MRVContext.Provider value={{ analysisData, setAnalysisData, reportData, setReportData, reportLoading, setReportLoading, requestBody, setRequestBody, locationName, setLocationName }}>
      {children}
    </MRVContext.Provider>
  );
};

export const useMRV = () => {
  const ctx = useContext(MRVContext);
  if (!ctx) throw new Error("useMRV must be used within MRVProvider");
  return ctx;
};
