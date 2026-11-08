"""ReportLab PDF generation matching Streamlit app.py v3.1 layout."""

from __future__ import annotations

import io
import math
from datetime import datetime

import plotly.graph_objects as go
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Image as RLImage,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .science import MS, MN, trend_stats

C = {
    "forest": "#0D2818",
    "dark": "#1A4731",
    "mid": "#2D6A4F",
    "accent": "#40916C",
    "sage": "#74C69D",
    "mist": "#D8F3DC",
    "pale": "#F0FBF4",
    "white": "#FFFFFF",
    "ink": "#0F1A14",
    "slate": "#4A5568",
    "border": "#C3E6CB",
    "warn": "#E67E22",
    "danger": "#C0392B",
    "good": "#27AE60",
}
RL = {k: colors.HexColor(v) for k, v in C.items()}

CHART_LAYOUT = dict(
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter", size=11, color=C["slate"]),
    margin=dict(l=48, r=16, t=48, b=40),
    hovermode="x unified",
)
_GRID = dict(showgrid=True, gridcolor="rgba(0,0,0,0.05)", zeroline=False)


def clean_pdf_text(text: str) -> str:
    if not text:
        return ""
    s = str(text)
    for ch in ["\u2010", "\u2011", "\u2012", "\u00ad", "\u2212"]:
        s = s.replace(ch, "-")
    s = s.replace("\u2013", "-").replace("\u2014", " - ")
    s = s.replace("ha⁻¹", "ha<sup>-1</sup>").replace("ha^-1", "ha<sup>-1</sup>")
    s = s.replace("yr⁻¹", "yr<sup>-1</sup>").replace("yr^-1", "yr<sup>-1</sup>")
    s = s.replace("t CO2e ha⁻¹", "t CO2e ha<sup>-1</sup>").replace("t CO2e ha-1", "t CO2e ha<sup>-1</sup>")
    s = s.replace("⁻¹", "<sup>-1</sup>").replace("⁻²", "<sup>-2</sup>").replace("⁻³", "<sup>-3</sup>")
    s = s.replace("⁻", "-").replace("¹", "1").replace("²", "2").replace("³", "3")
    for sup, digit in [("⁰", "0"), ("⁴", "4"), ("⁵", "5"), ("⁶", "6"), ("⁷", "7"), ("⁸", "8"), ("⁹", "9")]:
        s = s.replace(sup, digit)
    s = s.replace("\u2018", "'").replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"')
    s = s.replace("\u00a0", " ").replace("\u202f", " ").replace("\u200b", "")
    return s


def chart_to_png(fig, w=560, h=220):
    try:
        return fig.to_image(format="png", width=w, height=h, scale=2)
    except Exception:
        return None


def monthly_chart(ts, title):
    months = [d["month"] for d in ts]
    values = [d["ndvi"] for d in ts]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=months,
            y=values,
            mode="lines+markers",
            name="NDVI",
            line=dict(color=C["accent"], width=2.5),
            marker=dict(size=7, color=C["dark"], line=dict(color=C["white"], width=1.5)),
            fill="tozeroy",
            fillcolor="rgba(64,145,108,0.08)",
        )
    )
    fig.update_layout(**CHART_LAYOUT, title=dict(text=title), xaxis=dict(**_GRID), yaxis=dict(**_GRID, range=[0, 1]))
    return fig


