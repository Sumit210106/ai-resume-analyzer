import streamlit as st
import re
import os
import time
from backend.parser import extract_text_from_pdf
from backend.prompts import get_prompt
from backend.llm import generate_response
from backend.rag import create_chunks, create_vectorstore, retrieve_chunks

# ---------------------------------------------------------
# Page Strategy & Config
# ---------------------------------------------------------
st.set_page_config(
    page_title="ResumeAI | Precision Match",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ---------------------------------------------------------
# Persistence Logic
# ---------------------------------------------------------
if 'stage' not in st.session_state:
    st.session_state.stage = 'UPLOAD'
if 'analysis_data' not in st.session_state:
    st.session_state.analysis_data = None
if 'resume_metadata' not in st.session_state:
    st.session_state.resume_metadata = {}

# ---------------------------------------------------------
# Design System: Corporate Vercel Style
# ---------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@700;800&display=swap');

    :root {
        --primary: #6366f1;
        --secondary: #10b981;
        --bg: #000000;
        --surface-low: #0a0a0a;
        --surface-med: #111111;
        --border: #222222;
        --text-dim: #ffffff; /* Changed to full white as requested */
        --text-high: #ffffff;
    }

    body, .stApp {
        background-color: var(--bg);
        color: var(--text-high);
        font-family: 'Inter', sans-serif;
    }

    /* Stepper UI */
    .stepper-container {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 1rem;
        margin-bottom: 3rem;
        padding-top: 1rem;
    }

    .step-node {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 0.9rem;
        font-weight: 500;
        color: var(--text-dim);
    }

    .step-active { color: var(--primary); }
    .step-done { color: var(--secondary); }

    .step-circle {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background: var(--border);
    }

    .step-active .step-circle { background: var(--primary); box-shadow: 0 0 10px var(--primary); }
    .step-done .step-circle { background: var(--secondary); }

    /* Minimal Card */
    .card {
        background: var(--surface-low);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 2.5rem;
        transition: border 0.2s ease;
    }
    
    .card:hover { border-color: #333; }

    /* Header */
    .logo-text {
        font-family: 'Outfit', sans-serif;
        font-size: 1.8rem;
        letter-spacing: -1px;
        background: linear-gradient(to bottom right, #fff 50%, #888);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    /* Buttons */
    div.stButton > button {
        background-color: #fff !important;
        color: #000 !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        padding: 0.75rem 2.5rem !important;
        font-size: 0.95rem !important;
        transition: all 0.15s ease !important;
    }
    
    div.stButton > button:hover {
        transform: scale(1.02) !important;
        background-color: #eee !important;
    }

    /* Skill Pill V2 */
    .pill {
        display: inline-flex;
        align-items: center;
        padding: 4px 12px;
        border-radius: 100px;
        background: #111;
        border: 1px solid #222;
        font-size: 0.8rem;
        margin: 4px;
        font-weight: 500;
    }

    .pill-match { border-color: #10b981; color: #10b981; }
    .pill-missing { border-color: #333; color: #ffffff; }

    /* Custom Scrollbar */
    ::-webkit-scrollbar { width: 4px; }
    ::-webkit-scrollbar-thumb { background: #222; border-radius: 10px; }

    /* Hide Overflows */
    .block-container { padding-top: 3rem !important; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# UI Core Components
# ---------------------------------------------------------

def render_stepper(current_stage):
    stages = ['UPLOAD', 'REVIEW', 'ANALYSIS']
    idx = stages.index(current_stage)
    
    html = '<div class="stepper-container">'
    for i, s in enumerate(stages):
        cls = "step-active" if i == idx else ("step-done" if i < idx else "")
        label = s.capitalize()
        html += f'<div class="step-node {cls}"><div class="step-circle"></div> {label}</div>'
        if i < len(stages)-1:
            html += '<div style="width: 40px; height: 1px; background: #222;"></div>'
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

def render_score_gauge(score):
    # Elegant minimalistic SVG Gauge
    color = "#10b981" if score > 70 else ("#f59e0b" if score > 40 else "#ef4444")
    st.markdown(f"""
    <div style="display:flex; justify-content:center; align-items:center; flex-direction:column; padding: 20px;">
        <svg width="220" height="220" viewBox="0 0 100 100">
            <circle cx="50" cy="50" r="45" fill="none" stroke="#111" stroke-width="6" />
            <circle cx="50" cy="50" r="45" fill="none" stroke="{color}" stroke-width="6" 
                stroke-dasharray="283" stroke-dashoffset="{283 - (283 * score / 100)}" 
                stroke-linecap="round" transform="rotate(-90 50 50)" style="transition: stroke-dashoffset 1s ease-out;"/>
            <text x="50" y="55" font-family="Outfit" font-size="22" text-anchor="middle" fill="#fff" font-weight="800">{score}%</text>
            <text x="50" y="72" font-family="Inter" font-size="6" text-anchor="middle" fill="#555" text-transform="uppercase" letter-spacing="1">Match Score</text>
        </svg>
    </div>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------
# Logic & Data
# ---------------------------------------------------------

def parse_result(text):
    data = {"score": 0, "matching": [], "missing": [], "strengths": "", "weaknesses": "", "suggestions": ""}
    try:
        # Score Parsing
        score_block = re.search(r"Match Score\D*(\d+)", text, re.IGNORECASE)
        if score_block: data["score"] = int(score_block.group(1))

        def find_list(header, source):
            pattern = rf"{header}(.*?)(?=\d\.|$|###|Analysis)"
            block = re.search(pattern, source, re.DOTALL | re.IGNORECASE)
            if block:
                items = re.findall(r"-\s*(.*?)\n", block.group(1) + "\n")
                return [i.strip() for i in items if i.strip()]
            return []

        data["matching"] = find_list("Matching Skills", text)
        data["missing"] = find_list("Missing Skills", text)

        def find_block(header, source):
            pattern = rf"{header}(.*?)(?=\d\.|$|###|Analysis)"
            block = re.search(pattern, source, re.DOTALL | re.IGNORECASE)
            return block.group(1).strip() if block else "Details not available."

        data["strengths"] = find_block("Strengths of Candidate", text)
        data["weaknesses"] = find_block("Weaknesses", text)
        data["suggestions"] = find_block("Suggestions to Improve Resume", text)

    except Exception:
        pass
    return data

@st.cache_resource
def get_brain(text):
    return create_vectorstore(create_chunks(text))

# ---------------------------------------------------------
# Application Lifecycle
# ---------------------------------------------------------

# Global Header
st.markdown('<div class="logo-text">RESUME.AI</div>', unsafe_allow_html=True)
render_stepper(st.session_state.stage)

# --- PHASE: UPLOAD ---
if st.session_state.stage == 'UPLOAD':
    col_l, col_m, col_r = st.columns([1, 2.5, 1])
    with col_m:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.write("### System Initialization")
        st.write("Provide the core credentials for the matching engine.")
        
        up_file = st.file_uploader("Candidate Intel (PDF Resume)", type=['pdf'], label_visibility="collapsed")
        
        st.write("#### Targeted Opportunity")
        jd_input = st.text_area("Scope Requirements (Job Description)", height=180, placeholder="Identify key technical objectives...", label_visibility="collapsed")
        
        if up_file and jd_input:
            if st.button("Proceed to Verification"):
                try:
                    if not os.path.exists("data/resumes"): os.makedirs("data/resumes")
                    path = "data/resumes/active.pdf"
                    with open(path, "wb") as f: f.write(up_file.getbuffer())
                    
                    st.session_state.resume_text = extract_text_from_pdf(path)
                    st.session_state.jd_text = jd_input
                    st.session_state.stage = 'REVIEW'
                    st.rerun()
                except Exception as e:
                    st.error(f"Initialization Failed: {str(e)}")
        st.markdown('</div>', unsafe_allow_html=True)

# --- PHASE: REVIEW ---
elif st.session_state.stage == 'REVIEW':
    col_l, col_m, col_r = st.columns([1, 4, 1])
    with col_m:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.write("### Engine Verification")
        st.write("Confirm data integrity before launching the neural strategist.")
        
        r1, r2 = st.columns(2, gap="large")
        with r1:
            st.caption("RESUME SAMPLE (PARSED)")
            preview = st.session_state.resume_text[:500].replace("\n", " ").strip()
            st.markdown(f'<div style="font-size: 0.8rem; color: #fff; background:#050505; padding:15px; border-radius:10px;">{preview}...</div>', unsafe_allow_html=True)
        with r2:
            st.caption("TARGET SCOPE (RAW)")
            jd_preview = st.session_state.jd_text[:500].replace("\n", " ").strip()
            st.markdown(f'<div style="font-size: 0.8rem; color: #fff; background:#050505; padding:15px; border-radius:10px;">{jd_preview}...</div>', unsafe_allow_html=True)

        st.markdown('<div style="height:30px"></div>', unsafe_allow_html=True)
        
        b1, b2 = st.columns([1, 2])
        with b1:
            if st.button("Reset Session"):
                st.session_state.stage = 'UPLOAD'
                st.rerun()
        with b2:
            if st.button("Launch Analysis Pipeline"):
                try:
                    with st.status("Architecting Analysis...", expanded=True) as status:
                        st.write("Indexing candidate career fragments...")
                        vs = get_brain(st.session_state.resume_text)
                        st.write("Simulating job requirement match...")
                        context = retrieve_chunks(vs, st.session_state.jd_text)
                        st.write("Generating strategic fit report...")
                        prompt = get_prompt(context, st.session_state.jd_text)
                        raw = generate_response(prompt)
                        st.session_state.analysis_data = parse_result(raw)
                        st.session_state.raw_report = raw
                        status.update(label="Analysis Synthesized", state="complete")
                    
                    st.session_state.stage = 'ANALYSIS'
                    st.rerun()
                except Exception as e:
                    st.error(f"Critical System Failure: {str(e)}")
        st.markdown('</div>', unsafe_allow_html=True)

# --- PHASE: ANALYSIS ---
elif st.session_state.stage == 'ANALYSIS':
    data = st.session_state.analysis_data
    
    col_l, col_gauge, col_r = st.columns([1, 1, 1])
    with col_gauge:
        render_score_gauge(data['score'])

    st.markdown('<div class="card">', unsafe_allow_html=True)
    
    g_col1, g_col2 = st.columns(2, gap="large")
    with g_col1:
        st.write("#### Capability Alignment")
        matching = "".join([f'<span class="pill pill-match">{k}</span>' for k in data['matching']])
        st.markdown(f'<div>{matching if matching else "No direct matches."}</div>', unsafe_allow_html=True)

    with g_col2:
        st.write("#### Technical Disparity")
        missing = "".join([f'<span class="pill pill-missing">{k}</span>' for k in data['missing']])
        st.markdown(f'<div>{missing if missing else "No critical disparities."}</div>', unsafe_allow_html=True)

    st.markdown('<hr style="border-color: #222; margin: 2rem 0;">', unsafe_allow_html=True)

    n_col1, n_col2 = st.columns(2, gap="large")
    with n_col1:
        st.write("##### FIT ANALYSIS")
        st.write(data['strengths'])
        st.markdown('<br>', unsafe_allow_html=True)
        st.write("##### CRITICAL GAPS")
        st.write(data['weaknesses'])
    with n_col2:
        st.write("##### OPTIMIZATION STRATEGY")
        st.write(data['suggestions'])

    st.markdown('<div style="height:40px"></div>', unsafe_allow_html=True)
    
    b_reset, b_dl = st.columns([1, 1])
    with b_reset:
        if st.button("New Analysis"):
            st.session_state.stage = 'UPLOAD'
            st.session_state.analysis_data = None
            st.rerun()
    with b_dl:
        if 'raw_report' in st.session_state:
            st.download_button("Export Report (MD)", st.session_state.raw_report, file_name="resume_analysis.md")
    st.markdown('</div>', unsafe_allow_html=True)

# Global Footer
st.markdown(f"""
<div style="text-align: center; color: #444; font-size: 0.75rem; margin-top: 5rem; padding: 2rem; border-top: 1px solid #111;">
    SYSTEM-ID: {time.strftime('%Y%m%d%H%M')} | RAG-ENGINE v4.2 PRO | {os.getenv('MODEL_NAME', 'GROQ-LLAMA3-70B')}
</div>
""", unsafe_allow_html=True)