import re
import pdfplumber

def extract_pdf_text(uploaded_file) -> str:
    """Extracts raw text content from uploaded candidate PDF."""
    text = ""
    try:
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
    except Exception as e:
        print(f"PDF extraction notice: {e}")
    return text.strip()

def parse_cv_profile(cv_text: str) -> dict:
    """Extracts headline, seniority, skills, experience, and academic track from the CV."""
    lines = [line.strip() for line in cv_text.split("\n") if line.strip()]
    text_lower = cv_text.lower()

    # 1. Candidate Headline / Target Title Extraction
    headline = "Quantitative / Actuarial Analyst"
    for line in lines[:8]:
        line_l = line.lower()
        if any(term in line_l for term in [
            "actuarial", "data scientist", "quantitative analyst", "risk analyst", 
            "reserving analyst", "financial engineer", "student", "msc", "master"
        ]):
            headline = line
            break

    # 2. Seniority & Experience Level Detection
    seniority = "Entry Level / Graduate"
    if any(k in text_lower for k in ["senior", "lead", "director", "manager", "5+ years", "6+ years"]):
        seniority = "Senior Analyst / Lead"
    elif any(k in text_lower for k in ["associate", "2+ years", "3+ years", "experienced"]):
        seniority = "Associate / Intermediate"
    elif any(k in text_lower for k in ["intern", "stage", "internship", "pfe", "graduate", "junior", "entry level", "student"]):
        seniority = "Graduate / Junior Analyst / Intern"

    # 3. Contact Details
    email_match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", cv_text)
    phone_match = re.search(r"(\+?\d{1,3}[\s-]?)?\(?\d{2,4}\)?[\s-]?\d{3,4}[\s-]?\d{3,4}", cv_text)
    email = email_match.group(0) if email_match else "Available on request"
    phone = phone_match.group(0) if phone_match else "Available on request"

    # 4. Domain Competency Taxonomy
    competency_bank = [
        "python", "r", "sql", "excel", "power bi", "dax", "tableau", "c++", "vba",
        "pandas", "numpy", "scikit-learn", "pca", "mca", "knn", "git", "cholesky",
        "chain ladder", "london chain", "taylor separation", "mack", "reserving",
        "claims triangle", "solvency ii", "ifrs 17", "bel", "ibnr", "loss ratio",
        "monte carlo", "vasicek", "stochastic", "alm", "var", "value at risk",
        "credit risk", "market risk", "basel iii", "stress testing"
    ]
    detected_skills = [skill for skill in competency_bank if skill in text_lower]

    # 5. Work Experience Track
    experience_highlights = []
    edu_highlights = []

    for line in lines:
        line_l = line.lower()
        # Experience criteria
        if any(term in line_l for term in [
            "intern", "analyst", "assistant", "stage", "consultant", "engineer", "associate"
        ]) and len(line) < 95:
            if not any(h == line for h in experience_highlights):
                experience_highlights.append(line)
        # Academic criteria
        if any(term in line_l for term in [
            "master", "licence", "bachelor", "diplôme", "degree", "university", "université", "school", "faculty"
        ]) and len(line) < 95:
            if not any(e == line for e in edu_highlights):
                edu_highlights.append(line)

    return {
        "raw_text": cv_text,
        "headline": headline,
        "seniority": seniority,
        "email": email,
        "phone": phone,
        "skills": list(dict.fromkeys(detected_skills)),
        "experience_highlights": experience_highlights[:5],
        "education_highlights": edu_highlights[:4]
    }

def parse_user_intent(intent_text: str) -> dict:
    """Parses seniority preferences, functional keywords, and negative exclusions."""
    text_lower = intent_text.lower()

    # Detect requested seniority in prompt
    requested_seniority = None
    if any(k in text_lower for k in ["intern", "internship", "stage", "pfe"]):
        requested_seniority = "Internship"
    elif any(k in text_lower for k in ["entry level", "graduate", "junior", "first job"]):
        requested_seniority = "Junior / Graduate"
    elif any(k in text_lower for k in ["senior", "lead", "head of"]):
        requested_seniority = "Senior"
    elif any(k in text_lower for k in ["associate", "mid", "experienced"]):
        requested_seniority = "Associate"

    # Extract functional exclusions
    exclusions = []
    patterns = [
        r"(?:no|avoid|exclude|not|without|don't want|do not want)\s+([a-zA-Z\s\-]+?)(?=[,\.\n]|$)"
    ]
    for p in patterns:
        for match in re.findall(p, text_lower):
            clean = match.strip()
            if clean and len(clean) > 2:
                exclusions.append(clean)

    # Keywords to prioritize
    tokens = [w for w in re.findall(r"\b[a-zA-Z]{3,}\b", text_lower) if w not in [
        "the", "and", "for", "with", "from", "that", "this", "role", "position", "jobs", "exclude", "want"
    ]]

    return {
        "raw_intent": intent_text.strip() if intent_text.strip() else "Targeting quantitative, risk, and actuarial analysis.",
        "requested_seniority": requested_seniority,
        "exclusions": list(set(exclusions)),
        "core_keywords": list(dict.fromkeys(tokens))[:8]
    }