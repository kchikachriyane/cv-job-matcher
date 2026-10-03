import pandas as pd
import numpy as np
import re
import math
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from jobspy import scrape_jobs

# Regional Hub Configurations with Macro Fallbacks
FINANCIAL_CENTRE_MAP = {
    "United Kingdom": {
        "label": "United Kingdom",
        "indeed_code": "uk",
        "scrape_locations": ["London, UK", "Edinburgh, UK", "United Kingdom"]
    },
    "Morocco": {
        "label": "Morocco",
        "indeed_code": "morocco",
        "scrape_locations": ["Casablanca, Morocco", "Rabat, Morocco", "Morocco"]
    },
    "Europe (Whole Region)": {
        "label": "Europe",
        "indeed_code": "germany",
        "scrape_locations": ["Paris, France", "Frankfurt, Germany", "Amsterdam, Netherlands", "Zurich, Switzerland", "Luxembourg"]
    },
    "Gulf Countries (GCC: UAE, Qatar, Kuwait, KSA)": {
        "label": "Gulf / Middle East",
        "indeed_code": "uae",
        "scrape_locations": ["Dubai, UAE", "Abu Dhabi, UAE", "Doha, Qatar", "Riyadh, Saudi Arabia", "Kuwait City, Kuwait"]
    },
    "United States": {
        "label": "United States",
        "indeed_code": "usa",
        "scrape_locations": ["New York, NY", "Chicago, IL", "Boston, MA", "Charlotte, NC"]
    },
    "Canada": {
        "label": "Canada",
        "indeed_code": "canada",
        "scrape_locations": ["Toronto, ON", "Montreal, QC", "Calgary, AB"]
    }
}

# Tier-Weighted Taxonomy (3x for Core Mathematical/Actuarial, 2x Stack, 1x Standard)
WEIGHTED_TAXONOMY = {
    # Tier 1 (Weight: 3.0) — High-barrier Actuarial, Risk & Mathematical Models
    "chain ladder": 3.0, "mack": 3.0, "taylor separation": 3.0, "london chain": 3.0,
    "reserving": 3.0, "claims triangle": 3.0, "solvency ii": 3.0, "best estimate liabilities": 3.0,
    "bel": 3.0, "ibnr": 3.0, "ifrs 17": 3.0, "loss distribution": 3.0, "monte carlo": 3.0,
    "vasicek": 3.0, "stochastic": 3.0, "asset liability management": 3.0, "alm": 3.0,
    "value at risk": 3.0, "var": 3.0, "cholesky": 3.0, "basel iii": 3.0, "basel iv": 3.0,
    "stress testing": 3.0, "yield curve": 3.0, "counterparty credit risk": 3.0,
    # Tier 2 (Weight: 2.0) — Computational Infrastructure & Machine Learning
    "python": 2.0, "r": 2.0, "sql": 2.0, "power bi": 2.0, "dax": 2.0, "pandas": 2.0,
    "numpy": 2.0, "scikit-learn": 2.0, "pca": 2.0, "mca": 2.0, "knn": 2.0,
    "c++": 2.0, "vba": 2.0, "git": 2.0, "etl pipelines": 2.0, "credit risk modeling": 2.0,
    # Tier 3 (Weight: 1.0) — General Quantitative Core
    "excel": 1.0, "financial modeling": 1.0, "data analysis": 1.0, "reporting": 1.0,
    "portfolio analysis": 1.0, "econometrics": 1.0
}

SENIORITY_KEYWORDS = {
    "junior": ["graduate", "junior", "entry level", "intern", "stage", "trainee", "associate 1", "analyst 1", "0-2 years", "pfe"],
    "senior": ["senior", "lead", "principal", "manager", "head", "director", "vp", "5+ years", "7+ years"]
}

def tokenize(text: str) -> list:
    return re.findall(r"\b[a-zA-Z0-9_\-\.]{2,}\b", text.lower())

def compute_weighted_cosine_similarity(query_text: str, doc_texts: list) -> np.ndarray:
    """Computes TF-IDF similarity adjusted by Tier-1/2/3 quantitative weights."""
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
    query_vec = {}
    for term, count in query_tf.items():
        w = WEIGHTED_TAXONOMY.get(term, 1.0)
        query_vec[term] = count * idf.get(term, default_idf) * w

    query_norm = math.sqrt(sum(v ** 2 for v in query_vec.values())) or 1.0

    similarities = []
    for doc_tokens in doc_tokens_list:
        doc_tf = Counter(doc_tokens)
        doc_vec = {}
        for term, count in doc_tf.items():
            w = WEIGHTED_TAXONOMY.get(term, 1.0)
            doc_vec[term] = count * idf.get(term, default_idf) * w
            
        doc_norm = math.sqrt(sum(v ** 2 for v in doc_vec.values())) or 1.0
        
        intersection = set(query_vec.keys()) & set(doc_vec.keys())
        dot_product = sum(query_vec[term] * doc_vec[term] for term in intersection)
        similarities.append(dot_product / (query_norm * doc_norm))

    return np.array(similarities)

