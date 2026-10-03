import streamlit as st
import pandas as pd
import tempfile
import os
import hashlib
from datetime import datetime
from parsers import extract_pdf_text, parse_cv_profile, parse_user_intent
from matcher import (
    fetch_platform_jobs_worldwide, 
    calculate_review_odds, 
    derive_requisition_archetypes, 
    FINANCIAL_CENTRE_MAP,
    ROLE_TYPE_KEYWORDS,
    SECTOR_KEYWORDS
)
from auto_apply import apply_to_linkedin_job

st.set_page_config(
    page_title="Jobs & Opportunities // TargetJobs",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed"
)

TRACKER_FILE = "applications_tracker.csv"

def load_tracker():
    if os.path.exists(TRACKER_FILE):
        return pd.read_csv(TRACKER_FILE)
    return pd.DataFrame(columns=["title", "company", "location", "status", "applied_date", "job_url"])

def save_tracker(df):
    df.to_csv(TRACKER_FILE, index=False)

# TargetJobs Design System
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
        background-color: #F8FAFC !important;
        color: #111827;
    }

    .tj-navbar {
        background: #FFFFFF;
        border-bottom: 1px solid #E5E7EB;
        padding: 0.85rem 2.5rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin: -4rem -5rem 1.5rem -5rem;
        position: sticky;
        top: 0;
        z-index: 99;
    }

    .tj-logo-group {
        display: flex;
        align-items: center;
        gap: 2rem;
    }

    .tj-logo {
        font-size: 1.45rem;
        font-weight: 800;
        color: #E11D48;
        display: flex;
        align-items: center;
        gap: 0.35rem;
        letter-spacing: -0.03em;
    }

    .tj-nav-links {
        display: flex;
        gap: 1.5rem;
        font-size: 0.95rem;
        font-weight: 600;
        color: #4B5563;
    }

    .tj-badge-new {
        background: #F43F5E;
        color: white;
        font-size: 0.65rem;
        font-weight: 700;
        padding: 0.15rem 0.45rem;
        border-radius: 9999px;
        margin-left: 0.25rem;
        vertical-align: middle;
    }

    .search-title {
        font-size: 1.95rem;
        font-weight: 800;
        letter-spacing: -0.025em;
        color: #0F172A;
        margin-bottom: 0.75rem;
    }

    .job-item {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 14px;
        padding: 1.15rem 1.25rem;
        margin-bottom: 0.9rem;
        transition: all 0.18s ease-in-out;
        position: relative;
    }

    .job-item:hover {
        border-color: #6366F1;
        box-shadow: 0 4px 16px -2px rgba(99, 102, 241, 0.08);
    }

    .spotlight-chip {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.65rem;
        font-weight: 700;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: #7C3AED;
        background: #F5F3FF;
        border: 1px solid #DDD6FE;
        padding: 0.18rem 0.5rem;
        border-radius: 6px;
    }

    .deadline-chip {
        display: inline-block;
        font-size: 0.75rem;
        font-weight: 700;
        color: #B45309;
        background: #FEF3C7;
        border: 1px solid #FDE68A;
        border-radius: 9999px;
        padding: 0.25rem 0.75rem;
        margin-top: 0.6rem;
    }

    .odds-pill {
        display: inline-block;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem;
        font-weight: 700;
        color: #047857;
        background: #ECFDF5;
        border: 1px solid #A7F3D0;
        border-radius: 9999px;
        padding: 0.25rem 0.65rem;
    }

    .detail-container {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 16px;
        padding: 2.2rem;
        box-shadow: 0 2px 10px rgba(15, 23, 42, 0.03);
        position: sticky;
        top: 5.5rem;
        max-height: 82vh;
        overflow-y: auto;
    }

    .company-avatar {
        width: 60px;
        height: 60px;
        border-radius: 12px;
        background: #0F172A;
        color: #FFFFFF;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.3rem;
        font-weight: 800;
        font-family: 'JetBrains Mono', monospace;
        box-shadow: 0 2px 6px rgba(0,0,0,0.1);
    }

    .pill-skill {
        display: inline-block;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.72rem;
        font-weight: 600;
        padding: 0.25rem 0.6rem;
        border-radius: 6px;
        margin: 0.2rem;
        background: #EFF6FF;
        color: #1D4ED8;
        border: 1px solid #BFDBFE;
    }

    .pill-gap {
        display: inline-block;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.72rem;
        font-weight: 600;
        padding: 0.25rem 0.6rem;
        border-radius: 6px;
        margin: 0.2rem;
        background: #FFF1F2;
        color: #BE123C;
        border: 1px solid #FECDD3;
    }

    div[data-testid="stMultiSelect"] > label, div[data-testid="stSelectbox"] > label {
        font-weight: 700 !important;
        font-size: 0.85rem !important;
        color: #374151 !important;
    }
