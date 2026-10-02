import pandas as pd
import numpy as np
import re
import math
from collections import Counter
from jobspy import scrape_jobs

# Macro Jurisdictions & Economic Blocs (Broad Nationwide / Regional Crawl)
FINANCIAL_CENTRE_MAP = {
    "United Kingdom": "uk",
    "European Economic Area (EEA) - France": "france",
    "European Economic Area (EEA) - Germany": "germany",
    "European Economic Area (EEA) - Netherlands": "netherlands",
    "European Economic Area (EEA) - Ireland": "ireland",
    "European Economic Area (EEA) - Luxembourg / Belgium": "belgium",
    "European Economic Area (EEA) - Italy": "italy",
    "European Economic Area (EEA) - Spain": "spain",
    "European Economic Area (EEA) - Nordics (Norway/Sweden)": "norway",
    "Switzerland": "switzerland",
    "Morocco": "morocco",
    "United States": "usa",
    "Canada": "canada",
    "United Arab Emirates": "uae",
    "Singapore": "singapore",
    "Worldwide / Global Remote": "usa"
}

# Institutional Quantitative, Actuarial & Risk Taxonomy
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

def tokenize(text: str) -> list:
    """Extracts alphanumeric tokens of length >= 2."""
    return re.findall(r"\b[a-zA-Z0-9]{2,}\b", text.lower())

def compute_cosine_similarity(query_text: str, doc_texts: list) -> np.ndarray:
    """Pure-Python TF-IDF and Cosine Similarity (Zero C-Extension / DLL Dependencies)."""
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
    """Maps candidate competencies to tier-1 banking & actuarial search vectors."""
    combined = f"{custom_intent} {cv_text}".lower()
    queries = []

    # Priority 1: Actuarial Reserving & Insurance Risk
    if any(k in combined for k in ["reserving", "actuarial", "claims", "chain ladder", "solvency", "ifrs"]):
        queries.extend(["Actuarial Analyst", "Non-Life Reserving Analyst"])

    # Priority 2: Quantitative Risk Management & ALM
    if any(k in combined for k in ["quant", "monte carlo", "alm", "vasicek", "risk model", "stochastic"]):
        queries.append("Quantitative Risk Analyst")

    # Priority 3: Credit Risk Analytics & Data Modeling
    if any(k in combined for k in ["credit risk", "risk analytics", "power bi", "data science"]):
        if len(queries) < 3:
            queries.append("Risk Analytics Analyst")

    if not queries:
        queries = ["Quantitative Analyst", "Actuarial Analyst"]

    return list(dict.fromkeys(queries))[:3]

def extract_mandate_exclusions(intent_text: str) -> list:
    """Parses structural negative constraints and functional exclusions."""
    negatives = []
    patterns = [
        r"(?:no|avoid|exclude|not|without|don't want|do not want)\s+([a-zA-Z\s\-]+?)(?=[,\.\n]|$)"
    ]
    for p in patterns:
        for match in re.findall(p, intent_text.lower()):
            clean = match.strip()
            if clean and len(clean) > 2:
                negatives.append(clean)
    return list(set(negatives))

def fetch_platform_jobs_worldwide(
    search_term: str, 
    location: str = "", 
    country_choice: str = "United Kingdom", 
    is_remote: bool = False,
    results_wanted: int = 20,
    hours_old: int = 168
) -> pd.DataFrame:
    """Multi-threaded crawler with per-platform 429 rate-limit isolation."""
    target_country = FINANCIAL_CENTRE_MAP.get(country_choice, "uk")
    clean_country_name = country_choice.split(" - ")[-1].split(" (")[0]
    
    if is_remote:
        effective_loc = "Remote"
    elif "Worldwide" in country_choice:
        effective_loc = "Worldwide"
    else:
        effective_loc = clean_country_name

    collected_dfs = []

    # 1. Primary Scrape: LinkedIn & Indeed (Resilient, reliable throughput)
    try:
        df_primary = scrape_jobs(
            site_name=["linkedin", "indeed"],
            search_term=search_term,
            location=effective_loc,
            results_wanted=results_wanted,
            hours_old=hours_old,
            country_indeed=target_country,
            is_remote=is_remote,
            linkedin_fetch_description=True
        )
        if df_primary is not None and not df_primary.empty:
            collected_dfs.append(df_primary)
    except Exception as e:
        print(f"Primary board scrape notice ({search_term}): {e}")

    # 2. Secondary Scrape: Glassdoor (Isolated against 429 rate limit blocks)
    try:
        df_glassdoor = scrape_jobs(
            site_name=["glassdoor"],
            search_term=search_term,
            location=effective_loc,
            results_wanted=min(results_wanted, 8),
            hours_old=hours_old,
            country_indeed=target_country,
            is_remote=is_remote
        )
        if df_glassdoor is not None and not df_glassdoor.empty:
            collected_dfs.append(df_glassdoor)
    except Exception as e:
        print(f"Glassdoor notice (429 rate-limit or timeout bypassed): {e}")

    if collected_dfs:
        combined = pd.concat(collected_dfs, ignore_index=True)
        return combined.drop_duplicates(subset=["title", "company"], keep="first")

    return pd.DataFrame()

