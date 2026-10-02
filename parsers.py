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
    """Extracts structured candidate profile, technical skills, and experience."""
    text_lower = cv_text.lower()
    
    # 1. Contact details extraction
    email_match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", cv_text)
    phone_match = re.search(r"(\+?\d{1,3}[\s-]?)?\(?\d{2,4}\)?[\s-]?\d{3,4}[\s-]?\d{3,4}", cv_text)
    
    email = email_match.group(0) if email_match else "Available on request"
    phone = phone_match.group(0) if phone_match else "Available on request"

    # 2. Institutional domain skill set matching
    competency_bank = [
        "python", "r", "sql", "excel", "power bi", "dax", "tableau", "c++", "vba",
        "pandas", "numpy", "scikit-learn", "pca", "mca", "knn", "git",
        "chain ladder", "london chain", "taylor separation", "mack", "reserving",
        "claims triangle", "solvency ii", "ifrs 17", "bel", "ibnr",
        "monte carlo", "vasicek", "stochastic", "alm", "var", "value at risk",
        "credit risk", "market risk", "basel iii"
    ]
    detected_skills = [skill for skill in competency_bank if skill in text_lower]

    # 3. Work experience & credentials extraction
    experience_highlights = []
    edu_highlights = []
    
    lines = [line.strip() for line in cv_text.split("\n") if len(line.strip()) > 3]
    for line in lines:
        line_l = line.lower()
        if any(term in line_l for term in ["intern", "analyst", "assistant", "stage", "consultant", "developer"]):
            if len(line) < 90 and not any(h == line for h in experience_highlights):
                experience_highlights.append(line)
        if any(term in line_l for term in ["master", "licence", "bachelor", "diplôme", "university", "université"]):
            if len(line) < 90 and not any(e == line for e in edu_highlights):
                edu_highlights.append(line)

    return {
        "raw_text": cv_text,
        "email": email,
        "phone": phone,
        "skills": list(dict.fromkeys(detected_skills)),
        "experience_highlights": experience_highlights[:4],
        "education_highlights": edu_highlights[:3]
    }

def parse_user_intent(intent_text: str) -> dict:
    """Parses user-entered requirements, locations, and negative exclusions."""
    text_lower = intent_text.lower()
    
    locations = []
    loc_keywords = ["london", "paris", "casablanca", "new york", "frankfurt", "remote", "worldwide", "morocco", "uk", "france", "germany"]
    for loc in loc_keywords:
        if loc in text_lower:
            locations.append(loc.title())
    if not locations:
        locations = ["Macro Hub Scope"]

    exclusions = []
    patterns = [
        r"(?:no|avoid|exclude|not|without|don't want|do not want)\s+([a-zA-Z\s\-]+?)(?=[,\.\n]|$)"
    ]
    for p in patterns:
        for match in re.findall(p, text_lower):
            clean = match.strip()
            if clean and len(clean) > 2:
                exclusions.append(clean)

    return {
        "raw_intent": intent_text.strip() if intent_text.strip() else "Targeting quantitative and actuarial analysis.",
        "target_locations": list(set(locations)),
        "exclusions": list(set(exclusions))
    }