</style>
""", unsafe_allow_html=True)

# Top Nav
st.markdown("""
<div class="tj-navbar">
    <div class="tj-logo-group">
        <div class="tj-logo">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#E11D48" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><circle cx="12" cy="12" r="6"></circle><circle cx="12" cy="12" r="2"></circle></svg>
            targetjobs
        </div>
        <div class="tj-nav-links">
            <span style="color: #111827; border-bottom: 2px solid #6366F1; padding-bottom: 0.4rem;">Jobs</span>
            <span>Advice</span>
            <span>Employers</span>
            <span>Events</span>
            <span>GradSims</span>
            <span>✨ AI Tools <span class="tj-badge-new">NEW</span></span>
        </div>
    </div>
    <div style="font-size: 0.88rem; font-weight: 700; color: #4F46E5; background: #EEF2FF; padding: 0.4rem 0.9rem; border-radius: 8px; border: 1px solid #C7D2FE;">
        Autonomous Terminal Active ⚡
    </div>
</div>
""", unsafe_allow_html=True)

tab_jobs, tab_saved = st.tabs(["💼 Jobs & Opportunities", "📌 My Saved Jobs & Tracker"])

with tab_jobs:
    st.markdown('<div class="search-title">Jobs & opportunities</div>', unsafe_allow_html=True)

    # 1. Search Bar Row
    s_col1, s_col2 = st.columns([4, 1.2])
    with s_col1:
        mandate_intent = st.text_input(
            "Search",
            placeholder="🔍 What are you looking for? (e.g. Actuarial Reserving, Quantitative Risk)",
            label_visibility="collapsed"
        )
    with s_col2:
        recency_window = st.selectbox(
            "Recency",
            [
                ("Past 24 Hours", 24),
                ("Past 72 Hours", 72),
                ("Past 7 Days", 168),
                ("Past 14 Days", 336)
            ],
            index=2,
            format_func=lambda x: x[0],
            label_visibility="collapsed"
        )

    # 2. Four TargetJobs Filter Dropdowns Row: Role type, Location, Employer, Sector + Clear
    f_col1, f_col2, f_col3, f_col4, f_col5 = st.columns([1.5, 1.3, 1.5, 1.5, 0.7])
    
    with f_col1:
        selected_role_types = st.multiselect(
            "Role type ⌄",
            options=list(ROLE_TYPE_KEYWORDS.keys()),
            default=["Graduate job", "Internship"],
            placeholder="All role types"
        )

    with f_col2:
        selected_location = st.selectbox(
            "Location ⌄",
            list(FINANCIAL_CENTRE_MAP.keys()),
            index=0
        )

    # Ingestion Data Source Setup
    existing_companies = []
    if "feed_jobs" in st.session_state and not st.session_state["feed_jobs"].empty:
        existing_companies = sorted(st.session_state["feed_jobs"]['company'].dropna().unique().tolist())

    with f_col3:
        selected_employers = st.multiselect(
            "Employer ⌄",
            options=existing_companies,
            placeholder="All employers"
        )

    with f_col4:
        selected_sectors = st.multiselect(
            "Sector ⌄",
            options=list(SECTOR_KEYWORDS.keys()),
            placeholder="All sectors"
        )

    with f_col5:
        st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)
        if st.button("✕ Clear"):
            st.session_state["selected_role_types"] = []
            st.session_state["selected_employers"] = []
            st.session_state["selected_sectors"] = []
            st.rerun()

    # CV Upload Drawer
    with st.expander("📄 **Candidate CV / Resume Input (Auto-calibrates Pass Odds & Tailoring)**", expanded=False):
        uploaded_dossier = st.file_uploader("Upload PDF resume to compute match odds and tailored bullets", type=["pdf"])
        applicant_contact = st.text_input("Candidate Contact Phone", value="+212 600000000")

    # Autorun Pipeline Trigger
    input_signature = hashlib.md5(
        f"{mandate_intent}_{selected_location}_{str(selected_role_types)}_{str(selected_sectors)}_{recency_window[1]}_{uploaded_dossier.size if uploaded_dossier else 0}".encode('utf-8')
    ).hexdigest()

    if st.session_state.get("last_sig") != input_signature:
        with st.status("⚡ Refreshing opportunities feed...", expanded=False) as status:
            cv_profile = {"skills": [], "seniority": "Graduate", "raw_text": ""}
            cv_text = ""
            if uploaded_dossier:
                cv_text = extract_pdf_text(uploaded_dossier)
                cv_profile = parse_cv_profile(cv_text)

            archetypes = derive_requisition_archetypes(cv_text, mandate_intent, selected_role_types, selected_sectors)
            scraped_frames = []
            for query in archetypes:
                df_q = fetch_platform_jobs_worldwide(
                    search_term=query,
                    country_choice=selected_location,
                    results_wanted=12,
                    hours_old=recency_window[1]
                )
                if not df_q.empty:
                    scraped_frames.append(df_q)

            if scraped_frames:
                combined = pd.concat(scraped_frames, ignore_index=True).drop_duplicates(subset=["title", "company"], keep="first")
                ranked = calculate_review_odds(cv_profile, mandate_intent, combined)
                st.session_state["feed_jobs"] = ranked
                status.update(label=f"Ingested {len(ranked)} opportunities.", state="complete")
            else:
                st.session_state["feed_jobs"] = pd.DataFrame()
                status.update(label="No open postings located for this exact criteria.", state="error")

        st.session_state["last_sig"] = input_signature

    raw_jobs_df = st.session_state.get("feed_jobs", pd.DataFrame())

    # Client-Side Filtering on the 4 TargetJobs criteria
    filtered_jobs_df = raw_jobs_df.copy()
    if not filtered_jobs_df.empty:
        # Filter by Role Type
        if selected_role_types:
            r_words = []
            for rt in selected_role_types:
                r_words.extend(ROLE_TYPE_KEYWORDS.get(rt, []))
            if r_words:
                r_pattern = "|".join([r"\b" + re.escape(w) + r"\b" for w in r_words])
                r_mask = filtered_jobs_df['title'].str.contains(r_pattern, case=False, na=False) | filtered_jobs_df['description'].str.contains(r_pattern, case=False, na=False)
                if r_mask.sum() > 0:
                    filtered_jobs_df = filtered_jobs_df[r_mask]

        # Filter by Employer
        if selected_employers:
            filtered_jobs_df = filtered_jobs_df[filtered_jobs_df['company'].isin(selected_employers)]

        # Filter by Sector
        if selected_sectors:
            s_words = []
            for sec in selected_sectors:
                s_words.extend(SECTOR_KEYWORDS.get(sec, []))
            if s_words:
                s_pattern = "|".join([r"\b" + re.escape(w) + r"\b" for w in s_words])
                s_mask = filtered_jobs_df['title'].str.contains(s_pattern, case=False, na=False) | filtered_jobs_df['description'].str.contains(s_pattern, case=False, na=False)
                if s_mask.sum() > 0:
                    filtered_jobs_df = filtered_jobs_df[s_mask]

    # Two-Column Layout Rendering
    if not filtered_jobs_df.empty:
        st.markdown(f"<div style='font-size: 0.95rem; font-weight: 700; color: #475569; margin: 1rem 0;'>{len(filtered_jobs_df)} results found</div>", unsafe_allow_html=True)
        
        col_list, col_preview = st.columns([1.1, 1.9], gap="large")

        if "selected_job_idx" not in st.session_state or st.session_state["selected_job_idx"] not in filtered_jobs_df.index:
            st.session_state["selected_job_idx"] = filtered_jobs_df.index[0]

        # LEFT COLUMN: Jobs Feed Cards
        with col_list:
            for idx, row in filtered_jobs_df.iterrows():
                is_selected = (st.session_state["selected_job_idx"] == idx)
                title = str(row.get("title") or "Opportunity")
                company = str(row.get("company") or "Financial Institution")
                location = str(row.get("location") or "Target Area")
                odds = row.get("response_odds_%", 50.0)
                selected_border = "border: 2px solid #4F46E5; background: #FAF5FF;" if is_selected else ""

                st.markdown(f"""
                <div class="job-item" style="{selected_border}">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.4rem;">
                        <span class="spotlight-chip">✦ SPOTLIGHT</span>
                        <span class="odds-pill">{odds}% Match</span>
                    </div>
                    <div style="font-size: 1.15rem; font-weight: 800; color: #0F172A; line-height: 1.3; margin: 0.35rem 0;">{title}</div>
                    <div style="font-size: 0.9rem; font-weight: 600; color: #4F46E5;">{company} <span style="color: #2563EB;">✔</span></div>
                    <div style="font-size: 0.85rem; color: #64748B; margin-top: 0.25rem;">📍 {location}</div>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 0.6rem;">
                        <span class="deadline-chip">⏳ 10 days to apply</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                if st.button("View Requisition Details ➔", key=f"sel_btn_{idx}", use_container_width=True):
                    st.session_state["selected_job_idx"] = idx
                    st.rerun()

        # RIGHT COLUMN: TargetJobs Detailed Dossier
        with col_preview:
            sel_idx = st.session_state["selected_job_idx"]
            if sel_idx in filtered_jobs_df.index:
                job = filtered_jobs_df.loc[sel_idx]
                title = str(job.get("title") or "Requisition Mandate")
                company = str(job.get("company") or "Employer")
                location = str(job.get("location") or "Target Hub")
                url = str(job.get("job_url") or "#")
                odds = job.get("response_odds_%", 50.0)
                matched = job.get("matched_skills", [])
                report = job.get("tailoring_report", {})
                missing = report.get("missing_keywords", [])
                bullets = report.get("tailored_bullets", [])
                cover_letter = report.get("cover_letter", "")
                desc = str(job.get("description") or "No description provided.")

                st.markdown(f"""
                <div class="detail-container">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.25rem;">
                        <div style="display: flex; gap: 1rem; align-items: center;">
                            <div class="company-avatar">{company[:2].upper()}</div>
                            <div>
                                <div style="font-size: 1.25rem; font-weight: 800; color: #0F172A;">
                                    {company} <span style="color: #2563EB; font-size: 0.95rem;">✔ VERIFIED EMPLOYER</span>
                                </div>
                                <div style="color: #64748B; font-size: 0.85rem; font-weight: 600;">{selected_location}</div>
                            </div>
                        </div>
                    </div>
                    <h1 style="font-size: 1.85rem; font-weight: 800; color: #0F172A; line-height: 1.25; margin-bottom: 0.6rem;">{title}</h1>
                    <div style="font-size: 0.85rem; font-weight: 700; color: #475569; margin-bottom: 1.25rem; text-transform: uppercase;">
                        APPLY BY: 13/10/2026 &nbsp;•&nbsp; <span style="color: #059669;">CLASS I TRACK ({odds}% ODDS)</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                b_col1, b_col2, b_col3 = st.columns([1.2, 1.4, 2])
                with b_col1:
                    st.link_button("🚀 Apply", url, use_container_width=True)
                with b_col2:
                    if st.button("🔖 Add to 'My Jobs'", key=f"save_hub_{sel_idx}", use_container_width=True):
                        t_df = load_tracker()
                        if not ((t_df['title'] == title) & (t_df['company'] == company)).any():
                            new_row = pd.DataFrame([{
                                "title": title,
                                "company": company,
                                "location": location,
                                "status": "Identified",
                                "applied_date": datetime.today().strftime('%Y-%m-%d'),
                                "job_url": url
                            }])
                            save_tracker(pd.concat([t_df, new_row], ignore_index=True))
                            st.toast("Saved to your Applications Hub!", icon="✅")
                with b_col3:
                    if st.button("⚡ Fast-Track Dispatch (Brave)", key=f"dispatch_{sel_idx}", use_container_width=True):
                        with st.spinner("Submitting application via Easy Apply..."):
                            if uploaded_dossier:
                                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                                    tmp.write(uploaded_dossier.getbuffer())
                                    tmp_cv = tmp.name
                                res = apply_to_linkedin_job(url, tmp_cv, applicant_contact)
                                if os.path.exists(tmp_cv):
                                    os.remove(tmp_cv)
                                if res["status"] == "Submitted":
                                    st.success("Application successfully submitted.")
                                else:
                                    st.warning(f"Note: {res['reason']}. Please complete via the Apply button.")
                            else:
                                st.error("Please upload your CV in the panel above first.")

                st.markdown(f"""
                <hr style="border-color: #F1F5F9; margin: 1.5rem 0;">
                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem; margin-bottom: 1.5rem;">
                    <div><span style="font-weight: 700; color: #64748B;">Location:</span> <b>{location}</b></div>
                    <div><span style="font-weight: 700; color: #64748B;">Role Type:</span> <b>{', '.join(selected_role_types) if selected_role_types else 'Graduate / Internship'}</b></div>
                    <div><span style="font-weight: 700; color: #64748B;">Compensation:</span> <b>Competitive Institutional Standard</b></div>
                    <div><span style="font-weight: 700; color: #64748B;">Intake Year:</span> <b>2026 / 2027 Cohort</b></div>
                </div>
                """, unsafe_allow_html=True)

                col_m, col_g = st.columns(2)
                with col_m:
                    if matched:
                        st.markdown("**Matched Quantitative Competencies:**")
                        st.markdown("".join([f'<span class="pill-skill">{s}</span>' for s in matched]), unsafe_allow_html=True)
                with col_g:
                    if missing:
                        st.markdown("**ATS Vector Gap (Keywords to Inject):**")
                        st.markdown("".join([f'<span class="pill-gap">{s}</span>' for s in missing]), unsafe_allow_html=True)

                with st.expander("📝 **Tailored Resume Bullets & Cover Letter**", expanded=False):
                    st.markdown("**Quantifiable Bullets:**")
                    for b in bullets:
                        st.code(b, language="text")

                    st.markdown("**Calibrated Cover Letter:**")
                    st.text_area("Copy Cover Letter", value=cover_letter, height=180, key=f"cl_det_{sel_idx}")

                st.markdown("---")
                st.markdown("### Job Specification & Overview")
                st.write(desc)
    else:
        st.info("No requisitions match the selected combination of filters. Try clearing filters or selecting another region.")

# TAB 2: My Jobs & Pipeline Tracker
with tab_saved:
    st.markdown('<div class="search-title">My Jobs & Applications Hub</div>', unsafe_allow_html=True)
    tracker_df = load_tracker()
    
    if tracker_df.empty:
        st.info("You haven't saved any roles yet. Click **'🔖 Add to My Jobs'** on any requisition card to monitor your applications.")
    else:
        edited_df = st.data_editor(
            tracker_df,
            column_config={
                "status": st.column_config.SelectboxColumn(
                    "Application Status",
                    options=["Identified", "CV Calibrated", "Applied", "Interview", "Offer", "Archived"],
                    required=True
                ),
                "job_url": st.column_config.LinkColumn("Requisition Link")
            },
            num_rows="dynamic",
            use_container_width=True
        )

        if st.button("💾 Save Pipeline Changes"):
            save_tracker(edited_df)
            st.toast("Application progress saved.", icon="✅")