import pandas as pd
import numpy as np
import re
import math
from collections import Counter
from jobspy import scrape_jobs

# Pure EMEA Macro-Jurisdictions (Europe, Middle East, North Africa)
# Regional Macro-Hubs & Dedicated Markets
FINANCIAL_CENTRE_MAP = {
    "United Kingdom": {
        "label": "United Kingdom",
        "indeed_code": "uk",
        "scrape_locations": ["United Kingdom", "London"]
    },
    "Morocco": {
        "label": "Morocco",
        "indeed_code": "morocco",
        "scrape_locations": ["Morocco", "Casablanca", "Rabat"]
    },
    "Europe (Whole Region)": {
        "label": "Europe",
        "indeed_code": "germany",
        "scrape_locations": ["Europe", "Paris, France", "Frankfurt, Germany", "Amsterdam, Netherlands", "Zurich, Switzerland", "Luxembourg"]
    },
    "Gulf Countries (GCC: UAE, Qatar, Kuwait, KSA)": {
        "label": "Gulf / Middle East",
        "indeed_code": "uae",
        "scrape_locations": ["United Arab Emirates", "Dubai", "Doha, Qatar", "Kuwait City, Kuwait", "Riyadh, Saudi Arabia"]
    },
    "United States": {
        "label": "United States",
        "indeed_code": "usa",
        "scrape_locations": ["United States", "New York, NY", "Chicago, IL", "Boston, MA"]
    },
    "Canada": {
        "label": "Canada",
        "indeed_code": "canada",
        "scrape_locations": ["Canada", "Toronto, ON", "Montreal, QC"]
    }
}
INSTITUTIONAL_TAXONOMY = [
    # Actuarial Reserving & Solvency (P&C / Non-Life)
    "chain ladder", "london chain", "taylor separation", "mack stochastic",
    "reserving", "claims triangle", "best estimate liabilities", "bel", "ibnr",
    "loss distribution", "solvency ii", "technical provisions", "ifrs 17",
    "pricing adequacy", "loss ratio modeling", "actuarial consulting",
    # Quantitative Risk, ALM & Derivatives
    "monte carlo", "vasicek", "stochastic", "asset liability management", "alm",
    "value at risk", "var", "cholesky decomposition", "credit risk", "market risk",
    "basel iii", "basel iv", "portfolio optimization", "econometrics", "yield curve",
    "counterparty credit risk", "stress testing", "interest rate risk",
    # Computational Stack & Analytics Architecture
    "python", "r", "sql", "excel vba", "power bi", "dax", "tableau", "c++",
    "pandas", "numpy", "scikit-learn", "pca", "mca", "knn", "etl pipelines", "git"
]

SENIORITY_KEYWORDS = {
    "junior": ["graduate", "junior", "entry level", "intern", "stage", "trainee", "associate 1", "analyst 1", "0-2 years"],
    "senior": ["senior", "lead", "principal", "manager", "head", "vp", "director", "5+ years", "7+ years"]
}

def tokenize(text: str) -> list:
    return re.findall(r"\b[a-zA-Z0-9]{2,}\b", text.lower())

def compute_cosine_similarity(query_text: str, doc_texts: list) -> np.ndarray:
    if not doc_texts:
        return np.array([])

    query_tokens = tokenize(query_text)
    doc_tokens_list = [tokenize(doc) for doc in doc_texts]
    
    N = len(doc_tokens_list)
    df = Counter()
    for doc_tokens in doc_tokens_list:
        for token in set(doc_tokens):
            df[token] += 1
            
    idf = {term: math.log((1 + N) / (1 + count)) + 1.0 for term, count in df.items()}
    default_idf = math.log(1 + N) + 1.0

    query_tf = Counter(query_tokens)
    query_vec = {term: count * idf.get(term, default_idf) for term, count in query_tf.items()}
    query_norm = math.sqrt(sum(v ** 2 for v in query_vec.values())) or 1.0

    similarities = []
    for doc_tokens in doc_tokens_list:
        doc_tf = Counter(doc_tokens)
        doc_vec = {term: count * idf.get(term, default_idf) for term, count in doc_tf.items()}
        doc_norm = math.sqrt(sum(v ** 2 for v in doc_vec.values())) or 1.0
        
        intersection = set(query_vec.keys()) & set(doc_vec.keys())
        dot_product = sum(query_vec[term] * doc_vec[term] for term in intersection)
        similarities.append(dot_product / (query_norm * doc_norm))

    return np.array(similarities)

