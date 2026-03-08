

## Plan: Premium "Dark Forest" Redesign with Sidebar Navigation and Global Carbon Feed

### Overview
Restructure the app from the current tabs-based dashboard into a sidebar-driven layout with four sections, apply a dark forest theme throughout, add a real-time Global Carbon Feed, and ensure full mobile responsiveness.

### 1. Theme Overhaul (`src/index.css`)
- Replace current CSS custom properties with a dark forest palette:
  - Background: `#064e3b` (emerald-900), card surfaces: `#0f766e`/`#115e59`
  - Text: white/slate-200, muted: slate-400
  - Accent: `#34d399` (emerald-400)
- Keep both light and dark modes mapped to the dark forest palette (the app IS dark by default)
- Update `--gradient-hero` to use deeper emerald tones

### 2. Routing Restructure (`src/App.tsx`)
- Replace the flat `/dashboard` route with a sidebar layout at `/app/*`:
  - `/app/dashboard` - Main MRV Dashboard (analysis + carbon feed)
  - `/app/forests` - "My Forests" (project list from `projects` table)
  - `/app/verification` - Verification reports view
  - `/app/settings` - User settings placeholder
- Keep `/` (landing), `/about` as-is with the public Navbar
- Redirect `/dashboard` and `/mrv` to `/app/dashboard`

### 3. New App Layout (`src/components/app/AppLayout.tsx`)
- `SidebarProvider` + custom `AppSidebar` + `SidebarTrigger` in header
- Sidebar items: Dashboard (BarChart3), My Forests (TreePine), Verification (FileCheck), Settings (Settings)
- Dark sidebar using `#064e3b` background, white text, emerald-400 active highlights
- Mobile: sidebar collapses to offcanvas with hamburger trigger always visible

### 4. App Sidebar (`src/components/app/AppSidebar.tsx`)
- Uses existing `Sidebar` + `SidebarMenu` components
- TerrAI logo in header, "Back to Home" link in footer
- Active route highlighting via `NavLink`
- Collapsible to icon-only mode on desktop

### 5. Global Carbon Feed (`src/components/app/CarbonFeed.tsx`)
- Displayed on the `/app/dashboard` page below the MRV analysis section
- Database: enable Supabase Realtime on `verification_reports` table
- Query recent verification reports joined with project names
- Show as a scrollable feed with: project name, status badge (pending/approved/rejected), timestamp, location
- Subscribe to `postgres_changes` on `verification_reports` for live updates
- Since RLS restricts visibility, the feed shows the user's own reports (validators see all)

### 6. My Forests Page (`src/pages/app/MyForests.tsx`)
- Lists user's projects from the `projects` table using `useProjects` hook
- Cards showing: name, lat/lon, area, created date
- "Add Forest" button to create new projects
- Links to run analysis on each project

### 7. Verification Page (`src/pages/app/Verification.tsx`)
- Lists verification reports using `useVerificationReports`
- Status badges (color-coded), PDF download links
- Integrates existing MRVReport content

### 8. Mobile Responsiveness
- Sidebar: `collapsible="offcanvas"` on mobile (auto-detected via `useIsMobile`)
- All grid layouts use responsive breakpoints (`grid-cols-1 md:grid-cols-2 lg:grid-cols-4`)
- Cards stack vertically on small screens
- Touch-friendly tap targets (min 44px)
- Carbon feed becomes full-width scrollable list

### 9. Database Migration
- Enable Realtime on `verification_reports`: `ALTER PUBLICATION supabase_realtime ADD TABLE public.verification_reports;`

### Files to Create/Edit
- **Create:** `src/components/app/AppLayout.tsx`, `src/components/app/AppSidebar.tsx`, `src/components/app/CarbonFeed.tsx`, `src/pages/app/MyForests.tsx`, `src/pages/app/Verification.tsx`, `src/pages/app/Settings.tsx`
- **Edit:** `src/index.css` (theme), `src/App.tsx` (routing), `src/pages/mrv/MRVDashboard.tsx` (integrate feed), `src/components/Navbar.tsx` (update links)

