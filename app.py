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
    page_title="TALENTPULSE INSTITUTIONAL // Quantitative Analytics",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Executive Slate Light Design System
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'IBM Plex Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    code, pre, .mono {
        font-family: 'IBM Plex Mono', monospace !important;
    }

    /* Crisp Light Grey Canvas */
    .stApp {
        background-color: #F8FAFC !important;
        color: #0F172A !important;
    }

    /* Top Header */
    .inst-header {
        background: #FFFFFF !important;
        border-bottom: 2px solid #E2E8F0 !important;
        border-top: 3px solid #2563EB !important;
        padding: 1.5rem 2.2rem;
        margin-bottom: 2rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }

    .inst-title {
        font-size: 1.65rem;
        font-weight: 700;
        color: #0F172A !important;
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }

    .inst-badge {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.68rem;
        background: #EFF6FF !important;
        color: #1D4ED8 !important;
        border: 1px solid #BFDBFE !important;
        padding: 0.2rem 0.55rem;
        border-radius: 2px;
        text-transform: uppercase;
        font-weight: 600;
    }

    .live-badge {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.68rem;
        background: #ECFDF5 !important;
        color: #059669 !important;
        border: 1px solid #A7F3D0 !important;
        padding: 0.2rem 0.55rem;
        border-radius: 9999px;
        font-weight: 700;
        margin-left: 0.5rem;
    }

    .inst-sub {
        color: #64748B !important;
        font-size: 0.92rem;
        margin-top: 0.35rem;
    }

    /* Dossier Panels */
    .inst-panel {
        background: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 6px;
        padding: 1.4rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }

    .inst-panel-title {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.75rem;
        text-transform: uppercase;
        color: #2563EB !important;
        letter-spacing: 0.08em;
        font-weight: 600;
        margin-bottom: 0.75rem;
        border-bottom: 1px solid #E2E8F0 !important;
        padding-bottom: 0.4rem;
    }

    /* Mandate Postings Container */
    .mandate-card {
        background: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        border-left: 4px solid #CBD5E1 !important;
        border-radius: 6px;
        padding: 1.6rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 2px 5px rgba(0,0,0,0.04);
        transition: border-color 0.2s ease, transform 0.2s ease;
    }

    .mandate-card.tier-1 {
        border-left-color: #059669 !important;
    }

    .mandate-card.tier-2 {
        border-left-color: #D97706 !important;
    }

    .mandate-card:hover {
        border-color: #2563EB !important;
        transform: translateX(2px);
    }

    /* Class Ratings */
    .rating-badge {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.85rem;
        font-weight: 600;
        padding: 0.35rem 0.75rem;
        border-radius: 4px;
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
    }

    .rate-class-1 {
        background: #ECFDF5 !important;
        color: #047857 !important;
        border: 1px solid #A7F3D0 !important;
    }

    .rate-class-2 {
        background: #FFFBEB !important;
        color: #B45309 !important;
        border: 1px solid #FDE68A !important;
    }

    .rate-class-3 {
        background: #F1F5F9 !important;
        color: #475569 !important;
        border: 1px solid #CBD5E1 !important;
    }

    /* Taxonomy Token Pills */
    .token-pill {
        display: inline-block;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.75rem;
        padding: 0.25rem 0.55rem;
        border-radius: 4px;
        margin: 0.15rem;
        font-weight: 600;
    }

    .token-verified {
        background: #EFF6FF !important;
        color: #1D4ED8 !important;
        border: 1px solid #BFDBFE !important;
    }

    .token-gap {
        background: #FFF1F2 !important;
        color: #BE123C !important;
        border: 1px solid #FECDD3 !important;
    }

    .source-badge {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.68rem;
        padding: 0.2rem 0.45rem;
        border-radius: 3px;
        text-transform: uppercase;
        font-weight: 600;
        background: #F1F5F9 !important;
        color: #334155 !important;
        border: 1px solid #CBD5E1 !important;
    }

    /* Sidebar Refinement */
    [data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #E2E8F0 !important;
    }
</style>
""", unsafe_allow_html=True)

# Top Bar Header
st.markdown("""
<div class="inst-header">
    <div>
        <div class="inst-title">
            <span>🏛️ TALENTPULSE INSTITUTIONAL</span>
            <span class="inst-badge">FINANCIAL MARKETS EDITION</span>
            <span class="live-badge">⚡ AUTO-RUN ACTIVE</span>
        </div>
        <div class="inst-sub">
            Corporate requisition intelligence aggregating <b>LinkedIn, Indeed, and Glassdoor</b> across macroeconomic jurisdictions.
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Sidebar Mandate Configurations
with st.sidebar:
    st.markdown("### 🌐 Market Jurisdiction")
    centre_choice = st.selectbox(
        "Target Country / Economic Area",
        list(FINANCIAL_CENTRE_MAP.keys()),
        index=0  # Default UK
    )
    
    is_remote_only = st.checkbox("Cross-Border / Remote Mandates Only", value=False)
    
    st.markdown("---")
    st.markdown("### ⚙️ Crawling Parameters")
    mandates_per_archetype = st.slider("Requisitions per archetype", min_value=10, max_value=35, value=15)
    
    recency_window = st.selectbox(
        "Publication Window", 
        [
            ("Past 24 Hours (Class I Direct Track)", 24), 
            ("Past 72 Hours (Standard Operating Intake)", 72), 
            ("Past 7 Days", 168),
            ("Past 14 Days", 336)
        ], 
        index=1
    )
    
    st.markdown("---")
    st.markdown("### ⚡ Fast-Track Submissions")
    applicant_contact = st.text_input("Candidate Contact Phone", value="+212 ")