def derive_requisition_archetypes(cv_text: str, custom_intent: str) -> list:
    """Synthesizes search vectors taking into account seniority level and prompt keywords."""
    combined = f"{custom_intent} {cv_text}".lower()
    queries = []

    # Detect if seeking early career/graduate/intern
    is_early_career = any(k in combined for k in ["graduate", "junior", "entry level", "intern", "stage", "trainee"])
    prefix = "Junior " if is_early_career else ""

    # Priority 1: Actuarial Reserving & Insurance Risk
    if any(k in combined for k in ["reserving", "actuarial", "claims", "chain ladder", "solvency", "ifrs"]):
        queries.append(f"{prefix}Actuarial Analyst".strip())
        queries.append("Non-Life Reserving Analyst")

    # Priority 2: Quantitative Risk Management & ALM
    if any(k in combined for k in ["quant", "monte carlo", "alm", "vasicek", "risk model", "stochastic"]):
        queries.append(f"{prefix}Quantitative Analyst".strip())
        queries.append("Risk Analyst")

    # Priority 3: Credit Risk Analytics & Data Modeling
    if any(k in combined for k in ["credit risk", "risk analytics", "power bi", "data science"]):
        if len(queries) < 3:
            queries.append("Quantitative Risk Analyst")

    if not queries:
        queries = [f"{prefix}Quantitative Analyst".strip(), f"{prefix}Actuarial Analyst".strip()]

    return list(dict.fromkeys(queries))[:3]

def fetch_platform_jobs_worldwide(
    search_term: str, 
    location: str = "", 
    country_choice: str = "United Kingdom", 
    is_remote: bool = False,
    results_wanted: int = 15,
    hours_old: int = 168
) -> pd.DataFrame:
    """Scrapes aggregated jobs across UK, Morocco, Europe, or the Gulf region."""
    region_info = FINANCIAL_CENTRE_MAP.get(
        country_choice, 
        FINANCIAL_CENTRE_MAP["United Kingdom"]
    )
    
    collected_dfs = []
    
    if is_remote:
        locations_to_query = ["Remote"]
    else:
        # Queries top target hubs (e.g. ['Morocco', 'Casablanca'] or ['United Kingdom', 'London'])
        locations_to_query = region_info["scrape_locations"][:2]

    for loc in locations_to_query:
        try:
            df_primary = scrape_jobs(
                site_name=["linkedin", "indeed"],
                search_term=search_term,
                location=loc,
                results_wanted=results_wanted,
                hours_old=hours_old,
                country_indeed=region_info["indeed_code"],
                is_remote=is_remote,
                linkedin_fetch_description=True
            )
            if df_primary is not None and not df_primary.empty:
                collected_dfs.append(df_primary)
        except Exception as e:
            print(f"Scraper notice for {search_term} in {loc}: {e}")

    if collected_dfs:
        combined = pd.concat(collected_dfs, ignore_index=True)
        return combined.drop_duplicates(subset=["title", "company"], keep="first")

    return pd.DataFrame()

def generate_institutional_tailoring(cv_skills: set, job_text: str, role_title: str) -> dict:
    text_l = job_text.lower()
    job_skills = [s for s in INSTITUTIONAL_TAXONOMY if s in text_l]
    missing = [s for s in job_skills if s not in cv_skills]
    
    actions = []
    if missing:
        top_missing = missing[:3]
        actions.append(
            f"**ATS Vector Alignment:** Inject tokens `{', '.join(top_missing)}` into your Core Quantitative Competencies section to clear ATS semantic filters."
        )
        actions.append(
            f"**Metric-Driven Bullet Revision:** Highlight practical modeling in **{top_missing[0].upper()}** using quantitative metrics (*Action Verb + Computational Tool + Result achieved*)."
        )
    
    actions.append(
        f"**Executive Requisition Match:** Align your resume headline directly to **'{role_title}'** for recruiter review."
    )
    
    return {
        "missing_keywords": missing,
        "actions": actions
    }

