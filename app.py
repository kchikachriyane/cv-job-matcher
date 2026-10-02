import streamlit as st
import pandas as pd
import tempfile
import os
import hashlib
from parsers import extract_pdf_text, parse_cv_profile, parse_user_intent
from matcher import (
    fetch_platform_jobs_worldwide, 
    calculate_review_odds, 
    derive_requisition_archetypes, 
    FINANCIAL_CENTRE_MAP
)
from auto_apply import apply_to_linkedin_job

# Set Page Config
st.set_page_config(
    page_title="TALENTPULSE // Institutional Risk & Quantitative Terminal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Institutional Design System (Plus Jakarta Sans + JetBrains Mono)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    /* Global Foundation */
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
        color: #0F172A;
    }
    
    code, pre, .mono, [data-testid="stMetricValue"] {
        font-family: 'JetBrains Mono', monospace !important;
    }

    .stApp {
        background: linear-gradient(180deg, #F8FAFC 0%, #F1F5F9 100%) !important;
    }

    /* Top Executive Navigation Bar */
    .terminal-nav {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 1.25rem 2rem;
        margin-bottom: 2rem;
        box-shadow: 0 4px 20px -2px rgba(15, 23, 42, 0.05);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .terminal-brand {
        display: flex;
        align-items: center;
        gap: 0.9rem;
    }

    .terminal-title {
        font-size: 1.45rem;
        font-weight: 800;
        letter-spacing: -0.025em;
        color: #0F172A;
        margin: 0;
    }

    .terminal-tag {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.7rem;
        font-weight: 700;
        background: #EEF2FF;
        color: #4338CA;
        border: 1px solid #C7D2FE;
        padding: 0.25rem 0.65rem;
        border-radius: 6px;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }

    .pulse-indicator {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem;
        font-weight: 600;
        color: #059669;
        background: #ECFDF5;
        border: 1px solid #A7F3D0;
        padding: 0.3rem 0.8rem;
        border-radius: 9999px;
    }

    .pulse-dot {
        width: 8px;
        height: 8px;
        background-color: #10B981;
        border-radius: 50%;
        box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.2);
    }

    /* Executive Glass Panels */
    .dossier-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.03);
        height: 100%;
        margin-bottom: 1rem;
    }

    .dossier-label {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.72rem;
        font-weight: 700;
        color: #2563EB;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        border-bottom: 1px solid #F1F5F9;
        padding-bottom: 0.5rem;
        margin-bottom: 1rem;
    }

    /* Mandate Posting Component */
    .job-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 1.6rem;
        margin-bottom: 1.25rem;
        box-shadow: 0 2px 8px -1px rgba(15, 23, 42, 0.04);
        transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
        position: relative;
        overflow: hidden;
    }

    .job-card:hover {
        border-color: #3B82F6;
        box-shadow: 0 8px 24px -4px rgba(37, 99, 235, 0.08);
        transform: translateY(-2px);
    }

    .job-card::before {
        content: '';
        position: absolute;
        left: 0;
        top: 0;
        bottom: 0;
        width: 4px;
        background: #CBD5E1;
    }

    .job-card.tier-1::before { background: #10B981; }
    .job-card.tier-2::before { background: #F59E0B; }
    .job-card.tier-3::before { background: #94A3B8; }

    /* Score Badges */
    .badge-odds {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.85rem;
        font-weight: 700;
        padding: 0.4rem 0.85rem;
        border-radius: 8px;
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
    }

    .odds-t1 {
        background: #ECFDF5;
        color: #047857;
        border: 1px solid #6EE7B7;
    }

    .odds-t2 {
        background: #FFFBEB;
        color: #B45309;
        border: 1px solid #FCD34D;
    }

    .odds-t3 {
        background: #F8FAFC;
        color: #475569;
        border: 1px solid #E2E8F0;
    }

    /* Skill & Gap Taxonomy Pills */
    .pill {
        display: inline-block;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.72rem;
        font-weight: 600;
        padding: 0.25rem 0.6rem;
        border-radius: 6px;
        margin: 0.18rem;
    }

    .pill-match {
        background: #EFF6FF;
        color: #1D4ED8;
        border: 1px solid #BFDBFE;
    }

    .pill-gap {
        background: #FFF1F2;
        color: #BE123C;
        border: 1px solid #FECDD3;
    }

    .platform-pill {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.65rem;
        font-weight: 700;
        text-transform: uppercase;
        padding: 0.2rem 0.5rem;
        border-radius: 4px;
        background: #F1F5F9;
        color: #475569;
        border: 1px solid #CBD5E1;
    }

    /* Metric Cards */
    [data-testid="stMetric"] {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 1.1rem 1.4rem;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.03);
    }

    /* Sidebar Clean Styling */
    [data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #E2E8F0 !important;
    }

    /* Custom Streamlit Form Elements */
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {
        background-color: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 8px !important;
        color: #0F172A !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }

    .stTextInput>div>div>input:focus, .stTextArea>div>div>textarea:focus {
        border-color: #2563EB !important;
        box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.15) !important;
    }
</style>
""", unsafe_allow_html=True)

# Top Executive Navigation
st.markdown("""
<div class="terminal-nav">
    <div class="terminal-brand">
        <h1 class="terminal-title">⚡ TALENTPULSE</h1>
        <span class="terminal-tag">QUANTITATIVE MARKETS & RISK</span>
    </div>
    <div class="pulse-indicator">
        <span class="pulse-dot"></span>
        <span>AUTONOMOUS ENGINE ACTIVE</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Sidebar Mandate Configurations
with st.sidebar:
    st.markdown("### 🌐 Market Jurisdiction")
    centre_choice = st.selectbox(
        "Target Sovereign / Economic Bloc",
        list(FINANCIAL_CENTRE_MAP.keys()),
        index=0  # Defaults to UK
    )
    
    is_remote_only = st.checkbox("Cross-Border / Remote Mandates Only", value=False)
    
    st.markdown("---")
    st.markdown("### ⚙️ Crawling Parameters")
    mandates_per_archetype = st.slider("Target depth per vector", min_value=10, max_value=35, value=15)
    
    recency_window = st.selectbox(
        "Ingestion Recency Window", 
        [
            ("Past 24 Hours (Class I Direct Track)", 24), 
            ("Past 72 Hours (Standard Operating Intake)", 72), 
            ("Past 7 Days", 168),
            ("Past 14 Days", 336)
        ], 
        index=1
    )
    
    st.markdown("---")
    st.markdown("### ⚡ Fast-Track Dispatch")
    applicant_contact = st.text_input("Candidate Contact Phone", value="+212 ")

# Input Grid: Candidate Dossier & Mandate Intent
col_cv, col_intent = st.columns([1, 1])

with col_cv:
    uploaded_dossier = st.file_uploader("1. Candidate Resume / Academic Dossier (.PDF)", type=["pdf"])

with col_intent:
    mandate_intent = st.text_area(
        "2. Functional Target Archetype & Exclusions (Autonomous scan triggers on update)",
        placeholder="e.g. Quantitative Risk Analyst, Actuarial Reserving, Solvency II, Non-Life Chain Ladder, Asset-Liability Management (ALM). Exclude non-technical advisory, sales, or IT support.",
        height=145
    )

# Candidate Profile Intelligence Dossier
if uploaded_dossier or mandate_intent.strip():
    st.markdown("### 🗂 Candidate Quantitative Footprint & Constraints")
    col_dossier_cv, col_dossier_intent = st.columns(2)
    
    if uploaded_dossier:
        raw_cv = extract_pdf_text(uploaded_dossier)
        profile = parse_cv_profile(raw_cv)
        with col_dossier_cv:
            with st.container():
                st.markdown("""
                <div class="dossier-card">
                    <div class="dossier-label">// 01. COMPUTATIONAL STACK & VERIFIED COMPETENCIES</div>
                """, unsafe_allow_html=True)
                
                st.write(f"**Identified Domain Competencies ({len(profile['skills'])} Tokens):**")
                if profile['skills']:
                    skills_html = "".join([f'<span class="pill pill-match">{s}</span>' for s in profile['skills']])
                    st.markdown(skills_html, unsafe_allow_html=True)
                
                st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
                st.write("**Career Track Highlights:**")
                if profile['experience_highlights']:
                    for exp in profile['experience_highlights']:
                        st.markdown(f"- 💼 **{exp}**")
                else:
                    st.caption("No corporate experience records extracted.")

                if profile['education_highlights']:
                    st.write("**Academic Credentials:**")
                    for deg in profile['education_highlights']:
                        st.markdown(f"- 🎓 *{deg}*")
                
                st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
                st.caption(f"Contact Verification: `{profile['email']}` | `{profile['phone']}`")
                st.markdown("</div>", unsafe_allow_html=True)

    if mandate_intent.strip():
        parsed_intent = parse_user_intent(mandate_intent)
        with col_dossier_intent:
            with st.container():
                st.markdown("""
                <div class="dossier-card">
                    <div class="dossier-label">// 02. ACTIVE MANDATE CRITERIA & VECTOR PENALTIES</div>
                """, unsafe_allow_html=True)
                
                st.write("**Jurisdiction Scope:**")
                st.write(f"`{centre_choice}`")
                
                st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)
                st.write("**Active Functional Exclusions (Penalty Applied):**")
                if parsed_intent['exclusions']:
                    excl_html = "".join([f'<span class="pill pill-gap">🚫 {ex}</span>' for ex in parsed_intent['exclusions']])
                    st.markdown(excl_html, unsafe_allow_html=True)
                else:
                    st.caption("No functional negative constraints active.")
                
                st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)
                st.write("**Normalized Search Mandate:**")
                st.info(parsed_intent['raw_intent'])
                st.markdown("</div>", unsafe_allow_html=True)

