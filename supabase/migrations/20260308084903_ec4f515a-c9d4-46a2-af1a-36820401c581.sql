
-- 1. Role enum
CREATE TYPE public.app_role AS ENUM ('admin', 'validator', 'user');

-- 2. User roles table
CREATE TABLE public.user_roles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  role app_role NOT NULL,
  UNIQUE (user_id, role)
);
ALTER TABLE public.user_roles ENABLE ROW LEVEL SECURITY;

-- 3. Security definer function
CREATE OR REPLACE FUNCTION public.has_role(_user_id UUID, _role app_role)
RETURNS BOOLEAN
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = public
AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.user_roles WHERE user_id = _user_id AND role = _role
  )
$$;

-- 4. RLS on user_roles
CREATE POLICY "Users can read own roles" ON public.user_roles
  FOR SELECT USING (auth.uid() = user_id);

-- 5. Projects table
CREATE TABLE public.projects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  latitude DOUBLE PRECISION NOT NULL,
  longitude DOUBLE PRECISION NOT NULL,
  area_hectares DOUBLE PRECISION NOT NULL DEFAULT 0,
  owner_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE public.projects ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Owners can view own projects" ON public.projects
  FOR SELECT USING (auth.uid() = owner_id OR public.has_role(auth.uid(), 'validator'));
CREATE POLICY "Owners can insert own projects" ON public.projects
  FOR INSERT WITH CHECK (auth.uid() = owner_id);
CREATE POLICY "Owners can update own projects" ON public.projects
  FOR UPDATE USING (auth.uid() = owner_id);
CREATE POLICY "Owners can delete own projects" ON public.projects
  FOR DELETE USING (auth.uid() = owner_id);

-- 6. Biomass history table
CREATE TABLE public.biomass_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
  recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  carbon_density DOUBLE PRECISION NOT NULL,
  health_score DOUBLE PRECISION NOT NULL CHECK (health_score >= 0 AND health_score <= 1),
  source_url TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE public.biomass_history ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view biomass for their projects" ON public.biomass_history
  FOR SELECT USING (
    EXISTS (SELECT 1 FROM public.projects WHERE id = biomass_history.project_id AND (owner_id = auth.uid() OR public.has_role(auth.uid(), 'validator')))
  );
CREATE POLICY "Users can insert biomass for their projects" ON public.biomass_history
  FOR INSERT WITH CHECK (
    EXISTS (SELECT 1 FROM public.projects WHERE id = biomass_history.project_id AND owner_id = auth.uid())
  );

-- 7. Verification reports table
CREATE TYPE public.verification_status AS ENUM ('pending', 'approved', 'rejected');

CREATE TABLE public.verification_reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
  verifier_id UUID REFERENCES auth.users(id),
  status verification_status NOT NULL DEFAULT 'pending',
  pdf_url TEXT,
  integrity_seal_hash TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE public.verification_reports ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Owners and validators can view reports" ON public.verification_reports
  FOR SELECT USING (
    EXISTS (SELECT 1 FROM public.projects WHERE id = verification_reports.project_id AND (owner_id = auth.uid() OR public.has_role(auth.uid(), 'validator')))
  );
CREATE POLICY "Users can insert reports for own projects" ON public.verification_reports
  FOR INSERT WITH CHECK (
    EXISTS (SELECT 1 FROM public.projects WHERE id = verification_reports.project_id AND owner_id = auth.uid())
  );
CREATE POLICY "Validators can update reports" ON public.verification_reports
  FOR UPDATE USING (public.has_role(auth.uid(), 'validator'));

-- 8. Updated_at trigger
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END;
$$ LANGUAGE plpgsql SET search_path = public;

CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON public.projects
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
CREATE TRIGGER update_verification_reports_updated_at BEFORE UPDATE ON public.verification_reports
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

-- 9. Indexes
CREATE INDEX idx_projects_owner ON public.projects(owner_id);
CREATE INDEX idx_biomass_project ON public.biomass_history(project_id);
CREATE INDEX idx_biomass_recorded ON public.biomass_history(recorded_at);
CREATE INDEX idx_verification_project ON public.verification_reports(project_id);
CREATE INDEX idx_verification_status ON public.verification_reports(status);
