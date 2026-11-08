"""TerrAI — Digital MRV Platform · Nepal · v3.1"""

import streamlit as st
import ee
import folium
from streamlit_folium import st_folium
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os, json, io, math
from dotenv import load_dotenv

load_dotenv()

from utils.gee_utils import (
    get_sentinel_composite, compute_mean_ndvi,
    calculate_ndvi_timeseries, get_ndvi_visualization_params, create_aoi_from_point
)
from utils.nepal_data import (
    NEPAL_CENTER, get_all_locations, search_location, get_location_coords
)

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, Image as RLImage
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

# ── Tier 1 optional imports ────────────────────────────────────────────────────
try:
    from supabase import create_client, Client as SupabaseClient
    SUPABASE_OK = True
except ImportError:
    SUPABASE_OK = False

try:
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    SMTP_OK = True
except ImportError:
    SMTP_OK = False

try:
    import requests as _requests
    REQUESTS_OK = True
except ImportError:
    REQUESTS_OK = False

# ── Palette ────────────────────────────────────────────────────────────────────
C = {
    "forest":    "#0D2818",
    "dark":      "#1A4731",
    "mid":       "#2D6A4F",
    "accent":    "#40916C",
    "sage":      "#74C69D",
    "mist":      "#D8F3DC",
    "pale":      "#F0FBF4",
    "white":     "#FFFFFF",
    "ink":       "#0F1A14",
    "slate":     "#4A5568",
    "border":    "#C3E6CB",
    "warn":      "#E67E22",
    "danger":    "#C0392B",
    "good":      "#27AE60",
}
RL = {k: colors.HexColor(v) for k, v in C.items()}

NEPAL_CARBON = {
    "tropical_broadleaf":    {"agb": 180, "bgb_r": 0.26, "cf": 0.47},
    "subtropical_broadleaf": {"agb": 150, "bgb_r": 0.28, "cf": 0.47},
    "temperate_broadleaf":   {"agb": 120, "bgb_r": 0.30, "cf": 0.47},
    "conifer":               {"agb": 100, "bgb_r": 0.32, "cf": 0.51},
    "default":               {"agb": 140, "bgb_r": 0.28, "cf": 0.47},
}
CO2_FACTOR = 3.667

# ══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG & CSS
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(page_title="TerrAI", page_icon="🌿", layout="wide",
                   initial_sidebar_state="expanded")

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Playfair+Display:wght@600;700&display=swap');

*, *::before, *::after {{ box-sizing: border-box; }}
html, body, [class*="css"] {{
  font-family: 'Inter', sans-serif;
  color: {C['ink']};
  background: {C['white']};
}}

/* ── Hide streamlit chrome ── */
#MainMenu, footer, header {{ visibility: hidden; }}
.block-container {{ padding: 1.5rem 2rem 4rem 2rem !important; max-width: 1320px; }}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {{
  background: {C['forest']};
  border-right: 1px solid {C['dark']};
}}
section[data-testid="stSidebar"] > div {{ padding: 1.5rem 1.2rem; }}
section[data-testid="stSidebar"] * {{ color: {C['mist']} !important; }}
section[data-testid="stSidebar"] .stButton > button {{
  background: {C['accent']} !important;
  color: {C['white']} !important;
  font-weight: 600; border: none; border-radius: 8px;
  padding: 0.7rem 1rem; width: 100%; font-size: 0.9rem;
  letter-spacing: 0.02em; transition: all 0.15s;
  margin-top: 0.75rem;
}}
section[data-testid="stSidebar"] .stButton > button:hover {{
  background: {C['mid']} !important; transform: translateY(-1px);
}}
section[data-testid="stSidebar"] hr {{
  border-color: rgba(116,198,157,0.15) !important; margin: 1rem 0;
}}
section[data-testid="stSidebar"] label {{
  font-size: 0.72rem !important; font-weight: 600 !important;
  letter-spacing: 0.08em !important; text-transform: uppercase !important;
  color: {C['sage']} !important;
}}
section[data-testid="stSidebar"] h3 {{
  font-family: 'Playfair Display', serif !important;
  font-size: 0.95rem !important; color: {C['white']} !important;
  border-bottom: 1px solid rgba(116,198,157,0.2);
  padding-bottom: 0.5rem; margin: 1.2rem 0 0.8rem 0 !important;
}}

/* ── Wordmark ── */
.terrai-wordmark {{
  display: flex; align-items: baseline; gap: 2px;
  font-family: 'Playfair Display', serif;
}}
.terrai-terr {{ font-size: 1.9rem; color: {C['dark']}; font-weight: 700; }}
.terrai-ai   {{ font-size: 1.9rem; color: {C['accent']}; font-weight: 700; }}
.terrai-tag  {{
  font-size: 0.72rem; font-weight: 500; color: {C['slate']};
  letter-spacing: 0.06em; text-transform: uppercase;
  border-left: 2px solid {C['mist']}; padding-left: 0.75rem; margin-left: 0.75rem;
  line-height: 1.3;
}}

/* ── Top bar ── */
.topbar {{
  display: flex; justify-content: space-between; align-items: center;
  padding: 1rem 0 1.25rem 0;
  border-bottom: 1px solid {C['mist']};
  margin-bottom: 1.75rem;
}}
.topbar-pills {{ display: flex; gap: 0.5rem; }}
.pill {{
  background: {C['pale']}; border: 1px solid {C['border']};
  border-radius: 100px; padding: 0.3rem 0.75rem;
  font-size: 0.72rem; font-weight: 600; color: {C['accent']};
  letter-spacing: 0.04em;
}}

/* ── Section label ── */
.sec-label {{
  font-size: 0.68rem; font-weight: 700; letter-spacing: 0.1em;
  text-transform: uppercase; color: {C['sage']};
  margin: 2rem 0 0.75rem 0;
  display: flex; align-items: center; gap: 0.5rem;
}}
.sec-label::after {{
  content: ''; flex: 1; height: 1px; background: {C['mist']};
}}

/* ── Stat cards ── */
.stat-grid {{ display: grid; grid-template-columns: repeat(4,1fr); gap: 1rem; margin-bottom: 1.5rem; }}
.stat-card {{
  background: {C['white']}; border: 1px solid {C['mist']};
  border-radius: 12px; padding: 1.1rem 1.25rem;
  position: relative; overflow: hidden;
}}
.stat-card::before {{
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
  background: {C['accent']};
}}
.stat-card.danger::before {{ background: {C['danger']}; }}
.stat-card.warn::before   {{ background: {C['warn']}; }}
.stat-card.good::before   {{ background: {C['good']}; }}
.stat-lbl  {{ font-size: 0.68rem; font-weight: 600; letter-spacing: 0.07em; text-transform: uppercase; color: {C['slate']}; margin-bottom: 0.4rem; }}
.stat-val  {{ font-family: 'Playfair Display', serif; font-size: 1.8rem; color: {C['dark']}; line-height: 1; }}
.stat-sub  {{ font-size: 0.72rem; color: {C['slate']}; margin-top: 0.3rem; }}

