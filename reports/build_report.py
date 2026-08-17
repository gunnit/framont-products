#!/usr/bin/env python3
"""Build the Framont Access GA4 performance report (HTML -> PDF).

Data source: GA4 property 544861486 (access.framontmanagement.com),
pulled via Composio on 2026-08-17. Period: 2026-07-09 (stream live) -> 2026-08-17.
"""
import datetime as dt
import pathlib

OUT = pathlib.Path(__file__).parent
FONT_CSS = OUT / "fonts" / "fonts-embedded.css"

if not FONT_CSS.exists():          # fetch Playfair Display + Work Sans and inline them
    import base64
    import re
    import subprocess
    FONT_CSS.parent.mkdir(parents=True, exist_ok=True)
    api = ("https://fonts.googleapis.com/css2?family=Playfair+Display:wght@500;600;700"
           "&family=Work+Sans:wght@300;400;500;600;700&display=swap")
    ua = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
    css = subprocess.run(["curl", "-sS", "-m", "40", "-A", ua, api],
                         capture_output=True, text=True).stdout
    for url in sorted(set(re.findall(r"https://[^)]+\.woff2", css))):
        blob = subprocess.run(["curl", "-sS", "-m", "40", url], capture_output=True).stdout
        css = css.replace(url, "data:font/woff2;base64," + base64.b64encode(blob).decode())
    FONT_CSS.write_text(css)

FONTS = FONT_CSS.read_text()

# ---------------------------------------------------------------- brand
NAVY = "#002E5F"
NAVY_D = "#001F42"
ORANGE = "#FF8200"
ORANGE_D = "#B85C00"
SERIES_BLUE = "#1F5C99"   # validated categorical step (brand navy lightened)
INK = "#4D575E"
MUTED = "#7C848C"
SAND = "#E9E7E2"
SAND_L = "#F7F7F5"
PAPER = "#FFFFFF"

# ---------------------------------------------------------------- data
# date -> (activeUsers, newUsers, sessions, pageViews, engagedSessions)
DAILY_RAW = {
    "20260709": (3, 3, 3, 3, 0),
    "20260710": (2, 2, 2, 20, 1),
    "20260711": (1, 1, 1, 2, 1),
    "20260713": (12, 11, 16, 82, 15),
    "20260714": (2, 0, 4, 12, 3),
    "20260715": (3, 3, 3, 27, 3),
    "20260716": (8, 7, 8, 15, 5),
    "20260717": (2, 1, 4, 12, 3),
    "20260718": (5, 5, 5, 18, 4),
    "20260719": (2, 1, 2, 4, 2),
    "20260720": (5, 4, 5, 19, 5),
    "20260721": (2, 1, 2, 8, 2),
    "20260722": (5, 4, 7, 65, 5),
    "20260723": (1, 1, 1, 13, 1),
    "20260724": (9, 7, 11, 35, 11),
    "20260725": (2, 1, 3, 18, 3),
    "20260726": (2, 2, 2, 4, 2),
    "20260727": (4, 2, 5, 10, 3),
    "20260728": (4, 2, 6, 11, 5),
    "20260729": (0, 0, 1, 0, 0),
    "20260730": (1, 1, 1, 2, 1),
    "20260803": (1, 0, 2, 4, 2),
    "20260804": (2, 1, 5, 17, 5),
    "20260805": (1, 0, 1, 3, 1),
    "20260806": (1, 0, 1, 2, 1),
    "20260807": (4, 2, 6, 33, 6),
    "20260809": (2, 0, 2, 8, 2),
    "20260810": (3, 1, 4, 9, 4),
    "20260811": (2, 1, 2, 5, 2),
    "20260812": (1, 0, 1, 7, 1),
    "20260813": (1, 0, 1, 4, 1),
    "20260814": (1, 0, 2, 7, 2),
}
START = dt.date(2026, 7, 9)
END = dt.date(2026, 8, 17)
DAYS = [START + dt.timedelta(days=i) for i in range((END - START).days + 1)]


def day(d):
    return DAILY_RAW.get(d.strftime("%Y%m%d"), (0, 0, 0, 0, 0))


SESS = [day(d)[2] for d in DAYS]
VIEWS = [day(d)[3] for d in DAYS]
USERS = [day(d)[0] for d in DAYS]

TOT = dict(users=64, new_users=64, sessions=118, views=479, engaged=102,
           eng_rate=0.8644, avg_dur=279.84, events=1003, bounce=0.1356, vps=4.06)

CHANNELS = [  # channel, sessions, users, engagement, avg duration (s)
    ("Direct", 66, 55, 0.8333, 244.6),
    ("Organic Search", 52, 10, 0.9038, 324.6),
]
SOURCES = [("(direct) / (none)", 66, 55, 0.8333),
           ("google / organic", 41, 9, 0.8780),
           ("bing / organic", 11, 1, 1.0)]

PRODUCTS = [  # title, views, users, engagement seconds
    ("Framont Access — home", 185, 59, 688),
    ("ETI", 81, 21, 1064),
    ("AMC", 67, 16, 1202),
    ("Deals", 44, 16, 435),
    ("Fondi (IT)", 40, 9, 460),
    ("Funds (EN)", 29, 12, 394),
]
INSIGHTS_PAGES = [
    ("/articles/ — Insights hub (EN)", 13, 12),
    ("/articles/it/ — Insights hub (IT)", 12, 4),
    ("/articles/it/cos-e-un-eti.html", 3, 2),
    ("/articles/it/amc-certificati-gestione-attiva.html", 2, 2),
    ("/articles/amc-actively-managed-certificates.html", 1, 1),
    ("/articles/it/valutare-strategie-sistematiche.html", 1, 1),
    ("/articles/what-is-an-eti.html", 1, 1),
]

FUNNEL = [  # stage, users, note
    ("Visitors", 64, "everyone who reached the site"),
    ("Scrolled the page", 47, "scroll event"),
    ("Viewed a product", 16, "view_product"),
    ("Saw an access gate", 7, "gate_impression"),
    ("Started registration", 5, "registration_start"),
    ("Completed registration", 2, "registration_complete"),
]

# product, view_product, gate_impression, gate_click, reg_start, form_start
PRODUCT_FUNNEL = [
    ("ETI", 42, 0, 0, 0, 0),
    ("AMC", 19, 19, 5, 7, 3),
    ("Deals", 0, 24, 3, 0, 5),
    ("Funds (EN)", 4, 0, 0, 0, 0),
    ("Fondi (IT)", 3, 0, 0, 0, 0),
    ("Home", 0, 0, 0, 4, 7),
]

