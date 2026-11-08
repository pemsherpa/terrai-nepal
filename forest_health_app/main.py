import os
import json
import math
import io
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Union
import ee
from dotenv import load_dotenv

load_dotenv()

from utils.gee_utils import (
    get_sentinel_composite, compute_mean_ndvi,
    calculate_ndvi_timeseries, get_ndvi_visualization_params, create_aoi_from_point
)
from utils.nepal_data import (
    NEPAL_CENTER, get_all_locations, search_location, get_location_coords
)

# Bring in the logic functions we need from app.py
NEPAL_CARBON = {
    "tropical_broadleaf":    {"agb": 180, "bgb_r": 0.26, "cf": 0.47},
    "subtropical_broadleaf": {"agb": 150, "bgb_r": 0.28, "cf": 0.47},
    "temperate_broadleaf":   {"agb": 120, "bgb_r": 0.30, "cf": 0.47},
    "conifer":               {"agb": 100, "bgb_r": 0.32, "cf": 0.51},
    "default":               {"agb": 140, "bgb_r": 0.28, "cf": 0.47},
}
CO2_FACTOR = 3.667

MN = {1:"January",2:"February",3:"March",4:"April",5:"May",6:"June",
      7:"July",8:"August",9:"September",10:"October",11:"November",12:"December"}

MS = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
      7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}

def gee_init():
    pid = os.getenv('GEE_PROJECT_ID')
    if not pid:
        print("GEE_PROJECT_ID missing from .env")
        return False
    try:
        ee.Initialize(project=pid)
        print("Earth Engine initialized.")
        return True
    except Exception as e:
        print(f"Earth Engine init failed: {e}")
        return False

def parse_geojson(data: dict):
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

def chart_to_png(fig, w=560, h=220):
    try:
        return fig.to_image(format="png", width=w, height=h, scale=2)
    except:
        return None

def send_alert_email(to_email, location_name, ndvi_change_pct, ndvi2=0, lat=0.0, lon=0.0):
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
            This is an automated alert from the TerrAI Digital MRV platform.
          </p>
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