def trend_chart(data, location):
    years = [d["year"] for d in data]
    ndvis = [d["ndvi"] for d in data]
    slope, _direction = trend_stats(data)
    xm = sum(years) / len(years)
    ym = sum(ndvis) / len(ndvis)
    tline = [slope * (y - xm) + ym for y in years]
    fig = go.Figure()
    fig.add_hrect(y0=0.6, y1=1.0, fillcolor="rgba(39,174,96,0.04)", line_width=0)
    fig.add_hrect(y0=0.3, y1=0.6, fillcolor="rgba(230,126,34,0.03)", line_width=0)
    fig.add_hrect(y0=0.0, y1=0.3, fillcolor="rgba(192,57,43,0.04)", line_width=0)
    fig.add_trace(
        go.Scatter(
            x=years,
            y=tline,
            mode="lines",
            name="Trend",
            line=dict(color="rgba(64,145,108,0.35)", width=1.5, dash="dash"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=years,
            y=ndvis,
            mode="lines+markers",
            name="Annual NDVI",
            line=dict(color=C["accent"], width=2.5),
            marker=dict(size=9, color=C["dark"], line=dict(color=C["white"], width=2)),
            fill="tozeroy",
            fillcolor="rgba(64,145,108,0.08)",
        )
    )
    fig.update_layout(
        **CHART_LAYOUT,
        title=dict(text=f"Multi-Year NDVI — {location}"),
        xaxis=dict(**_GRID, tickmode="linear", dtick=1),
        yaxis=dict(**_GRID, range=[0, 1]),
    )
    return fig


def build_comparison_map_image(lat, lon, buf_km, y1, y2, n1, n2, width=560, height=300):
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.patches import Circle

        fig, axes = plt.subplots(1, 2, figsize=(width / 100, height / 100), dpi=100)
        fig.patch.set_facecolor("#1A4731")

        for ax, yr, ndvi_val, label in [
            (axes[0], y1, n1, f"Year {y1}"),
            (axes[1], y2, n2, f"Year {y2}"),
        ]:
            ax.set_facecolor("#0D2818")
            ax.set_xlim(-1, 1)
            ax.set_ylim(-1, 1)
            if ndvi_val:
                g = min(1.0, ndvi_val / 0.8)
                fill_color = (0.1 * (1 - g), 0.4 + 0.4 * g, 0.1 + 0.2 * g, 0.7)
            else:
                fill_color = (0.4, 0.4, 0.4, 0.5)
            ax.add_patch(Circle((0, 0), 0.72, color=fill_color, zorder=2))
            ax.add_patch(Circle((0, 0), 0.72, fill=False, edgecolor="#FFD700", linewidth=2.5, zorder=3))
            ax.plot(0, 0, "o", color="#FFD700", markersize=8, zorder=4)
            ndvi_str = f"{ndvi_val:.4f}" if ndvi_val else "N/A"
            ax.text(0, 0.1, ndvi_str, ha="center", va="center", fontsize=14, fontweight="bold", color="white", zorder=5)
            ax.text(0, -0.18, "NDVI", ha="center", va="center", fontsize=8, color="#74C69D", zorder=5)
            ax.text(0, -0.88, f"r = {buf_km} km", ha="center", va="center", fontsize=7, color="#FFD700")
            ax.set_title(label, color="white", fontsize=10, fontweight="bold", pad=8)
            ax.set_xticks([])
            ax.set_yticks([])
            for spine in ax.spines.values():
                spine.set_edgecolor("#2D6A4F")

        fig.suptitle(f"NDVI Comparison — {lat:.3f}°N {lon:.3f}°E", color="#74C69D", fontsize=9, y=0.02)
        plt.tight_layout(pad=0.8)
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=100, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close(fig)
        buf.seek(0)
        return buf.getvalue()
    except Exception:
        return None


def get_ndvi_diff_image_png(lat, lon, buf_km, y1, y2, n1, n2, width=560, height=220):
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        dpct = ((n2 - n1) / n1 * 100) if (n1 and n2 and n1 != 0) else 0
        change_color = "#27AE60" if dpct >= 0 else ("#E67E22" if dpct > -10 else "#C0392B")
        fig, ax = plt.subplots(figsize=(width / 100, height / 100), dpi=100)
        fig.patch.set_facecolor("#1A4731")
        ax.set_facecolor("#0D2818")
        years_label = [str(y1), str(y2)]
        ndvi_vals = [n1 or 0, n2 or 0]
        bars = ax.bar(years_label, ndvi_vals, color=["#2D6A4F", change_color], width=0.45, edgecolor="#74C69D", linewidth=1.2)
        for bar, val in zip(bars, ndvi_vals):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.01,
                f"{val:.4f}",
                ha="center",
                va="bottom",
                fontsize=10,
                fontweight="bold",
                color="white",
            )
        ax.set_ylim(0, 1.05)
        ax.set_ylabel("NDVI", color="#74C69D", fontsize=9)
        ax.set_title(f"NDVI Change: {dpct:+.1f}%  ({y1} → {y2})", color="white", fontsize=10, fontweight="bold")
        ax.tick_params(colors="#74C69D", labelsize=9)
        ax.spines["bottom"].set_color("#2D6A4F")
        ax.spines["left"].set_color("#2D6A4F")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.yaxis.grid(True, color="#2D6A4F", alpha=0.4, linewidth=0.7)
        ax.annotate(
            "",
            xy=(1, n2 or 0),
            xytext=(0, n1 or 0),
            arrowprops=dict(arrowstyle="->", color=change_color, lw=2),
        )
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=100, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close(fig)
        buf.seek(0)
        return buf.getvalue()
    except Exception:
        return None