INTENT = [("Registration completed", 2, 2), ("Access request sent", 4, 4),
          ("Deals access request", 1, 1), ("Call requested (submitted)", 1, 1),
          ("Product info requested", 2, 1)]

CITIES = [("Amsterdam", "Netherlands", 13, 13), ("Dublin", "Ireland", 12, 12),
          ("Milan", "Italy", 6, 7), ("Trezzano sul Naviglio", "Italy", 4, 4),
          ("Venice", "Italy", 4, 4), ("Swieqi", "Malta", 4, 21),
          ("Udine", "Italy", 2, 7), ("Mosta", "Malta", 2, 7),
          ("Greece (city not set)", "Greece", 2, 5), ("Ashburn, VA", "United States", 2, 2)]

DEVICES = [("Desktop", 98, 50, 0.8673, 294.9), ("Mobile", 19, 13, 0.8421, 133.8),
           ("Tablet", 1, 1, 1.0, 1583.2)]

WEEKS = [  # label, sessions, users, views
    ("Jul 9–15", 29, 23, 146), ("Jul 16–22", 33, 29, 141),
    ("Jul 23–29", 29, 22, 91), ("Jul 30–Aug 5", 9, 5, 26),
    ("Aug 6–12", 16, 13, 64), ("Aug 13–17*", 3, 2, 11),
]


def mmss(s):
    return f"{int(s)//60}m {int(round(s))%60:02d}s"


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ---------------------------------------------------------------- charts
def trend_panel(values, label, color, fill, height=120, show_x=True, peak_note=None):
    """Column chart over the full day range. Direct label on max; sparse x ticks."""
    w, pad_l, pad_r, pad_t, pad_b = 700, 34, 8, 28, 20 if show_x else 6
    plot_w = w - pad_l - pad_r
    plot_h = height - pad_t - pad_b
    vmax = max(values) or 1
    n = len(values)
    step = plot_w / n
    bw = min(step - 2.4, 13)
    parts = []
    # gridlines + y labels
    for frac in (0, 0.5, 1.0):
        y = pad_t + plot_h - frac * plot_h
        parts.append(f'<line x1="{pad_l}" y1="{y:.1f}" x2="{w-pad_r}" y2="{y:.1f}" '
                     f'stroke="{SAND}" stroke-width="1"/>')
        parts.append(f'<text x="{pad_l-7:.0f}" y="{y+3.5:.1f}" text-anchor="end" '
                     f'class="ax">{round(vmax*frac)}</text>')
    for i, v in enumerate(values):
        x = pad_l + i * step + (step - bw) / 2
        if v == 0:
            parts.append(f'<rect x="{x:.1f}" y="{pad_t+plot_h-1.5:.1f}" width="{bw:.1f}" '
                         f'height="1.5" fill="{SAND}"/>')
            continue
        h = max(v / vmax * plot_h, 2.5)
        y = pad_t + plot_h - h
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{h:.1f}" '
                     f'rx="2" fill="{fill}"/>')
        if v == vmax:
            parts.append(f'<text x="{x+bw/2:.1f}" y="{y-4:.1f}" text-anchor="middle" '
                         f'class="dl">{v}</text>')
    if show_x:
        for i, d in enumerate(DAYS):
            if i % 7 == 0 or i == len(DAYS) - 1:
                x = pad_l + i * step + step / 2
                parts.append(f'<text x="{x:.1f}" y="{height-5:.0f}" text-anchor="middle" '
                             f'class="ax">{d.strftime("%-d %b")}</text>')
    parts.append(f'<text x="{pad_l}" y="{11}" class="panel-lab" fill="{color}">{label}</text>')
    return (f'<svg viewBox="0 0 {w} {height}" width="100%" role="img" '
            f'aria-label="{label} per day">{"".join(parts)}</svg>')


def funnel_chart():
    w, h = 700, 148
    pad_l, pad_r, top, rowh = 168, 96, 2, 25
    plot_w = w - pad_l - pad_r
    base = FUNNEL[0][1]
    parts = []
    for i, (stage, val, note) in enumerate(FUNNEL):
        y = top + i * rowh
        bw = max(val / base * plot_w, 3)
        shade = ORANGE if i >= 3 else SERIES_BLUE
        parts.append(f'<rect x="{pad_l}" y="{y}" width="{plot_w}" height="20" rx="3" fill="{SAND_L}"/>')
        parts.append(f'<rect x="{pad_l}" y="{y}" width="{bw:.1f}" height="20" rx="3" fill="{shade}"/>')
        parts.append(f'<text x="{pad_l-12}" y="{y+14}" text-anchor="end" class="fl">{esc(stage)}</text>')
        pct = val / base * 100
        parts.append(f'<text x="{pad_l+plot_w+10}" y="{y+14}" class="fv">{val} '
                     f'<tspan class="fp">· {pct:.0f}%</tspan></text>')
        if i:
            drop = FUNNEL[i-1][1] - val
            if drop:
                parts.append(f'<text x="{pad_l+bw+8:.1f}" y="{y+14}" class="fdrop">−{drop}</text>')
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" role="img" '
            f'aria-label="Visitor to registration funnel">{"".join(parts)}</svg>')


def weekly_chart():
    w, h = 700, 150
    pad_l, pad_b, pad_t = 34, 34, 18
    plot_w, plot_h = w - pad_l - 10, h - pad_b - pad_t
    vmax = max(x[1] for x in WEEKS)
    step = plot_w / len(WEEKS)
    bw = step * 0.46
    parts = []
    for frac in (0, 0.5, 1.0):
        y = pad_t + plot_h - frac * plot_h
        parts.append(f'<line x1="{pad_l}" y1="{y:.1f}" x2="{w-10}" y2="{y:.1f}" stroke="{SAND}" stroke-width="1"/>')
        parts.append(f'<text x="{pad_l-7}" y="{y+3.5:.1f}" text-anchor="end" class="ax">{round(vmax*frac)}</text>')
    for i, (lab, s, u, v) in enumerate(WEEKS):
        x = pad_l + i * step + (step - bw) / 2
        hh = max(s / vmax * plot_h, 2)
        y = pad_t + plot_h - hh
        col = ORANGE if i == len(WEEKS) - 1 else SERIES_BLUE
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{hh:.1f}" rx="3" fill="{col}"/>')
        parts.append(f'<text x="{x+bw/2:.1f}" y="{y-5:.1f}" text-anchor="middle" class="dl">{s}</text>')
        parts.append(f'<text x="{x+bw/2:.1f}" y="{h-14:.0f}" text-anchor="middle" class="ax">{lab}</text>')
    parts.append(f'<text x="{pad_l}" y="10" class="panel-lab" fill="{SERIES_BLUE}">Sessions per week</text>')
    parts.append(f'<text x="{w-10}" y="{h-2}" text-anchor="end" class="ax">*partial week (3 of 5 days had no traffic)</text>')
    return f'<svg viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="Sessions per week">{"".join(parts)}</svg>'


