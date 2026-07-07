"""
RecruitAI — Resume Ranking System
Clean light-theme UI with top navigation bar.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import requests
import streamlit as st

from frontend.components.charts import (
    experience_scatter, missing_skill_bar, quality_gauge,
    recommendation_pie, score_bar_chart, score_distribution, skill_match_bar,
)
from frontend.components.export import results_to_dataframe, to_csv, to_excel, to_pdf_report

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="RecruitAI",
    page_icon="R",
    layout="wide",
    initial_sidebar_state="collapsed",
)

if "page" not in st.session_state:
    st.session_state.page = "home"

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

/* ── Reset ── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html, body, [class*="css"] { font-family: 'Inter', system-ui, sans-serif; }

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
section[data-testid="stSidebar"]   { display: none !important; }
[data-testid="collapsedControl"]   { display: none !important; }
[data-testid="stDecoration"]       { display: none !important; }

/* ── Page background ── */
.stApp { background: #F1F5F9; }

/* ── Block container — top padding for nav, side padding for content ── */
.main .block-container {
    padding-top: 16px !important;
    padding-left: 40px !important;
    padding-right: 40px !important;
    padding-bottom: 60px !important;
    max-width: 1400px !important;
}

/* ─────────────────────────────────────────────────────
   NAV BAR — horizontal row at top of page
───────────────────────────────────────────────────── */

/* Nav-area secondary buttons look like text links */
div[data-testid="stButton"] > button[kind="secondary"] {
    background: transparent !important;
    color: #64748B !important;
    border: 1px solid transparent !important;
    box-shadow: none !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    padding: 7px 6px !important;
    border-radius: 8px !important;
    transition: all 0.15s !important;
    width: 100% !important;
}
div[data-testid="stButton"] > button[kind="secondary"]:hover {
    background: #EEF2FF !important;
    color: #4F46E5 !important;
    border-color: #C7D2FE !important;
    transform: none !important;
    box-shadow: none !important;
}

/* ─────────────────────────────────────────────────────
   CONTENT AREA
───────────────────────────────────────────────────── */

/* ── Page header ── */
.page-header { margin-bottom: 28px; }
.page-title {
    font-size: 1.75rem;
    font-weight: 800;
    color: #0F172A;
    letter-spacing: -0.5px;
    line-height: 1.2;
}
.page-desc {
    font-size: 0.95rem;
    color: #64748B;
    margin-top: 6px;
    line-height: 1.6;
    max-width: 680px;
}
.page-divider {
    height: 1px;
    background: #E2E8F0;
    margin: 20px 0 28px 0;
}

/* ── Cards ── */
.card {
    background: #FFFFFF;
    border-radius: 14px;
    border: 1px solid #E2E8F0;
    padding: 24px 28px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    margin-bottom: 16px;
}
.card-sm {
    background: #FFFFFF;
    border-radius: 12px;
    border: 1px solid #E2E8F0;
    padding: 18px 22px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}

/* ── Stat cards ── */
.stat-card {
    background: #FFFFFF;
    border-radius: 14px;
    border: 1px solid #E2E8F0;
    padding: 22px 20px;
    text-align: center;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    transition: transform 0.15s, box-shadow 0.15s;
}
.stat-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 16px rgba(0,0,0,0.08);
}
.stat-val {
    font-size: 2rem;
    font-weight: 800;
    color: #0F172A;
    line-height: 1;
    letter-spacing: -1px;
}
.stat-lbl {
    font-size: 0.78rem;
    color: #94A3B8;
    margin-top: 6px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.8px;
}
.stat-icon {
    font-size: 0.7rem;
    color: #94A3B8;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 10px;
}

/* ── Candidate card ── */
.cand-card {
    background: #FFFFFF;
    border-radius: 14px;
    border: 1px solid #E2E8F0;
    padding: 20px 24px;
    margin-bottom: 10px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    transition: all 0.15s;
}
.cand-card:hover {
    border-color: #C7D2FE;
    box-shadow: 0 4px 16px rgba(79,70,229,0.08);
}
.cand-rank {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 32px; height: 32px;
    border-radius: 8px;
    font-weight: 700;
    font-size: 0.85rem;
    flex-shrink: 0;
}
.rank-gold   { background: #FEF3C7; color: #92400E; border: 1px solid #FDE68A; }
.rank-silver { background: #F1F5F9; color: #475569; border: 1px solid #CBD5E1; }
.rank-bronze { background: #FEF9EE; color: #92400E; border: 1px solid #FED7AA; }
.rank-other  { background: #F8FAFC; color: #94A3B8; border: 1px solid #E2E8F0; }
.cand-name {
    font-size: 1rem;
    font-weight: 700;
    color: #0F172A;
}
.cand-meta {
    font-size: 0.8rem;
    color: #94A3B8;
    margin-top: 2px;
}

/* ── Score progress bar ── */
.score-track {
    background: #F1F5F9;
    border-radius: 999px;
    height: 8px;
    overflow: hidden;
    margin-top: 8px;
}
.score-fill {
    height: 100%;
    border-radius: 999px;
}
.score-fill-high   { background: linear-gradient(90deg, #059669, #10B981); }
.score-fill-good   { background: linear-gradient(90deg, #0284C7, #38BDF8); }
.score-fill-mid    { background: linear-gradient(90deg, #D97706, #FBBF24); }
.score-fill-low    { background: linear-gradient(90deg, #EA580C, #FB923C); }
.score-fill-poor   { background: linear-gradient(90deg, #DC2626, #EF4444); }

/* ── Badges ── */
.badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 999px;
    font-size: 0.74rem;
    font-weight: 600;
    letter-spacing: 0.2px;
}
.b-excellent { background: #D1FAE5; color: #065F46; }
.b-strong    { background: #DCFCE7; color: #166534; }
.b-suitable  { background: #FEF3C7; color: #92400E; }
.b-average   { background: #FFEDD5; color: #9A3412; }
.b-not       { background: #FEE2E2; color: #991B1B; }

/* ── Skill chips ── */
.chip {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 6px;
    font-size: 0.74rem;
    font-weight: 500;
    margin: 2px 3px 2px 0;
    letter-spacing: 0.1px;
}
.c-green  { background: #ECFDF5; color: #065F46; border: 1px solid #A7F3D0; }
.c-red    { background: #FFF1F2; color: #9F1239; border: 1px solid #FECDD3; }
.c-blue   { background: #EFF6FF; color: #1E40AF; border: 1px solid #BFDBFE; }
.c-purple { background: #F5F3FF; color: #5B21B6; border: 1px solid #DDD6FE; }
.c-gray   { background: #F8FAFC; color: #475569; border: 1px solid #E2E8F0; }

/* ── Section label ── */
.sec-label {
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #94A3B8;
    margin-bottom: 10px;
}

/* ── Info strip ── */
.info-strip {
    background: #EEF2FF;
    border: 1px solid #C7D2FE;
    border-radius: 10px;
    padding: 12px 16px;
    font-size: 0.86rem;
    color: #3730A3;
    margin-bottom: 20px;
    line-height: 1.5;
}

/* ── Empty state ── */
.empty-state {
    text-align: center;
    padding: 60px 20px;
    color: #94A3B8;
}
.empty-title {
    font-size: 1rem;
    font-weight: 600;
    color: #64748B;
    margin-top: 12px;
}
.empty-sub {
    font-size: 0.85rem;
    margin-top: 4px;
}

/* ── Pipeline steps ── */
.step {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 14px;
    background: #F8FAFC;
    border-radius: 8px;
    border: 1px solid #E2E8F0;
    margin-bottom: 6px;
    font-size: 0.875rem;
    color: #374151;
}
.step-n {
    width: 24px; height: 24px;
    background: #4F46E5;
    color: white;
    border-radius: 6px;
    font-size: 0.72rem;
    font-weight: 700;
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0;
}

/* ── Threshold rows ── */
.threshold-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 9px 14px;
    border-radius: 8px;
    margin-bottom: 5px;
    font-size: 0.85rem;
    font-weight: 600;
}

/* ── Primary action buttons (content area) ── */
div[data-testid="stButton"] > button[kind="primary"] {
    background: #4F46E5 !important;
    color: #FFFFFF !important;
    border: 1.5px solid #4F46E5 !important;
    border-radius: 9px !important;
    font-weight: 600 !important;
    font-size: 0.875rem !important;
    padding: 10px 22px !important;
    cursor: pointer !important;
    transition: all 0.15s !important;
    letter-spacing: 0.1px !important;
    box-shadow: 0 2px 8px rgba(79,70,229,0.35) !important;
}
div[data-testid="stButton"] > button[kind="primary"]:hover {
    background: #4338CA !important;
    border-color: #4338CA !important;
    box-shadow: 0 4px 16px rgba(79,70,229,0.45) !important;
    transform: translateY(-1px) !important;
}

/* ── Inputs ── */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea {
    border-radius: 9px !important;
    border-color: #D1D5DB !important;
    font-size: 0.9rem !important;
    background: #FFFFFF !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
    border-color: #6366F1 !important;
    box-shadow: 0 0 0 3px rgba(99,102,241,0.12) !important;
}

/* ── Selectbox ── */
[data-testid="stSelectbox"] > div > div {
    border-radius: 9px !important;
    border-color: #D1D5DB !important;
    background: #FFFFFF !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: #F1F5F9;
    border-radius: 10px;
    padding: 4px;
    gap: 4px;
    border-bottom: none !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 7px !important;
    font-size: 0.86rem !important;
    font-weight: 500 !important;
    color: #64748B !important;
    padding: 7px 18px !important;
    background: transparent !important;
    border: none !important;
}
.stTabs [aria-selected="true"] {
    background: #FFFFFF !important;
    color: #0F172A !important;
    font-weight: 600 !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.08) !important;
}

/* ── File uploader ── */
[data-testid="stFileUploader"] {
    background: #FAFAFA !important;
    border: 2px dashed #CBD5E1 !important;
    border-radius: 12px !important;
    padding: 10px !important;
    transition: border-color 0.15s !important;
}
[data-testid="stFileUploader"]:hover {
    border-color: #818CF8 !important;
    background: #F5F3FF !important;
}

/* ── Expander ── */
[data-testid="stExpander"] {
    background: #FFFFFF;
    border: 1px solid #E2E8F0 !important;
    border-radius: 12px !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
    margin-bottom: 8px;
    overflow: hidden;
}
[data-testid="stExpander"] summary {
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    color: #1E293B !important;
    padding: 14px 18px !important;
    background: #FFFFFF !important;
}
[data-testid="stExpander"] summary:hover {
    background: #F8FAFC !important;
}

/* ── Divider ── */
hr { border: none; border-top: 1px solid #E2E8F0; margin: 24px 0; }

/* ── Download button ── */
[data-testid="stDownloadButton"] > button {
    border-radius: 9px !important;
    font-weight: 600 !important;
    font-size: 0.875rem !important;
    border: 1.5px solid #D1D5DB !important;
    background: #FFFFFF !important;
    color: #374151 !important;
    padding: 10px 18px !important;
    transition: all 0.15s !important;
}
[data-testid="stDownloadButton"] > button:hover {
    background: #F8FAFC !important;
    border-color: #9CA3AF !important;
    color: #111827 !important;
}

/* ── Slider ── */
[data-testid="stSlider"] [data-testid="stThumbValue"],
[data-testid="stSlider"] [class*="StyledThumb"] {
    background: #4F46E5 !important;
}
</style>
""", unsafe_allow_html=True)


