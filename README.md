# TerrAI Nepal

Forest carbon MRV platform for Nepal — Vite/React frontend + Django/DRF backend on local PostgreSQL.

## Stack

- **Frontend:** React, TypeScript, Vite, TanStack Query, shadcn/ui, Leaflet
- **Backend:** Django + Django REST Framework + SimpleJWT + Google Earth Engine + Groq
- **Database:** PostgreSQL (`terrai_nepal`)

## Prerequisites

- Node.js 18+ (frontend only)
- Python 3.12+
- PostgreSQL running locally
- Google Earth Engine project + Groq API key (see `forest_health_app/.env` or root `.env`)

## Setup

```bash
# Create DB (once)
createdb terrai_nepal

# Backend
cd backend
pip3 install -r requirements.txt
python3 manage.py migrate
python3 manage.py runserver 8001

# Frontend (separate terminal)
cd ..
npm install
npm run dev
```

Frontend: http://localhost:8080
API: http://localhost:8001/api/ (Vite proxies `/api` → Django)

## Using the application

1. Register or sign in at `/auth`.
2. Open **Dashboard**.
3. Choose an area using a district, community forest, coordinates, drawn
   polygon, or GeoJSON.
4. Choose **Exact dates** for a two-date comparison, or **Season window** for
   cloud-resistant seasonal composites.
5. Select the forest type and optional project, then click **Analyse Forest**.
6. Read the NDVI, change, area, biomass, and CO₂e cards. Use the map buttons
   to switch between baseline, comparison, hotspot, and daily-pass layers.
7. Enable the multi-year trend, monthly series, hotspot map, or AI report when
   needed. Download the PDF after the report is ready.
8. Use **Run vision models** to evaluate live Sentinel-2 thumbnails with the
   local prototype checkpoints. The U-Net mask, Siamese change mask, Vision
   Transformer class, Grad-CAM, and uncertainty outputs are screening
   evidence, not certified carbon measurements.

### Vision prototype setup

The optional prototype training and live inference dependencies are listed in
[`backend/requirements-vision.txt`](./backend/requirements-vision.txt).

```bash
python3 -m pip install -r backend/requirements-vision.txt
python3 backend/mrv/train_vision.py --limit 3000 --epochs 3
```

For live Earth Engine thumbnails, set `GEE_PROJECT_ID` and authenticate Earth
Engine (`earthengine authenticate`). The live endpoint is
`POST /api/vision/infer/` and requires an authenticated user.

The Vision Transformer is trained on real EuroSAT class labels. The U-Net
uses EuroSAT green-canopy pseudo-masks and the Siamese model uses synthetic
change masks, so all three outputs remain labelled prototype evidence.

Optional Celery worker (when Redis is running):

```bash
# brew install redis && brew services start redis
# export REDIS_URL=redis://127.0.0.1:6379/0
npm run dev:worker
```

Without Redis, analyze jobs still run in a background thread and results are cached in the Postgres `terrai_cache_table`.

Carbon estimates apply FRTC / ICIMOD physiographic zone caps (Terai, Siwaliks, Middle Mountains, High Mountains, High Himal) so tropical NDVI saturation (e.g. Chitwan) cannot over-credit AGB.

Hybrid optical + SAR: Max-NDVI composites with S2 cloud-probability masking, Sentinel-1 RVI during monsoon, and regional strata (`terai_sal`, `high_mountain_conifer`, …). Projects store a field-inventory calibration coefficient (`Final = satellite × coeff`).

## Auth

JWT email/password auth.

| Method | Path | Notes |
|--------|------|-------|
| POST | `/api/auth/register/` | `{ email, password, full_name, organization_name? }` |
| POST | `/api/auth/login/` | `{ email, password }` → access + refresh |
| POST | `/api/auth/refresh/` | `{ refresh }` |
| GET/PATCH | `/api/auth/profile/me/` | Authenticated profile |
| GET/POST | `/api/auth/organizations/` | List / create NGO orgs |
| GET | `/api/auth/organizations/:id/` | Org detail |
| GET/POST | `/api/auth/organizations/:id/members/` | List / invite members |

## API resources

| Resource | Path | Notes |
|----------|------|-------|
| Projects | `/api/projects/` | Owner + org-scoped |
| Biomass | `/api/biomass-history/?project_id=` | Create + list |
| Verification | `/api/verification-reports/` | Includes `project_name` |
| Feed | `/api/verification-reports/feed/` | Polled by CarbonFeed |
| Analyze | `POST /api/analyze/` | Async job (202) or cache hit (200) |
| Analyze job | `GET /api/analyze/jobs/:id/` | Poll status / result |
| Report | `/api/report/generate/` | Groq due-diligence JSON |
| PDF | `/api/export/pdf/` | Downloadable PDF |
| Pass dates | `/api/pass-dates/` | Cached Sentinel-2 dates |
| Daily NDVI | `/api/daily-ndvi/` | Cached single-pass NDVI |
| Baselines | `/api/baselines/` | Cached district benchmarks |

## Multi-tenancy

- `Organization` + `OrganizationMembership` (owner / manager / member)
- Projects may belong to an organization; managers see all org projects
- Register with `organization_name` to auto-create an org as owner

## Prototype reference

`forest_health_app/` holds the original Streamlit/FastAPI science prototype (`app.py`, `main.py`). It is not the production web stack.

## Tests

```bash
cd backend && python3 manage.py test forests -v2
npm test
```