def bar_cell(val, vmax, color=SERIES_BLUE):
    pct = 0 if not vmax else val / vmax * 100
    return (f'<span class="cellbar"><span class="cellbar-f" style="width:{pct:.1f}%;'
            f'background:{color}"></span></span>')


# ---------------------------------------------------------------- html
def kpi(v, label, sub=""):
    tail = '<div class="kpi-s">%s</div>' % sub if sub else ""
    return (f'<div class="kpi"><div class="kpi-v">{v}</div><div class="kpi-l">{label}</div>'
            f'{tail}</div>')


max_ch = max(c[1] for c in CHANNELS)
max_pv = max(p[1] for p in PRODUCTS)
max_ip = max(p[1] for p in INSIGHTS_PAGES)
max_city = max(c[2] for c in CITIES)

channel_rows = "".join(
    f'<tr><td class="strong">{esc(c)}</td><td class="num">{s}</td><td class="bar-td">{bar_cell(s, max_ch)}</td>'
    f'<td class="num">{u}</td><td class="num">{e*100:.0f}%</td><td class="num">{mmss(d)}</td></tr>'
    for c, s, u, e, d in CHANNELS)

source_rows = "".join(
    f'<tr><td class="mono">{esc(s)}</td><td class="num">{ses}</td><td class="num">{u}</td>'
    f'<td class="num">{e*100:.0f}%</td></tr>' for s, ses, u, e in SOURCES)

product_rows = "".join(
    f'<tr><td class="strong">{esc(t)}</td><td class="num">{v}</td><td class="bar-td">{bar_cell(v, max_pv)}</td>'
    f'<td class="num">{u}</td><td class="num">{mmss(e/u)}</td></tr>'
    for t, v, u, e in PRODUCTS)

insight_rows = "".join(
    f'<tr><td class="mono">{esc(p)}</td><td class="num">{v}</td><td class="bar-td">{bar_cell(v, max_ip, ORANGE)}</td>'
    f'<td class="num">{u}</td></tr>' for p, v, u in INSIGHTS_PAGES)

pf_rows = "".join(
    f'<tr><td class="strong">{esc(p)}</td><td class="num">{vp or "—"}</td><td class="num">{gi or "—"}</td>'
    f'<td class="num">{gc or "—"}</td><td class="num">{fs or "—"}</td><td class="num">{rs or "—"}</td></tr>'
    for p, vp, gi, gc, rs, fs in PRODUCT_FUNNEL)

city_rows = "".join(
    f'<tr><td class="strong">{esc(c)}</td><td>{esc(co)}</td><td class="num">{u}</td>'
    f'<td class="bar-td">{bar_cell(u, max_city)}</td><td class="num">{s}</td>'
    f'<td class="num">{s/u:.1f}</td></tr>' for c, co, u, s in CITIES)

device_rows = "".join(
    f'<tr><td class="strong">{esc(d)}</td><td class="num">{s}</td><td class="num">{s/118*100:.0f}%</td>'
    f'<td class="num">{u}</td><td class="num">{e*100:.0f}%</td><td class="num">{mmss(dur)}</td></tr>'
    for d, s, u, e, dur in DEVICES)

intent_rows = "".join(
    f'<tr><td class="strong">{esc(n)}</td><td class="num">{e}</td><td class="num">{u}</td></tr>'
    for n, e, u in INTENT)

def daily_table(days):
    rows = "".join(
        f'<tr><td>{d.strftime("%a %-d %b")}</td><td class="num">{day(d)[0]}</td>'
        f'<td class="num">{day(d)[2]}</td><td class="num">{day(d)[3]}</td>'
        f'<td class="num">{day(d)[4]}</td></tr>' for d in days)
    return ('<table><thead><tr><th>Day</th><th class="num">Vis.</th><th class="num">Sess.</th>'
            '<th class="num">Views</th><th class="num">Eng.</th></tr></thead>'
            f'<tbody>{rows}</tbody></table>')


half = (len(DAYS) + 1) // 2
daily_left, daily_right = daily_table(DAYS[:half]), daily_table(DAYS[half:])

week_rows = "".join(
    f'<tr><td class="strong">{esc(l)}</td><td class="num">{s}</td><td class="num">{u}</td>'
    f'<td class="num">{v}</td><td class="num">{v/s:.1f}</td></tr>' for l, s, u, v in WEEKS)