# ----------------- AUTORUN PIPELINE ----------------- #
if uploaded_dossier:
    # State signature tracking changes automatically across any parameter
    input_signature = hashlib.md5(
        f"{uploaded_dossier.name}_{uploaded_dossier.size}_{mandate_intent.strip()}_{centre_choice}_{is_remote_only}_{recency_window[1]}_{mandates_per_archetype}".encode('utf-8')
    ).hexdigest()

    if st.session_state.get("last_signature") != input_signature:
        with st.status("⚡ Ingesting live mandates across corporate boards...", expanded=True) as status:
            st.write("Deconstructing quantitative resume footprint...")
            cv_text = extract_pdf_text(uploaded_dossier)
            cv_profile = parse_cv_profile(cv_text)

            st.write("Synthesizing market search vectors...")
            target_queries = derive_requisition_archetypes(cv_text, mandate_intent)
            st.info(f"Active search archetypes: **{', '.join([q.title() for q in target_queries])}**")

            all_jobs_list = []
            search_scope_label = centre_choice.split(" - ")[-1]

            for q in target_queries:
                st.write(f"Harvesting **{q.title()}** listings in `{search_scope_label}`...")
                df_q = fetch_platform_jobs_worldwide(
                    search_term=q,
                    location="",
                    country_choice=centre_choice,
                    is_remote=is_remote_only,
                    results_wanted=mandates_per_archetype,
                    hours_old=recency_window[1]
                )
                if not df_q.empty:
                    all_jobs_list.append(df_q)

            if not all_jobs_list:
                status.update(label="No open requisitions identified for this scope.", state="error")
                st.session_state["ranked_jobs"] = pd.DataFrame()
            else:
                combined_jobs = pd.concat(all_jobs_list, ignore_index=True)
                combined_jobs = combined_jobs.drop_duplicates(subset=["title", "company"], keep="first")
                
                st.write(f"Scoring {len(combined_jobs)} positions against the Institutional Fit Model...")
                ranked_jobs = calculate_review_odds(cv_profile, mandate_intent, combined_jobs)
                status.update(label=f"Scan complete. Ranked {len(ranked_jobs)} institutional opportunities.", state="complete")
                st.session_state["ranked_jobs"] = ranked_jobs

            st.session_state["last_signature"] = input_signature

