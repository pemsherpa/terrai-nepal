

## Analysis: Already Implemented

After reviewing the codebase, **all three requested features are already fully implemented**:

### A. `analyzeForest` — `POST /api/analyze`
- **API function**: `src/lib/mrv-api.ts` lines 41-49 — sends the exact payload you described to `http://localhost:8000/api/analyze`
- **UI wiring**: `src/pages/mrv/MRVDashboard.tsx` line 56 — called on "Analyse Forest" click, populates stat cards (NDVI year1/year2, change %, area), Carbon Stock panel, and Recharts charts (ndvi_trend, monthly_ndvi)
- **Loading state**: Spinner shown on button while `loading` is true
- **Error handling**: Toast notification on failure with error message

### B. `generateReport` — `POST /api/report/generate`
- **API function**: `src/lib/mrv-api.ts` lines 51-58
- **UI wiring**: Called automatically after successful analysis (MRVDashboard line 75), or manually via button in `MRVReport.tsx`. Populates Executive Summary, Key Findings, Risk Level badge, Risk Details, and Recommendations
- **Loading state**: Loader2 spinner on generate button
- **Error handling**: Toast on failure

### C. `downloadPdf` — `POST /api/export/pdf`
- **API function**: `src/lib/mrv-api.ts` lines 61-77 — already handles Blob response, creates temporary `<a>` tag, sets `download="TerrAI_Report.pdf"`, triggers click
- **UI wiring**: `MRVExport.tsx` line 32 — wired to "Download PDF Report" button
- **Loading/disabled state**: Button disabled while downloading, shows spinner
- **Error handling**: Toast on failure

### State & UX
- **MRVContext** shares `analysisData`, `reportData`, and `requestBody` across Dashboard, Report, and Export tabs
- **Skeleton/empty states**: Each page shows placeholder with icon when no data exists
- **Toast notifications**: All three endpoints catch errors and display destructive toasts via the existing `useToast` hook
- **PDF button disabled logic**: Export page already returns early with a "run analysis first" message when `analysisData` is null

### What's Missing (minor enhancement opportunities)

1. **PDF button not disabled when report is missing** — currently the Export page only checks for `analysisData`, not `reportData`. If you want the PDF button disabled until *both* analysis and report are loaded, that's a small change.
2. **Skeleton loaders** — the dashboard shows a spinner on the button but doesn't show skeleton placeholders for the cards/charts area while loading. Could add `Skeleton` components during the loading phase.
3. **Report generation loading on dashboard** — report generates silently in background; no visible indicator that the AI report is still generating.

### Recommended Plan (if you want enhancements)

Since the core wiring is complete, I can make these targeted improvements:

1. **Add skeleton loaders** to MRVDashboard — show pulsing card placeholders while analysis is in-flight
2. **Add `reportLoading` state** to MRVContext so the Export page can disable the PDF button until both analysis AND report are ready
3. **Show a "Report generating..." indicator** on the Dashboard after analysis completes, so users know the AI report is being prepared in the background

These are ~3 small file edits. Want me to proceed with these enhancements, or is there something else about the backend integration that isn't working as expected?