def derive_requisition_archetypes(cv_text: str, custom_intent: str) -> list:
    combined = f"{custom_intent} {cv_text}".lower()
    queries = []

    is_early_career = any(k in combined for k in ["graduate", "junior", "entry level", "intern", "stage", "trainee", "pfe"])
    prefix = "Junior " if is_early_career else ""

    if any(k in combined for k in ["reserving", "actuarial", "claims", "chain ladder", "solvency", "ifrs"]):
        queries.append(f"{prefix}Actuarial Analyst".strip())
        queries.append("Non-Life Reserving Analyst")

    if any(k in combined for k in ["quant", "monte carlo", "alm", "vasicek", "risk model", "stochastic"]):
        queries.append(f"{prefix}Quantitative Analyst".strip())
        queries.append("Risk Analyst")

    if any(k in combined for k in ["credit risk", "risk analytics", "power bi", "data science"]):
        if len(queries) < 3:
            queries.append("Quantitative Risk Analyst")

    if not queries:
        queries = [f"{prefix}Quantitative Analyst".strip(), f"{prefix}Actuarial Analyst".strip()]

    return list(dict.fromkeys(queries))[:3]

def _scrape_single_hub(site_list, search_term, location, results_wanted, hours_old, country_indeed, is_remote):
    """Scrapes a single hub with fault tolerance."""
    try:
        df = scrape_jobs(
            site_name=site_list,
            search_term=search_term,
            location=location,
            results_wanted=results_wanted,
            hours_old=hours_old,
            country_indeed=country_indeed,
            is_remote=is_remote,
            linkedin_fetch_description=True
        )
        return df if (df is not None and not df.empty) else pd.DataFrame()
    except Exception as e:
        print(f"Scraper notice for {search_term} in {location}: {e}")
        return pd.DataFrame()

def fetch_platform_jobs_worldwide(
    search_term: str, 
    location: str = "", 
    country_choice: str = "United Kingdom", 
    is_remote: bool = False,
    results_wanted: int = 15,
    hours_old: int = 168
) -> pd.DataFrame:
    """Multi-threaded concurrent scraper across regional financial hubs."""
    region_info = FINANCIAL_CENTRE_MAP.get(country_choice, FINANCIAL_CENTRE_MAP["United Kingdom"])
    
    if is_remote:
        locations_to_query = ["Remote"]
    else:
        locations_to_query = region_info["scrape_locations"][:3]

    tasks = []
    with ThreadPoolExecutor(max_workers=min(4, len(locations_to_query))) as executor:
        for loc in locations_to_query:
            tasks.append(
                executor.submit(
                    _scrape_single_hub,
                    ["linkedin", "indeed"],
                    search_term,
                    loc,
                    results_wanted,
                    hours_old,
                    region_info["indeed_code"],
                    is_remote
                )
            )

    results = []
    for future in as_completed(tasks):
        df_res = future.result()
        if not df_res.empty:
            results.append(df_res)

    if results:
        combined = pd.concat(results, ignore_index=True)
        return combined.drop_duplicates(subset=["title", "company"], keep="first")

    return pd.DataFrame()

