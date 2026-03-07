import { createContext, useContext, useState, type ReactNode } from "react";
import type { AnalyzeResponse, ReportResponse } from "@/lib/mrv-api";

interface MRVContextValue {
  analysisData: AnalyzeResponse | null;
  setAnalysisData: (data: AnalyzeResponse | null) => void;
  reportData: ReportResponse | null;
  setReportData: (data: ReportResponse | null) => void;
  requestBody: Record<string, unknown> | null;
  setRequestBody: (body: Record<string, unknown> | null) => void;
}

const MRVContext = createContext<MRVContextValue | null>(null);

export const MRVProvider = ({ children }: { children: ReactNode }) => {
  const [analysisData, setAnalysisData] = useState<AnalyzeResponse | null>(null);
  const [reportData, setReportData] = useState<ReportResponse | null>(null);
  const [requestBody, setRequestBody] = useState<Record<string, unknown> | null>(null);

  return (
    <MRVContext.Provider value={{ analysisData, setAnalysisData, reportData, setReportData, requestBody, setRequestBody }}>
      {children}
    </MRVContext.Provider>
  );
};

export const useMRV = () => {
  const ctx = useContext(MRVContext);
  if (!ctx) throw new Error("useMRV must be used within MRVProvider");
  return ctx;
};