# ── API helpers ───────────────────────────────────────────────────────────────
def _api(method, path, **kwargs):
    try:
        return getattr(requests, method)(f"http://localhost:8000{path}", timeout=60, **kwargs)
    except requests.exceptions.ConnectionError:
        return None
    except Exception:
        return None

def api_get(path, params=None):
    r = _api("get", path, params=params)
    return r.json() if r and r.status_code == 200 else None

def api_post(path, **kwargs):
    r = _api("post", path, **kwargs)
    return r.json() if r and r.status_code in (200, 201) else None

def api_delete(path):
    r = _api("delete", path)
    return r and r.status_code == 204


# ── UI helpers ────────────────────────────────────────────────────────────────
def page_header(title: str, desc: str):
    st.markdown(f"""
    <div class="page-header">
        <div class="page-title">{title}</div>
        <div class="page-desc">{desc}</div>
    </div>
    <div class="page-divider"></div>
    """, unsafe_allow_html=True)

def stat_card(value: str, label: str, sublabel: str = ""):
    return f"""
    <div class="stat-card">
        <div class="stat-icon">{sublabel}</div>
        <div class="stat-val">{value}</div>
        <div class="stat-lbl">{label}</div>
    </div>"""

def score_bar_html(score: float) -> str:
    if score >= 80:   cls = "score-fill-high"
    elif score >= 60: cls = "score-fill-good"
    elif score >= 40: cls = "score-fill-mid"
    elif score >= 20: cls = "score-fill-low"
    else:             cls = "score-fill-poor"
    return f"""
    <div style="display:flex;justify-content:space-between;align-items:center;
                font-size:0.82rem;color:#64748B;margin-bottom:5px;">
        <span>Match Score</span>
        <span style="font-weight:700;color:#0F172A;">{score:.1f}%</span>
    </div>
    <div class="score-track">
        <div class="score-fill {cls}" style="width:{score}%;"></div>
    </div>"""