def calculate_review_odds(cv_data: dict, custom_intent: str, jobs_df: pd.DataFrame) -> pd.DataFrame:
    """Calculates review odds considering skills, prompt intent, seniority level, and exclusions."""
    if jobs_df.empty:
        return jobs_df

    cv_text = cv_data.get("raw_text", "")
    user_skills = set(cv_data.get("skills", []))
    cv_seniority = cv_data.get("seniority", "Entry Level / Graduate").lower()
    custom_intent_clean = custom_intent.strip().lower()

    searchable_texts = []
    titles = []
    for _, row in jobs_df.iterrows():
        t = str(row.get("title") or "")
        c = str(row.get("company") or "")
        d = str(row.get("description") or "")
        titles.append(t.lower())
        searchable_texts.append(f"{t} {t} {c} {d}".strip().lower())

    # 1. Requisition Intent Correlation (30%)
    if custom_intent_clean:
        intent_sim = compute_cosine_similarity(custom_intent_clean, searchable_texts)
        intent_sim = np.clip(intent_sim, 0.0, 1.0)
    else:
        intent_sim = np.zeros(len(searchable_texts))

    # 2. Competency Profile Correlation (30%)
    cv_sim = compute_cosine_similarity(cv_text, searchable_texts)
    cv_sim = np.clip(cv_sim, 0.0, 1.0)

    # 3. Direct Taxonomy Match, Seniority Fit & Exclusion Penalties
    taxonomy_scores = []
    seniority_adjustments = []
    matched_skills_list = []
    tailoring_reports = []
    penalties = []

    # Parse exclusions from user prompt
    exclusions = []
    for m in re.findall(r"(?:no|avoid|exclude|not|without|don't want)\s+([a-zA-Z\s\-]+?)(?=[,\.\n]|$)", custom_intent_clean):
        if len(m.strip()) > 2:
            exclusions.append(m.strip())

    for idx, text in enumerate(searchable_texts):
        matched = [s for s in user_skills if s in text]
        t_score = min(len(matched) / min(len(user_skills), 6), 1.0) if user_skills else 0.3
        taxonomy_scores.append(t_score)
        matched_skills_list.append(matched)

        # Seniority Match Calibration
        title_l = titles[idx]
        sen_adj = 0.0
        
        # If candidate is Junior / Graduate
        if any(g in cv_seniority for g in ["graduate", "junior", "intern", "entry"]):
            if any(j in title_l or j in text[:300] for j in SENIORITY_KEYWORDS["junior"]):
                sen_adj += 0.15  # Positive boost for matching early-career requisitions
            elif any(s in title_l for s in ["senior", "lead", "director", "head", "vp"]):
                sen_adj -= 0.35  # Penalty for senior roles that filter out juniors
        # If candidate is Senior
        elif "senior" in cv_seniority:
            if any(s in title_l for s in SENIORITY_KEYWORDS["senior"]):
                sen_adj += 0.15
            elif any(j in title_l for j in ["intern", "graduate", "trainee"]):
                sen_adj -= 0.25

        seniority_adjustments.append(sen_adj)

        # Negative Exclusion Rule Checking
        penalty = 0.0
        for excl in exclusions:
            if excl in text:
                penalty += 0.40
        penalties.append(penalty)

        advice = generate_institutional_tailoring(
            cv_skills=user_skills,
            job_text=text,
            role_title=str(jobs_df.iloc[idx].get("title", "this mandate"))
        )
        tailoring_reports.append(advice)

    # 4. Market Recency Alpha (15%)
    recency_boost = []
    for _, row in jobs_df.iterrows():
        d_post = str(row.get("date_posted") or "").lower()
        if any(t in d_post for t in ["today", "1 day", "24 hours"]):
            recency_boost.append(0.15)
        elif any(t in d_post for t in ["2 days", "3 days"]):
            recency_boost.append(0.08)
        else:
            recency_boost.append(0.0)

    # Final Composite Probability Calculation
    if custom_intent_clean:
        composite = (
            intent_sim * 0.30 + 
            cv_sim * 0.30 + 
            np.array(taxonomy_scores) * 0.15 + 
            np.array(seniority_adjustments) +
            np.array(recency_boost) + 0.10 - 
            np.array(penalties)
        ) * 100
    else:
        composite = (
            cv_sim * 0.50 + 
            np.array(taxonomy_scores) * 0.25 + 
            np.array(seniority_adjustments) +
            np.array(recency_boost) + 0.10
        ) * 100

    final_scores = np.clip(composite, 10.0, 98.0)

    jobs_df["response_odds_%"] = np.round(final_scores, 1)
    jobs_df["matched_skills"] = matched_skills_list
    jobs_df["tailoring_report"] = tailoring_reports

    return jobs_df.sort_values(by="response_odds_%", ascending=False)