/* ── Status banner ── */
.status-banner {{
  border-radius: 10px; padding: 1rem 1.4rem;
  display: flex; align-items: center; gap: 1rem;
  margin-bottom: 1.5rem; border: 1px solid;
}}
.sb-critical {{ background:#FEF2F2; border-color:#FECACA; }}
.sb-warning  {{ background:#FFFBEB; border-color:#FDE68A; }}
.sb-good     {{ background:{C['pale']}; border-color:{C['mist']}; }}
.sb-icon  {{ font-size:1.75rem; flex-shrink:0; }}
.sb-title {{ font-weight:700; font-size:0.95rem; }}
.sb-desc  {{ font-size:0.83rem; color:{C['slate']}; margin-top:0.15rem; line-height:1.5; }}

/* ── Carbon panel ── */
.carbon-panel {{
  background: linear-gradient(135deg, {C['dark']} 0%, {C['mid']} 100%);
  border-radius: 14px; padding: 1.5rem 1.75rem; margin-bottom: 1.5rem;
}}
.cp-title {{ font-family:'Playfair Display',serif; font-size:1rem; color:{C['mist']}; margin-bottom:1.1rem; }}
.cp-grid  {{ display:grid; grid-template-columns:repeat(4,1fr); gap:0.9rem; }}
.cp-cell  {{ background:rgba(255,255,255,0.08); border-radius:10px; padding:0.9rem; text-align:center; border:1px solid rgba(116,198,157,0.2); }}
.cp-lbl   {{ font-size:0.62rem; font-weight:700; letter-spacing:0.09em; text-transform:uppercase; color:{C['sage']}; margin-bottom:5px; }}
.cp-val   {{ font-family:'Playfair Display',serif; font-size:1.55rem; color:{C['white']}; line-height:1; }}
.cp-unit  {{ font-size:0.66rem; color:rgba(216,243,220,0.65); margin-top:3px; }}
.cp-note  {{ font-size:0.7rem; color:rgba(216,243,220,0.55); margin-top:1rem; font-style:italic; }}

/* ── Report card ── */
.rpt-wrap {{ border:1px solid {C['mist']}; border-radius:14px; overflow:hidden; margin-bottom:1.5rem; }}
.rpt-head {{ background:{C['dark']}; padding:1.25rem 1.75rem; display:flex; justify-content:space-between; align-items:center; }}
.rpt-head-title {{ font-family:'Playfair Display',serif; color:{C['white']}; font-size:1.15rem; }}
.rpt-head-meta  {{ color:{C['sage']}; font-size:0.76rem; text-align:right; line-height:1.6; }}
.rpt-body {{ padding:1.5rem 1.75rem; background:{C['pale']}; }}
.rpt-sec {{ font-family:'Playfair Display',serif; font-size:0.95rem; color:{C['mid']}; border-left:3px solid {C['accent']}; padding-left:0.65rem; margin:1.2rem 0 0.5rem 0; }}
.rpt-box {{ background:{C['white']}; border:1px solid {C['border']}; border-radius:8px; padding:0.9rem 1.1rem; font-size:0.87rem; line-height:1.7; color:{C['ink']}; }}
.rpt-kv  {{ display:grid; grid-template-columns:1fr 1fr; gap:0.75rem; margin-top:0.75rem; }}
.rpt-foot {{ background:{C['dark']}; padding:0.75rem 1.75rem; display:flex; justify-content:space-between; align-items:center; }}
.rft {{ color:{C['sage']}; font-size:0.72rem; }}
.seal {{ background:{C['accent']}; color:{C['white']}; font-size:0.66rem; font-weight:700; letter-spacing:0.1em; text-transform:uppercase; padding:0.3rem 0.7rem; border-radius:4px; }}
.risk-badge {{
  display:inline-block; font-size:0.7rem; font-weight:700;
  letter-spacing:0.07em; text-transform:uppercase;
  padding:0.25rem 0.65rem; border-radius:100px;
}}

/* ── Daily NDVI panel ── */
.daily-panel {{
  background:{C['white']}; border:1px solid {C['mist']}; border-radius:14px;
  overflow:hidden; margin-bottom:1.5rem;
}}
.daily-head {{
  background: linear-gradient(90deg, {C['mid']} 0%, {C['accent']} 100%);
  padding:0.9rem 1.4rem; display:flex; justify-content:space-between; align-items:center;
}}
.daily-head-title {{ font-family:'Playfair Display',serif; color:{C['white']}; font-size:1rem; }}
.daily-head-badge {{
  background:rgba(255,255,255,0.2); border:1px solid rgba(255,255,255,0.3);
  border-radius:100px; padding:0.2rem 0.65rem;
  font-size:0.68rem; font-weight:700; color:{C['white']}; letter-spacing:0.06em;
}}
.daily-body {{ padding:1.25rem 1.5rem; }}
.acq-chip {{
  display:inline-block; margin:3px; padding:0.3rem 0.7rem;
  border-radius:100px; font-size:0.75rem; font-weight:600;
  cursor:pointer; transition:all 0.12s;
  border:1px solid {C['border']};
}}
.acq-chip.selected {{
  background:{C['dark']}; color:{C['white']}; border-color:{C['dark']};
}}
.acq-chip.available {{
  background:{C['pale']}; color:{C['accent']};
}}

/* ── NDVI colorbar ── */
.ndvi-bar {{
  background:{C['white']}; border:1px solid {C['mist']}; border-radius:8px;
  padding:0.65rem 0.9rem; margin-top:0.5rem;
}}
.ndvi-bar-inner {{ display:flex; height:12px; border-radius:4px; overflow:hidden; margin:6px 0 4px 0; }}
.ndvi-scale {{ display:flex; justify-content:space-between; font-size:10px; color:{C['slate']}; }}

/* ── Tab styling ── */
.stTabs [data-baseweb="tab"] {{ font-weight:600; font-size:0.88rem; }}
.stTabs [aria-selected="true"] {{ color:{C['dark']} !important; border-bottom-color:{C['accent']} !important; border-bottom-width:2px !important; }}

/* ── Download button ── */
.stDownloadButton > button {{
  background: {C['dark']} !important; color: {C['white']} !important;
  font-weight:600; border:none; border-radius:8px;
  font-size:0.9rem; transition:all 0.15s;
}}
.stDownloadButton > button:hover {{
  background: {C['mid']} !important; transform:translateY(-1px);
}}

/* ── Empty state ── */
.empty-state {{
  text-align:center; padding:4rem 2rem; color:{C['slate']};
}}
.empty-icon {{ font-size:3rem; margin-bottom:1rem; opacity:0.4; }}
.empty-title {{ font-family:'Playfair Display',serif; font-size:1.3rem; color:{C['dark']}; margin-bottom:0.5rem; }}
.empty-sub {{ font-size:0.87rem; line-height:1.6; max-width:420px; margin:0 auto; }}

.feat-grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:1rem; margin-top:1.5rem; }}
.feat-card {{
  border:1px solid {C['mist']}; border-radius:12px; padding:1.25rem;
  background:{C['white']}; transition:border-color 0.15s;
}}
.feat-card:hover {{ border-color:{C['sage']}; }}
.feat-ico   {{ font-size:1.4rem; margin-bottom:0.6rem; }}
.feat-title {{ font-weight:700; font-size:0.9rem; color:{C['dark']}; margin-bottom:0.3rem; }}
.feat-desc  {{ font-size:0.8rem; color:{C['slate']}; line-height:1.5; }}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════
MN = {1:"January",2:"February",3:"March",4:"April",5:"May",6:"June",
      7:"July",8:"August",9:"September",10:"October",11:"November",12:"December"}
MS = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
      7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}

def gee_init():
    pid = os.getenv('GEE_PROJECT_ID')
    if not pid:
        st.error("GEE_PROJECT_ID missing from .env")
        return False
    try:
        ee.Initialize(project=pid)
        return True
    except Exception as e:
        st.error(f"Earth Engine init failed: {e}")
        st.info("Run `earthengine authenticate` first.")
        return False

def make_map(lat, lon, zoom=11):
    m = folium.Map(
        location=[lat, lon], zoom_start=zoom,
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri'
    )
    folium.Marker([lat, lon], icon=folium.Icon(color='green', icon='leaf', prefix='fa')).add_to(m)
    return m

def add_ee_layer(m, image, vis, name, opacity=0.85):
    try:
        url = image.getMapId(vis)['tile_fetcher'].url_format
        folium.TileLayer(tiles=url, attr='GEE', name=name,
                         overlay=True, control=True, opacity=opacity).add_to(m)
        return True
    except:
        return False

def parse_geojson(f):
    data = json.loads(f.read())
    geom, name = None, "Uploaded Boundary"
    t = data.get("type")
    if t == "FeatureCollection":
        feats = data.get("features", [])
        if not feats: raise ValueError("Empty FeatureCollection")
        geom  = feats[0].get("geometry")
        props = feats[0].get("properties", {})
        name  = props.get("name") or props.get("NAME") or name
    elif t == "Feature":
        geom  = data.get("geometry")
        props = data.get("properties", {})
        name  = props.get("name") or props.get("NAME") or name
    elif t in ("Polygon","MultiPolygon"):
        geom = data
    else:
        raise ValueError(f"Unsupported GeoJSON type: {t}")
    if not geom: raise ValueError("No geometry found")
    aoi  = ee.Geometry(geom)
    c    = aoi.centroid(maxError=1).coordinates().getInfo()
    area = aoi.area(maxError=1).getInfo() / 10000
    return aoi, c[1], c[0], area, name

def carbon_estimate(ndvi, area_ha, ftype="default", change_pct=None):
    if ndvi is None or area_ha <= 0: return None
    p  = NEPAL_CARBON.get(ftype, NEPAL_CARBON["default"])
    sc = max(0.1, min(1.5, ndvi / 0.75))
    agb = p["agb"] * sc
    bgb = agb * p["bgb_r"]
    bio = agb + bgb
    c_ha   = bio * p["cf"]
    co2_ha = c_ha * CO2_FACTOR
    res = dict(
        agb_ha=round(agb,1), bgb_ha=round(bgb,1),
        bio_ha=round(bio,1),  c_ha=round(c_ha,1),
        co2_ha=round(co2_ha,1),
        total_c=round(c_ha*area_ha),
        total_co2=round(co2_ha*area_ha),
        area_ha=round(area_ha,1), ftype=ftype
    )
    if change_pct is not None:
        delta = res["total_co2"] * change_pct / 100
        res["co2_delta"] = round(delta)
        res["change_pct"] = round(change_pct,1)
    return res

def annual_ndvi_series(aoi, start_m, end_m, start_yr=2019):
    results = []
    for yr in range(start_yr, datetime.now().year + 1):
        try:
            c = get_sentinel_composite(aoi, f"{yr}-{start_m:02d}-01", f"{yr}-{end_m:02d}-28")
            v = compute_mean_ndvi(c, aoi)
            if v: results.append({"year": yr, "ndvi": round(v, 4)})
        except: pass
    return results

def trend_stats(data):
    if len(data) < 2: return 0, "stable"
    xs = [d["year"] for d in data]
    ys = [d["ndvi"]  for d in data]
    xm, ym = sum(xs)/len(xs), sum(ys)/len(ys)
    num = sum((xs[i]-xm)*(ys[i]-ym) for i in range(len(xs)))
    den = sum((xs[i]-xm)**2 for i in range(len(xs)))
    slope = num/den if den else 0
    direction = "improving" if slope > 0.001 else ("declining" if slope < -0.001 else "stable")
    return slope, direction


# ══════════════════════════════════════════════════════════════════════════════
# DAILY NDVI — SENTINEL-2 ACQUISITION DATES
# ══════════════════════════════════════════════════════════════════════════════

def get_sentinel2_acquisition_dates(aoi, year, month):
    """
    Query GEE for all Sentinel-2 SR scenes that intersect the AOI
    for the given year+month. Returns sorted list of date strings (YYYY-MM-DD).
    Filters cloud cover < 80% so cloudy-only passes are excluded.
    """
    try:
        start = f"{year}-{month:02d}-01"
        # End of month
        if month == 12:
            end = f"{year+1}-01-01"
        else:
            end = f"{year}-{month+1:02d}-01"

        col = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
               .filterBounds(aoi)
               .filterDate(start, end)
               .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 80)))

        dates_list = col.aggregate_array('system:time_start').getInfo()
        if not dates_list:
            return []

        # Convert ms timestamps → date strings, deduplicate (multiple tiles same day)
        seen = set()
        dates = []
        for ts in sorted(dates_list):
            d = datetime.utcfromtimestamp(ts / 1000).strftime('%Y-%m-%d')
            if d not in seen:
                seen.add(d)
                dates.append(d)
        return dates
    except Exception as e:
        return []


def compute_daily_ndvi(aoi, date_str):
    """
    Build a single-day NDVI image and mean value for a specific acquisition date.
    Returns (ee.Image with NDVI band, float mean_ndvi, cloud_pct).
    """
    try:
        d = datetime.strptime(date_str, '%Y-%m-%d')
        d_next = (d + timedelta(days=1)).strftime('%Y-%m-%d')

        col = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
               .filterBounds(aoi)
               .filterDate(date_str, d_next)
               .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 80)))

        img = col.median()

        # NDVI
        nir = img.select('B8')
        red = img.select('B4')
        ndvi_img = nir.subtract(red).divide(nir.add(red)).rename('NDVI')
        img_with_ndvi = img.addBands(ndvi_img)

        # Mean NDVI over AOI
        mean_dict = ndvi_img.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=aoi,
            scale=20,
            maxPixels=1e9
        )
        mean_val = mean_dict.get('NDVI').getInfo()

        # Cloud pct from first image metadata
        cloud_pct = col.first().get('CLOUDY_PIXEL_PERCENTAGE').getInfo()

        return img_with_ndvi, round(mean_val, 4) if mean_val else None, round(cloud_pct, 1) if cloud_pct else None
    except Exception as e:
        return None, None, None


def ndvi_quality_label(ndvi):
    if ndvi is None:
        return "N/A", C['slate']
    if ndvi >= 0.6:
        return "Dense Forest", C['good']
    elif ndvi >= 0.4:
        return "Moderate Vegetation", C['accent']
    elif ndvi >= 0.2:
        return "Sparse Vegetation", C['warn']
    else:
        return "Bare / Degraded", C['danger']


def render_daily_ndvi_section(aoi, lat, lon, buf_km, aoi_custom):
    """
    Renders the full Daily NDVI Explorer section.
    """
    st.markdown('<div class="sec-label">🛰 Daily NDVI Explorer — Sentinel-2 Pass Dates</div>',
                unsafe_allow_html=True)

    st.markdown(f"""
    <div class="daily-panel">
      <div class="daily-head">
        <div class="daily-head-title">Daily NDVI Explorer</div>
        <div class="daily-head-badge">~5-day Sentinel-2 Revisit</div>
      </div>
      <div class="daily-body" style="padding-bottom:0.25rem;">
        <p style="font-size:0.83rem;color:{C['slate']};margin:0 0 1rem 0;line-height:1.6;">
          Select a year and month to load all available Sentinel-2 acquisition dates for this location.
          Each date represents a real satellite overpass with &lt;80% cloud cover.
          NDVI is computed from the raw scene — no multi-image compositing.
        </p>
      </div>
    </div>""", unsafe_allow_html=True)

    cur_yr = datetime.now().year
    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        d_year = st.selectbox("Year", range(2019, cur_yr + 1),
                              index=cur_yr - 2019 - 1, key="daily_year")
    with col2:
        d_month = st.selectbox("Month", range(1, 13),
                               index=datetime.now().month - 2,
                               format_func=lambda x: datetime(2000, x, 1).strftime('%B'),
                               key="daily_month")
    with col3:
        load_dates = st.button("🔍 Load available pass dates", use_container_width=True, key="load_dates_btn")

    if load_dates or st.session_state.get('daily_dates_loaded'):
        if load_dates:
            with st.spinner(f"Querying Sentinel-2 passes for {MN[d_month]} {d_year}…"):
                dates = get_sentinel2_acquisition_dates(aoi, d_year, d_month)
            st.session_state['daily_dates'] = dates
            st.session_state['daily_dates_loaded'] = True
            st.session_state['daily_selected_date'] = None

        dates = st.session_state.get('daily_dates', [])

        if not dates:
            st.warning(f"No cloud-free Sentinel-2 passes found for {MN[d_month]} {d_year} over this location. Try a different month.")
            return

        # Show date chips
        n_dates = len(dates)
        st.markdown(f"""
        <div style="background:{C['pale']};border:1px solid {C['mist']};border-radius:10px;
                    padding:0.9rem 1.1rem;margin-bottom:1rem;">
          <div style="font-size:0.68rem;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;
                      color:{C['accent']};margin-bottom:0.6rem;">
            {n_dates} pass{'es' if n_dates!=1 else ''} available — {MN[d_month]} {d_year}
          </div>
          <div style="font-size:0.8rem;color:{C['slate']};line-height:1.6;">
            Each tile = one Sentinel-2 overpass. Select a date below to compute NDVI for that exact scene.
          </div>
        </div>""", unsafe_allow_html=True)

        selected_date = st.selectbox(
            "Select acquisition date",
            dates,
            format_func=lambda d: datetime.strptime(d, '%Y-%m-%d').strftime('%d %B %Y (%A)'),
            key="daily_date_picker"
        )

        if st.button("📡 Compute NDVI for this date", use_container_width=False, key="compute_daily"):
            with st.spinner(f"Computing NDVI for {selected_date}…"):
                daily_img, daily_ndvi, cloud_pct = compute_daily_ndvi(aoi, selected_date)
            st.session_state['daily_result'] = {
                'date': selected_date,
                'ndvi': daily_ndvi,
                'cloud_pct': cloud_pct,
                'img': daily_img
            }

        # Render result if available
        res = st.session_state.get('daily_result')
        if res and res['date'] == selected_date:
            _render_daily_result(res, lat, lon, buf_km, aoi_custom)