def rec_badge(rec: str) -> str:
    cls = {"Excellent Candidate":"b-excellent","Strong Match":"b-strong",
           "Suitable":"b-suitable","Average Match":"b-average","Not Recommended":"b-not"}.get(rec,"b-not")
    return f'<span class="badge {cls}">{rec}</span>'

def rank_badge(rank: int) -> str:
    cls = {1:"rank-gold",2:"rank-silver",3:"rank-bronze"}.get(rank,"rank-other")
    return f'<span class="cand-rank {cls}">{rank}</span>'

def chip(text: str, kind: str = "c-gray") -> str:
    return f'<span class="chip {kind}">{text}</span>'

def chips(items: list, kind: str = "c-gray") -> str:
    return " ".join(chip(i, kind) for i in items)

def sec_label(text: str):
    st.markdown(f'<div class="sec-label">{text}</div>', unsafe_allow_html=True)

def info_strip(text: str):
    st.markdown(f'<div class="info-strip">{text}</div>', unsafe_allow_html=True)

def card_start():
    st.markdown('<div class="card">', unsafe_allow_html=True)

def card_end():
    st.markdown('</div>', unsafe_allow_html=True)


# ── Top navigation ────────────────────────────────────────────────────────────
health = api_get("/health")
dot_label = "API Online" if health else "API Offline"

