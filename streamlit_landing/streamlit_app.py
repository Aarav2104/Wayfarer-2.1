"""Wayfarer: Streamlit front door. Styled after the Figma-inspired design system (white canvas,
black pill buttons, pastel blocks). The real app runs on a normal web host; this page explains
it and links to it. Set WAYFARER_URL (and optionally REPO_URL) in Streamlit Secrets."""
import base64, os
from pathlib import Path
import streamlit as st

OWNER = "Aarav Garg"
PHONE_DISPLAY, PHONE_LINK = "+91 96901 09311", "+919690109311"   # delete both lines' values to hide

st.set_page_config(page_title="Wayfarer · Plan your errands", page_icon="🧭", layout="wide")


def cfg(key):
    try:
        return st.secrets.get(key, "") or os.getenv(key, "")
    except Exception:
        return os.getenv(key, "")


APP_URL, REPO_URL = cfg("WAYFARER_URL"), cfg("REPO_URL")
img = Path(__file__).parent / "assets" / "preview.png"
IMG = base64.b64encode(img.read_bytes()).decode() if img.exists() else ""

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300..700&family=JetBrains+Mono:wght@400;500&display=swap');
#MainMenu, footer, header[data-testid="stHeader"], [data-testid="stToolbar"] {display:none !important}
.stApp {background:#fff}
.block-container {padding:0 !important; max-width:1200px !important}
.wf, .wf * {font-family:'Inter',system-ui,'SF Pro Display',Helvetica,sans-serif; color:#000; box-sizing:border-box; letter-spacing:-0.01em}
.wf {padding:0 32px 40px}
.wf a {text-decoration:none}
.nav {display:flex; align-items:center; justify-content:space-between; height:72px}
.brand {display:flex; align-items:center; gap:10px; font-weight:600; font-size:22px; letter-spacing:-0.02em}
.dot {width:24px; height:24px; border-radius:50%; background:#000; display:inline-block; position:relative}
.dot:after {content:""; position:absolute; left:7px; top:5px; border:5px solid transparent; border-bottom:9px solid #fff; transform:rotate(35deg)}
.pill {display:inline-flex; align-items:center; justify-content:center; min-height:44px; padding:10px 24px; border-radius:50px; font-weight:480; font-size:17px; cursor:pointer; transition:transform .15s}
.pill:active {transform:scale(.97)}
.pill.dark {background:#000; color:#fff !important}
.pill.dark * {color:#fff !important}
.pill.light {background:#fff; color:#000; box-shadow:inset 0 0 0 1.5px #000}
.eyebrow {font-family:'JetBrains Mono',ui-monospace,Menlo,monospace !important; font-size:13px; letter-spacing:.06em; text-transform:uppercase; margin:56px 0 18px}
h1.wf-h1 {font-size:clamp(40px,7vw,84px); line-height:1.02; font-weight:340; letter-spacing:-0.035em; margin:0 0 24px; max-width:900px}
.lead {font-size:clamp(18px,2.2vw,22px); line-height:1.45; font-weight:330; max-width:720px; margin:0 0 32px}
.row {display:flex; gap:12px; flex-wrap:wrap}
.note {font-size:14px; font-weight:330; margin-top:14px}
.panel {border-radius:24px; padding:48px; margin:72px 0 0}
.lilac {background:#c5b0f4} .lime {background:#dceeb1} .navy {background:#1f1d3d} .navy * {color:#fff}
.shot {display:block; width:100%; height:auto; border-radius:8px}
.cap {font-size:13px; margin-top:14px; font-weight:330}
h2.wf-h2 {font-size:clamp(30px,4.6vw,56px); line-height:1.08; font-weight:340; letter-spacing:-0.03em; margin:0 0 28px}
.grid3 {display:grid; grid-template-columns:repeat(3,1fr); gap:16px}
.card {background:#f7f7f5; border-radius:16px; padding:28px}
.card h3 {font-size:22px; font-weight:600; margin:0 0 10px; letter-spacing:-0.015em}
.card p {font-size:16px; line-height:1.5; font-weight:330; margin:0}
.steps {display:grid; grid-template-columns:repeat(4,1fr); gap:20px}
.step b.n {display:flex; align-items:center; justify-content:center; width:36px; height:36px; border-radius:50%; background:#000; color:#fff; font-weight:600; margin-bottom:14px}
.step b.n {color:#fff !important}
.step p {font-size:17px; line-height:1.4; font-weight:400; margin:0}
.chips {display:flex; gap:8px; flex-wrap:wrap; margin-bottom:16px}
.chip {background:#f7f7f5; border-radius:50px; padding:8px 16px; font-size:15px; font-weight:480}
.foot {margin-top:72px; padding-top:28px; border-top:1px solid #e6e6e6; display:flex; justify-content:space-between; gap:24px; flex-wrap:wrap; font-size:15px; font-weight:330}
.foot b {font-weight:600}
@media (max-width:820px) {
  .wf {padding:0 18px 32px} .panel {padding:24px; margin-top:48px; border-radius:20px}
  .grid3, .steps {grid-template-columns:1fr} .pill {width:100%} .nav .pill {width:auto}
}
</style>
"""


def btn(label, url, kind="dark"):
    return f'<a class="pill {kind}" href="{url}" target="_blank" rel="noopener noreferrer">{label}</a>'


open_btn = btn("Open Wayfarer", APP_URL) if APP_URL else '<span class="pill light" aria-disabled="true">Link coming soon</span>'
nav_btn = btn("Open app", APP_URL) if APP_URL else ""
code_btn = btn("View the code", REPO_URL, "light") if REPO_URL else ""
phone = f'<a href="tel:{PHONE_LINK}"><b>{PHONE_DISPLAY}</b></a>' if PHONE_LINK else ""
shot = f'<img class="shot" alt="Wayfarer on a laptop and a phone: a route with three numbered stops and a next-turn card" src="data:image/png;base64,{IMG}">' if IMG else ""

HTML = f"""
<div class="wf">
<div class="nav"><div class="brand"><span class="dot"></span>Wayfarer</div>{nav_btn}</div>
<div class="eyebrow">Errand planning · Version 2.1</div>
<h1 class="wf-h1">Your errands, in the right order.</h1>
<p class="lead">Wayfarer turns a to-do list into a route. Tell it what you need to do and by when. It finds nearby places, checks their opening hours, plans the order, and guides you there. When your day changes, it re-plans.</p>
<div class="row">{open_btn}{code_btn}</div>
<p class="note">No account needed. Works on phone and laptop. Allow location so it can find places near you.</p>
<div class="panel lilac">{shot}<p class="cap">Illustration with sample data. The live app uses real maps and places near you.</p></div>
<div class="eyebrow">What it does</div>
<h2 class="wf-h2">One plan for the whole day.</h2>
<div class="grid3">
<div class="card"><h3>Plans around deadlines</h3><p>Say “bank before 2 pm” and Wayfarer visits it first. It checks each shop’s opening hours at your arrival time and warns you when a stop will not fit.</p></div>
<div class="card"><h3>Finds the right place</h3><p>Searches OpenStreetMap for banks, pharmacies, groceries and named places near you, ranks them by match and distance, and lets you pick or pin the exact spot.</p></div>
<div class="card"><h3>Guides and adapts</h3><p>Spoken turn prompts, your live position on the map, and a fresh plan when you add, skip or finish a task. You approve every change.</p></div>
</div>
<div class="panel lime"><div class="eyebrow" style="margin-top:0">How it works</div><h2 class="wf-h2">Four steps from list to done.</h2>
<div class="steps">
<div class="step"><b class="n">1</b><p>Type your tasks in plain words.</p></div>
<div class="step"><b class="n">2</b><p>Review the suggested order and places.</p></div>
<div class="step"><b class="n">3</b><p>Start the journey and follow the voice guidance.</p></div>
<div class="step"><b class="n">4</b><p>Confirm each stop. The plan updates itself.</p></div>
</div></div>
<div class="eyebrow">Built with</div>
<div class="chips"><span class="chip">Python</span><span class="chip">FastAPI</span><span class="chip">Google OR-Tools</span><span class="chip">OpenStreetMap</span><span class="chip">Leaflet</span><span class="chip">Gemini (optional)</span></div>
<p class="lead" style="font-size:16px">Opening hours come from map data and are sometimes missing. You can type them in, or look them up online and verify them. All times are estimates.</p>
<div class="panel navy" style="text-align:left"><h2 class="wf-h2" style="margin-bottom:20px">Try it on your phone.</h2>
<p class="lead" style="margin-bottom:24px">The first open after a quiet period can take about a minute while the free server wakes up.</p>
{btn("Open Wayfarer", APP_URL, "light") if APP_URL else ""}</div>
<div class="foot"><div>Built by <b>{OWNER}</b></div><div>{phone}</div><div>Idea first presented at the Tata Imagination Challenge 2026 · Map data © OpenStreetMap contributors</div></div>
</div>
"""

# Streamlit's markdown treats indented or blank-line HTML as code, so flatten it first.
flat = "\n".join(line.strip() for line in (CSS + HTML).splitlines() if line.strip())
st.markdown(flat, unsafe_allow_html=True)
if not APP_URL:
    st.info("Owner note: add WAYFARER_URL in this app's Secrets to turn on the Open Wayfarer buttons.")