def _render_daily_result(res, lat, lon, buf_km, aoi_custom):
    """Renders the NDVI result for a selected daily pass."""
    date_str  = res['date']
    ndvi_val  = res['ndvi']
    cloud_pct = res['cloud_pct']
    daily_img = res['img']

    d_fmt = datetime.strptime(date_str, '%Y-%m-%d').strftime('%d %B %Y')
    quality_label, quality_color = ndvi_quality_label(ndvi_val)

    # Metric row
    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("Date", d_fmt)
    mc2.metric("NDVI", f"{ndvi_val:.4f}" if ndvi_val else "N/A")
    mc3.metric("Cloud Cover", f"{cloud_pct}%" if cloud_pct is not None else "N/A")
    mc4.metric("Vegetation Status", quality_label)

    # Quality bar
    ndvi_display = ndvi_val or 0
    bar_w = min(100, int(ndvi_display * 100))
    st.markdown(f"""
    <div style="background:{C['white']};border:1px solid {C['mist']};border-radius:10px;
                padding:1rem 1.25rem;margin-bottom:1rem;">
      <div style="display:flex;justify-content:space-between;margin-bottom:8px;">
        <span style="font-size:0.78rem;font-weight:600;color:{C['slate']};">NDVI Health Indicator</span>
        <span style="font-size:0.78rem;font-weight:700;color:{quality_color};">{quality_label}</span>
      </div>
      <div style="height:10px;background:{C['mist']};border-radius:5px;">
        <div style="height:100%;width:{bar_w}%;background:linear-gradient(90deg,{C['warn']},{C['accent']},{C['good']});border-radius:5px;transition:width 0.4s;"></div>
      </div>
      <div style="display:flex;justify-content:space-between;font-size:10px;color:{C['slate']};margin-top:4px;">
        <span>0.0 Bare</span><span>0.25</span><span>0.5</span><span>0.75</span><span>1.0 Dense</span>
      </div>
    </div>""", unsafe_allow_html=True)

    # Map
    if daily_img:
        st.markdown(f"**Satellite Map — {d_fmt}**")
        vis = get_ndvi_visualization_params()
        m_daily = make_map(lat, lon, zoom=12)
        ndvi_layer = daily_img.select('NDVI')
        ok = add_ee_layer(m_daily, ndvi_layer, vis, f'NDVI {date_str}')
        if aoi_custom is None:
            folium.Circle(
                location=[lat, lon], radius=buf_km * 1000,
                color='#FFD700', fill=False, weight=2.5,
                tooltip=f"Analysis radius: {buf_km} km"
            ).add_to(m_daily)
        folium.LayerControl(collapsed=False).add_to(m_daily)
        st_folium(m_daily, height=400, returned_objects=[], use_container_width=True)

        if ok:
            st.markdown(f"""
            <div class="ndvi-bar">
              <span style="font-size:0.72rem;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;color:{C['accent']};">NDVI Scale — {date_str}</span>
              <div class="ndvi-bar-inner">
                <div style="flex:1;background:#d73027"></div><div style="flex:1;background:#fc8d59"></div>
                <div style="flex:1;background:#fee08b"></div><div style="flex:1;background:#d9ef8b"></div>
                <div style="flex:1;background:#91cf60"></div><div style="flex:1;background:#1a9850"></div>
              </div>
              <div class="ndvi-scale"><span>0.0 Bare</span><span>0.2</span><span>0.4</span><span>0.6</span><span>0.8</span><span>1.0 Dense</span></div>
            </div>""", unsafe_allow_html=True)

    st.caption(f"Single-scene NDVI · Sentinel-2 SR · {date_str} · No compositing applied · Cloud cover: {cloud_pct}%")


# ══════════════════════════════════════════════════════════════════════════════
# SATELLITE MAP → PNG FOR PDF
# ══════════════════════════════════════════════════════════════════════════════

def fetch_static_satellite_map(lat, lon, buf_km, zoom=12, width=600, height=360):
    """
    Fetches a static satellite basemap tile image centered on the AOI using
    the OpenStreetMap/ESRI tile standard. Returns PNG bytes or None.
    Uses the staticmap library if available, otherwise falls back to manual tile fetch.
    """
    try:
        from staticmap import StaticMap, CircleMarker, Line
        import math as _math

        m = StaticMap(width, height, url_template='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}')

        # Draw the AOI circle (approximate, using multiple points)
        # Convert km radius to degrees for rough approximation
        lat_rad = _math.radians(lat)
        dlat = buf_km / 111.0
        dlon = buf_km / (111.0 * _math.cos(lat_rad))
        num_pts = 64
        circle_coords = []
        for i in range(num_pts + 1):
            angle = 2 * _math.pi * i / num_pts
            clat = lat + dlat * _math.sin(angle)
            clon = lon + dlon * _math.cos(angle)
            circle_coords.append((clon, clat))

        line = Line(circle_coords, '#FFD700', 3)
        m.add_line(line)

        # Center marker
        marker = CircleMarker((lon, lat), '#40916C', 12)
        m.add_marker(marker)

        img = m.render(zoom=zoom)
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        return buf.getvalue()
    except Exception:
        pass

    # Fallback: plain tile fetch via requests
    try:
        import requests
        # Use a simple single-tile approach
        def _deg2tile(lat_deg, lon_deg, z):
            lat_r = math.radians(lat_deg)
            n = 2 ** z
            xt = int((lon_deg + 180.0) / 360.0 * n)
            yt = int((1.0 - math.asinh(math.tan(lat_r)) / math.pi) / 2.0 * n)
            return xt, yt

        z = zoom
        xt, yt = _deg2tile(lat, lon, z)
        url = f"https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{yt}/{xt}"
        resp = requests.get(url, timeout=8, headers={'User-Agent': 'TerrAI/3.1'})
        if resp.status_code == 200:
            return resp.content
    except Exception:
        pass

    return None


def build_comparison_map_image(lat, lon, buf_km, y1, y2, n1, n2, width=560, height=300):
    """
    Creates a simple side-by-side comparison figure using matplotlib showing
    the AOI location with NDVI values annotated. Returns PNG bytes.
    This is used in PDF when a real satellite tile cannot be fetched.
    """
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        from matplotlib.patches import Circle
        import numpy as np

        fig, axes = plt.subplots(1, 2, figsize=(width/100, height/100), dpi=100)
        fig.patch.set_facecolor('#1A4731')

        for ax, yr, ndvi_val, label in [
            (axes[0], y1, n1, f"Year {y1}"),
            (axes[1], y2, n2, f"Year {y2}")
        ]:
            ax.set_facecolor('#0D2818')
            ax.set_xlim(-1, 1)
            ax.set_ylim(-1, 1)

            # NDVI-scaled color
            if ndvi_val:
                g = min(1.0, ndvi_val / 0.8)
                fill_color = (0.1 * (1-g), 0.4 + 0.4*g, 0.1 + 0.2*g, 0.7)
            else:
                fill_color = (0.4, 0.4, 0.4, 0.5)

            # Draw AOI circle
            circle_fill = Circle((0, 0), 0.72, color=fill_color, zorder=2)
            circle_edge = Circle((0, 0), 0.72, fill=False, edgecolor='#FFD700', linewidth=2.5, zorder=3)
            ax.add_patch(circle_fill)
            ax.add_patch(circle_edge)

            # Center dot
            ax.plot(0, 0, 'o', color='#FFD700', markersize=8, zorder=4)

            # NDVI text
            ndvi_str = f"{ndvi_val:.4f}" if ndvi_val else "N/A"
            ax.text(0, 0.1, ndvi_str, ha='center', va='center',
                    fontsize=14, fontweight='bold', color='white', zorder=5)
            ax.text(0, -0.18, 'NDVI', ha='center', va='center',
                    fontsize=8, color='#74C69D', zorder=5)

            # Radius label
            ax.text(0, -0.88, f"r = {buf_km} km", ha='center', va='center',
                    fontsize=7, color='#FFD700')

            ax.set_title(label, color='white', fontsize=10, fontweight='bold', pad=8)
            ax.set_xticks([]); ax.set_yticks([])
            for spine in ax.spines.values():
                spine.set_edgecolor('#2D6A4F')

        # Title
        fig.suptitle(f"NDVI Comparison — {lat:.3f}°N {lon:.3f}°E", 
                     color='#74C69D', fontsize=9, y=0.02)
        plt.tight_layout(pad=0.8)

        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight',
                    facecolor=fig.get_facecolor())
        plt.close(fig)
        buf.seek(0)
        return buf.getvalue()
    except Exception as e:
        return None


def get_ndvi_diff_image_png(lat, lon, buf_km, y1, y2, n1, n2, width=560, height=220):
    """
    Build a matplotlib figure showing the NDVI change between two years with
    geographic context: AOI circle + colour-coded NDVI bars. Returns PNG bytes.
    """
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        import numpy as np

        dpct = ((n2 - n1) / n1 * 100) if (n1 and n2 and n1 != 0) else 0
        change_color = '#27AE60' if dpct >= 0 else ('#E67E22' if dpct > -10 else '#C0392B')

        fig, ax = plt.subplots(figsize=(width/100, height/100), dpi=100)
        fig.patch.set_facecolor('#1A4731')
        ax.set_facecolor('#0D2818')

        years_label = [str(y1), str(y2)]
        ndvi_vals   = [n1 or 0, n2 or 0]
        bar_colors  = ['#2D6A4F', change_color]

        bars = ax.bar(years_label, ndvi_vals, color=bar_colors, width=0.45,
                      edgecolor='#74C69D', linewidth=1.2)

        for bar, val in zip(bars, ndvi_vals):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                    f'{val:.4f}', ha='center', va='bottom',
                    fontsize=10, fontweight='bold', color='white')

        ax.set_ylim(0, 1.05)
        ax.set_ylabel('NDVI', color='#74C69D', fontsize=9)
        ax.set_title(f'NDVI Change: {dpct:+.1f}%  ({y1} → {y2})',
                     color='white', fontsize=10, fontweight='bold')
        ax.tick_params(colors='#74C69D', labelsize=9)
        ax.spines['bottom'].set_color('#2D6A4F')
        ax.spines['left'].set_color('#2D6A4F')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.yaxis.grid(True, color='#2D6A4F', alpha=0.4, linewidth=0.7)
        ax.set_facecolor('#0D2818')

        # Annotate change arrow
        ax.annotate('', xy=(1, n2 or 0), xytext=(0, n1 or 0),
                    arrowprops=dict(arrowstyle='->', color=change_color, lw=2),
                    xycoords=('data', 'data'), textcoords=('data', 'data'),
                    annotation_clip=False)

        plt.tight_layout(pad=0.6)
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight',
                    facecolor=fig.get_facecolor())
        plt.close(fig)
        buf.seek(0)
        return buf.getvalue()
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════════════════════
# CHARTS
# ══════════════════════════════════════════════════════════════════════════════
CHART_LAYOUT = dict(
    plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
    font=dict(family="Inter", size=11, color=C['slate']),
    margin=dict(l=48, r=16, t=48, b=40),
    hovermode='x unified',
)
_GRID = dict(showgrid=True, gridcolor='rgba(0,0,0,0.05)', zeroline=False)

def monthly_chart(ts, title):
    df = pd.DataFrame(ts)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['month'], y=df['ndvi'], mode='lines+markers', name='NDVI',
        line=dict(color=C['accent'], width=2.5),
        marker=dict(size=7, color=C['dark'], line=dict(color=C['white'], width=1.5)),
        fill='tozeroy', fillcolor='rgba(64,145,108,0.08)',
        hovertemplate='<b>%{x}</b>: %{y:.4f}<extra></extra>'
    ))
    fig.update_layout(**CHART_LAYOUT,
        title=dict(text=title, font=dict(size=14, color=C['dark'], family="Playfair Display")),
        xaxis=dict(**_GRID),
        yaxis=dict(**_GRID, range=[0, 1]),
    )
    return fig

def trend_chart(data, location):
    df = pd.DataFrame(data)
    years, ndvis = df['year'].tolist(), df['ndvi'].tolist()
    slope, direction = trend_stats(data)
    xm = sum(years)/len(years); ym = sum(ndvis)/len(ndvis)
    tline = [slope*(y - xm) + ym for y in years]
    fig = go.Figure()
    fig.add_hrect(y0=0.6,y1=1.0,fillcolor="rgba(39,174,96,0.04)",line_width=0)
    fig.add_hrect(y0=0.3,y1=0.6,fillcolor="rgba(230,126,34,0.03)",line_width=0)
    fig.add_hrect(y0=0.0,y1=0.3,fillcolor="rgba(192,57,43,0.04)",line_width=0)
    fig.add_trace(go.Scatter(
        x=years, y=tline, mode='lines', name='Trend',
        line=dict(color='rgba(64,145,108,0.35)', width=1.5, dash='dash')
    ))
    fig.add_trace(go.Scatter(
        x=years, y=ndvis, mode='lines+markers', name='Annual NDVI',
        line=dict(color=C['accent'], width=2.5),
        marker=dict(size=9, color=C['dark'], line=dict(color=C['white'], width=2)),
        fill='tozeroy', fillcolor='rgba(64,145,108,0.08)',
        hovertemplate='<b>%{x}</b>: %{y:.4f}<extra></extra>'
    ))
    arrow = "↑" if direction=="improving" else ("↓" if direction=="declining" else "→")
    fig.update_layout(**CHART_LAYOUT,
        title=dict(
            text=f"Multi-Year NDVI — {location}  ({arrow} {direction})",
            font=dict(size=14, color=C['dark'], family="Playfair Display")
        ),
        xaxis=dict(**_GRID, tickmode='linear', dtick=1),
        yaxis=dict(**_GRID, range=[0, 1]),
        legend=dict(orientation='h', y=1.08, x=1, xanchor='right')
    )
    return fig