NAV_PAGES = [
    ("home",      "Home"),
    ("resumes",   "Upload Resumes"),
    ("jobs",      "Job Description"),
    ("rankings",  "Rankings"),
    ("analytics", "Analytics"),
    ("history",   "History"),
]

cur = st.session_state.page

# Navigation bar — brand | nav items | api status
br, h, r, jo, rk, an, hi, st_col = st.columns([1.8, 0.9, 1.3, 1.35, 1.1, 1.1, 1.0, 1.3])

br.markdown(f"""
<div style="display:flex;align-items:center;gap:10px;padding:10px 0 8px 0;">
    <div style="width:34px;height:34px;background:linear-gradient(135deg,#4F46E5,#7C3AED);
                border-radius:9px;display:flex;align-items:center;justify-content:center;
                color:white;font-weight:800;font-size:1rem;flex-shrink:0;">R</div>
    <span style="font-size:1.05rem;font-weight:700;color:#0F172A;letter-spacing:-0.3px;">RecruitAI</span>
</div>
""", unsafe_allow_html=True)

st_col.markdown(f"""
<div style="display:flex;align-items:center;justify-content:flex-end;gap:8px;
            padding:10px 0 8px 0;font-size:0.78rem;color:#64748B;white-space:nowrap;">
    <span style="width:8px;height:8px;border-radius:50%;flex-shrink:0;
                 background:{'#10B981' if health else '#EF4444'};
                 box-shadow:0 0 0 2px {'#D1FAE5' if health else '#FEE2E2'};
                 display:inline-block;"></span>
    {dot_label}
</div>
""", unsafe_allow_html=True)

_NAV_COLS = [(h, "home", "Home"), (r, "resumes", "Upload Resumes"),
             (jo, "jobs", "Job Description"), (rk, "rankings", "Rankings"),
             (an, "analytics", "Analytics"), (hi, "history", "History")]

for _col, _key, _label in _NAV_COLS:
    with _col:
        if _key == cur:
            st.markdown(f"""
            <div style="text-align:center;padding:8px 2px 6px 2px;">
                <span style="color:#4F46E5;font-size:0.82rem;font-weight:700;
                             background:#EEF2FF;border:1.5px solid #C7D2FE;
                             border-radius:8px;padding:6px 10px;white-space:nowrap;">
                    {_label}
                </span>
            </div>
            """, unsafe_allow_html=True)
        else:
            if st.button(_label, key=f"nav_{_key}", use_container_width=True):
                st.session_state.page = _key
                cur = _key
                st.rerun()