# Input Grid: Candidate Dossier & Mandate Intent
col_cv, col_intent = st.columns([1, 1])

with col_cv:
    uploaded_dossier = st.file_uploader("1. Candidate Resume / Academic Dossier (.PDF)", type=["pdf"])

with col_intent:
    mandate_intent = st.text_area(
        "2. Functional Target Archetype & Exclusions (Updates automatically)",
        placeholder="e.g. Focus on quantitative analyst, actuarial non-life reserving, Solvency II, or stochastic ALM risk positions using Python and SQL. Exclude advisory sales, recruitment, or non-technical support.",
        height=145
    )

# Candidate Profile Intelligence Dossier
if uploaded_dossier or mandate_intent.strip():
    st.markdown("### 🗂️ Candidate Competency Dossier & Active Constraints")
    col_dossier_cv, col_dossier_intent = st.columns(2)
    
    if uploaded_dossier:
        raw_cv = extract_pdf_text(uploaded_dossier)
        profile = parse_cv_profile(raw_cv)
        with col_dossier_cv:
            with st.container():
                st.markdown("""
                <div class="inst-panel">
                    <div class="inst-panel-title">// 01. QUANTITATIVE COMPETENCIES & TRACK RECORD</div>
                """, unsafe_allow_html=True)
                
                st.write(f"**Verified Quantitative Stack ({len(profile['skills'])} Tokens):**")
                if profile['skills']:
                    skills_html = "".join([f'<span class="token-pill token-verified">{s}</span>' for s in profile['skills']])
                    st.markdown(skills_html, unsafe_allow_html=True)
                
                st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                st.write("**Professional Work Experience & Reserving History:**")
                if profile['experience_highlights']:
                    for exp in profile['experience_highlights']:
                        st.markdown(f"- 💼 **{exp}**")
                else:
                    st.caption("No standard experience entries parsed.")

                if profile['education_highlights']:
                    st.write("**Academic Credentials & Degrees:**")
                    for deg in profile['education_highlights']:
                        st.markdown(f"- 🎓 *{deg}*")
                
                st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                st.caption(f"Contact Verification: `{profile['email']}` | `{profile['phone']}`")
                st.markdown("</div>", unsafe_allow_html=True)

    if mandate_intent.strip():
        parsed_intent = parse_user_intent(mandate_intent)
        with col_dossier_intent:
            with st.container():
                st.markdown("""
                <div class="inst-panel">
                    <div class="inst-panel-title">// 02. REQUISITION PARAMETERS & NEGATIVE CRITERIA</div>
                """, unsafe_allow_html=True)
                
                st.write("**Target Geographic Boundaries:**")
                st.write(f"`{centre_choice}`")
                
                st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
                st.write("**Functional Exclusions (Penalty Applied):**")
                if parsed_intent['exclusions']:
                    excl_html = "".join([f'<span class="token-pill token-gap">🚫 {ex}</span>' for ex in parsed_intent['exclusions']])
                    st.markdown(excl_html, unsafe_allow_html=True)
                else:
                    st.caption("No active functional exclusions.")
                
                st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
                st.write("**Synthesized Mandate Intent:**")
                st.info(parsed_intent['raw_intent'])
                st.markdown("</div>", unsafe_allow_html=True)

# ----------------- AUTORUN PIPELINE ----------------- #
if uploaded_dossier:
    input_signature = hashlib.md5(
        f"{uploaded_dossier.name}_{uploaded_dossier.size}_{mandate_intent.strip()}_{centre_choice}_{is_remote_only}_{recency_window[1]}_{mandates_per_archetype}".encode('utf-8')
    ).hexdigest()

    if st.session_state.get("last_signature") != input_signature:
        with st.status("⚡ Change detected. Auto-running multi-platform market scan...", expanded=True) as status:
            st.write("Extracting candidate quantitative footprint...")
            cv_text = extract_pdf_text(uploaded_dossier)
            cv_profile = parse_cv_profile(cv_text)

            st.write("Synthesizing primary institutional search archetypes...")
            target_queries = derive_requisition_archetypes(cv_text, mandate_intent)
            st.info(f"🔍 Active market search vectors: **{', '.join([q.title() for q in target_queries])}**")

            all_jobs_list = []
            search_scope_label = centre_choice.split(" - ")[-1]

            for q in target_queries:
                st.write(f"Querying **{q.title()}** requisitions across LinkedIn, Indeed, Glassdoor in `{search_scope_label}`...")
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
                status.update(label="No open requisitions discovered for this scope.", state="error")
                st.session_state["ranked_jobs"] = pd.DataFrame()
            else:
                combined_jobs = pd.concat(all_jobs_list, ignore_index=True)
                combined_jobs = combined_jobs.drop_duplicates(subset=["title", "company"], keep="first")
                
                st.write(f"Scoring fit for {len(combined_jobs)} positions...")
                ranked_jobs = calculate_review_odds(cv_profile, mandate_intent, combined_jobs)
                status.update(label=f"Done! Evaluated {len(ranked_jobs)} market requisitions.", state="complete")
                st.session_state["ranked_jobs"] = ranked_jobs

            st.session_state["last_signature"] = input_signature