# Display Requisitions Ranked by Fit Score
if "ranked_jobs" in st.session_state and uploaded_dossier is not None:
    ranked_jobs = st.session_state["ranked_jobs"]

    if not ranked_jobs.empty:
        top_score = ranked_jobs.iloc[0]['response_odds_%']

        st.markdown("<hr style='border-color: #E2E8F0; margin: 2rem 0;'>", unsafe_allow_html=True)
        
        # Telemetry KPI Grid
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Ingested Mandates", len(ranked_jobs))
        m2.metric("Peak Pass Probability", f"{top_score}%")
        m3.metric("Class I Track (≥75%)", int((ranked_jobs['response_odds_%'] >= 75).sum()))
        m4.metric("Competitive Pool (60-74%)", int(((ranked_jobs['response_odds_%'] >= 60) & (ranked_jobs['response_odds_%'] < 75)).sum()))

        # Download Export Desk
        csv_data = ranked_jobs[["title", "company", "location", "site", "date_posted", "response_odds_%", "job_url"]].to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Export Current Mandate Portfolio (CSV / Excel Format)",
            data=csv_data,
            file_name="TalentPulse_Institutional_Portfolio.csv",
            mime="text/csv"
        )

        st.markdown(f"### 🎯 Requisition Scorecards ({len(ranked_jobs)} Opportunities)")

        for idx, row in ranked_jobs.iterrows():
            score = row.get("response_odds_%", 0.0)
            
            if score >= 75:
                rate_class = "odds-t1"
                mandate_tier = "tier-1"
                class_desc = "Class I — Direct Interview Track"
            elif score >= 60:
                rate_class = "odds-t2"
                mandate_tier = "tier-2"
                class_desc = "Class II — Competitive Applicant Pool"
            else:
                rate_class = "odds-t3"
                mandate_tier = "tier-3"
                class_desc = "Class III — Lateral Alignment"

            title = str(row.get("title") or "Position Mandate")
            company = str(row.get("company") or "Financial Institution")
            platform_name = str(row.get("site") or "Corporate").title()
            location_str = str(row.get("location") or "Target Area")
            date_posted = str(row.get("date_posted") or "Recent")
            job_url = row.get("job_url")
            report = row.get("tailoring_report", {})
            missing_kw = report.get("missing_keywords", [])
            actions = report.get("actions", [])
            matched = row.get("matched_skills", [])

            st.markdown(f"""
            <div class="job-card {mandate_tier}">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.9rem;">
                    <div>
                        <h3 style="margin: 0 0 0.35rem 0; font-size: 1.35rem; color: #0F172A; font-weight: 700; letter-spacing: -0.015em;">
                            {title} <span style="color: #94A3B8; font-weight: 400;">/</span> <span style="color: #2563EB;">{company}</span>
                        </h3>
                        <div style="color: #64748B; font-size: 0.88rem; display: flex; align-items: center; gap: 0.65rem;">
                            <span>📍 {location_str}</span>
                            <span>•</span>
                            <span class="platform-pill">{platform_name.upper()}</span>
                            <span>•</span>
                            <span>📅 {date_posted}</span>
                        </div>
                    </div>
                    <div class="badge-odds {rate_class}">
                        <span>{score}% Pass Odds</span>
                        <span style="opacity: 0.7; font-size: 0.75rem;">| {class_desc}</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            # Taxonomy Alignment Grid
            col_m, col_g = st.columns(2)
            with col_m:
                if matched:
                    st.write("**Candidate Competencies Verified by Requisition:**")
                    m_html = "".join([f'<span class="pill pill-match">{s}</span>' for s in matched])
                    st.markdown(m_html, unsafe_allow_html=True)
            with col_g:
                if missing_kw:
                    st.write("**ATS Vector Gap (Workday / Taleo Filters):**")
                    g_html = "".join([f'<span class="pill pill-gap">{s}</span>' for s in missing_kw])
                    st.markdown(g_html, unsafe_allow_html=True)

            # Tailoring Action Plan Expander
            with st.expander("📝 **Institutional CV Calibration & Keyword Injectors**", expanded=False):
                st.markdown("#### Strategic Calibration Points:")
                for action in actions:
                    st.markdown(f"- {action}")
                
                desc = str(row.get("description") or "No description available.")
                st.markdown("---")
                st.markdown("**Requisition Description Snippet:**")
                st.write(desc[:900] + ("..." if len(desc) > 900 else ""))

            # Application Dispatch Rail
            btn_col1, btn_col2 = st.columns([1, 4])
            with btn_col1:
                if job_url and pd.notna(job_url):
                    st.link_button(f"🔗 Open on {platform_name}", str(job_url))
            
            with btn_col2:
                if platform_name.lower() == "linkedin" and job_url and pd.notna(job_url):
                    if st.button("⚡ Fast-Track Dispatch (Brave)", key=f"auto_btn_{idx}"):
                        with st.spinner(f"Submitting fast-track requisition for '{title}' via Brave..."):
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                                tmp.write(uploaded_dossier.getbuffer())
                                temp_cv_path = tmp.name

                            result = apply_to_linkedin_job(
                                job_url=str(job_url),
                                cv_pdf_path=temp_cv_path,
                                phone_number=applicant_contact
                            )

                            if os.path.exists(temp_cv_path):
                                os.remove(temp_cv_path)

                            if result["status"] == "Submitted":
                                st.success("🎉 Fast-track submission registered via Easy Apply.")
                            else:
                                st.warning(f"Notice: {result['reason']}. Complete manual application via the link.")

            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.warning("No live requisitions matched this criteria. Consider widening the publication window or expanding to a broader economic area.")