st.markdown('<hr style="margin:0 0 28px 0;border:none;border-top:2px solid #E2E8F0;">', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# HOME
# ─────────────────────────────────────────────────────────────────────────────
if cur == "home":
    page_header(
        "Resume Ranking Dashboard",
        "An AI-powered recruitment tool that reads resumes, extracts skills and experience, "
        "and ranks every candidate against your job description — automatically."
    )

    resumes = api_get("/resumes") or []
    jobs    = api_get("/jobs") or []
    history = api_get("/history") or []
    ranked  = [h for h in history if h.get("total_resumes", 0) > 0]
    avg_top = round(sum(h["top_score"] for h in ranked if h.get("top_score")) / len(ranked), 1) if ranked else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(stat_card(str(len(resumes)),  "Resumes Stored",    "TOTAL UPLOADED"), unsafe_allow_html=True)
    c2.markdown(stat_card(str(len(jobs)),     "Job Descriptions",  "ON FILE"),        unsafe_allow_html=True)
    c3.markdown(stat_card(str(len(ranked)),   "Rankings Run",      "SESSIONS"),       unsafe_allow_html=True)
    c4.markdown(stat_card(f"{avg_top}%" if avg_top else "—", "Avg Top Score", "BEST CANDIDATE"), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col_l, col_r = st.columns([1, 1], gap="large")

    with col_l:
        sec_label("HOW IT WORKS")
        steps = [
            "Upload resume files in PDF, DOCX, or TXT format",
            "Add a job description by typing, pasting, or uploading a file",
            "AI parses every resume — extracts skills, education, experience",
            "TF-IDF converts resume and JD text into mathematical vectors",
            "Cosine similarity computes a match score for each candidate",
            "Candidates are ranked highest to lowest with skill gap analysis",
            "Export results as CSV, Excel spreadsheet, or a PDF report",
        ]
        for i, s in enumerate(steps, 1):
            st.markdown(f'<div class="step"><div class="step-n">{i}</div>{s}</div>', unsafe_allow_html=True)

    with col_r:
        sec_label("SCORE THRESHOLDS")
        thresholds = [
            ("Excellent Candidate", "95% and above",  "#D1FAE5", "#065F46"),
            ("Strong Match",        "80% – 94%",      "#DCFCE7", "#166534"),
            ("Suitable",            "60% – 79%",      "#FEF3C7", "#92400E"),
            ("Average Match",       "40% – 59%",      "#FFEDD5", "#9A3412"),
            ("Not Recommended",     "Below 40%",      "#FEE2E2", "#991B1B"),
        ]
        for label, rng, bg, fg in thresholds:
            st.markdown(f"""
            <div class="threshold-row" style="background:{bg};">
                <span style="color:{fg};">{label}</span>
                <span style="color:{fg};font-size:0.9rem;">{rng}</span>
            </div>
            """, unsafe_allow_html=True)

        if not resumes:
            st.markdown("<br>", unsafe_allow_html=True)
            info_strip("No resumes yet. Go to <b>Upload Resumes</b> and click <b>Generate Sample Data</b> to load 20 demo resumes and 5 job descriptions instantly.")


# ─────────────────────────────────────────────────────────────────────────────
# UPLOAD RESUMES
# ─────────────────────────────────────────────────────────────────────────────
elif cur == "resumes":
    page_header(
        "Upload Resumes",
        "Upload candidate resumes as PDF, DOCX, or TXT files. The system automatically extracts "
        "name, contact details, skills, education, work experience, projects, and certifications."
    )

    tab_up, tab_demo, tab_list = st.tabs(["Upload Files", "Sample Data", "Stored Resumes"])

    with tab_up:
        st.markdown("<br>", unsafe_allow_html=True)
        info_strip("Select one or multiple files at once. Duplicate files are detected by hash and skipped automatically.")
        uploaded = st.file_uploader("Drop files here or click Browse", type=["pdf","docx","txt"], accept_multiple_files=True)

        if uploaded:
            st.markdown(f"<div style='font-size:0.83rem;color:#64748B;margin:8px 0;'>{len(uploaded)} file(s) ready to upload</div>", unsafe_allow_html=True)
            if st.button("Upload and Parse All", type="primary"):
                with st.spinner("Parsing resumes…"):
                    resp = _api("post", "/upload-resume",
                                files=[("files",(f.name,f.getvalue(),f.type)) for f in uploaded])
                if resp and resp.status_code == 201:
                    st.success(f"{len(resp.json())} resume(s) processed.")
                    for r in resp.json():
                        name = r.get("candidate_name") or r["filename"]
                        with st.expander(name):
                            a, b, c = st.columns(3)
                            a.write(f"Email: {r.get('email') or '—'}")
                            a.write(f"Phone: {r.get('phone') or '—'}")
                            b.write(f"Experience: {r.get('experience_years',0)} years")
                            b.write(f"Education: {', '.join(r.get('education',[])[:1]) or '—'}")
                            c.write(f"Quality Score: {r.get('completeness_score',0):.0f}%")
                            c.write(f"Skills found: {len(r.get('skills',[]))}")
                            if r.get("skills"):
                                st.markdown(chips(r["skills"][:25], "c-green"), unsafe_allow_html=True)

    with tab_demo:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""
        <div style="background:#F5F3FF;border:1px solid #DDD6FE;border-radius:14px;
                    padding:28px;text-align:center;">
            <div style="font-size:1.15rem;font-weight:700;color:#3730A3;">
                Generate Demo Data
            </div>
            <div style="font-size:0.9rem;color:#4338CA;margin-top:8px;line-height:1.6;max-width:520px;margin-left:auto;margin-right:auto;">
                Creates 20 realistic synthetic resumes across five profiles — Data Scientist,
                Software Engineer, DevOps Engineer, ML Engineer, and Frontend Developer —
                along with 5 matching job descriptions. Ready to rank immediately.
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        _, mid, _ = st.columns([1,2,1])
        with mid:
            if st.button("Generate Sample Data", type="primary", use_container_width=True):
                with st.spinner("Generating…"):
                    try:
                        from backend.database import SessionLocal, init_db
                        from backend.config import setup_logging
                        from data.sample_generator import generate_all
                        setup_logging(); init_db()
                        db = SessionLocal()
                        try:
                            r = generate_all(db, force=False)
                            st.success(f"Created {r['resumes']} resumes and {r['jobs']} job descriptions.")
                        finally:
                            db.close()
                    except Exception as e:
                        st.error(str(e))

    with tab_list:
        st.markdown("<br>", unsafe_allow_html=True)
        resumes = api_get("/resumes") or []
        if not resumes:
            st.markdown('<div class="empty-state"><div style="font-size:2.5rem;opacity:0.3">&#9654;</div><div class="empty-title">No resumes yet</div><div class="empty-sub">Upload files or generate sample data</div></div>', unsafe_allow_html=True)
        else:
            srch = st.text_input("Search by name or skill", placeholder="Type to filter…")
            filtered = [r for r in resumes if not srch or srch.lower() in (r.get("candidate_name") or "").lower()
                        or any(srch.lower() in s.lower() for s in r.get("skills", []))]
            st.markdown(f"<div style='font-size:0.82rem;color:#94A3B8;margin-bottom:12px;'>{len(filtered)} of {len(resumes)} resumes</div>", unsafe_allow_html=True)
            for r in filtered:
                name = r.get("candidate_name") or r["filename"]
                with st.expander(f"{name}   ·   {r.get('experience_years',0)} yrs   ·   Quality {r.get('completeness_score',0):.0f}%"):
                    a, b, c = st.columns(3)
                    a.write(f"Email: {r.get('email') or '—'}")
                    b.write(f"Phone: {r.get('phone') or '—'}")
                    c.write(f"Skills: {len(r.get('skills',[]))}")
                    if r.get("skills"):
                        st.markdown("<br>" + chips(r["skills"][:30], "c-green"), unsafe_allow_html=True)
                    if r.get("certifications"):
                        st.markdown(chips(r["certifications"][:5], "c-purple"), unsafe_allow_html=True)
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("Delete", key=f"dr_{r['id']}"):
                        if api_delete(f"/delete/{r['id']}"): st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# JOB DESCRIPTION
# ─────────────────────────────────────────────────────────────────────────────
elif cur == "jobs":
    page_header(
        "Job Description",
        "Define the role you are hiring for. Paste the job description as text or upload "
        "a file. The AI extracts required skills and qualifications automatically."
    )

    tab_text, tab_file, tab_saved = st.tabs(["Paste Text", "Upload File", "Saved Jobs"])

    with tab_text:
        st.markdown("<br>", unsafe_allow_html=True)
        info_strip("The more detailed the job description, the more accurate the ranking. Include skills, tools, responsibilities, and qualifications.")
        title = st.text_input("Job Title", placeholder="e.g. Senior Data Scientist")
        text  = st.text_area("Job Description", height=260, placeholder="Paste the full job posting here…")
        if st.button("Save Job Description", type="primary"):
            if not title.strip(): st.warning("Enter a job title.")
            elif not text.strip(): st.warning("Paste the job description.")
            else:
                with st.spinner("Processing…"):
                    r = api_post("/upload-job", data={"title": title, "text": text})
                if r:
                    st.success(f"Saved '{r['title']}' (ID {r['id']})")
                    if r.get("required_skills"):
                        st.markdown("Skills extracted: " + chips(r["required_skills"][:20], "c-green"), unsafe_allow_html=True)

    with tab_file:
        st.markdown("<br>", unsafe_allow_html=True)
        title_f = st.text_input("Job Title", placeholder="e.g. DevOps Engineer", key="jd_title_f")
        jdf = st.file_uploader("Job Description File (PDF / DOCX / TXT)", type=["pdf","docx","txt"])
        if jdf and st.button("Upload and Save", type="primary"):
            if not title_f.strip(): st.warning("Enter a job title.")
            else:
                r = api_post("/upload-job", data={"title": title_f},
                             files={"file":(jdf.name, jdf.getvalue(), jdf.type)})
                if r: st.success(f"Saved '{r['title']}' (ID {r['id']})")

    with tab_saved:
        st.markdown("<br>", unsafe_allow_html=True)
        jobs = api_get("/jobs") or []
        if not jobs:
            st.markdown('<div class="empty-state"><div style="font-size:2.5rem;opacity:0.3">&#9654;</div><div class="empty-title">No job descriptions yet</div></div>', unsafe_allow_html=True)
        else:
            for j in jobs:
                with st.expander(f"{j['title']}   ·   {len(j.get('required_skills',[]))} skills extracted"):
                    if j.get("required_skills"):
                        st.markdown(chips(j["required_skills"][:30], "c-green"), unsafe_allow_html=True)
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("Delete", key=f"dj_{j['id']}"):
                        if api_delete(f"/jobs/{j['id']}"): st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# RANKINGS
# ─────────────────────────────────────────────────────────────────────────────
elif cur == "rankings":
    page_header(
        "Ranking Results",
        "Select a job description, choose a similarity engine, and run the ranking. "
        "Every resume gets a score, a recommendation, and a full skill gap breakdown."
    )

    jobs = api_get("/jobs") or []
    if not jobs:
        info_strip("No job descriptions found. Go to <b>Job Description</b> to add one first.")
        st.stop()

    # Controls
    col_jd, col_eng, col_min = st.columns([3, 1.5, 1.5])
    job_map = {f"#{j['id']}  {j['title']}": j["id"] for j in jobs}
    sel   = col_jd.selectbox("Job Description", list(job_map.keys()))
    job_id = job_map[sel]
    engine = col_eng.selectbox("Engine", ["tfidf", "sbert"])
    min_s  = col_min.slider("Min Score", 0, 100, 0)

    btn_cols = st.columns([1.4, 1.4, 5])
    run  = btn_cols[0].button("Run Ranking", type="primary", use_container_width=True)
    load = btn_cols[1].button("Load Saved",  use_container_width=True)

    if run:
        with st.spinner("Computing scores…"):
            r = api_get("/rank", params={"job_id": job_id, "engine": engine})
        if r: st.session_state["rr"] = r

    if load:
        r = api_get("/results", params={"job_id": job_id})
        if r: st.session_state["rr"] = r

    rr = st.session_state.get("rr")
    if not rr:
        st.markdown("<br>", unsafe_allow_html=True)
        info_strip("Click <b>Run Ranking</b> to start. Results are saved automatically and can be loaded in future sessions.")
        st.stop()

    results = [r for r in rr["results"] if r["similarity_score"] >= min_s]
    scores  = [r["similarity_score"] for r in results]

    # Summary row
    st.markdown("<br>", unsafe_allow_html=True)
    s1, s2, s3, s4 = st.columns(4)
    s1.markdown(stat_card(f"{max(scores):.1f}%" if scores else "—", "Top Score",   "BEST MATCH"),   unsafe_allow_html=True)
    s2.markdown(stat_card(f"{sum(scores)/len(scores):.1f}%" if scores else "—", "Average Score", "ALL CANDIDATES"), unsafe_allow_html=True)
    s3.markdown(stat_card(str(len(results)), "Candidates", "IN RESULTS"), unsafe_allow_html=True)
    exc = sum(1 for r in results if r["recommendation"] == "Excellent Candidate")
    s4.markdown(stat_card(str(exc), "Excellent", "HIGH MATCHES"), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Search + filter
    fc1, fc2 = st.columns([2, 3])
    srch = fc1.text_input("Search candidate", placeholder="Name…")
    frec = fc2.multiselect("Filter recommendation",
        ["Excellent Candidate","Strong Match","Suitable","Average Match","Not Recommended"])
    if srch: results = [r for r in results if srch.lower() in (r.get("candidate_name") or "").lower()]
    if frec: results = [r for r in results if r["recommendation"] in frec]

    sec_label(f"CANDIDATES — {rr['job_title']}")

    # Pagination
    PG = 8
    total_pg = max(1, (len(results) + PG - 1) // PG)
    pg_num   = st.number_input("Page", 1, total_pg, 1, label_visibility="collapsed")
    page_res = results[(pg_num-1)*PG : pg_num*PG]

    for r in page_res:
        rank    = r["rank"]
        score   = r["similarity_score"]
        name    = r.get("candidate_name") or r["filename"]
        matched = r.get("matched_skills", [])
        missing = r.get("missing_skills", [])
        extra   = r.get("extra_skills", [])

        with st.expander(f"{rank}.  {name}   ·   {score:.1f}%   ·   {r['recommendation']}"):
            left, right = st.columns([1.2, 1])
            with left:
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">
                    {rank_badge(rank)}
                    <div>
                        <div class="cand-name">{name}</div>
                        <div class="cand-meta">{r.get('experience_years',0)} yrs exp
                        &nbsp;·&nbsp; Quality {r.get('quality_score',0):.0f}%
                        &nbsp;·&nbsp; KW density {r.get('keyword_density',0):.2f}%</div>
                    </div>
                    <div style="margin-left:auto;">{rec_badge(r['recommendation'])}</div>
                </div>
                {score_bar_html(score)}
                """, unsafe_allow_html=True)

                if matched:
                    st.markdown("<br>", unsafe_allow_html=True)
                    sec_label("MATCHED SKILLS")
                    st.markdown(chips(matched, "c-green"), unsafe_allow_html=True)
                if extra:
                    st.markdown("<br>", unsafe_allow_html=True)
                    sec_label("ADDITIONAL SKILLS")
                    st.markdown(chips(extra[:12], "c-blue"), unsafe_allow_html=True)

            with right:
                if missing:
                    sec_label("MISSING SKILLS")
                    st.markdown(chips(missing, "c-red"), unsafe_allow_html=True)
                else:
                    st.markdown("""
                    <div style="background:#ECFDF5;border:1px solid #A7F3D0;border-radius:10px;
                                padding:16px;text-align:center;margin-top:16px;">
                        <div style="font-weight:700;color:#065F46;font-size:0.9rem;">
                            All required skills matched
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

    st.markdown(f"<div style='font-size:0.8rem;color:#94A3B8;margin-top:8px;'>Page {pg_num} of {total_pg}</div>", unsafe_allow_html=True)

    # Export
    st.markdown("<hr>", unsafe_allow_html=True)
    sec_label("EXPORT RESULTS")
    e1, e2, e3 = st.columns(3)
    e1.download_button("Download CSV",   to_csv(results),   f"ranking_{job_id}.csv",  "text/csv",  use_container_width=True)
    e2.download_button("Download Excel", to_excel(results, rr["job_title"]),
                       f"ranking_{job_id}.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       use_container_width=True)
    pdf = to_pdf_report(results, rr["job_title"])
    if pdf:
        e3.download_button("Download PDF Report", pdf, f"report_{job_id}.pdf", "application/pdf", use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# ANALYTICS
# ─────────────────────────────────────────────────────────────────────────────
elif cur == "analytics":
    page_header(
        "Analytics",
        "Visual breakdown of ranking results — score distributions, skill coverage across all "
        "candidates, recommendation split, and experience versus performance analysis."
    )

    rr = st.session_state.get("rr")
    if not rr:
        jobs = api_get("/jobs") or []
        if jobs:
            jmap = {f"#{j['id']}  {j['title']}": j["id"] for j in jobs}
            sel  = st.selectbox("Load results for", list(jmap.keys()))
            if st.button("Load Results", type="primary"):
                r = api_get("/results", params={"job_id": jmap[sel]})
                if r: st.session_state["rr"] = r; st.rerun()
        info_strip("Run a ranking first from the <b>Rankings</b> page to see analytics here.")
        st.stop()

    results = rr["results"]
    st.markdown(f'<div class="sec-label">{rr["job_title"].upper()} — {len(results)} CANDIDATES</div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2, gap="large")
    with c1: st.plotly_chart(score_bar_chart(results),    use_container_width=True)
    with c2: st.plotly_chart(recommendation_pie(results), use_container_width=True)
    st.markdown("<hr>", unsafe_allow_html=True)

    c3, c4 = st.columns(2, gap="large")
    with c3: st.plotly_chart(skill_match_bar(results),  use_container_width=True)
    with c4: st.plotly_chart(missing_skill_bar(results), use_container_width=True)
    st.markdown("<hr>", unsafe_allow_html=True)

    c5, c6 = st.columns(2, gap="large")
    with c5: st.plotly_chart(score_distribution(results),  use_container_width=True)
    with c6: st.plotly_chart(experience_scatter(results),  use_container_width=True)

    if results:
        st.markdown("<hr>", unsafe_allow_html=True)
        top = results[0]
        sec_label(f"TOP CANDIDATE RESUME QUALITY — {(top.get('candidate_name') or top['filename']).upper()}")
        _, mid, _ = st.columns([1, 2, 1])
        with mid:
            st.plotly_chart(quality_gauge(top.get("quality_score", 0),
                                          top.get("candidate_name") or "—"), use_container_width=True)

    st.markdown("<hr>", unsafe_allow_html=True)
    with st.expander("Raw Data Table"):
        df = results_to_dataframe(results)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button("Download CSV", to_csv(results), "analytics.csv", "text/csv")


# ─────────────────────────────────────────────────────────────────────────────
# HISTORY
# ─────────────────────────────────────────────────────────────────────────────
elif cur == "history":
    page_header(
        "Ranking History",
        "Every ranking session is saved automatically. Load any previous result to view "
        "the full rankings or analytics without re-running the AI engine."
    )

    history = api_get("/history") or []
    if not history:
        st.markdown('<div class="empty-state"><div style="font-size:2.5rem;opacity:0.3">&#9654;</div><div class="empty-title">No history yet</div><div class="empty-sub">Run your first ranking from the Rankings page</div></div>', unsafe_allow_html=True)
    else:
        sec_label(f"{len(history)} JOB(S) ON RECORD")
        for h in history:
            has  = h.get("total_resumes", 0) > 0
            top  = h.get("top_score", 0) or 0
            with st.expander(f"{h['job_title']}   ·   {h.get('total_resumes',0)} candidates ranked"):
                mc1, mc2, mc3, mc4 = st.columns(4)
                mc1.markdown(stat_card(h.get("top_candidate") or "—", "Top Candidate", "BEST MATCH"), unsafe_allow_html=True)
                mc2.markdown(stat_card(f"{top:.1f}%" if top else "—", "Top Score",   "HIGHEST"),      unsafe_allow_html=True)
                mc3.markdown(stat_card(str(h.get("total_resumes",0)), "Candidates",  "RANKED"),        unsafe_allow_html=True)
                mc4.markdown(stat_card(str(h.get("ranked_at","—"))[:10], "Date",     "RUN ON"),        unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)
                if has:
                    _, btn_col, _ = st.columns([1, 2, 1])
                    if btn_col.button("Load These Results", key=f"hl_{h['job_id']}", type="primary", use_container_width=True):
                        r = api_get("/results", params={"job_id": h["job_id"]})
                        if r:
                            st.session_state["rr"] = r
                            st.success("Loaded. Go to Rankings or Analytics to view.")