HTML = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Framont Access — Digital Performance Report</title>
<style>
{FONTS}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
@page {{ size: A4; margin: 0; }}
html {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
body {{ font-family: 'Work Sans', Arial, sans-serif; color: {INK}; background: {PAPER};
       font-size: 9.4pt; line-height: 1.5; }}
.page {{ width: 210mm; height: 297mm; padding: 17mm 16mm 14mm; position: relative;
        page-break-after: always; overflow: hidden; }}
.page:last-child {{ page-break-after: auto; }}

/* ---------- cover ---------- */
.cover {{ background: {NAVY}; color: #fff; padding: 0; }}
.cover-inner {{ padding: 30mm 18mm 18mm; height: 100%; display: flex; flex-direction: column; }}
.cover .mark {{ font-family: 'Work Sans'; font-weight: 600; letter-spacing: .42em;
               font-size: 8.4pt; text-transform: uppercase; color: {ORANGE}; }}
.cover h1 {{ font-family: 'Playfair Display', serif; font-weight: 600; font-size: 40pt;
            line-height: 1.06; margin-top: 14mm; color: #fff; letter-spacing: -.01em; }}
.cover h1 em {{ font-style: italic; color: {ORANGE}; }}
.cover .sub {{ font-size: 12pt; font-weight: 300; color: #BFC8D2; margin-top: 7mm;
              max-width: 118mm; line-height: 1.5; }}
.rule {{ width: 34mm; height: 3px; background: {ORANGE}; margin: 11mm 0; }}
.cover-meta {{ margin-top: auto; display: grid; grid-template-columns: repeat(2, 1fr);
              gap: 7mm 10mm; border-top: 1px solid rgba(255,255,255,.22); padding-top: 8mm; }}
.cover-meta dt {{ font-size: 7.4pt; letter-spacing: .17em; text-transform: uppercase;
                 color: {ORANGE}; font-weight: 600; margin-bottom: 1.5mm; }}
.cover-meta dd {{ font-size: 10pt; color: #E9EDF2; font-weight: 300; }}
.cover-foot {{ margin-top: 9mm; font-size: 7.6pt; color: #8FA0B4; letter-spacing: .05em; }}

/* ---------- structure ---------- */
.head {{ display: flex; justify-content: space-between; align-items: baseline;
        border-bottom: 1px solid {SAND}; padding-bottom: 3mm; margin-bottom: 7mm; }}
.head .t {{ font-size: 7.4pt; letter-spacing: .2em; text-transform: uppercase;
           color: {MUTED}; font-weight: 600; }}
.head .n {{ font-size: 7.4pt; letter-spacing: .12em; color: {MUTED}; }}
h2 {{ font-family: 'Playfair Display', serif; font-weight: 600; font-size: 20pt;
     color: {NAVY}; line-height: 1.18; margin-bottom: 2.5mm; letter-spacing: -.005em; }}
h3 {{ font-family: 'Work Sans'; font-size: 8pt; letter-spacing: .17em; text-transform: uppercase;
     color: {NAVY}; font-weight: 600; margin: 6mm 0 2.5mm; }}
h3:first-of-type {{ margin-top: 5mm; }}
.lede {{ font-size: 10.2pt; font-weight: 300; line-height: 1.55; color: {INK};
        max-width: 165mm; margin-bottom: 2mm; }}
p {{ margin-bottom: 2.6mm; }}
.foot {{ position: absolute; left: 16mm; right: 16mm; bottom: 8mm; display: flex;
        justify-content: space-between; font-size: 7pt; color: {MUTED};
        border-top: 1px solid {SAND}; padding-top: 2.5mm; letter-spacing: .06em; }}
strong {{ font-weight: 600; color: {NAVY}; }}

/* ---------- kpis ---------- */
.kpis {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 3mm; margin: 4mm 0 1mm; }}
.kpi {{ background: {SAND_L}; border-top: 2.5px solid {NAVY}; padding: 3.2mm 3.5mm 3.6mm; }}
.kpi-v {{ font-family: 'Playfair Display', serif; font-size: 21pt; color: {NAVY};
         line-height: 1; font-weight: 600; }}
.kpi-l {{ font-size: 7.2pt; letter-spacing: .14em; text-transform: uppercase;
         color: {MUTED}; margin-top: 2.5mm; font-weight: 600; }}
.kpi-s {{ font-size: 8pt; color: {INK}; margin-top: 1.5mm; font-weight: 300; }}
.kpi.accent {{ border-top-color: {ORANGE}; }}
.kpi.accent .kpi-v {{ color: {ORANGE_D}; }}

/* ---------- callouts ---------- */
.callout {{ background: {SAND_L}; border-left: 3px solid {ORANGE}; padding: 3.4mm 4.5mm;
           margin: 3.4mm 0; font-size: 9pt; line-height: 1.5; }}
.callout .ct {{ font-weight: 600; color: {NAVY}; display: block; margin-bottom: 1.5mm;
               font-size: 8pt; letter-spacing: .12em; text-transform: uppercase; }}
.note {{ font-size: 7.9pt; color: {MUTED}; line-height: 1.45; margin-top: 2mm; font-weight: 300; }}

/* ---------- tables ---------- */
table {{ width: 100%; border-collapse: collapse; font-size: 8.6pt; margin-top: 2mm; }}
th {{ font-size: 7pt; letter-spacing: .13em; text-transform: uppercase; color: {MUTED};
     font-weight: 600; text-align: left; padding: 0 2.5mm 1.6mm 0; border-bottom: 1px solid {NAVY}; }}
td {{ padding: 1.6mm 2.5mm 1.6mm 0; border-bottom: 1px solid {SAND}; vertical-align: middle; }}
th.num, td.num {{ text-align: right; padding-right: 0; }}
td.strong {{ font-weight: 600; color: {NAVY}; }}
td.mono {{ font-family: 'Work Sans'; font-size: 8pt; color: {INK}; }}
.bar-td {{ width: 30%; padding-left: 4mm; }}
.est th:nth-child(2), .est th:nth-child(3), .est td:nth-child(2), .est td:nth-child(3) {{ width: 20mm; }}
.est th:last-child, .est td:last-child {{ padding-left: 7mm; width: 92mm; }}
.est2 th:nth-child(2), .est2 td:nth-child(2) {{ width: 26mm; }}
.est2 th:nth-child(3), .est2 td:nth-child(3) {{ width: 34mm; }}
.est2 th:last-child, .est2 td:last-child {{ padding-left: 8mm; width: 68mm; }}
.zero th:nth-child(2), .zero td:nth-child(2) {{ width: 24mm; }}
.zero th:last-child, .zero td:last-child {{ padding-left: 8mm; width: 110mm; }}
.zed {{ color: {ORANGE_D}; font-weight: 600; }}
.cellbar {{ display: block; height: 6px; background: {SAND}; border-radius: 3px; overflow: hidden; }}
.cellbar-f {{ display: block; height: 100%; border-radius: 3px; }}
tbody tr:last-child td {{ border-bottom: none; }}

/* ---------- charts ---------- */
.chart {{ margin: 3mm 0 1mm; }}
.ax {{ font: 400 7.4px 'Work Sans'; fill: {MUTED}; }}
.dl {{ font: 600 8.4px 'Work Sans'; fill: {NAVY}; }}
.panel-lab {{ font: 600 8px 'Work Sans'; letter-spacing: .12em; text-transform: uppercase; }}
.fl {{ font: 400 10px 'Work Sans'; fill: {INK}; }}
.fv {{ font: 600 11px 'Work Sans'; fill: {NAVY}; }}
.fp {{ font: 400 9.5px 'Work Sans'; fill: {MUTED}; }}
.fdrop {{ font: 400 9px 'Work Sans'; fill: {ORANGE_D}; }}
.legend {{ display: flex; gap: 6mm; font-size: 7.6pt; color: {MUTED}; margin-top: 1mm; }}
.legend i {{ display: inline-block; width: 9px; height: 9px; border-radius: 2px;
            margin-right: 2mm; vertical-align: -1px; }}

/* ---------- recommendations ---------- */
.rec {{ display: grid; grid-template-columns: 13mm 1fr; gap: 0 4mm; padding: 3.4mm 0;
       border-bottom: 1px solid {SAND}; }}
.rec:last-child {{ border-bottom: none; }}
.rec-n {{ font-family: 'Playfair Display', serif; font-size: 17pt; color: {ORANGE};
         line-height: 1; font-weight: 600; }}
.rec h4 {{ font-size: 10.4pt; color: {NAVY}; font-weight: 600; margin-bottom: 1.5mm; }}
.rec p {{ font-size: 8.8pt; line-height: 1.55; margin-bottom: 1.5mm; font-weight: 300; }}
.tag {{ display: inline-block; font-size: 6.8pt; letter-spacing: .12em; text-transform: uppercase;
       font-weight: 600; padding: 1mm 2.2mm; border-radius: 2px; margin-right: 2mm; }}
.tag.hi {{ background: {ORANGE}; color: #3A1D00; }}
.tag.md {{ background: {SAND}; color: {NAVY}; }}
.evidence {{ font-size: 8.2pt; color: {MUTED}; font-weight: 300; }}
.evidence b {{ color: {NAVY}; font-weight: 600; }}
ul.clean {{ list-style: none; }}
ul.clean li {{ padding-left: 5mm; position: relative; margin-bottom: 2mm; font-size: 8.8pt;
              line-height: 1.5; font-weight: 300; }}
ul.clean li::before {{ content: "—"; position: absolute; left: 0; color: {ORANGE}; }}
.two {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8mm; }}
.appendix table td, .appendix table th {{ font-size: 7.6pt; padding-top: 0.95mm; padding-bottom: 0.95mm; }}
</style></head><body>

<!-- ============ COVER ============ -->
<section class="page cover"><div class="cover-inner">
  <div class="mark">Framont Access</div>
  <h1>Digital Performance<br><em>Report</em></h1>
  <div class="sub">The first forty days of access.framontmanagement.com — traffic,
    audience quality, product interest and the path from visitor to registered investor.</div>
  <div class="rule"></div>
  <dl class="cover-meta">
    <div><dt>Reporting period</dt><dd>9 July – 17 August 2026</dd></div>
    <div><dt>Coverage</dt><dd>Since measurement went live</dd></div>
    <div><dt>Property</dt><dd>GA4 · 544861486</dd></div>
    <div><dt>Data stream</dt><dd>G-YRE5XX3RN2 · Web</dd></div>
    <div><dt>Time zone</dt><dd>Europe/Malta</dd></div>
    <div><dt>Issued</dt><dd>17 August 2026</dd></div>
  </dl>
  <div class="cover-foot">Prepared by NIUEXA · Source: Google Analytics 4 Data API</div>
</div></section>

<!-- ============ 1. EXECUTIVE SUMMARY ============ -->
<section class="page">
  <div class="head"><span class="t">Executive summary</span><span class="n">Framont Access · Jul–Aug 2026</span></div>
  <h2>A small, serious audience — and a funnel that stops<br>one step before the finish line</h2>
  <p class="lede">In its first forty days of measurement the site drew <strong>64 visitors</strong> across
  <strong>118 sessions</strong>. That is a small sample, so read the percentages as direction, not precision.
  What the sample says is consistent and useful: the people who arrive are genuinely engaged, they
  concentrate on two products, and almost none of them finish registering.</p>

  <div class="kpis">
    {kpi("64", "Visitors", "all first-time")}
    {kpi("118", "Sessions", "1.8 per visitor")}
    {kpi("4m 40s", "Avg. session", "vs ~1m typical")}
    {kpi("86%", "Engagement rate", "13.6% bounce")}
  </div>
  <div class="kpis">
    {kpi("479", "Page views", "4.1 per session")}
    {kpi("16", "Viewed a product", "25% of visitors")}
    {kpi("5", "Started registration", "7.8% of visitors")}
    {kpi("2", "Completed", "3.1% of visitors", )}
  </div>

  <h3>The four things worth acting on</h3>
  <div class="callout"><span class="ct">1 · ETI is the magnet with no hook</span>
    ETI is the most-viewed product — <strong>42 product views from 11 people</strong>, more than double AMC —
    yet it produced <strong>zero gate impressions and zero registration starts</strong>. The strongest source
    of demand has no conversion mechanism attached to it.</div>
  <div class="callout"><span class="ct">2 · Registration leaks at the last step</span>
    <strong>11 registration starts became 2 completions.</strong> Five people began, two finished. The interest
    is real and it is being lost inside the form, not before it.</div>
  <div class="callout"><span class="ct">3 · A quarter of the traffic is your own team</span>
    Malta accounts for <strong>28 of 118 sessions (24%)</strong> from just 6 people — consistent with internal
    use. A further 25 visitors from Amsterdam and Dublin show a one-session, no-engagement pattern typical of
    cloud infrastructure. The genuine external audience is closer to <strong>~30 people</strong>.</div>
  <div class="callout"><span class="ct">4 · Traffic is fading, because nothing is feeding it</span>
    Weekly sessions fell from 33 (mid-July) to 3 in the final partial week, and
    <strong>no activity at all was recorded after 14 August</strong>. There is no referral, paid, social or
    email traffic — only direct visits and a handful of organic searches.</div>

  <div class="foot"><span>Framont Access · Digital Performance Report</span><span>1</span></div>
</section>

<!-- ============ 2. TRAFFIC OVER TIME ============ -->
<section class="page">
  <div class="head"><span class="t">01 · Traffic over time</span><span class="n">9 Jul – 17 Aug 2026</span></div>
  <h2>Daily trend since measurement went live</h2>
  <p class="lede">Every day since the data stream was created on 9 July. Eight days recorded no traffic at all,
  including the last three days of the period.</p>

  <div class="chart">{trend_panel(SESS, "Sessions per day", NAVY, SERIES_BLUE, 132, False)}</div>
  <div class="chart">{trend_panel(VIEWS, "Page views per day", ORANGE_D, ORANGE, 140, True)}</div>
  <div class="legend">
    <span><i style="background:{SERIES_BLUE}"></i>Sessions</span>
    <span><i style="background:{ORANGE}"></i>Page views</span>
    <span><i style="background:{SAND}"></i>Day with no traffic</span>
  </div>

  <p class="note">The 13 July spike (16 sessions, 82 page views) and the 22 July page-view spike (65 views from
  7 sessions) are single-day events driven by a handful of people moving through many product screens —
  they are depth of browsing, not a rise in audience.</p>

  <h3>The same data, weekly</h3>
  <div class="chart">{weekly_chart()}</div>
  <table>
    <thead><tr><th>Week</th><th class="num">Sessions</th><th class="num">Visitors</th>
    <th class="num">Page views</th><th class="num">Views / session</th></tr></thead>
    <tbody>{week_rows}</tbody>
  </table>
  <p class="note">*13–17 August is a partial week; 15, 16 and 17 August recorded no traffic. The three full weeks
  from 9–29 July averaged 30 sessions per week; the two most recent full weeks averaged 12.5 — a decline of
  roughly 58%.</p>

  <div class="foot"><span>Framont Access · Digital Performance Report</span><span>2</span></div>
</section>

<!-- ============ 3. ACQUISITION ============ -->
<section class="page">
  <div class="head"><span class="t">02 · Acquisition</span><span class="n">Where the audience comes from</span></div>
  <h2>Two channels, and one of them is mostly you</h2>
  <p class="lede">All 118 sessions arrived through just two channels. There is no referral, paid, social,
  email or affiliate traffic in the entire period — the site is currently discovered by people who already
  know the address.</p>

  <h3>Channels</h3>
  <table>
    <thead><tr><th>Channel</th><th class="num">Sessions</th><th></th><th class="num">Visitors</th>
    <th class="num">Engaged</th><th class="num">Avg. session</th></tr></thead>
    <tbody>{channel_rows}</tbody>
  </table>

  <h3>Sources</h3>
  <table>
    <thead><tr><th>Source / medium</th><th class="num">Sessions</th><th class="num">Visitors</th>
    <th class="num">Engagement rate</th></tr></thead>
    <tbody>{source_rows}</tbody>
  </table>

  <div class="callout"><span class="ct">Read the organic number carefully</span>
    Organic Search shows 52 sessions but only <strong>10 distinct people</strong> — 5.2 sessions each, against
    1.2 for direct traffic. Eleven of those sessions come from a single Bing user. This pattern is far more
    consistent with repeat internal or SEO-monitoring visits than with 52 prospective investors finding you
    on Google.</div>

  <h3>New vs. returning</h3>
  <table>
    <thead><tr><th>Visitor type</th><th class="num">Sessions</th><th class="num">Visitors</th>
    <th class="num">Share of sessions</th><th class="num">Engagement rate</th></tr></thead>
    <tbody>
      <tr><td class="strong">New</td><td class="num">64</td><td class="num">64</td><td class="num">54%</td><td class="num">84%</td></tr>
      <tr><td class="strong">Returning</td><td class="num">52</td><td class="num">10</td><td class="num">44%</td><td class="num">92%</td></tr>
      <tr><td class="strong">Not set</td><td class="num">3</td><td class="num">—</td><td class="num">2%</td><td class="num">—</td></tr>
    </tbody>
  </table>
  <p class="note">Ten returning people generate 44% of all sessions — a very small group carries the activity.</p>

  <h3>The channels that recorded nothing</h3>
  <table class="zero">
    <thead><tr><th>Channel</th><th class="num">Sessions</th><th>What it would take</th></tr></thead>
    <tbody>
      <tr><td class="strong">Referral</td><td class="num zed">0</td>
        <td>Links from partner, custodian or industry-association sites</td></tr>
      <tr><td class="strong">Organic Social</td><td class="num zed">0</td>
        <td>A LinkedIn presence posting the Insights material</td></tr>
      <tr><td class="strong">Paid Search</td><td class="num zed">0</td>
        <td>Bids on ETI, AMC and structured-product terms</td></tr>
      <tr><td class="strong">Paid Social</td><td class="num zed">0</td>
        <td>LinkedIn targeting by job title, firm type and geography</td></tr>
      <tr><td class="strong">Email</td><td class="num zed">0</td>
        <td>A tagged newsletter or deal alert to the existing contact base</td></tr>
      <tr><td class="strong">Cross-network / Display</td><td class="num zed">0</td>
        <td>Retargeting the visitors who viewed a product but never registered</td></tr>
    </tbody>
  </table>
  <p class="note">For an audience defined by profession rather than search behaviour, referral and LinkedIn are
  the largest gaps.</p>

  <div class="foot"><span>Framont Access · Digital Performance Report</span><span>3</span></div>
</section>

<!-- ============ AUDIENCE QUALITY ============ -->
<section class="page">
  <div class="head"><span class="t">03 · Audience quality</span><span class="n">Who is really visiting</span></div>
  <h2>How many of the 64 are actually prospects?</h2>
  <p class="lede">With a sample this small, knowing who the visitors are matters more than counting them.
  Location and session patterns separate the genuine audience from internal use and automated traffic.</p>

  <h3>Where visitors are</h3>
  <table>
    <thead><tr><th>City</th><th>Country</th><th class="num">Visitors</th><th></th>
    <th class="num">Sessions</th><th class="num">Sess./visitor</th></tr></thead>
    <tbody>{city_rows}</tbody>
  </table>
  <p class="note">Top ten locations of 33 recorded. Italy is the largest genuine market by visitor count
  once the cloud-hosting locations are set aside.</p>

  <h3>Estimating the real audience</h3>
  <table class="est">
    <thead><tr><th>Segment</th><th class="num">Visitors</th><th class="num">Sessions</th><th>Why</th></tr></thead>
    <tbody>
      <tr><td class="strong">Malta (Swieqi, Mosta)</td><td class="num">6</td><td class="num">28</td>
        <td>4.7 sessions each — consistent with the Framont team's own use</td></tr>
      <tr><td class="strong">Amsterdam &amp; Dublin</td><td class="num">25</td><td class="num">25</td>
        <td>Exactly one session each; major cloud-hosting hubs</td></tr>
      <tr><td class="strong">Ashburn, Virginia</td><td class="num">2</td><td class="num">2</td>
        <td>The largest concentration of data centres in the world</td></tr>
      <tr><td class="strong">Everyone else</td><td class="num">~31</td><td class="num">~63</td>
        <td>Italy, Greece, Luxembourg, Switzerland and the remaining locations</td></tr>
    </tbody>
  </table>

  <div class="callout"><span class="ct">What this means for every number in this report</span>
    Roughly <strong>half the recorded visitors are not prospective investors</strong>. The engagement figures
    are flattered by internal use (long, repeated sessions) and depressed by automated traffic (single,
    empty sessions). Until an internal-traffic filter and bot exclusion are in place, treat the totals as an
    upper bound and the funnel — which only counts people who actually opened a product — as the reliable
    part of this report.</div>

  <p class="note">By browser, Windows with Chrome or Edge accounts for 75% of sessions — the corporate desktop
  profile — though 18 of those Edge sessions come from just 2 people, another repeat-visitor pattern.</p>

  <div class="foot"><span>Framont Access · Digital Performance Report</span><span>4</span></div>
</section>

<!-- ============ 4. WHAT PEOPLE LOOK AT ============ -->
<section class="page">
  <div class="head"><span class="t">04 · Content &amp; product interest</span><span class="n">What holds attention</span></div>
  <h2>ETI and AMC hold attention; everything else is a glance</h2>
  <p class="lede">The site is a single-page application, so every product screen is recorded on the same URL and
  separated by page title. Ranked by engaged time per visitor, the picture is clear.</p>

  <h3>Product screens</h3>
  <table>
    <thead><tr><th>Screen</th><th class="num">Views</th><th></th><th class="num">Visitors</th>
    <th class="num">Engaged time / visitor</th></tr></thead>
    <tbody>{product_rows}</tbody>
  </table>
  <p class="note">AMC commands the most attention per person (1m 15s), followed by ETI (50s) — against 12s on
  the home screen. These two products are what the audience actually came to understand.</p>

  <div class="callout"><span class="ct">Italian matters more than the traffic suggests</span>
    The Italian funds screen (<em>Fondi</em>) drew 40 views against 29 for the English <em>Funds</em>, and
    <strong>11 people manually switched language</strong> (15 switches). Italian is roughly a third of the
    audience but has to ask for itself.</div>

  <h3>Insights articles</h3>
  <table>
    <thead><tr><th>Page</th><th class="num">Views</th><th></th><th class="num">Visitors</th></tr></thead>
    <tbody>{insight_rows}</tbody>
  </table>
  <p class="note">Insights accounts for <strong>33 of 479 page views (6.9%)</strong> — 25 to the two hubs, 8 to
  the five articles. One reader spent 2m 54s on “What Is an ETI?”: a distribution problem, not a quality one.</p>

  <h3>Devices</h3>
  <table>
    <thead><tr><th>Device</th><th class="num">Sessions</th><th class="num">Share</th><th class="num">Visitors</th>
    <th class="num">Engaged</th><th class="num">Avg. session</th></tr></thead>
    <tbody>{device_rows}</tbody>
  </table>
  <p class="note">Desktop suits an institutional audience; mobile sessions last less than half as long, which
  is worth testing against the gate and the form. The single tablet session is an outlier.</p>

  <div class="foot"><span>Framont Access · Digital Performance Report</span><span>5</span></div>
</section>

<!-- ============ 5. FUNNEL ============ -->
<section class="page">
  <div class="head"><span class="t">05 · Conversion</span><span class="n">Visitor to registered investor</span></div>
  <h2>Where the 64 visitors went</h2>
  <p class="lede">Measured by distinct people, not events. Each step is the number of visitors who reached it
  at least once during the period.</p>

  <div class="chart">{funnel_chart()}</div>
  <div class="legend">
    <span><i style="background:{SERIES_BLUE}"></i>Reach &amp; engagement</span>
    <span><i style="background:{ORANGE}"></i>Access &amp; registration</span>
    <span style="margin-left:auto">Orange figures show visitors lost at each step</span>
  </div>

  <p class="note">Three quarters of visitors scroll, but only a quarter open a product. In event terms the last
  step is starker still: <strong>11 registration starts produced 2 completions — 82% abandonment inside the
  form.</strong></p>

  <h3>The funnel by product screen</h3>
  <table>
    <thead><tr><th>Screen</th><th class="num">Product views</th><th class="num">Gate shown</th>
    <th class="num">Gate clicked</th><th class="num">Form started</th><th class="num">Registration started</th></tr></thead>
    <tbody>{pf_rows}</tbody>
  </table>
  <p class="note">Event counts. The single most actionable finding in this report: <strong>ETI generates the most
  interest and offers no next step</strong>, while AMC is the only product that carries a visitor from view to
  registration.</p>

  <div class="callout"><span class="ct">The Deals gate is being shown, not taken</span>
    Deals produced <strong>24 gate impressions to only 5 people</strong> — the same visitors meeting the same
    wall repeatedly — converting into 3 clicks and 3 abandonments. A gate seen five times per person and
    clicked once is asking for commitment before it has given a reason.</div>

  <h3>High-intent actions recorded</h3>
  <table>
    <thead><tr><th>Action</th><th class="num">Events</th><th class="num">Visitors</th></tr></thead>
    <tbody>{intent_rows}</tbody>
  </table>
  <p class="note">About <strong>8 qualified enquiries</strong> in forty days from ~30 real visitors: a good rate,
  far too small a volume.</p>

  <div class="foot"><span>Framont Access · Digital Performance Report</span><span>6</span></div>
</section>

<!-- ============ 6. RECOMMENDATIONS ============ -->
<section class="page">
  <div class="head"><span class="t">06 · Recommendations</span><span class="n">Ranked by expected impact</span></div>
  <h2>What to do next</h2>
  <p class="lede">Seven actions, ordered by the size of the gap they close. The first three are changes to the
  site itself; the rest are measurement and demand.</p>

  <div class="rec"><div class="rec-n">1</div><div>
    <h4>Put an access gate and a call-to-action on ETI</h4>
    <p><span class="tag hi">Highest impact</span><span class="tag md">Site change</span></p>
    <p>ETI attracts more attention than any other product and currently ends in a dead end. Give it the same
    gate, registration prompt and “request a term sheet” path that AMC has.</p>
    <p class="evidence"><b>Evidence:</b> 42 product views · 11 visitors · 0 gate impressions · 0 registration starts.</p>
  </div></div>

  <div class="rec"><div class="rec-n">2</div><div>
    <h4>Rebuild the registration form around completion</h4>
    <p><span class="tag hi">Highest impact</span><span class="tag md">Site change</span></p>
    <p>Cut the form to the minimum an institutional contact will give on a first approach, show progress, and
    add field-level events so the abandoning step is visible next month rather than inferred.</p>
    <p class="evidence"><b>Evidence:</b> 11 registration starts → 2 completions (82% abandonment); 15 form starts
    across three screens.</p>
  </div></div>

  <div class="rec"><div class="rec-n">3</div><div>
    <h4>Give the Deals gate something to earn</h4>
    <p><span class="tag hi">Highest impact</span><span class="tag md">Site change</span></p>
    <p>Preview one or two live deals — name, structure, headline terms — before requiring registration, and stop
    re-showing the gate to a visitor who has already declined it in the same session.</p>
    <p class="evidence"><b>Evidence:</b> 24 gate impressions to 5 visitors · 3 clicks · 3 abandonments.</p>
  </div></div>

  <div class="rec"><div class="rec-n">4</div><div>
    <h4>Filter internal traffic and mark key events as conversions</h4>
    <p><span class="tag md">Measurement</span></p>
    <p>Add an internal-traffic filter for the Malta office IPs and a bot exclusion, then mark
    <em>registration_complete</em>, <em>access_request</em> and <em>call_request_submit</em> as key events so
    they appear in standard GA4 reports. Link Search Console to see which queries actually reach the site.</p>
    <p class="evidence"><b>Evidence:</b> 24% of sessions from Malta (6 people); 25 visitors from Amsterdam and
    Dublin with one session each and no engagement.</p>
  </div></div>

  <div class="rec"><div class="rec-n">5</div><div>
    <h4>Create demand — the site has no acquisition channel</h4>
    <p><span class="tag hi">Highest impact</span><span class="tag md">Marketing</span></p>
    <p>Nothing currently brings new people to the site. A targeted LinkedIn programme to family offices and
    wealth managers, distribution of the Insights articles through the Framont network, and partner referral
    links would each produce measurable channels within a month.</p>
    <p class="evidence"><b>Evidence:</b> 0 referral, 0 paid, 0 social, 0 email sessions; weekly sessions down
    ~58% from the July peak; no traffic after 14 August.</p>
  </div></div>

  <div class="foot"><span>Framont Access · Digital Performance Report</span><span>7</span></div>
</section>

<section class="page">
  <div class="head"><span class="t">06 · Recommendations</span><span class="n">continued</span></div>

  <div class="rec" style="padding-top:0"><div class="rec-n">6</div><div>
    <h4>Detect language automatically</h4>
    <p><span class="tag md">Site change</span></p>
    <p>Serve Italian to Italian browsers by default and keep the manual switch as an override. A third of the
    audience is Italian and currently has to find the toggle.</p>
    <p class="evidence"><b>Evidence:</b> 15 manual language switches by 11 visitors; Fondi (IT) 40 views vs
    Funds (EN) 29.</p>
  </div></div>

  <div class="rec"><div class="rec-n">7</div><div>
    <h4>Promote Insights instead of publishing more of it</h4>
    <p><span class="tag md">Content</span></p>
    <p>The articles are good — one reader spent nearly three minutes on the ETI guide — but almost nobody
    reaches them. Link them from the product screens they explain, and use them as the LinkedIn payload before
    writing anything new.</p>
    <p class="evidence"><b>Evidence:</b> 33 of 479 page views (6.9%); five articles drew 8 views between them.</p>
  </div></div>

  <h3>What to look for in the next report</h3>
  <table class="est2">
    <thead><tr><th>Measure</th><th class="num">Now</th><th class="num">Target next cycle</th><th>Depends on</th></tr></thead>
    <tbody>
      <tr><td class="strong">Registration completion rate</td><td class="num">18%</td><td class="num">50%</td>
        <td>Recommendation 2</td></tr>
      <tr><td class="strong">Products with a conversion path</td><td class="num">2 of 5</td><td class="num">5 of 5</td>
        <td>Recommendation 1</td></tr>
      <tr><td class="strong">Acquisition channels with traffic</td><td class="num">2</td><td class="num">4+</td>
        <td>Recommendation 5</td></tr>
      <tr><td class="strong">External visitors per week</td><td class="num">~8</td><td class="num">40+</td>
        <td>Recommendations 5 &amp; 7</td></tr>
      <tr><td class="strong">Qualified enquiries</td><td class="num">8 in 40 days</td><td class="num">8 per month</td>
        <td>All of the above</td></tr>
    </tbody>
  </table>
  <p class="note">Targets are deliberately modest: on a base this small the goal for the next cycle is a working
  funnel and a measurable acquisition channel, not volume.</p>

  <div class="callout" style="margin-top:9mm"><span class="ct">The next forty days</span>
    Two of these seven actions would change the shape of this report by the next cycle. Giving ETI a conversion
    path turns the site's strongest source of interest into enquiries, and rebuilding the registration form
    stops losing the people who have already decided they want in. Everything else — filters, language,
    content, demand — makes the numbers truer or bigger; those two make them work.</div>

  <div class="foot"><span>Framont Access · Digital Performance Report</span><span>8</span></div>
</section>

<!-- ============ 7. METHOD + APPENDIX ============ -->
<section class="page appendix">
  <div class="head"><span class="t">Appendix</span><span class="n">Method, caveats &amp; daily data</span></div>
  <h2>How to read this report</h2>

  <div class="two">
    <div>
      <h3>Method</h3>
      <ul class="clean">
        <li>All figures come from the Google Analytics 4 Data API, property 544861486, web stream
            G-YRE5XX3RN2 (access.framontmanagement.com), pulled on 17 August 2026.</li>
        <li>Period: 9 July – 17 August 2026 — the full life of the data stream, which was created
            9 July 2026. No earlier data exists.</li>
        <li>Dates and sessions follow the property's time zone, Europe/Malta.</li>
        <li>Funnel steps are counted as distinct visitors reaching a step at least once; the
            by-product table counts events.</li>
      </ul>
    </div>
    <div>
      <h3>Caveats</h3>
      <ul class="clean">
        <li><strong>Small sample.</strong> 64 visitors and 118 sessions. Percentages indicate direction;
            a single person moves them by 1.6 points.</li>
        <li><strong>Internal traffic is not filtered.</strong> Malta contributes 24% of sessions from
            6 people.</li>
        <li><strong>Likely automated traffic.</strong> 25 visitors from Amsterdam and Dublin and 2 from
            Ashburn, Virginia show one session each with no engagement — a cloud-hosting signature.</li>
        <li><strong>Single-page application.</strong> Product screens share the URL “/” and are separated
            by page title, so URL-level reporting understates product depth.</li>
        <li><strong>Partial final days.</strong> 15–17 August recorded no traffic; 17 August is also
            incomplete.</li>
      </ul>
    </div>
  </div>

  <h3>Daily detail · 9 July – 17 August 2026</h3>
  <div class="two" style="gap:10mm">
    <div>{daily_left}</div>
    <div>{daily_right}</div>
  </div>
  <p class="note">Vis. = active visitors · Sess. = sessions · Eng. = engaged sessions. Daily visitors sum to more
  than the period total of 64; all totals come from GA4 directly, not from this table.</p>

  <div class="foot"><span>Framont Access · Digital Performance Report · Prepared by NIUEXA</span><span>9</span></div>
</section>

</body></html>
"""

(OUT / "framont-report.html").write_text(HTML)
print("wrote framont-report.html", len(HTML), "bytes")