def build_pdf(
    rd,
    loc,
    lat,
    lon,
    buf_km,
    area_ha,
    y1,
    y2,
    sm,
    em,
    n1,
    n2,
    dpct,
    cd,
    td,
    ts,
    monthly_fig=None,
    trend_fig=None,
):
    buf = io.BytesIO()
    W, H = A4
    MAR = 18 * mm
    CW = W - 2 * MAR

    def S(name, **kw):
        base = dict(fontName="Helvetica", fontSize=9.5, leading=14, textColor=RL["ink"], spaceAfter=4)
        base.update(kw)
        return ParagraphStyle(name, **base)

    styles = {
        "h_title": S("ht", fontName="Helvetica-Bold", fontSize=20, textColor=colors.white, spaceAfter=2),
        "h_sub": S("hs", fontSize=9, textColor=RL["sage"], spaceAfter=0),
        "h1": S("h1", fontName="Helvetica-Bold", fontSize=13, textColor=RL["dark"], spaceBefore=10, spaceAfter=5),
        "h2": S("h2", fontName="Helvetica-Bold", fontSize=10, textColor=RL["mid"], spaceBefore=7, spaceAfter=3),
        "body": S("bd", fontSize=9, leading=14, spaceAfter=5),
        "bullet": S("bl", fontSize=9, leading=13, leftIndent=12, spaceAfter=3),
        "note": S("nt", fontSize=7.5, leading=11, textColor=RL["slate"], fontName="Helvetica-Oblique", spaceAfter=4),
        "th": S("th", fontName="Helvetica-Bold", fontSize=8.5, textColor=colors.white, alignment=TA_CENTER),
        "td": S("td", fontSize=8.5, leading=12),
        "tdc": S("tdc", fontSize=8.5, leading=12, alignment=TA_CENTER),
        "footer": S("ft", fontSize=7, textColor=RL["slate"], alignment=TA_CENTER),
        "footer_l": S("ftl", fontSize=7, textColor=RL["slate"], alignment=TA_LEFT),
        "footer_c": S("ftc", fontSize=7, textColor=RL["slate"], alignment=TA_CENTER),
        "footer_r": S("ftr", fontSize=7, textColor=RL["slate"], alignment=TA_RIGHT),
        "map_cap": S("mc", fontSize=7.5, textColor=RL["slate"], alignment=TA_CENTER, spaceAfter=6),
    }

    risk = rd.get("risk_level", "N/A") if rd else "N/A"
    risk_clr = {"LOW": RL["good"], "MEDIUM": RL["warn"], "HIGH": RL["danger"], "CRITICAL": RL["danger"]}.get(risk, RL["slate"])
    gen_date = datetime.utcnow().strftime("%d %B %Y, %H:%M UTC")
    n1s = f"{n1:.4f}" if n1 else "N/A"
    n2s = f"{n2:.4f}" if n2 else "N/A"
    story = []

    banner = Table(
        [
            [
                Paragraph("<b>TerrAI</b>", styles["h_title"]),
                Paragraph(
                    f"Risk: <b>{risk}</b>",
                    S("rs", fontName="Helvetica-Bold", fontSize=10, textColor=colors.white, alignment=TA_CENTER),
                ),
            ]
        ],
        colWidths=[CW - 40 * mm, 40 * mm],
    )
    banner.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), RL["dark"]),
                ("BACKGROUND", (1, 0), (1, 0), risk_clr),
                ("TOPPADDING", (0, 0), (-1, -1), 14),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
                ("LEFTPADDING", (0, 0), (0, 0), 14),
                ("RIGHTPADDING", (1, 0), (1, 0), 10),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.append(banner)

    subrow = Table(
        [
            [
                Paragraph(f"Forest Health Due Diligence Report — {loc}", styles["h_sub"]),
                Paragraph(
                    f"Generated: {gen_date}",
                    S("gs", fontSize=8.5, textColor=RL["sage"], alignment=TA_RIGHT),
                ),
            ]
        ],
        colWidths=[CW * 0.65, CW * 0.35],
    )
    subrow.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), RL["mid"]),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (0, 0), 14),
                ("RIGHTPADDING", (1, 0), (1, 0), 10),
            ]
        )
    )
    story.append(subrow)
    story.append(Spacer(1, 7 * mm))

    def mcell(lbl, val, unit=""):
        t = Table(
            [
                [Paragraph(lbl.upper(), S("ml", fontSize=6.5, fontName="Helvetica-Bold", textColor=RL["accent"], alignment=TA_CENTER))],
                [Paragraph(str(val), S("mv", fontSize=15, fontName="Helvetica-Bold", textColor=RL["dark"], alignment=TA_CENTER))],
                [Paragraph(unit, S("mu", fontSize=7, textColor=RL["slate"], alignment=TA_CENTER))],
            ],
            colWidths=["100%"],
        )
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), RL["pale"]),
                    ("BOX", (0, 0), (-1, -1), 0.5, RL["border"]),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        return t

    cw4 = (CW - 9 * mm) / 4
    area_display = f"{area_ha:,.0f}" if area_ha else f"{math.pi * buf_km ** 2 * 100:.0f}"
    mrow = Table(
        [[mcell(f"NDVI {y1}", n1s), mcell(f"NDVI {y2}", n2s), mcell("Change", f"{dpct:+.1f}%"), mcell("Area", area_display, "hectares")]],
        colWidths=[cw4] * 4,
    )
    mrow.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(mrow)
    story.append(Spacer(1, 5 * mm))

    story.append(HRFlowable(width="100%", thickness=1, color=RL["mist"], spaceAfter=3))
    story.append(Paragraph("Analysis Parameters", styles["h1"]))
    radius_label = f"{buf_km} km" if buf_km else "Custom polygon"
    ptbl = Table(
        [
            [Paragraph("Parameter", styles["th"]), Paragraph("Value", styles["th"])],
            ["Location", loc],
            ["Coordinates", f"{lat:.4f} N, {lon:.4f} E"],
            ["Analysis Radius", radius_label],
            ["Season", f"{MN[sm]} to {MN[em]}"],
            ["Years", f"{y1} vs {y2}"],
            ["Satellite", "Sentinel-2 SR, 10 m resolution"],
            ["Report Date", gen_date],
        ],
        colWidths=[CW * 0.38, CW * 0.62],
    )
    ptbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), RL["dark"]),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, RL["pale"]]),
                ("GRID", (0, 0), (-1, -1), 0.3, RL["mist"]),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
                ("TEXTCOLOR", (0, 1), (0, -1), RL["accent"]),
            ]
        )
    )
    story.append(ptbl)
    story.append(Spacer(1, 4 * mm))

    # Satellite Map — AOI Comparison (app.py v3.1)
    story.append(HRFlowable(width="100%", thickness=1, color=RL["mist"], spaceAfter=3))
    story.append(Paragraph("Satellite Map — AOI Comparison", styles["h1"]))
    story.append(
        Paragraph(
            f"Area of interest: {loc} · {lat:.4f}°N, {lon:.4f}°E · Radius {buf_km} km · "
            f"Gold circle marks the analysis boundary. Left = {y1}, Right = {y2}.",
            styles["note"],
        )
    )

    sat_png = build_comparison_map_image(lat, lon, buf_km or 5, y1, y2, n1, n2, width=560, height=280)
    diff_png = get_ndvi_diff_image_png(lat, lon, buf_km or 5, y1, y2, n1, n2, width=560, height=200)
    map_cells_added = False
    if sat_png and diff_png:
        half_w = (CW - 4 * mm) / 2
        try:
            sat_io = io.BytesIO(sat_png)
            sat_io.seek(0)
            diff_io = io.BytesIO(diff_png)
            diff_io.seek(0)
            sat_img = RLImage(sat_io, width=half_w, height=half_w * 0.55)
            diff_img = RLImage(diff_io, width=half_w, height=half_w * 0.55)
            map_tbl = Table(
                [
                    [sat_img, diff_img],
                    [
                        Paragraph(
                            f"AOI Overview — {y1} vs {y2}<br/>Gold circle = {buf_km or 5} km analysis radius",
                            styles["map_cap"],
                        ),
                        Paragraph(f"NDVI Change: {dpct:+.1f}%<br/>{y1}: {n1s} → {y2}: {n2s}", styles["map_cap"]),
                    ],
                ],
                colWidths=[half_w, half_w],
            )
            map_tbl.setStyle(
                TableStyle(
                    [
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 2),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                        ("TOPPADDING", (0, 0), (-1, -1), 2),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                        ("BOX", (0, 0), (0, 0), 0.5, RL["mist"]),
                        ("BOX", (1, 0), (1, 0), 0.5, RL["mist"]),
                    ]
                )
            )
            story.append(map_tbl)
            map_cells_added = True
        except Exception:
            pass
    if not map_cells_added and sat_png:
        try:
            sat_io = io.BytesIO(sat_png)
            sat_io.seek(0)
            story.append(RLImage(sat_io, width=CW, height=CW * 0.45))
            story.append(
                Paragraph(f"AOI: {loc} · Gold circle = {buf_km or 5} km radius · {y1} vs {y2}", styles["map_cap"])
            )
            map_cells_added = True
        except Exception:
            pass
    if not map_cells_added:
        story.append(Paragraph("Satellite map image unavailable.", styles["note"]))
    story.append(Spacer(1, 4 * mm))

    # NDVI Timeseries
    story.append(HRFlowable(width="100%", thickness=1, color=RL["mist"], spaceAfter=3))
    story.append(Paragraph("NDVI Timeseries Analysis", styles["h1"]))
    charts_added = False
    if monthly_fig or trend_fig:
        img_w = CW
        if monthly_fig and trend_fig:
            img_w = (CW - 4 * mm) / 2
        chart_cells = []
        for fig, caption in [
            (monthly_fig, f"Monthly NDVI — {MS[sm]} to {MS[em]} {y2}"),
            (trend_fig, "Multi-Year NDVI Trend (2019–present)"),
        ]:
            if fig:
                png = chart_to_png(fig, w=int(img_w / mm * 1.5), h=150)
                if png:
                    img_io = io.BytesIO(png)
                    img_io.seek(0)
                    rl_img = RLImage(img_io, width=img_w, height=img_w * 0.42)
                    cap = Paragraph(caption, S("cap", fontSize=7.5, textColor=RL["slate"], alignment=TA_CENTER))
                    chart_cells.append([rl_img, cap])
        if len(chart_cells) == 2:
            chart_tbl = Table(
                [[chart_cells[0][0], chart_cells[1][0]], [chart_cells[0][1], chart_cells[1][1]]],
                colWidths=[(CW - 4 * mm) / 2, (CW - 4 * mm) / 2],
            )
            chart_tbl.setStyle(
                TableStyle(
                    [
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 2),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                    ]
                )
            )
            story.append(chart_tbl)
            charts_added = True
        elif len(chart_cells) == 1:
            img, cap = chart_cells[0]
            story.append(img)
            story.append(cap)
            charts_added = True
    if not charts_added:
        story.append(Paragraph("NDVI chart images not available in this export.", styles["note"]))
    story.append(Spacer(1, 4 * mm))

    if cd:
        story.append(HRFlowable(width="100%", thickness=1, color=RL["mist"], spaceAfter=3))
        story.append(Paragraph("Carbon Stock Estimate", styles["h1"]))
        cd_area = float(cd.get("area_ha") or area_ha or 0)
        agb = float(cd.get("agb_ha") or 0)
        bgb = float(cd.get("bgb_ha") or agb * 0.24)
        bio = float(cd.get("bio_ha") or agb + bgb)
        c_ha = float(cd.get("c_ha") or bio * 0.47)
        total_c = float(cd.get("total_c") or c_ha * cd_area)
        co2_ha = float(cd.get("co2_ha") or c_ha * 3.667)
        total_co2 = float(cd.get("total_co2") or co2_ha * cd_area)
        crows = [
            [Paragraph("Metric", styles["th"]), Paragraph("Per Hectare", styles["th"]), Paragraph("Total", styles["th"])],
            ["Above-Ground Biomass", f"{agb:,.0f} t/ha", f"{agb * cd_area:,.0f} t"],
            ["Below-Ground Biomass", f"{bgb:,.0f} t/ha", f"{bgb * cd_area:,.0f} t"],
            ["Total Biomass", f"{bio:,.0f} t/ha", f"{bio * cd_area:,.0f} t"],
            ["Carbon Stock", f"{c_ha:,.0f} tC/ha", f"{total_c:,.0f} t C"],
            [
                Paragraph("CO<sub>2</sub> Equivalent", styles["td"]),
                Paragraph(f"{co2_ha:,.0f} t CO<sub>2</sub>e/ha", styles["tdc"]),
                Paragraph(f"{total_co2:,.0f} t CO<sub>2</sub>e", styles["tdc"]),
            ],
        ]
        if "co2_delta" in cd:
            sign = "+" if cd["co2_delta"] >= 0 else ""
            pct_val = float(cd.get("change_pct", dpct) or 0)
            crows.append(
                [
                    Paragraph("CO<sub>2</sub>e Change", styles["td"]),
                    f"{pct_val:+.1f}%",
                    Paragraph(f"{sign}{cd['co2_delta']:,} t CO<sub>2</sub>e", styles["tdc"]),
                ]
            )
        ctbl = Table(crows, colWidths=[CW * 0.44, CW * 0.28, CW * 0.28])
        style_cmds = [
            ("BACKGROUND", (0, 0), (-1, 0), RL["dark"]),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, RL["pale"]]),
            ("GRID", (0, 0), (-1, -1), 0.3, RL["mist"]),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
            ("TEXTCOLOR", (0, 1), (0, -1), RL["dark"]),
        ]
        if "co2_delta" in cd:
            style_cmds.append(("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#FFFBEB")))
        ctbl.setStyle(TableStyle(style_cmds))
        story.append(ctbl)
        story.append(
            Paragraph(
                f"Indicative estimates only. Forest type: {cd.get('ftype', 'default').replace('_', ' ').title()}. "
                "Source: FAO/ICIMOD Nepal. Field calibration required before use in verified credits.",
                styles["note"],
            )
        )

    if td and len(td) > 1:
        story.append(HRFlowable(width="100%", thickness=1, color=RL["mist"], spaceAfter=3))
        story.append(Paragraph("Annual NDVI Record", styles["h1"]))
        thead = [Paragraph(str(d["year"]), styles["th"]) for d in td]
        tvals = [str(d["ndvi"]) for d in td]
        col_w = CW / (len(td) + 1)
        ttbl = Table(
            [
                [Paragraph("Year", styles["th"])] + thead,
                [Paragraph("NDVI", S("tnl", fontName="Helvetica-Bold", fontSize=8.5, textColor=RL["accent"]))] + tvals,
            ],
            colWidths=[col_w] * (len(td) + 1),
        )
        ttbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), RL["dark"]),
                    ("GRID", (0, 0), (-1, -1), 0.3, RL["mist"]),
                    ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, RL["pale"]]),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(ttbl)

    if rd:
        story.append(PageBreak())
        story.append(HRFlowable(width="100%", thickness=1, color=RL["mist"], spaceAfter=3))
        story.append(Paragraph("AI-Generated Due Diligence Analysis", styles["h1"]))
        story.append(
            Paragraph(
                "Generated by Llama 3 (Groq) from satellite inputs. Not certified verification. "
                "Review by qualified environmental scientists required.",
                styles["note"],
            )
        )
        story.append(Spacer(1, 3 * mm))
        for title, key in [
            ("Executive Summary", "executive_summary"),
            ("Vegetation Health Analysis", "vegetation_analysis"),
            ("Carbon Stock Implications", "carbon_implications"),
            ("Risk Assessment", "risk_assessment"),
            ("Data Confidence", "data_confidence"),
            ("Next Monitoring", "next_monitoring"),
        ]:
            val = rd.get(key, "")
            if val:
                story.append(Paragraph(title, styles["h2"]))
                story.append(Paragraph(clean_pdf_text(str(val)), styles["body"]))
        for title, key in [("Key Findings", "key_findings"), ("Recommendations", "recommendations")]:
            items = rd.get(key, []) or []
            if items:
                story.append(Paragraph(title, styles["h2"]))
                for i, item in enumerate(items):
                    prefix = f"{i + 1}." if key == "recommendations" else "&bull;"
                    story.append(Paragraph(f"{prefix}  {clean_pdf_text(str(item))}", styles["bullet"]))

    story.append(Spacer(1, 6 * mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=RL["mist"]))
    ftbl = Table(
        [
            [
                Paragraph("Satellite data: Sentinel-2 SR via Google Earth Engine", styles["footer_l"]),
                Paragraph("TerrAI · Digital MRV Platform · Nepal", styles["footer_c"]),
                Paragraph("Satellite estimates pending field validation", styles["footer_r"]),
            ]
        ],
        colWidths=[CW * 0.40, CW * 0.28, CW * 0.32],
    )
    ftbl.setStyle(
        TableStyle(
            [
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
                ("ALIGN", (1, 0), (1, -1), "CENTER"),
                ("ALIGN", (2, 0), (2, -1), "RIGHT"),
            ]
        )
    )
    story.append(ftbl)

    def on_page(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(RL["dark"])
        canvas.rect(0, 0, W, 7 * mm, fill=1, stroke=0)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica", 6.5)
        canvas.drawString(MAR, 2.2 * mm, f"TerrAI — {loc} — {gen_date}")
        canvas.drawRightString(W - MAR, 2.2 * mm, f"Page {doc.page}  |  CONFIDENTIAL — Satellite estimates only")
        canvas.restoreState()

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=MAR,
        rightMargin=MAR,
        topMargin=MAR,
        bottomMargin=16 * mm,
        title=f"TerrAI — {loc}",
        author="TerrAI",
    )
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return buf.getvalue()