def chart_to_png(fig, w=560, h=220):
    """Export plotly fig to PNG bytes for PDF embedding."""
    try:
        return fig.to_image(format="png", width=w, height=h, scale=2)
    except:
        return None


# ══════════════════════════════════════════════════════════════════════════════
# STATUS + CARBON UI
# ══════════════════════════════════════════════════════════════════════════════
def status_banner(pct):
    if pct < -10:
        cls, icon = "sb-critical", "🚨"
        title = "Degradation Alert"
        desc  = f"NDVI dropped <strong>{abs(pct):.1f}%</strong>. Active deforestation or severe stress detected. Ground verification recommended."
    elif pct < -5:
        cls, icon = "sb-warning", "⚠️"
        title = "Moderate Change"
        desc  = f"NDVI decreased <strong>{abs(pct):.1f}%</strong>. Possible selective logging or early encroachment. Increase monitoring frequency."
    elif pct >= 0:
        cls, icon = "sb-good", "✅"
        title = "Forest Healthy"
        desc  = f"NDVI {'increased <strong>+'+str(round(pct,1))+'%</strong>' if pct > 0 else 'stable'}. No significant degradation detected."
    else:
        cls, icon = "sb-good", "🟡"
        title = "Minor Variation"
        desc  = f"NDVI change of <strong>{pct:.1f}%</strong> within normal seasonal range."
    st.markdown(f"""
    <div class="status-banner {cls}">
      <div class="sb-icon">{icon}</div>
      <div><div class="sb-title">{title}</div><div class="sb-desc">{desc}</div></div>
    </div>""", unsafe_allow_html=True)