app = FastAPI(title="TerrAI Backend API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    gee_init()

class AnalyzeRequest(BaseModel):
    lat: Optional[float] = None
    lon: Optional[float] = None
    geojson: Optional[dict] = None
    buf_km: float = 5.0
    year1: int
    year2: int
    start_month: int
    end_month: int
    forest_type: str = "default"
    run_multiyear: bool = True

class AnalyzeResponse(BaseModel):
    ndvi_year1: Optional[float]
    ndvi_year2: Optional[float]
    change_pct: float
    carbon_estimate: Optional[dict]
    trend_data: List[dict]
    monthly_series: List[dict]

@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest):
    import math
    try:
        if req.geojson:
            aoi, lat, lon, area_ha, name = parse_geojson(req.geojson)
        else:
            if req.lat is None or req.lon is None:
                raise HTTPException(status_code=400, detail="Must provide either lat/lon or geojson")
            aoi = create_aoi_from_point(req.lat, req.lon, req.buf_km)
            lat, lon = req.lat, req.lon
            area_ha = math.pi * (req.buf_km**2) * 100

        c1_ = get_sentinel_composite(aoi, f"{req.year1}-{req.start_month:02d}-01", f"{req.year1}-{req.end_month:02d}-28")
        c2_ = get_sentinel_composite(aoi, f"{req.year2}-{req.start_month:02d}-01", f"{req.year2}-{req.end_month:02d}-28")
        n1 = compute_mean_ndvi(c1_, aoi)
        n2 = compute_mean_ndvi(c2_, aoi)
        
        dpct = ((n2 - n1) / n1 * 100) if (n1 and n2 and n1 != 0) else 0.0
        cd = carbon_estimate(n2, area_ha, req.forest_type, dpct)

        ts = calculate_ndvi_timeseries(aoi, req.year2, req.start_month, req.end_month) or []
        
        trend_data = []
        if req.run_multiyear:
            trend_data = annual_ndvi_series(aoi, req.start_month, req.end_month)

        # --- GENERATE MAP TILE URL FOR LOVABLE ---
        vis_params = get_ndvi_visualization_params() 
        ndvi_image = c2_.select('NDVI') # Grab the NDVI band from Year 2
        map_id_dict = ndvi_image.getMapId(vis_params)
        generated_tile_url = map_id_dict['tile_fetcher'].url_format
        # -----------------------------------------

        return AnalyzeResponse(
            ndvi_year1=n1,
            ndvi_year2=n2,
            change_pct=dpct,
            carbon_estimate=cd,
            trend_data=trend_data,
            monthly_series=ts,
            tile_url=generated_tile_url  # <--- PASS IT TO THE FRONTEND
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ReportRequest(BaseModel):
    location: str
    lat: float
    lon: float
    year1: int
    year2: int
    start_month: int
    end_month: int
    ndvi_year1: Optional[float]
    ndvi_year2: Optional[float]
    change_pct: float
    monthly_series: List[dict] = []
    carbon_estimate: Optional[dict] = None
    trend_data: List[dict] = []

@app.post("/api/report/generate")
def generate_report(req: ReportRequest):
    groq_key = os.getenv('GROQ_API_KEY', '')
    if not groq_key:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY not configured")
    
    report_data, err = call_groq(
        groq_key, req.location, req.lat, req.lon,
        req.year1, req.year2, req.start_month, req.end_month,
        req.ndvi_year1, req.ndvi_year2, req.change_pct,
        req.monthly_series, req.carbon_estimate, req.trend_data
    )
    if err:
        raise HTTPException(status_code=500, detail=f"Report failed: {err}")
    return report_data

class AlertRequest(BaseModel):
    email: str
    location_name: str
    ndvi_change_pct: float
    ndvi2: float = 0.0
    lat: float = 0.0
    lon: float = 0.0

@app.post("/api/alerts/test")
def test_alert(req: AlertRequest):
    ok, msg = send_alert_email(req.email, req.location_name, req.ndvi_change_pct, req.ndvi2, req.lat, req.lon)
    if not ok:
        raise HTTPException(status_code=500, detail=msg)
    return {"message": "Success"}

# PDF logic requires quite some code, let me append that next

import pandas as pd
import plotly.graph_objects as go
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, Image as RLImage
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

C = {
    "forest":    "#0D2818", "dark":      "#1A4731", "mid":       "#2D6A4F",
    "accent":    "#40916C", "sage":      "#74C69D", "mist":      "#D8F3DC",
    "pale":      "#F0FBF4", "white":     "#FFFFFF", "ink":       "#0F1A14",
    "slate":     "#4A5568", "border":    "#C3E6CB", "warn":      "#E67E22",
    "danger":    "#C0392B", "good":      "#27AE60",
}
RL = {k: colors.HexColor(v) for k, v in C.items()}

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
        fill='tozeroy', fillcolor='rgba(64,145,108,0.08)'
    ))
    fig.update_layout(**CHART_LAYOUT, title=dict(text=title), xaxis=dict(**_GRID), yaxis=dict(**_GRID, range=[0, 1]))
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
        fill='tozeroy', fillcolor='rgba(64,145,108,0.08)'
    ))
    fig.update_layout(**CHART_LAYOUT, title=dict(text=f"Multi-Year NDVI — {location}"),
        xaxis=dict(**_GRID, tickmode='linear', dtick=1), yaxis=dict(**_GRID, range=[0, 1])
    )
    return fig


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

    # ── NDVI Charts ──
    story.append(HRFlowable(width="100%", thickness=1, color=RL["mist"], spaceAfter=3))
    story.append(Paragraph("NDVI Satellite Analysis", styles["h1"]))

    charts_added = False
    if monthly_fig or trend_fig:
        img_w = CW
        if monthly_fig and trend_fig:
            img_w = (CW - 4*mm) / 2  # side by side

        chart_cells = []
        for fig, caption in [(monthly_fig, f"Monthly NDVI — {MS[sm]} to {MS[em]} {y2}"),
                             (trend_fig,   "Multi-Year NDVI Trend (2019-present)")]:
            if fig:
                png = chart_to_png(fig, w=int(img_w/mm*1.5), h=150)
                if png:
                    img_io = io.BytesIO(png)
                    img_io.seek(0)
                    rl_img = RLImage(img_io, width=img_w, height=img_w*0.42)
                    cap = Paragraph(caption, S("cap",fontSize=7.5,textColor=RL["slate"],alignment=TA_CENTER))
                    chart_cells.append([rl_img, cap])

        if len(chart_cells) == 2:
            # Two charts side by side
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
        canvas.restoreState()

    doc = SimpleDocTemplate(buf, pagesize=A4,
                             leftMargin=MAR, rightMargin=MAR,
                             topMargin=MAR, bottomMargin=16*mm,
                             title=f"TerrAI — {loc}", author="TerrAI")
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return buf.getvalue()



class PdfRequest(BaseModel):
    report_data: dict
    location: str
    lat: float
    lon: float
    buf_km: float
    area_ha: float
    year1: int
    year2: int
    start_month: int
    end_month: int
    ndvi_year1: Optional[float]
    ndvi_year2: Optional[float]
    change_pct: float
    carbon_estimate: Optional[dict] = None
    trend_data: List[dict] = []
    monthly_series: List[dict] = []

@app.post("/api/export/pdf")
def export_pdf(req: PdfRequest):
    monthly_fig = None
    if req.monthly_series:
        monthly_fig = monthly_chart(req.monthly_series, f"Monthly NDVI {req.year2} — {req.location}")
    
    trend_fig = None
    if req.trend_data and len(req.trend_data) >= 2:
        trend_fig = trend_chart(req.trend_data, req.location)

    try:
        # build_pdf is imported from app, but ideally it shouldn't be long term. Since instructions say "extract all core scientific logic... without removing my current app.py code or changing anything in it. do the following... generate a complete, fully-commented main.py file"
        # I'll just keep the function inside main.py string directly to ensure we have a standalone main.py
        
        pdf_bytes = build_pdf(
            req.report_data, req.location, req.lat, req.lon, req.buf_km, req.area_ha,
            req.year1, req.year2, req.start_month, req.end_month, req.ndvi_year1, req.ndvi_year2, 
            req.change_pct, req.carbon_estimate, req.trend_data, req.monthly_series,
            monthly_fig=monthly_fig, trend_fig=trend_fig
        )
        return StreamingResponse(
            io.BytesIO(pdf_bytes), 
            media_type="application/pdf", 
            headers={"Content-Disposition": f"attachment; filename=TerrAI_{req.location.replace(' ','_')}_{req.year2}.pdf"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {e}")

# End of main.py