# Display Requisitions Ranked by Fit Score
if "ranked_jobs" in st.session_state and uploaded_dossier is not None:
    ranked_jobs = st.session_state["ranked_jobs"]

    if not ranked_jobs.empty:
        top_score = ranked_jobs.iloc[0]['response_odds_%']

        st.markdown("<hr style='border-color: #E2E8F0; margin: 2rem 0;'>", unsafe_allow_html=True)
        
        # Executive KPI Row
        m1, m2, m3 = st.columns(3)
        m1.metric("Requisitions Ingested", len(ranked_jobs))
        m2.metric("Peak Pass Probability", f"{top_score}%")
        m3.metric("Class I Candidates (≥70%)", int((ranked_jobs['response_odds_%'] >= 70).sum()))

        # Export Button for Requisition Tracker
        csv_data = ranked_jobs[["title", "company", "location", "site", "date_posted", "response_odds_%", "job_url"]].to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Export Mandate Portfolio to CSV (Recruitment Desk Format)",
            data=csv_data,
            file_name="Institutional_Requisitions_Report.csv",
            mime="text/csv"
        )

        st.markdown(f"### 🎯 Requisition Fit Scorecards ({len(ranked_jobs)} Opportunities Found)")

        for idx, row in ranked_jobs.iterrows():
            score = row.get("response_odds_%", 0.0)
            
            if score >= 75:
                rate_class = "rate-class-1"
                mandate_tier = "tier-1"
                class_desc = "Class I — Direct Interview Track"
            elif score >= 60:
                rate_class = "rate-class-2"
                mandate_tier = "tier-2"
                class_desc = "Class II — Competitive Applicant Pool"
            else:
                rate_class = "rate-class-3"
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
            <div class="mandate-card {mandate_tier}">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.8rem;">
                    <div>
                        <h3 style="margin: 0 0 0.35rem 0; font-size: 1.35rem; color: #0F172A; font-weight: 700;">
                            {title} <span style="color: #64748B;">|</span> <span style="color: #2563EB;">{company}</span>
                        </h3>
                        <div style="color: #64748B; font-size: 0.88rem; display: flex; align-items: center; gap: 0.6rem;">
                            <span>📍 {location_str}</span>
                            <span>•</span>
                            <span class="source-badge">{platform_name.upper()}</span>
                            <span>•</span>
                            <span>📅 {date_posted}</span>
                        </div>
                    </div>
                    <div class="rating-badge {rate_class}">
                        <span>{score}% Match</span>
                        <span style="opacity: 0.8; font-size: 0.78rem;">| {class_desc}</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            # Quantitative Taxonomy Overlap
            col_m, col_g = st.columns(2)
            with col_m:
                if matched:
                    st.write("**Candidate Competencies Verified by Requisition:**")
                    m_html = "".join([f'<span class="token-pill token-verified">{s}</span>' for s in matched])
                    st.markdown(m_html, unsafe_allow_html=True)
            with col_g:
                if missing_kw:
                    st.write("**ATS Vector Gap (Workday / Taleo Filters):**")
                    g_html = "".join([f'<span class="token-pill token-gap">{s}</span>' for s in missing_kw])
                    st.markdown(g_html, unsafe_allow_html=True)

            # Tailoring Blueprint
            with st.expander("📝 **Institutional Resume Calibration & Impact Statements**", expanded=False):
                st.markdown("#### Requisition-Specific Adjustments:")
                for action in actions:
                    st.markdown(f"- {action}")
                
                desc = str(row.get("description") or "No description available.")
                st.markdown("---")
                st.markdown("**Requisition Specification Snippet:**")
                st.write(desc[:900] + ("..." if len(desc) > 900 else ""))

            # Action Buttons
            btn_col1, btn_col2 = st.columns([1, 4])
            with btn_col1:
                if job_url and pd.notna(job_url):
                    st.link_button(f"🔗 View Mandate on {platform_name}", str(job_url))
            
            with btn_col2:
                if platform_name.lower() == "linkedin" and job_url and pd.notna(job_url):
                    if st.button("⚡ Execute Direct Fast-Track (Brave Application)", key=f"auto_btn_{idx}"):
                        with st.spinner(f"Initiating fast-track submission for '{title}' via Brave..."):
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
                                st.warning(f"Notice: {result['reason']}. Proceed with manual application via the link on the left.")

            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.warning("No postings found for this search. Try widening the publication window or selecting another country/EEA jurisdiction.")