def carbon_panel(cd):
    if not cd: return
    change_cell = ""
    if "co2_delta" in cd:
        dv = cd["co2_delta"]
        col = C["danger"] if dv < 0 else C["good"]
        arrow = "▼" if dv < 0 else "▲"
        change_cell = f"""<div class="cp-cell">
          <div class="cp-lbl">CO&#8322;e Change</div>
          <div class="cp-val" style="color:{col};">{arrow}{abs(dv):,}</div>
          <div class="cp-unit">t CO&#8322;e</div></div>"""
    st.markdown(f"""
    <div class="carbon-panel">
      <div class="cp-title">Carbon Stock Estimate — Satellite Based</div>
      <div class="cp-grid">
        <div class="cp-cell">
          <div class="cp-lbl">Above-Ground Biomass</div>
          <div class="cp-val">{cd['agb_ha']:,.0f}</div>
          <div class="cp-unit">t ha&#8315;&#185;</div>
        </div>
        <div class="cp-cell">
          <div class="cp-lbl">Total Carbon Stock</div>
          <div class="cp-val">{cd['total_c']:,}</div>
          <div class="cp-unit">t C</div>
        </div>
        <div class="cp-cell">
          <div class="cp-lbl">Total CO&#8322; Equivalent</div>
          <div class="cp-val">{cd['total_co2']:,}</div>
          <div class="cp-unit">t CO&#8322;e</div>
        </div>
        {change_cell}
      </div>
      <div class="cp-note">
        Indicative estimates · FAO/ICIMOD Nepal values ·
        Forest type: {cd['ftype'].replace('_',' ').title()} ·
        Area: {cd['area_ha']:,} ha · Field calibration required for certified credits
      </div>
    </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# AI REPORT — GROQ
# ══════════════════════════════════════════════════════════════════════════════
def call_groq(api_key, loc, lat, lon, y1, y2, sm, em, n1, n2, dpct, ts, cd, td):
    try:
        from groq import Groq
    except ImportError:
        return None, "install_groq"
    try:
        client = Groq(api_key=api_key)
        status = "CRITICAL" if dpct<-10 else "WARNING" if dpct<-5 else "STABLE" if dpct<0 else "HEALTHY"
        carbon_str = f"CO2e stock: {cd['co2_ha']} t CO2e/ha, total {cd['total_co2']:,} t CO2e" if cd else ""
        trend_str  = "Annual NDVI: " + ", ".join(f"{d['year']}:{d['ndvi']}" for d in td) if td else ""
        prompt = f"""Senior environmental scientist specializing in Himalayan forest MRV, Nepal.

DATA:
Location: {loc} ({lat:.4f}N {lon:.4f}E)
Period: {MN[sm]}-{MN[em]}, {y1} vs {y2}
NDVI {y1}: {f'{n1:.4f}' if n1 else 'N/A'} | NDVI {y2}: {f'{n2:.4f}' if n2 else 'N/A'}
Change: {dpct:+.2f}% | Status: {status}
{carbon_str}
{trend_str}

Return ONLY valid JSON (no markdown):
{{"executive_summary":"2-3 sentence overview.",
"key_findings":["f1","f2","f3","f4"],
"vegetation_analysis":"paragraph with specific numbers.",
"carbon_implications":"paragraph on CO2e implications.",
"risk_level":"LOW|MEDIUM|HIGH|CRITICAL",
"risk_assessment":"paragraph on risk drivers.",
"recommendations":["r1","r2","r3","r4"],
"data_confidence":"data quality notes.",
"next_monitoring":"timeframe suggestion."}}"""
        resp = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role":"user","content":prompt}],
            temperature=0.25, max_tokens=1400
        )
        raw = resp.choices[0].message.content.strip().replace("```json","").replace("```","").strip()
        return json.loads(raw), None
    except json.JSONDecodeError as e:
        return None, f"JSON error: {e}"
    except Exception as e:
        return None, str(e)

def render_report_card(rd, loc, lat, lon, y1, y2, n1, n2, dpct, sm, em):
    risk = rd.get("risk_level", "MEDIUM")
    risk_colors = {"LOW": C["good"], "MEDIUM": C["warn"], "HIGH": C["danger"], "CRITICAL": C["danger"]}
    rc   = risk_colors.get(risk, C["slate"])
    n1s  = f"{n1:.4f}" if n1 else "N/A"
    n2s  = f"{n2:.4f}" if n2 else "N/A"
    dpct_color = C["danger"] if dpct < -5 else C["good"]
    today = datetime.now().strftime("%d %B %Y")

    findings_html = "".join(
        f'<div style="padding:5px 0;border-bottom:1px solid {C["mist"]};">&#x2022; {f}</div>'
        for f in rd.get("key_findings", [])
    )
    recs_html = "".join(
        f'<div style="padding:5px 0;border-bottom:1px solid {C["mist"]};"><strong style="color:{C["accent"]}">{i+1}.</strong> {r}</div>'
        for i, r in enumerate(rd.get("recommendations", []))
    )
    exec_sum      = rd.get("executive_summary", "")
    veg_analysis  = rd.get("vegetation_analysis", "")
    carbon_impl   = rd.get("carbon_implications", "")
    risk_assess   = rd.get("risk_assessment", "")
    data_conf     = rd.get("data_confidence", "N/A")
    next_mon      = rd.get("next_monitoring", "N/A")

    st.markdown(f"""
    <div class="rpt-wrap">
      <div class="rpt-head">
        <div>
          <div class="rpt-head-title">Forest Health Due Diligence Report</div>
          <div style="color:{C['sage']};font-size:0.78rem;margin-top:2px;">{loc} &middot; {lat:.4f}&deg;N, {lon:.4f}&deg;E</div>
        </div>
        <div class="rpt-head-meta">
          <div>{today}</div>
          <div>{MS[sm]}&ndash;{MS[em]} &middot; {y1} vs {y2}</div>
          <div style="margin-top:4px;">
            <span class="risk-badge" style="background:{rc}22;color:{rc};border:1px solid {rc}66;">{risk} RISK</span>
          </div>
        </div>
      </div>
      <div class="rpt-body">
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:0.75rem;margin-bottom:1.25rem;">
          <div class="rpt-box" style="text-align:center;">
            <div style="font-size:0.68rem;font-weight:700;letter-spacing:0.07em;text-transform:uppercase;color:{C['accent']};margin-bottom:4px;">NDVI {y1}</div>
            <div style="font-family:'Playfair Display',serif;font-size:1.5rem;color:{C['dark']};">{n1s}</div>
          </div>
          <div class="rpt-box" style="text-align:center;">
            <div style="font-size:0.68rem;font-weight:700;letter-spacing:0.07em;text-transform:uppercase;color:{C['accent']};margin-bottom:4px;">NDVI {y2}</div>
            <div style="font-family:'Playfair Display',serif;font-size:1.5rem;color:{C['dark']};">{n2s}</div>
          </div>
          <div class="rpt-box" style="text-align:center;">
            <div style="font-size:0.68rem;font-weight:700;letter-spacing:0.07em;text-transform:uppercase;color:{C['accent']};margin-bottom:4px;">Change</div>
            <div style="font-family:'Playfair Display',serif;font-size:1.5rem;color:{dpct_color};">{dpct:+.1f}%</div>
          </div>
        </div>
        <div class="rpt-sec">Executive Summary</div>
        <div class="rpt-box">{exec_sum}</div>
        <div class="rpt-sec">Key Findings</div>
        <div class="rpt-box">{findings_html}</div>
        <div class="rpt-sec">Vegetation Health Analysis</div>
        <div class="rpt-box">{veg_analysis}</div>
        <div class="rpt-sec">Carbon Stock Implications</div>
        <div class="rpt-box">{carbon_impl}</div>
        <div class="rpt-sec">Risk Assessment</div>
        <div class="rpt-box" style="border-left:3px solid {rc};">
          <strong style="color:{rc};">Risk Level: {risk}</strong><br/><br/>{risk_assess}
        </div>
        <div class="rpt-sec">Recommendations</div>
        <div class="rpt-box">{recs_html}</div>
        <div class="rpt-kv">
          <div class="rpt-box">
            <div style="font-size:0.68rem;font-weight:700;letter-spacing:0.07em;text-transform:uppercase;color:{C['accent']};margin-bottom:4px;">Data Confidence</div>
            {data_conf}
          </div>
          <div class="rpt-box">
            <div style="font-size:0.68rem;font-weight:700;letter-spacing:0.07em;text-transform:uppercase;color:{C['accent']};margin-bottom:4px;">Next Monitoring</div>
            {next_mon}
          </div>
        </div>
      </div>
      <div class="rpt-foot">
        <div class="rft">Sentinel-2 SR &middot; TerrAI Digital MRV &middot; Estimates pending field validation</div>
        <div class="seal">&#9649; Satellite Integrity Seal</div>
      </div>
    </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PDF BUILDER  (v3.1 — satellite map images replacing chart-only section)
# ══════════════════════════════════════════════════════════════════════════════
def build_pdf(rd, loc, lat, lon, buf_km, area_ha, y1, y2, sm, em,
              n1, n2, dpct, cd, td, ts,
              monthly_fig=None, trend_fig=None):

    buf   = io.BytesIO()
    W, H  = A4
    MAR   = 18*mm
    CW    = W - 2*MAR

    def S(name, **kw):
        base = dict(fontName="Helvetica", fontSize=9.5, leading=14,
                    textColor=RL["ink"], spaceAfter=4)
        base.update(kw)
        return ParagraphStyle(name, **base)

    styles = {
        "h_title":  S("ht", fontName="Helvetica-Bold", fontSize=20, textColor=colors.white, spaceAfter=2),
        "h_sub":    S("hs", fontSize=9,  textColor=RL["sage"],  spaceAfter=0),
        "h1":       S("h1", fontName="Helvetica-Bold", fontSize=13, textColor=RL["dark"], spaceBefore=10, spaceAfter=5),
        "h2":       S("h2", fontName="Helvetica-Bold", fontSize=10, textColor=RL["mid"],  spaceBefore=7,  spaceAfter=3),
        "body":     S("bd", fontSize=9, leading=14, spaceAfter=5),
        "bullet":   S("bl", fontSize=9, leading=13, leftIndent=12, spaceAfter=3),
        "note":     S("nt", fontSize=7.5, leading=11, textColor=RL["slate"],
                       fontName="Helvetica-Oblique", spaceAfter=4),
        "th":       S("th", fontName="Helvetica-Bold", fontSize=8.5,
                       textColor=colors.white, alignment=TA_CENTER),
        "td":       S("td", fontSize=8.5, leading=12),
        "tdc":      S("tdc",fontSize=8.5, leading=12, alignment=TA_CENTER),
        "footer":   S("ft", fontSize=7,   textColor=RL["slate"], alignment=TA_CENTER),
        "map_cap":  S("mc", fontSize=7.5, textColor=RL["slate"], alignment=TA_CENTER, spaceAfter=6),
    }

    risk      = rd.get("risk_level","N/A") if rd else "N/A"
    risk_clr  = {"LOW":RL["good"],"MEDIUM":RL["warn"],"HIGH":RL["danger"],"CRITICAL":RL["danger"]}.get(risk, RL["slate"])
    gen_date  = datetime.now().strftime("%d %B %Y, %H:%M UTC")
    n1s = f"{n1:.4f}" if n1 else "N/A"
    n2s = f"{n2:.4f}" if n2 else "N/A"

    story = []

    # ── Banner ──
    banner = Table([[
        Paragraph("<b>TerrAI</b>", styles["h_title"]),
        Paragraph(f"Risk: <b>{risk}</b>", S("rs",fontName="Helvetica-Bold",fontSize=10,
                   textColor=colors.white, alignment=TA_CENTER))
    ]], colWidths=[CW-40*mm, 40*mm])
    banner.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), RL["dark"]),
        ("BACKGROUND",    (1,0),(1,0),   risk_clr),
        ("TOPPADDING",    (0,0),(-1,-1), 14),
        ("BOTTOMPADDING", (0,0),(-1,-1), 14),
        ("LEFTPADDING",   (0,0),(0,0),   14),
        ("RIGHTPADDING",  (1,0),(1,0),   10),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
    ]))
    story.append(banner)

    subrow = Table([[
        Paragraph(f"Forest Health Due Diligence Report — {loc}", styles["h_sub"]),
        Paragraph(f"Generated: {gen_date}", S("gs",fontSize=8.5,textColor=RL["sage"],alignment=TA_RIGHT))
    ]], colWidths=[CW*0.65, CW*0.35])
    subrow.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), RL["mid"]),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LEFTPADDING",   (0,0),(0,0),   14),
        ("RIGHTPADDING",  (1,0),(1,0),   10),
    ]))
    story.append(subrow)
    story.append(Spacer(1, 7*mm))

    # ── Key metrics ──
    def mcell(lbl, val, unit=""):
        t = Table([
            [Paragraph(lbl.upper(), S("ml",fontSize=6.5,fontName="Helvetica-Bold",
                                       textColor=RL["accent"],alignment=TA_CENTER))],
            [Paragraph(str(val),    S("mv",fontSize=15,fontName="Helvetica-Bold",
                                       textColor=RL["dark"],alignment=TA_CENTER))],
            [Paragraph(unit,        S("mu",fontSize=7,textColor=RL["slate"],alignment=TA_CENTER))],
        ], colWidths=["100%"])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0),(-1,-1), RL["pale"]),
            ("BOX",        (0,0),(-1,-1), 0.5, RL["border"]),
            ("TOPPADDING", (0,0),(-1,-1), 7),("BOTTOMPADDING",(0,0),(-1,-1),7),
            ("LEFTPADDING",(0,0),(-1,-1), 5),("RIGHTPADDING",  (0,0),(-1,-1),5),
        ]))
        return t

    cw4 = (CW - 9*mm) / 4
    mrow = Table([[
        mcell(f"NDVI {y1}", n1s),
        mcell(f"NDVI {y2}", n2s),
        mcell("Change", f"{dpct:+.1f}%"),
        mcell("Area", f"{area_ha:,.0f}" if area_ha else f"{math.pi*buf_km**2*100:.0f}", "hectares"),
    ]], colWidths=[cw4]*4)
    mrow.setStyle(TableStyle([
        ("LEFTPADDING", (0,0),(-1,-1),2),("RIGHTPADDING",(0,0),(-1,-1),2),
        ("TOPPADDING",  (0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0),
    ]))
    story.append(mrow)
    story.append(Spacer(1, 5*mm))

    # ── Params table ──
    story.append(HRFlowable(width="100%", thickness=1, color=RL["mist"], spaceAfter=3))
    story.append(Paragraph("Analysis Parameters", styles["h1"]))
    ptbl = Table([
        [Paragraph("Parameter", styles["th"]), Paragraph("Value", styles["th"])],
        ["Location",        loc],
        ["Coordinates",     f"{lat:.4f} N, {lon:.4f} E"],
        ["Analysis Radius", f"{buf_km} km"],
        ["Season",          f"{MN[sm]} to {MN[em]}"],
        ["Years",           f"{y1} vs {y2}"],
        ["Satellite",       "Sentinel-2 SR, 10 m resolution"],
        ["Report Date",     gen_date],
    ], colWidths=[CW*0.38, CW*0.62])
    ptbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0),  RL["dark"]),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [colors.white, RL["pale"]]),
        ("GRID",          (0,0),(-1,-1), 0.3, RL["mist"]),
        ("FONTSIZE",      (0,0),(-1,-1), 8.5),
        ("TOPPADDING",    (0,0),(-1,-1), 4),("BOTTOMPADDING",(0,0),(-1,-1),4),
        ("LEFTPADDING",   (0,0),(-1,-1), 7),
        ("FONTNAME",      (0,1),(0,-1),  "Helvetica-Bold"),
        ("TEXTCOLOR",     (0,1),(0,-1),  RL["accent"]),
    ]))
    story.append(ptbl)
    story.append(Spacer(1, 4*mm))

    # ══════════════════════════════════════════════════════════════════════════
    # SATELLITE MAP IMAGES (NEW v3.1)
    # ══════════════════════════════════════════════════════════════════════════
    story.append(HRFlowable(width="100%", thickness=1, color=RL["mist"], spaceAfter=3))
    story.append(Paragraph("Satellite Map — AOI Comparison", styles["h1"]))
    story.append(Paragraph(
        f"Area of interest: {loc} · {lat:.4f}°N, {lon:.4f}°E · Radius {buf_km} km · "
        f"Gold circle marks the analysis boundary. Left = {y1}, Right = {y2}.",
        styles["note"]
    ))

    # Build the satellite comparison map image
    sat_png = build_comparison_map_image(lat, lon, buf_km, y1, y2, n1, n2, width=560, height=280)
    diff_png = get_ndvi_diff_image_png(lat, lon, buf_km, y1, y2, n1, n2, width=560, height=200)

    map_cells_added = False

    if sat_png and diff_png:
        # Side-by-side: comparison map + bar chart
        half_w = (CW - 4*mm) / 2
        try:
            sat_io  = io.BytesIO(sat_png);  sat_io.seek(0)
            diff_io = io.BytesIO(diff_png); diff_io.seek(0)

            sat_img  = RLImage(sat_io,  width=half_w, height=half_w * 0.55)
            diff_img = RLImage(diff_io, width=half_w, height=half_w * 0.55)

            map_tbl = Table([
                [sat_img, diff_img],
                [Paragraph(f"AOI Overview — {y1} vs {y2}<br/>Gold circle = {buf_km} km analysis radius",
                           styles["map_cap"]),
                 Paragraph(f"NDVI Change: {dpct:+.1f}%<br/>{y1}: {n1s} → {y2}: {n2s}",
                           styles["map_cap"])],
            ], colWidths=[half_w, half_w])
            map_tbl.setStyle(TableStyle([
                ("ALIGN",         (0,0),(-1,-1), "CENTER"),
                ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
                ("LEFTPADDING",   (0,0),(-1,-1), 2),
                ("RIGHTPADDING",  (0,0),(-1,-1), 2),
                ("TOPPADDING",    (0,0),(-1,-1), 2),
                ("BOTTOMPADDING", (0,0),(-1,-1), 2),
                ("BOX",           (0,0),(0,0),   0.5, RL["mist"]),
                ("BOX",           (1,0),(1,0),   0.5, RL["mist"]),
            ]))
            story.append(map_tbl)
            map_cells_added = True
        except Exception:
            pass

    if not map_cells_added and sat_png:
        try:
            sat_io = io.BytesIO(sat_png); sat_io.seek(0)
            sat_img = RLImage(sat_io, width=CW, height=CW * 0.45)
            story.append(sat_img)
            story.append(Paragraph(
                f"AOI: {loc} · Gold circle = {buf_km} km radius · {y1} vs {y2}",
                styles["map_cap"]
            ))
            map_cells_added = True
        except Exception:
            pass

    if not map_cells_added:
        story.append(Paragraph(
            "Satellite map image unavailable. Install staticmap or requests for map rendering.",
            styles["note"]
        ))

    story.append(Spacer(1, 4*mm))

    # ── NDVI Timeseries Charts ──
    story.append(HRFlowable(width="100%", thickness=1, color=RL["mist"], spaceAfter=3))
    story.append(Paragraph("NDVI Timeseries Analysis", styles["h1"]))

    charts_added = False
    if monthly_fig or trend_fig:
        img_w = CW
        if monthly_fig and trend_fig:
            img_w = (CW - 4*mm) / 2

        chart_cells = []
        for fig, caption in [(monthly_fig, f"Monthly NDVI — {MS[sm]} to {MS[em]} {y2}"),
                             (trend_fig,   "Multi-Year NDVI Trend (2019–present)")]:
            if fig:
                png = chart_to_png(fig, w=int(img_w/mm*1.5), h=150)
                if png:
                    img_io = io.BytesIO(png)
                    img_io.seek(0)
                    rl_img = RLImage(img_io, width=img_w, height=img_w*0.42)
                    cap = Paragraph(caption, S("cap",fontSize=7.5,textColor=RL["slate"],alignment=TA_CENTER))
                    chart_cells.append([rl_img, cap])

        if len(chart_cells) == 2:
            chart_tbl = Table([
                [chart_cells[0][0], chart_cells[1][0]],
                [chart_cells[0][1], chart_cells[1][1]],
            ], colWidths=[(CW-4*mm)/2, (CW-4*mm)/2])
            chart_tbl.setStyle(TableStyle([
                ("ALIGN",  (0,0),(-1,-1), "CENTER"),
                ("VALIGN", (0,0),(-1,-1), "MIDDLE"),
                ("LEFTPADDING",  (0,0),(-1,-1), 2),
                ("RIGHTPADDING", (0,0),(-1,-1), 2),
            ]))
            story.append(chart_tbl)
            charts_added = True
        elif len(chart_cells) == 1:
            img, cap = chart_cells[0]
            story.append(img)
            story.append(cap)
            charts_added = True

    if not charts_added:
        story.append(Paragraph("NDVI chart images not available in this export.", styles["note"]))

    story.append(Spacer(1, 4*mm))

    # ── Carbon stock ──
    if cd:
        story.append(HRFlowable(width="100%", thickness=1, color=RL["mist"], spaceAfter=3))
        story.append(Paragraph("Carbon Stock Estimate", styles["h1"]))
        crows = [
            [Paragraph("Metric", styles["th"]),
             Paragraph("Per Hectare", styles["th"]),
             Paragraph("Total", styles["th"])],
            ["Above-Ground Biomass",
             f"{cd['agb_ha']:,.0f} t/ha",
             f"{cd['agb_ha']*cd['area_ha']:,.0f} t"],
            ["Below-Ground Biomass",
             f"{cd['bgb_ha']:,.0f} t/ha",
             f"{cd['bgb_ha']*cd['area_ha']:,.0f} t"],
            ["Total Biomass",
             f"{cd['bio_ha']:,.0f} t/ha",
             f"{cd['bio_ha']*cd['area_ha']:,.0f} t"],
            ["Carbon Stock",
             f"{cd['c_ha']:,.0f} tC/ha",
             f"{cd['total_c']:,.0f} t C"],
            [Paragraph("CO<sub>2</sub> Equivalent", styles["td"]),
             Paragraph(f"{cd['co2_ha']:,.0f} t CO<sub>2</sub>e/ha", styles["tdc"]),
             Paragraph(f"{cd['total_co2']:,.0f} t CO<sub>2</sub>e", styles["tdc"])],
        ]
        if "co2_delta" in cd:
            sign = "+" if cd["co2_delta"] >= 0 else ""
            crows.append([
                Paragraph("CO<sub>2</sub>e Change", styles["td"]),
                f"{cd['change_pct']:+.1f}%",
                Paragraph(f"{sign}{cd['co2_delta']:,} t CO<sub>2</sub>e", styles["tdc"])
            ])
        ctbl = Table(crows, colWidths=[CW*0.44, CW*0.28, CW*0.28])
        ctbl.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,0),  RL["dark"]),
            ("ROWBACKGROUNDS",(0,1),(-1,-1), [colors.white, RL["pale"]]),
            ("GRID",          (0,0),(-1,-1), 0.3, RL["mist"]),
            ("FONTSIZE",      (0,0),(-1,-1), 8.5),
            ("ALIGN",         (1,0),(-1,-1), "CENTER"),
            ("TOPPADDING",    (0,0),(-1,-1), 4),("BOTTOMPADDING",(0,0),(-1,-1),4),
            ("LEFTPADDING",   (0,0),(-1,-1), 7),
            ("FONTNAME",      (0,1),(0,-1),  "Helvetica-Bold"),
            ("TEXTCOLOR",     (0,1),(0,-1),  RL["dark"]),
            ("BACKGROUND",    (0,-1),(-1,-1), colors.HexColor("#FFFBEB"))
                if "co2_delta" in cd else ("NOP", (0,0),(0,0)),
        ]))
        story.append(ctbl)
        story.append(Paragraph(
            f"Indicative estimates only. Forest type: {cd['ftype'].replace('_',' ').title()}. "
            "Source: FAO/ICIMOD Nepal. Field calibration required before use in verified credits.",
            styles["note"]
        ))

    # ── Multi-year trend table ──
    if td and len(td) > 1:
        story.append(HRFlowable(width="100%", thickness=1, color=RL["mist"], spaceAfter=3))
        story.append(Paragraph("Annual NDVI Record", styles["h1"]))
        thead = [Paragraph(str(d["year"]), styles["th"]) for d in td]
        tvals = [str(d["ndvi"]) for d in td]
        col_w = CW / (len(td)+1)
        ttbl = Table([
            [Paragraph("Year", styles["th"])] + thead,
            [Paragraph("NDVI", S("tnl",fontName="Helvetica-Bold",fontSize=8.5,
                                  textColor=RL["accent"]))] + tvals
        ], colWidths=[col_w]*(len(td)+1))
        ttbl.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0), RL["dark"]),
            ("GRID",      (0,0),(-1,-1),0.3, RL["mist"]),
            ("FONTSIZE",  (0,0),(-1,-1),8.5),
            ("ALIGN",     (0,0),(-1,-1),"CENTER"),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white, RL["pale"]]),
            ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),
        ]))
        story.append(ttbl)

    # ── AI sections ──
    if rd:
        story.append(PageBreak())
        story.append(HRFlowable(width="100%", thickness=1, color=RL["mist"], spaceAfter=3))
        story.append(Paragraph("AI-Generated Due Diligence Analysis", styles["h1"]))
        story.append(Paragraph(
            "Generated by Llama 3 (Groq) from satellite inputs. Not certified verification. "
            "Review by qualified environmental scientists required.",
            styles["note"]
        ))
        story.append(Spacer(1, 3*mm))

        for title, key in [
            ("Executive Summary",         "executive_summary"),
            ("Vegetation Health Analysis","vegetation_analysis"),
            ("Carbon Stock Implications", "carbon_implications"),
            ("Risk Assessment",           "risk_assessment"),
            ("Data Confidence",           "data_confidence"),
            ("Next Monitoring",           "next_monitoring"),
        ]:
            val = rd.get(key,"")
            if val:
                story.append(Paragraph(title, styles["h2"]))
                story.append(Paragraph(val, styles["body"]))

        for title, key in [("Key Findings","key_findings"),("Recommendations","recommendations")]:
            items = rd.get(key, [])
            if items:
                story.append(Paragraph(title, styles["h2"]))
                for i, item in enumerate(items):
                    prefix = f"{i+1}." if key=="recommendations" else "•"
                    story.append(Paragraph(f"{prefix}  {item}", styles["bullet"]))

    # ── Footer ──
    story.append(Spacer(1, 6*mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=RL["mist"]))
    ftbl = Table([[
        Paragraph("Satellite data: Sentinel-2 SR via Google Earth Engine", styles["footer"]),
        Paragraph("TerrAI · Digital MRV Platform · Nepal", styles["footer"]),
        Paragraph("Satellite estimates pending field validation", styles["footer"]),
    ]], colWidths=[CW/3]*3)
    ftbl.setStyle(TableStyle([
        ("TOPPADDING",    (0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),
        ("ALIGN",         (0,0),(0,-1),"LEFT"),
        ("ALIGN",         (1,0),(1,-1),"CENTER"),
        ("ALIGN",         (2,0),(2,-1),"RIGHT"),
    ]))
    story.append(ftbl)

    def on_page(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(RL["dark"])
        canvas.rect(0, 0, W, 7*mm, fill=1, stroke=0)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica", 6.5)
        canvas.drawString(MAR, 2.2*mm, f"TerrAI — {loc} — {gen_date}")
        canvas.drawRightString(W-MAR, 2.2*mm,
                               f"Page {doc.page}  |  CONFIDENTIAL — Satellite estimates only")
        canvas.restoreRect()

    def on_page(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(RL["dark"])
        canvas.rect(0, 0, W, 7*mm, fill=1, stroke=0)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica", 6.5)
        canvas.drawString(MAR, 2.2*mm, f"TerrAI — {loc} — {gen_date}")
        canvas.drawRightString(W-MAR, 2.2*mm,
                               f"Page {doc.page}  |  CONFIDENTIAL — Satellite estimates only")
        canvas.restoreState()

    doc = SimpleDocTemplate(buf, pagesize=A4,
                             leftMargin=MAR, rightMargin=MAR,
                             topMargin=MAR, bottomMargin=16*mm,
                             title=f"TerrAI — {loc}", author="TerrAI")
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return buf.getvalue()


# ══════════════════════════════════════════════════════════════════════════════
# TIER 1 — FEATURE 1: NDVI DIFFERENCE HOTSPOT MAP
# ══════════════════════════════════════════════════════════════════════════════
def add_ndvi_diff_layer(folium_map, composite1, composite2, aoi):
    try:
        ndvi1 = composite1.select('NDVI')
        ndvi2 = composite2.select('NDVI')
        diff  = ndvi2.subtract(ndvi1).rename('diff')
        vis = {
            'min': -0.3, 'max': 0.3,
            'palette': ['#C0392B','#E74C3C','#F39C12','#F0F0F0','#82C341','#27AE60','#1A5E20']
        }
        tile_url = diff.getMapId(vis)['tile_fetcher'].url_format
        folium.TileLayer(
            tiles=tile_url, attr='GEE',
            name='NDVI Change (red=loss, green=gain)',
            overlay=True, control=True, opacity=0.80
        ).add_to(folium_map)
        return True
    except:
        return False


# ══════════════════════════════════════════════════════════════════════════════
# TIER 1 — FEATURE 2: SUPABASE AUTH + SAVED FORESTS
# ══════════════════════════════════════════════════════════════════════════════
def get_supabase():
    url = os.getenv('SUPABASE_URL', '')
    key = os.getenv('SUPABASE_ANON_KEY', '')
    if not url or not key or not SUPABASE_OK:
        return None
    try:
        return create_client(url, key)
    except:
        return None

def auth_sidebar(sb):
    if sb is None:
        return None
    if 'terrai_user' in st.session_state:
        u = st.session_state['terrai_user']
        st.markdown(f"""
        <div style="background:rgba(64,145,108,0.15);border:1px solid rgba(116,198,157,0.3);
                    border-radius:8px;padding:0.6rem 0.8rem;margin-bottom:0.5rem;">
          <div style="font-size:0.7rem;color:{C['sage']};font-weight:700;letter-spacing:0.06em;text-transform:uppercase;">Signed in as</div>
          <div style="font-size:0.82rem;color:{C['white']};margin-top:2px;">{u.get('email','')}</div>
        </div>""", unsafe_allow_html=True)
        if st.button("Sign out", use_container_width=True):
            del st.session_state['terrai_user']
            st.rerun()
        return u
    with st.expander("Sign in / Create account"):
        tab_in, tab_up = st.tabs(["Sign in", "Sign up"])
        with tab_in:
            email = st.text_input("Email", key="login_email")
            pwd   = st.text_input("Password", type="password", key="login_pwd")
            if st.button("Sign in", key="do_login", use_container_width=True):
                try:
                    res = sb.auth.sign_in_with_password({"email": email, "password": pwd})
                    st.session_state['terrai_user'] = {"id": res.user.id, "email": res.user.email}
                    st.rerun()
                except Exception as e:
                    st.error(f"Login failed: {e}")
        with tab_up:
            email2 = st.text_input("Email", key="reg_email")
            pwd2   = st.text_input("Password (min 6 chars)", type="password", key="reg_pwd")
            if st.button("Create account", key="do_register", use_container_width=True):
                try:
                    res = sb.auth.sign_up({"email": email2, "password": pwd2})
                    st.success("Account created — check your email to confirm.")
                except Exception as e:
                    st.error(f"Sign up failed: {e}")
    return None

def save_forest(sb, user_id, name, lat, lon, buf_km, forest_type, alert_email=""):
    if not sb: return False
    try:
        sb.table("saved_forests").insert({
            "user_id":     user_id,
            "name":        name,
            "lat":         lat,
            "lon":         lon,
            "buf_km":      buf_km,
            "forest_type": forest_type,
            "alert_email": alert_email,
            "created_at":  datetime.utcnow().isoformat(),
        }).execute()
        return True
    except:
        return False

def load_saved_forests(sb, user_id):
    if not sb: return []
    try:
        res = sb.table("saved_forests").select("*").eq("user_id", user_id).execute()
        return res.data or []
    except:
        return []

def delete_saved_forest(sb, forest_id):
    if not sb: return
    try:
        sb.table("saved_forests").delete().eq("id", forest_id).execute()
    except:
        pass


# ══════════════════════════════════════════════════════════════════════════════
# TIER 1 — FEATURE 3: EMAIL ALERT SYSTEM
# ══════════════════════════════════════════════════════════════════════════════
def send_alert_email(to_email, location_name, ndvi_change_pct, ndvi2, lat, lon):
    if not SMTP_OK:
        return False, "smtplib unavailable"
    from_email = os.getenv("ALERT_EMAIL_FROM", "")
    password   = os.getenv("ALERT_EMAIL_PASSWORD", "")
    smtp_host  = os.getenv("ALERT_SMTP_HOST", "smtp.gmail.com")
    smtp_port  = int(os.getenv("ALERT_SMTP_PORT", "587"))
    if not from_email or not password:
        return False, "ALERT_EMAIL_FROM and ALERT_EMAIL_PASSWORD not set in .env"
    severity = "CRITICAL" if ndvi_change_pct < -10 else "WARNING"
    color    = "#C0392B"  if severity == "CRITICAL" else "#E67E22"
    today    = datetime.now().strftime("%d %B %Y")
    html_body = f"""
    <html><body style="font-family:Inter,sans-serif;background:#f8f9fa;padding:0;margin:0;">
      <div style="max-width:560px;margin:32px auto;background:#fff;border-radius:12px;overflow:hidden;border:1px solid #e0e0e0;">
        <div style="background:#1A4731;padding:24px 28px;">
          <span style="font-size:22px;font-weight:700;color:#fff;">Terr</span><span style="font-size:22px;font-weight:700;color:#40916C;">AI</span>
          <div style="color:#74C69D;font-size:12px;margin-top:4px;letter-spacing:0.06em;text-transform:uppercase;">Forest Degradation Alert</div>
        </div>
        <div style="padding:28px;">
          <div style="background:{color}18;border:1px solid {color}44;border-left:4px solid {color};border-radius:8px;padding:14px 16px;margin-bottom:20px;">
            <div style="font-weight:700;color:{color};font-size:15px;">{severity} — {location_name}</div>
            <div style="color:#444;font-size:13px;margin-top:6px;">
              NDVI has changed by <strong>{ndvi_change_pct:+.1f}%</strong> — satellite analysis detected significant vegetation change.
            </div>
          </div>
          <table style="width:100%;border-collapse:collapse;font-size:13px;">
            <tr style="background:#F0FBF4;">
              <td style="padding:9px 12px;font-weight:600;color:#2D6A4F;border:1px solid #D8F3DC;">Location</td>
              <td style="padding:9px 12px;border:1px solid #D8F3DC;">{location_name}</td>
            </tr>
            <tr>
              <td style="padding:9px 12px;font-weight:600;color:#2D6A4F;border:1px solid #D8F3DC;">Coordinates</td>
              <td style="padding:9px 12px;border:1px solid #D8F3DC;">{lat:.4f}&deg;N, {lon:.4f}&deg;E</td>
            </tr>
            <tr style="background:#F0FBF4;">
              <td style="padding:9px 12px;font-weight:600;color:#2D6A4F;border:1px solid #D8F3DC;">Current NDVI</td>
              <td style="padding:9px 12px;border:1px solid #D8F3DC;">{ndvi2:.4f}</td>
            </tr>
            <tr>
              <td style="padding:9px 12px;font-weight:600;color:#2D6A4F;border:1px solid #D8F3DC;">NDVI Change</td>
              <td style="padding:9px 12px;color:{color};font-weight:700;border:1px solid #D8F3DC;">{ndvi_change_pct:+.1f}%</td>
            </tr>
            <tr style="background:#F0FBF4;">
              <td style="padding:9px 12px;font-weight:600;color:#2D6A4F;border:1px solid #D8F3DC;">Alert Date</td>
              <td style="padding:9px 12px;border:1px solid #D8F3DC;">{today}</td>
            </tr>
          </table>
          <p style="font-size:12px;color:#888;margin-top:20px;">
            This is an automated alert from the TerrAI Digital MRV platform. Log in to view the full analysis and PDF report.
            Satellite-based estimates only — field verification recommended.
          </p>
        </div>
        <div style="background:#1A4731;padding:12px 28px;font-size:11px;color:#74C69D;">
          TerrAI &middot; Digital MRV Platform &middot; Nepal &middot; Sentinel-2 SR via Google Earth Engine
        </div>
      </div>
    </body></html>"""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[TerrAI {severity}] {location_name} — NDVI {ndvi_change_pct:+.1f}%"
    msg["From"]    = from_email
    msg["To"]      = to_email
    msg.attach(MIMEText(html_body, "html"))
    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.login(from_email, password)
            server.sendmail(from_email, to_email, msg.as_string())
        return True, "sent"
    except Exception as e:
        return False, str(e)

def render_alert_setup(location_name, ndvi_change_pct, ndvi2, lat, lon):
    with st.expander("🔔 Email Alerts — get notified when this forest degrades"):
        alert_email = st.text_input(
            "Your email address",
            placeholder="you@example.com",
            help="TerrAI will email you when NDVI drops more than 5% for this forest."
        )
        threshold   = st.slider("Alert threshold (%)", -20, -1, -5)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Test alert email", use_container_width=True):
                if alert_email:
                    ok, msg = send_alert_email(alert_email, location_name, ndvi_change_pct, ndvi2, lat, lon)
                    if ok: st.success("Test email sent!")
                    else:
                        st.error(f"Failed: {msg}")
                        st.caption("Set ALERT_EMAIL_FROM and ALERT_EMAIL_PASSWORD in .env")
                else:
                    st.warning("Enter an email address first.")
        with col2:
            if ndvi_change_pct < threshold and alert_email:
                ok, msg = send_alert_email(alert_email, location_name, ndvi_change_pct, ndvi2, lat, lon)
                if ok: st.warning(f"⚡ Threshold crossed — alert sent to {alert_email}")
                else: st.caption(f"Auto-alert failed: {msg}")
        st.caption("Requires ALERT_EMAIL_FROM and ALERT_EMAIL_PASSWORD in .env · Works with Gmail App Passwords")


# ══════════════════════════════════════════════════════════════════════════════
# TIER 1 — FEATURE 4: DISTRICT BASELINE COMPARISON
# ══════════════════════════════════════════════════════════════════════════════
DISTRICT_BASELINE = {
    "Dolakha":       {"ndvi": 0.62, "forest_cover_pct": 48},
    "Sindhupalchok": {"ndvi": 0.58, "forest_cover_pct": 45},
    "Rasuwa":        {"ndvi": 0.66, "forest_cover_pct": 62},
    "Nuwakot":       {"ndvi": 0.55, "forest_cover_pct": 41},
    "Kavrepalanchok":{"ndvi": 0.54, "forest_cover_pct": 39},
    "Makwanpur":     {"ndvi": 0.60, "forest_cover_pct": 52},
    "Chitwan":       {"ndvi": 0.57, "forest_cover_pct": 44},
    "Nawalpur":      {"ndvi": 0.52, "forest_cover_pct": 37},
    "Palpa":         {"ndvi": 0.59, "forest_cover_pct": 49},
    "Gorkha":        {"ndvi": 0.63, "forest_cover_pct": 55},
    "Lamjung":       {"ndvi": 0.61, "forest_cover_pct": 53},
    "Kaski":         {"ndvi": 0.64, "forest_cover_pct": 58},
    "Tanahu":        {"ndvi": 0.56, "forest_cover_pct": 43},
    "Syangja":       {"ndvi": 0.57, "forest_cover_pct": 44},
    "Parbat":        {"ndvi": 0.60, "forest_cover_pct": 51},
    "Myagdi":        {"ndvi": 0.65, "forest_cover_pct": 60},
    "Baglung":       {"ndvi": 0.61, "forest_cover_pct": 54},
    "Dang":          {"ndvi": 0.54, "forest_cover_pct": 38},
    "Banke":         {"ndvi": 0.50, "forest_cover_pct": 34},
    "Bardiya":       {"ndvi": 0.55, "forest_cover_pct": 41},
    "Kailali":       {"ndvi": 0.51, "forest_cover_pct": 36},
    "Kanchanpur":    {"ndvi": 0.49, "forest_cover_pct": 33},
    "Ilam":          {"ndvi": 0.68, "forest_cover_pct": 63},
    "Taplejung":     {"ndvi": 0.70, "forest_cover_pct": 66},
    "Panchthar":     {"ndvi": 0.66, "forest_cover_pct": 60},
    "Dhankuta":      {"ndvi": 0.64, "forest_cover_pct": 57},
    "Solukhumbu":    {"ndvi": 0.55, "forest_cover_pct": 42},
    "Nepal (National Avg)": {"ndvi": 0.58, "forest_cover_pct": 45},
}

def render_district_comparison(forest_ndvi, selected_district="Nepal (National Avg)"):
    st.markdown('<div class="sec-label">Benchmark Comparison</div>', unsafe_allow_html=True)
    col_sel, _ = st.columns([1, 2])
    with col_sel:
        district = st.selectbox(
            "Compare against",
            list(DISTRICT_BASELINE.keys()),
            index=list(DISTRICT_BASELINE.keys()).index(selected_district),
            label_visibility="collapsed"
        )
    baseline = DISTRICT_BASELINE[district]
    bench_ndvi = baseline["ndvi"]
    forest_cover = baseline["forest_cover_pct"]
    diff = forest_ndvi - bench_ndvi
    diff_pct = (diff / bench_ndvi) * 100
    verdict_color = C["good"] if diff >= 0 else (C["danger"] if diff < -0.08 else C["warn"])
    verdict_word  = "Above average" if diff >= 0.02 else ("Below average" if diff < -0.02 else "At average")
    bar_forest = min(100, int((forest_ndvi / 1.0) * 100))
    bar_bench  = min(100, int((bench_ndvi  / 1.0) * 100))
    st.markdown(f"""
    <div style="background:{C['white']};border:1px solid {C['mist']};border-radius:12px;padding:1.25rem 1.5rem;margin-bottom:1.5rem;">
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:1.5rem;margin-bottom:1.25rem;">
        <div>
          <div style="font-size:0.68rem;font-weight:700;letter-spacing:0.07em;text-transform:uppercase;color:{C['accent']};margin-bottom:6px;">This Forest</div>
          <div style="font-family:'Playfair Display',serif;font-size:2rem;color:{C['dark']};">{forest_ndvi:.4f}</div>
          <div style="height:8px;background:{C['mist']};border-radius:4px;margin-top:8px;">
            <div style="height:100%;width:{bar_forest}%;background:{C['accent']};border-radius:4px;"></div>
          </div>
        </div>
        <div>
          <div style="font-size:0.68rem;font-weight:700;letter-spacing:0.07em;text-transform:uppercase;color:{C['slate']};margin-bottom:6px;">{district}</div>
          <div style="font-family:'Playfair Display',serif;font-size:2rem;color:{C['slate']};">{bench_ndvi:.4f}</div>
          <div style="height:8px;background:{C['mist']};border-radius:4px;margin-top:8px;">
            <div style="height:100%;width:{bar_bench}%;background:{C['slate']};border-radius:4px;opacity:0.5;"></div>
          </div>
        </div>
      </div>
      <div style="background:{verdict_color}12;border:1px solid {verdict_color}33;border-radius:8px;padding:0.75rem 1rem;display:flex;justify-content:space-between;align-items:center;">
        <div>
          <span style="font-weight:700;color:{verdict_color};">{verdict_word}</span>
          <span style="font-size:0.85rem;color:{C['slate']};margin-left:6px;">district benchmark</span>
        </div>
        <div style="font-family:'Playfair Display',serif;font-size:1.3rem;color:{verdict_color};">{diff:+.4f} ({diff_pct:+.1f}%)</div>
      </div>
      <div style="font-size:0.75rem;color:{C['slate']};margin-top:0.75rem;">
        {district} district avg forest cover: <strong>{forest_cover}%</strong> &middot;
        Benchmark NDVI from MODIS/Sentinel literature &middot; ICIMOD Nepal Forest Atlas
      </div>
    </div>""", unsafe_allow_html=True)
    return district


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    today = datetime.now().strftime("%d %B %Y")
    st.markdown(f"""
    <div class="topbar">
      <div class="terrai-wordmark">
        <span class="terrai-terr">Terr</span><span class="terrai-ai">AI</span>
        <span class="terrai-tag">Digital MRV<br>Nepal</span>
      </div>
      <div class="topbar-pills">
        <span class="pill">🛰 Sentinel-2</span>
        <span class="pill">🌿 Carbon MRV</span>
        <span class="pill">📈 Trend Analysis</span>
        <span class="pill">📅 Daily NDVI</span>
        <span class="pill">{today}</span>
      </div>
    </div>""", unsafe_allow_html=True)

    if not gee_init():
        st.stop()

    sb   = get_supabase()
    user = None

    # ── Sidebar ──────────────────────────────────────────────────────────────
    with st.sidebar:
        if sb:
            user = auth_sidebar(sb)
            if user:
                saved = load_saved_forests(sb, user["id"])
                if saved:
                    st.markdown("### Saved Forests")
                    for sf in saved:
                        c1, c2 = st.columns([3,1])
                        if c1.button(f"📌 {sf['name']}", key=f"load_{sf['id']}", use_container_width=True):
                            st.session_state['load_forest'] = sf
                        if c2.button("✕", key=f"del_{sf['id']}"):
                            delete_saved_forest(sb, sf['id'])
                            st.rerun()
            st.markdown("---")
        st.markdown("### Location")
        mode = st.radio("Input method", ["District / Forest", "Coordinates", "Upload GeoJSON"],
                        label_visibility="collapsed")

        aoi_custom, area_ha, uploaded_name = None, None, None

        if mode == "District / Forest":
            q = st.text_input("Search", placeholder="Filter locations…")
            locs = search_location(q) if q else sorted(get_all_locations().keys())
            sel  = st.selectbox("Location", locs) if locs else "Unknown"
            lat, lon = get_location_coords(sel) if locs else (NEPAL_CENTER['lat'], NEPAL_CENTER['lon'])
            selected_location = sel

        elif mode == "Coordinates":
            c1, c2 = st.columns(2)
            lat = c1.number_input("Lat", value=NEPAL_CENTER['lat'], min_value=26.0, max_value=31.0, format="%.4f")
            lon = c2.number_input("Lon", value=NEPAL_CENTER['lon'], min_value=80.0, max_value=89.0, format="%.4f")
            selected_location = f"Custom ({lat:.3f}°N, {lon:.3f}°E)"

        else:
            uf = st.file_uploader("GeoJSON boundary", type=["geojson","json"])
            if uf:
                try:
                    aoi_custom, lat, lon, area_ha, uploaded_name = parse_geojson(uf)
                    selected_location = uploaded_name
                    st.success(f"✓ {area_ha:,.0f} ha loaded")
                except ValueError as e:
                    st.error(str(e))
                    lat, lon = NEPAL_CENTER['lat'], NEPAL_CENTER['lon']
                    selected_location = "Upload failed"
            else:
                lat, lon = NEPAL_CENTER['lat'], NEPAL_CENTER['lon']
                selected_location = "Awaiting upload"

        if aoi_custom is None:
            buf_km = st.slider("Radius (km)", 1, 20, 5)
        else:
            buf_km = 5
            st.caption("Using uploaded boundary")

        st.markdown("### Time Period")
        st.caption("Jan–Mar avoids monsoon clouds")
        cur_yr = datetime.now().year
        c1, c2 = st.columns(2)
        y1 = c1.selectbox("Year 1", range(2019, cur_yr),   index=3)
        y2 = c2.selectbox("Year 2", range(2019, cur_yr+1), index=4)
        c1, c2 = st.columns(2)
        sm = c1.selectbox("Start", range(1,13), index=0,  format_func=lambda x: datetime(2000,x,1).strftime('%b'))
        em = c2.selectbox("End",   range(1,13), index=2,  format_func=lambda x: datetime(2000,x,1).strftime('%b'))

        st.markdown("### Options")
        forest_type   = st.selectbox("Forest type",
            list(NEPAL_CARBON.keys()),
            format_func=lambda x: x.replace('_',' ').title())
        run_multiyear = st.checkbox("Multi-year trend (2019–now)", value=True)
        show_hotspot  = st.checkbox("NDVI change hotspot map", value=True)
        gen_ai        = st.checkbox("AI due diligence report", value=True)
        groq_key      = os.getenv('GROQ_API_KEY','')
        if gen_ai and not groq_key:
            st.caption("Add GROQ_API_KEY to .env — free at console.groq.com")

        if user and sb:
            alert_email_save = st.text_input("Alert email (optional)", placeholder="you@example.com")
            if st.button("💾 Save this forest", use_container_width=True):
                ok = save_forest(sb, user["id"], selected_location, lat, lon, buf_km,
                                 forest_type, alert_email_save)
                st.success("Forest saved!") if ok else st.error("Save failed.")

        st.markdown("---")
        go = st.button("Analyse Forest", use_container_width=True)

    # ── Empty state ───────────────────────────────────────────────────────────
    if not go:
        st.markdown("""
        <div class="empty-state">
          <div class="empty-icon">🌳</div>
          <div class="empty-title">Configure your analysis</div>
          <div class="empty-sub">Select a location and time period in the sidebar, then click Analyse Forest to begin satellite-based forest health monitoring.</div>
        </div>""", unsafe_allow_html=True)

        m = folium.Map(location=[NEPAL_CENTER['lat'], NEPAL_CENTER['lon']],
                       zoom_start=NEPAL_CENTER['zoom'],
                       tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                       attr='Esri')
        st_folium(m, height=400, returned_objects=[], use_container_width=True)

        st.markdown("""
        <div class="feat-grid">
          <div class="feat-card"><div class="feat-ico">🛰️</div><div class="feat-title">Sentinel-2 Imagery</div><div class="feat-desc">10 m resolution, 5-day revisit. Cloud-masked composites optimised for Nepal's monsoon seasons.</div></div>
          <div class="feat-card"><div class="feat-ico">📅</div><div class="feat-title">Daily NDVI Explorer</div><div class="feat-desc">Browse every Sentinel-2 overpass date for your AOI. Pick exact acquisition dates and compute single-scene NDVI without compositing.</div></div>
          <div class="feat-card"><div class="feat-ico">📈</div><div class="feat-title">Multi-Year Trend</div><div class="feat-desc">Annual NDVI from 2019 to present with linear slope, degradation bands, and YoY table.</div></div>
          <div class="feat-card"><div class="feat-ico">📄</div><div class="feat-title">PDF Due Diligence</div><div class="feat-desc">Professional report with satellite map images and NDVI charts. Ready for NGO donors and VERRA submissions.</div></div>
        </div>""", unsafe_allow_html=True)
        return

    # ── Run analysis ──────────────────────────────────────────────────────────
    with st.spinner("Fetching satellite imagery…"):
        try:
            aoi = aoi_custom if aoi_custom else create_aoi_from_point(lat, lon, buf_km)
            if not area_ha:
                area_ha = math.pi * buf_km**2 * 100

            prog = st.progress(0, "Loading Year 1…")
            c1_ = get_sentinel_composite(aoi, f"{y1}-{sm:02d}-01", f"{y1}-{em:02d}-28")
            prog.progress(25, "Loading Year 2…")
            c2_ = get_sentinel_composite(aoi, f"{y2}-{sm:02d}-01", f"{y2}-{em:02d}-28")
            prog.progress(50, "Computing NDVI…")
            n1 = compute_mean_ndvi(c1_, aoi)
            n2 = compute_mean_ndvi(c2_, aoi)
            prog.progress(65, "Monthly time-series…")
            ts  = calculate_ndvi_timeseries(aoi, y2, sm, em) or []
            prog.progress(80, "Done.")
            prog.empty()

            dpct = ((n2 - n1) / n1 * 100) if (n1 and n2 and n1 != 0) else 0.0
            cd   = carbon_estimate(n2, area_ha, forest_type, dpct)

        except Exception as e:
            st.error(f"Analysis failed: {e}")
            st.info("Try adjusting the date range or location.")
            return

    st.success("Analysis complete")

    # ── Stat cards ──
    change_cls = "danger" if dpct<-10 else "warn" if dpct<-5 else "good"
    n1s = f"{n1:.4f}" if n1 else "N/A"
    n2s = f"{n2:.4f}" if n2 else "N/A"
    st.markdown(f"""
    <div class="stat-grid">
      <div class="stat-card">
        <div class="stat-lbl">NDVI {y1}</div>
        <div class="stat-val">{n1s}</div>
        <div class="stat-sub">Baseline year</div>
      </div>
      <div class="stat-card">
        <div class="stat-lbl">NDVI {y2}</div>
        <div class="stat-val">{n2s}</div>
        <div class="stat-sub">Comparison year</div>
      </div>
      <div class="stat-card {change_cls}">
        <div class="stat-lbl">Change</div>
        <div class="stat-val">{dpct:+.1f}%</div>
        <div class="stat-sub">{MS[sm]}–{MS[em]} season</div>
      </div>
      <div class="stat-card">
        <div class="stat-lbl">Area</div>
        <div class="stat-val">{area_ha:,.0f}</div>
        <div class="stat-sub">hectares</div>
      </div>
    </div>""", unsafe_allow_html=True)

    status_banner(dpct)

    # ── Carbon ──
    st.markdown('<div class="sec-label">Carbon Stock Estimate</div>', unsafe_allow_html=True)
    carbon_panel(cd)

    # District baseline
    if n2:
        render_district_comparison(n2)

    # ── Maps ──
    st.markdown('<div class="sec-label">NDVI Satellite Maps</div>', unsafe_allow_html=True)
    vis = get_ndvi_visualization_params()

    if show_hotspot:
        t1, t2, t3 = st.tabs([f"Year {y1}", f"Year {y2}", "Change Hotspot"])
    else:
        t1, t2 = st.tabs([f"Year {y1}", f"Year {y2}"])

    for tab, yr, comp in [(t1, y1, c1_), (t2, y2, c2_)]:
        with tab:
            m = make_map(lat, lon)
            ok = add_ee_layer(m, comp.select('NDVI'), vis, f'NDVI {yr}')
            if aoi_custom is None:
                folium.Circle(location=[lat,lon], radius=buf_km*1000,
                              color='#FFD700', fill=False, weight=2.5).add_to(m)
            folium.LayerControl(collapsed=False).add_to(m)
            st_folium(m, height=440, returned_objects=[], use_container_width=True)
            if ok:
                st.markdown(f"""
                <div class="ndvi-bar">
                  <span style="font-size:0.72rem;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;color:{C['accent']};">NDVI Scale</span>
                  <div class="ndvi-bar-inner">
                    <div style="flex:1;background:#d73027"></div><div style="flex:1;background:#fc8d59"></div>
                    <div style="flex:1;background:#fee08b"></div><div style="flex:1;background:#d9ef8b"></div>
                    <div style="flex:1;background:#91cf60"></div><div style="flex:1;background:#1a9850"></div>
                  </div>
                  <div class="ndvi-scale"><span>0.0 Bare</span><span>0.2</span><span>0.4</span><span>0.6</span><span>0.8</span><span>1.0 Dense</span></div>
                </div>""", unsafe_allow_html=True)

    if show_hotspot:
        with t3:
            m_diff = make_map(lat, lon)
            ok_diff = add_ndvi_diff_layer(m_diff, c1_, c2_, aoi)
            if aoi_custom is None:
                folium.Circle(location=[lat,lon], radius=buf_km*1000,
                              color='#FFD700', fill=False, weight=2.5).add_to(m_diff)
            folium.LayerControl(collapsed=False).add_to(m_diff)
            st_folium(m_diff, height=440, returned_objects=[], use_container_width=True)
            if ok_diff:
                st.markdown(f"""
                <div class="ndvi-bar">
                  <span style="font-size:0.72rem;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;color:{C['accent']};">Change Scale</span>
                  <div class="ndvi-bar-inner">
                    <div style="flex:1;background:#C0392B"></div><div style="flex:1;background:#E74C3C"></div>
                    <div style="flex:1;background:#F39C12"></div><div style="flex:1;background:#F0F0F0"></div>
                    <div style="flex:1;background:#82C341"></div><div style="flex:1;background:#27AE60"></div>
                  </div>
                  <div class="ndvi-scale"><span>-0.3 Loss</span><span></span><span>0 No change</span><span></span><span>+0.3 Gain</span></div>
                </div>""", unsafe_allow_html=True)
                st.caption(f"Pixel-level NDVI change: {y1} → {y2}. Red pixels indicate exact locations of vegetation loss.")

    # ── Monthly trend chart ──
    monthly_fig = None
    st.markdown('<div class="sec-label">Monthly NDVI Trend</div>', unsafe_allow_html=True)
    if ts:
        monthly_fig = monthly_chart(ts, f"Monthly NDVI {y2} — {selected_location}")
        st.plotly_chart(monthly_fig, use_container_width=True)
    else:
        st.caption("No monthly data available for selected period.")

    # ══════════════════════════════════════════════════════════════════════════
    # DAILY NDVI EXPLORER (NEW v3.1)
    # ══════════════════════════════════════════════════════════════════════════
    render_daily_ndvi_section(aoi, lat, lon, buf_km, aoi_custom)

    # ── Multi-year trend ──
    trend_data, trend_fig = [], None
    if run_multiyear:
        st.markdown('<div class="sec-label">Multi-Year NDVI Trend</div>', unsafe_allow_html=True)
        with st.spinner("Computing annual composites 2019–present (~20 s)…"):
            trend_data = annual_ndvi_series(aoi, sm, em)
        if len(trend_data) >= 2:
            trend_fig = trend_chart(trend_data, selected_location)
            st.plotly_chart(trend_fig, use_container_width=True)
            slope, direction = trend_stats(trend_data)
            total_change = (trend_data[-1]["ndvi"] - trend_data[0]["ndvi"]) / trend_data[0]["ndvi"] * 100
            yrs = trend_data[-1]["year"] - trend_data[0]["year"]
            st.caption(f"Over {yrs} years: {total_change:+.1f}% total change · {direction} at {slope:+.4f} NDVI/yr"
                       + (" · ⚠️ Decline warrants field investigation" if slope < -0.005 else ""))
            with st.expander("Raw annual data"):
                df_t = pd.DataFrame(trend_data)
                df_t.columns = ["Year","NDVI"]
                df_t["YoY %"] = df_t["NDVI"].pct_change().mul(100).round(1).apply(lambda x: f"{x:+.1f}%" if pd.notna(x) else "—")
                st.dataframe(df_t, hide_index=True, use_container_width=True)

    # ── AI report ──
    report_data = None
    if gen_ai:
        st.markdown('<div class="sec-label">AI Due Diligence Report</div>', unsafe_allow_html=True)
        if not groq_key:
            st.info("Add GROQ_API_KEY to your .env file. Free key at console.groq.com")
        else:
            with st.spinner("Generating report with Groq + Llama 3…"):
                report_data, err = call_groq(
                    groq_key, selected_location, lat, lon,
                    y1, y2, sm, em, n1, n2, dpct, ts, cd, trend_data
                )
            if err == "install_groq": st.error("Run: pip install groq")
            elif err: st.error(f"Report failed: {err}")
            elif report_data:
                render_report_card(report_data, selected_location, lat, lon,
                                   y1, y2, n1, n2, dpct, sm, em)

    # Email alerts
    if n2:
        render_alert_setup(selected_location, dpct, n2, lat, lon)

    # ── PDF export ──
    st.markdown('<div class="sec-label">Export</div>', unsafe_allow_html=True)
    try:
        pdf = build_pdf(
            report_data, selected_location, lat, lon, buf_km, area_ha,
            y1, y2, sm, em, n1, n2, dpct, cd, trend_data, ts,
            monthly_fig=monthly_fig, trend_fig=trend_fig
        )
        fname = f"TerrAI_{selected_location.replace(' ','_')}_{y2}.pdf"
        st.download_button("📄 Download PDF Report", pdf, fname,
                           "application/pdf", use_container_width=True)
    except Exception as e:
        st.error(f"PDF error: {e}")
        st.caption("Ensure reportlab, kaleido and matplotlib are installed: pip install reportlab kaleido matplotlib")

    with st.expander("About NDVI & Carbon Methodology"):
        st.markdown(f"""
| NDVI | Interpretation |
|------|----------------|
| 0.6 – 1.0 | Dense healthy forest |
| 0.3 – 0.6 | Moderate vegetation |
| 0.0 – 0.3 | Sparse / bare soil |
| < 0.0 | Water / clouds |

**Daily NDVI Explorer** queries the Sentinel-2 SR Harmonized collection for all acquisition dates in a selected month
where cloud cover is below 80%. Each scene is a single overpass — no temporal compositing — giving you the raw
per-date signal. Sentinel-2 has a ~5-day revisit over Nepal.

**Carbon estimation** uses Nepal FAO/ICIMOD literature values (above-ground biomass by forest type),
IPCC Tier 1 root-to-shoot ratios, and NDVI scaling (reference NDVI = 0.75 for healthy Himalayan broadleaf).
All figures are **indicative satellite estimates**. Field allometric surveys required for VERRA/ART-TREES credits.

**PDF maps** use matplotlib to render a side-by-side AOI visualisation with the gold analysis-circle boundary.
Install `staticmap` for real satellite tile backgrounds: `pip install staticmap`.
        """)


if __name__ == "__main__":
    main()