def generate_institutional_tailoring(cv_skills: set, job_text: str, role_title: str) -> dict:
    """Generates Workday/Taleo ATS token diffs and institutional bullet revisions."""
    text_l = job_text.lower()
    job_skills = [s for s in INSTITUTIONAL_TAXONOMY if s in text_l]
    missing = [s for s in job_skills if s not in cv_skills]
    
    actions = []
    if missing:
        top_missing = missing[:3]
        actions.append(
            f"**ATS Vector Alignment:** Inject tokens `{', '.join(top_missing)}` into your Core Quantitative Competencies section to clear Workday/Taleo semantic parsers."
        )
        actions.append(
            f"**Metric-Driven Deliverable Statement:** Detail practical application of **{top_missing[0].upper()}** using standard banking notation (*Action Verb + Computational Engine + Metric Result*)."
        )
    
    actions.append(
        f"**Executive Requisition Match:** Align your summary header directly to **'{role_title}'** to pass initial human committee screening."
    )
    
    return {
        "missing_keywords": missing,
        "actions": actions
    }

def calculate_review_odds(cv_data: dict, custom_intent: str, jobs_df: pd.DataFrame) -> pd.DataFrame:
    """Institutional Candidate Scoring Model (ICSM) evaluating screening pass probability."""
    if jobs_df.empty:
        return jobs_df

    cv_text = cv_data.get("raw_text", "")
    user_skills = set(cv_data.get("skills", []))
    custom_intent_clean = custom_intent.strip()
    negative_rules = extract_mandate_exclusions(custom_intent_clean)

    searchable_texts = []
    for _, row in jobs_df.iterrows():
        title = str(row.get("title") or "")
        company = str(row.get("company") or "")
        desc = str(row.get("description") or "")
        searchable_texts.append(f"{title} {title} {company} {desc}".strip())

    # 1. Requisition Intent Correlation (35%)
    if custom_intent_clean:
        intent_sim = compute_cosine_similarity(custom_intent_clean, searchable_texts)
        intent_sim = np.clip(intent_sim, 0.0, 1.0)
    else:
        intent_sim = np.zeros(len(searchable_texts))

    # 2. Competency Alpha (35%)
    cv_sim = compute_cosine_similarity(cv_text, searchable_texts)
    cv_sim = np.clip(cv_sim, 0.0, 1.0)

    # 3. Direct Taxonomy Overlap & Constraint Penalties (15%)
    taxonomy_scores = []
    matched_skills_list = []
    tailoring_reports = []
    penalties = []

    for idx, text in enumerate(searchable_texts):
        text_lower = text.lower()
        matched = [s for s in user_skills if s in text_lower]
        
        t_score = min(len(matched) / min(len(user_skills), 6), 1.0) if user_skills else 0.3
        taxonomy_scores.append(t_score)
        matched_skills_list.append(matched)

        advice = generate_institutional_tailoring(
            cv_skills=user_skills,
            job_text=text,
            role_title=str(jobs_df.iloc[idx].get("title", "this mandate"))
        )
        tailoring_reports.append(advice)

        penalty = 0.0
        for neg in negative_rules:
            if len(neg) > 2 and neg in text_lower:
                penalty += 0.40
        penalties.append(penalty)

    # 4. Market Recency Alpha (15%)
    recency_boost = []
    for _, row in jobs_df.iterrows():
        date_str = str(row.get("date_posted") or "").lower()
        if any(t in date_str for t in ["today", "1 day", "24 hours"]):
            recency_boost.append(0.15)
        elif any(t in date_str for t in ["2 days", "3 days"]):
            recency_boost.append(0.08)
        else:
            recency_boost.append(0.0)

    # Composite Probability Formula
    if custom_intent_clean:
        composite = (
            intent_sim * 0.35 + 
            cv_sim * 0.35 + 
            np.array(taxonomy_scores) * 0.15 + 
            np.array(recency_boost) + 0.10 - 
            np.array(penalties)
        ) * 100
    else:
        composite = (
            cv_sim * 0.50 + 
            np.array(taxonomy_scores) * 0.30 + 
            np.array(recency_boost) + 0.10
        ) * 100

    final_scores = np.clip(composite, 12.0, 97.5)

    jobs_df["response_odds_%"] = np.round(final_scores, 1)
    jobs_df["matched_skills"] = matched_skills_list
    jobs_df["tailoring_report"] = tailoring_reports

    return jobs_df.sort_values(by="response_odds_%", ascending=False)