def generate_institutional_tailoring(cv_skills: set, job_text: str, role_title: str, company: str) -> dict:
    """Generates tailored CV bullets and executive cover letter text."""
    text_l = job_text.lower()
    job_skills = [s for s in WEIGHTED_TAXONOMY.keys() if s in text_l]
    missing = [s for s in job_skills if s not in cv_skills]
    
    actions = []
    if missing:
        top_missing = missing[:3]
        actions.append(f"**ATS Vector Alignment:** Inject tokens `{', '.join(top_missing)}` into your Core Competencies table.")
        actions.append(f"**Metric-Driven Bullet Revision:** Highlight practical modeling in **{top_missing[0].upper()}** using quantitative metrics.")
    actions.append(f"**Executive Requisition Match:** Align your resume headline directly to **'{role_title}'**.")

    # High-impact resume bullets
    b_skills = missing[:2] if missing else ["stochastic simulation", "loss reserve modeling"]
    bullets = [
        f"Engineered quantitative {b_skills[0].title()} models, stress-testing Solvency II parameters and enhancing forecast precision across multi-period horizons.",
        f"Automated claims triangulation and reserve evaluation using Python and SQL, eliminating data friction and reducing valuation cycles by 40%.",
        f"Synthesized comprehensive risk sensitivity analysis using {b_skills[-1].title()} methodology, reporting executive-ready findings to senior risk governance committees."
    ]

    # Executive cover letter template
    cover_letter = f"""Dear Hiring Team at {company},

I am writing to express my strong interest in the {role_title} position. With a strong quantitative foundation spanning non-life actuarial reserving, stochastic modeling, and risk simulation, I bring hands-on experience implementing institutional models including Chain Ladder valuation, Solvency II regulatory standards, and automated statistical pipelines.

In my recent actuarial and financial modeling work, I engineered stochastic simulations across multiple market scenarios and automated complex claims triangles utilizing Python, SQL, and Power BI. My background aligns directly with the quantitative competencies required for {role_title}, particularly in building robust, data-driven frameworks that inform risk governance and strategic capital allocation.

I would welcome the opportunity to discuss how my analytical expertise and computational stack can add immediate value to the {company} team. Thank you for your consideration.

Sincerely,
Candidate"""

    return {
        "missing_keywords": missing,
        "actions": actions,
        "tailored_bullets": bullets,
        "cover_letter": cover_letter
    }

def calculate_review_odds(cv_data: dict, custom_intent: str, jobs_df: pd.DataFrame) -> pd.DataFrame:
    """Calculates review odds using weighted TF-IDF, seniority checks, and exclusions."""
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

    # 1. Weighted Cosine Similarities (30% Intent, 30% CV Profile)
    if custom_intent_clean:
        intent_sim = compute_weighted_cosine_similarity(custom_intent_clean, searchable_texts)
        intent_sim = np.clip(intent_sim, 0.0, 1.0)
    else:
        intent_sim = np.zeros(len(searchable_texts))

    cv_sim = compute_weighted_cosine_similarity(cv_text, searchable_texts)
    cv_sim = np.clip(cv_sim, 0.0, 1.0)

    # 2. Weighted Taxonomy, Seniority Adjustments & Exclusions
    taxonomy_scores = []
    seniority_adjustments = []
    matched_skills_list = []
    tailoring_reports = []
    penalties = []

    exclusions = []
    for m in re.findall(r"(?:no|avoid|exclude|not|without|don't want)\s+([a-zA-Z\s\-]+?)(?=[,\.\n]|$)", custom_intent_clean):
        if len(m.strip()) > 2:
            exclusions.append(m.strip())

    for idx, text in enumerate(searchable_texts):
        matched = [s for s in user_skills if s in text]
        weighted_score = sum(WEIGHTED_TAXONOMY.get(s, 1.0) for s in matched)
        max_possible = sum(sorted([WEIGHTED_TAXONOMY.get(s, 1.0) for s in user_skills], reverse=True)[:8]) or 1.0
        t_score = min(weighted_score / max_possible, 1.0)
        taxonomy_scores.append(t_score)
        matched_skills_list.append(matched)

        # Seniority Match Logic
        title_l = titles[idx]
        sen_adj = 0.0
        if any(g in cv_seniority for g in ["graduate", "junior", "intern", "entry"]):
            if any(j in title_l or j in text[:300] for j in SENIORITY_KEYWORDS["junior"]):
                sen_adj += 0.15
            elif any(s in title_l for s in ["senior", "lead", "director", "head", "vp"]):
                sen_adj -= 0.35
        elif "senior" in cv_seniority:
            if any(s in title_l for s in SENIORITY_KEYWORDS["senior"]):
                sen_adj += 0.15
            elif any(j in title_l for j in ["intern", "graduate", "trainee"]):
                sen_adj -= 0.25
        seniority_adjustments.append(sen_adj)

        # Exclusions Penalty
        penalty = 0.0
        for excl in exclusions:
            if excl in text:
                penalty += 0.40
        penalties.append(penalty)

        role_name = str(jobs_df.iloc[idx].get("title", "Position"))
        comp_name = str(jobs_df.iloc[idx].get("company", "Institution"))
        advice = generate_institutional_tailoring(
            cv_skills=user_skills,
            job_text=text,
            role_title=role_name,
            company=comp_name
        )
        tailoring_reports.append(advice)

    # 3. Market Recency Boost (15%)
    recency_boost = []
    for _, row in jobs_df.iterrows():
        d_post = str(row.get("date_posted") or "").lower()
        if any(t in d_post for t in ["today", "1 day", "24 hours"]):
            recency_boost.append(0.15)
        elif any(t in d_post for t in ["2 days", "3 days"]):
            recency_boost.append(0.08)
        else:
            recency_boost.append(0.0)

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