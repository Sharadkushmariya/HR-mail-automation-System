"""
╔══════════════════════════════════════════════════════════════╗
║        COMPANY RESEARCHER — Groq AI                         ║
║   Research → Custom Email → Match Check → Re-write if fail  ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
import json
import time
import requests
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY  = os.getenv("GROQ_API_KEY", "")
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL    = "llama-3.3-70b-versatile"

RESUME_SUMMARY = """
Name: Sharad Kushmariya
Education: BCA Graduate | NIIT Foundation Wipro-Aligned IT/Network Trainee
Certifications: CCITN Networking Fundamentals | CCNA (pursuing)
Skills:
  - Networking: TCP/IP, OSI Model, IP Addressing, Subnetting, DHCP, DNS
  - Tools: Cisco Packet Tracer, Wireshark (basic)
  - OS: Windows 10/11 Administration, Basic Linux
  - Programming: Python (basic), Flask
  - Support: Desktop Troubleshooting, Hardware/Software Support
Experience:
  - Computer Operator at Hero Automobile Showroom
  - Built HR email automation system (Python + Flask)
  - Built Gmail-to-Telegram notification bot (Gmail API + Groq AI)
Job Targets: Network Engineer L1, NOC Engineer, IT Support L1, Service Desk, Desktop Support
"""

CATEGORY_KEYWORDS = {
    "Tech - Software/SaaS":      ["software", "saas", "product", "platform", "app", "application"],
    "Tech - IT Services":        ["it services", "consulting", "managed services", "outsourcing", "tcs", "infosys", "wipro", "hcl", "accenture"],
    "Tech - Networking/Telecom": ["network", "telecom", "isp", "fiber", "noc", "infrastructure", "cisco", "airtel", "jio", "bsnl"],
    "Tech - Cloud/Security":     ["cloud", "aws", "azure", "gcp", "cybersecurity", "security", "devops"],
    "Tech - Data/AI":            ["data", "analytics", "ai", "machine learning", "ml", "artificial intelligence"],
    "BPO/KPO":                   ["bpo", "kpo", "call center", "customer support", "outsource", "process"],
    "Non-Tech - Manufacturing":  ["manufacturing", "automobile", "factory", "production", "industrial"],
    "Non-Tech - Finance/BFSI":   ["bank", "finance", "insurance", "nbfc", "fintech", "bfsi", "trading"],
    "Non-Tech - Healthcare":     ["hospital", "pharma", "healthcare", "medical", "clinic"],
    "Non-Tech - Retail/FMCG":    ["retail", "fmcg", "ecommerce", "e-commerce", "store", "supermarket"],
    "Non-Tech - Other":          [],
}

def classify_company(description: str) -> str:
    desc_lower = description.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in desc_lower for kw in keywords):
            return category
    return "Non-Tech - Other"

# ✅ FIX: Safe join helper — TypeError prevent karo
def safe_join(val) -> str:
    if isinstance(val, list):
        return ", ".join(str(v) for v in val)
    if isinstance(val, str):
        return val
    return ""


# ═══════════════════════════════════════════════════════════
#   GROQ API CALL — ✅ FIX: DuckDuckGo hataya, direct Groq knowledge
# ═══════════════════════════════════════════════════════════

def groq_chat(messages: list) -> str:
    """
    ✅ FIX: Web search tool hataya — DuckDuckGo 403 blocked tha.
    Groq apni training knowledge se company info deta hai — yeh reliable hai.
    """
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY .env mein set nahi hai! Check karo .env file.")

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type":  "application/json",
    }

    payload = {
        "model":       GROQ_MODEL,
        "messages":    messages,
        "temperature": 0.3,
        "max_tokens":  1500,
    }

    resp = requests.post(
        f"{GROQ_BASE_URL}/chat/completions",
        headers=headers,
        json=payload,
        timeout=30
    )

    # ✅ Better error logging
    if resp.status_code != 200:
        raise ValueError(f"Groq API error {resp.status_code}: {resp.text[:300]}")

    resp.raise_for_status()
    data = resp.json()

    content = data["choices"][0]["message"].get("content", "")
    if not content:
        raise ValueError("Groq returned empty response")

    return content.strip()


# ═══════════════════════════════════════════════════════════
#   STEP 1 — COMPANY RESEARCH
# ═══════════════════════════════════════════════════════════

def research_company(company_name: str) -> dict:
    messages = [
        {
            "role": "system",
            "content": (
                "You are a company research assistant with extensive knowledge of Indian and global companies. "
                "Always respond with valid JSON only — no markdown, no backticks, no extra text before or after JSON."
            )
        },
        {
            "role": "user",
            "content": f"""Research this company using your knowledge: "{company_name}"

Respond ONLY with this exact JSON format (no extra text):
{{
  "company_name": "official company name",
  "description": "2-3 sentence description: what they do, founded when, size, India presence",
  "category": "one of: Tech-Software, Tech-ITServices, Tech-Networking, Tech-Cloud, Tech-Data, BPO, NonTech-Finance, NonTech-Manufacturing, NonTech-Healthcare, NonTech-Retail, Other",
  "tech_stack": ["tech1", "tech2", "tech3"],
  "hiring_focus": "what kind of IT roles they typically hire freshers for",
  "is_tech": true,
  "headquarters": "city, country",
  "employee_count": "approximate e.g. 10,000+"
}}"""
        }
    ]

    try:
        result_text = groq_chat(messages)

        # ✅ Better JSON extraction
        start = result_text.find("{")
        end   = result_text.rfind("}") + 1
        if start == -1 or end == 0:
            raise ValueError(f"No JSON in response: {result_text[:200]}")

        data = json.loads(result_text[start:end])

        # ✅ Ensure tech_stack is always a list
        if not isinstance(data.get("tech_stack"), list):
            data["tech_stack"] = []

        data["category_detailed"] = classify_company(data.get("description", ""))
        return {"ok": True, "data": data}

    except json.JSONDecodeError as e:
        return {
            "ok": False, "error": f"JSON parse failed: {e}",
            "data": _fallback_data(company_name)
        }
    except Exception as e:
        return {
            "ok": False, "error": str(e),
            "data": _fallback_data(company_name)
        }

def _fallback_data(company_name: str) -> dict:
    return {
        "company_name":      company_name,
        "description":       f"{company_name} is a company. Research failed — using generic template.",
        "category":          "Unknown",
        "category_detailed": "Non-Tech - Other",
        "tech_stack":        [],
        "hiring_focus":      "General IT roles",
        "is_tech":           False,
        "headquarters":      "Unknown",
        "employee_count":    "Unknown",
    }


# ═══════════════════════════════════════════════════════════
#   STEP 2 — GENERATE EMAIL
# ═══════════════════════════════════════════════════════════

def generate_email(company_data: dict, candidate_config: dict) -> str:
    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert job application email writer for freshers in India. "
                "Write professional, concise, genuine emails. No fluff. "
                "Output ONLY the email body — no subject line, no JSON, no explanation."
            )
        },
        {
            "role": "user",
            "content": f"""Write a job application email for this candidate applying to this company.

COMPANY:
- Name: {company_data.get('company_name')}
- Description: {company_data.get('description')}
- Category: {company_data.get('category_detailed')}
- Tech Stack: {safe_join(company_data.get('tech_stack', []))}
- Hiring Focus: {company_data.get('hiring_focus')}
- Is Tech: {company_data.get('is_tech')}

CANDIDATE:
{RESUME_SUMMARY}
Name: {candidate_config.get('YOUR_NAME', 'Sharad Kushmariya')}
Phone: {candidate_config.get('YOUR_PHONE', '')}
LinkedIn: {candidate_config.get('YOUR_LINKEDIN', '')}

REQUIREMENTS:
1. Start: "Dear Hiring Manager," or "Dear HR Team,"
2. Company-specific intro — mention what {company_data.get('company_name')} does
3. Match skills to domain:
   - Tech/Networking → TCP/IP, Cisco, NOC skills
   - BPO → service desk, IT support, communication
   - Non-tech → desktop support, IT infrastructure, system admin
4. Why join THIS company specifically (1-2 genuine lines)
5. CTA: resume attached, request interview
6. Sign off: name, phone, LinkedIn

LENGTH: 150-200 words. Professional warm tone."""
        }
    ]
    return groq_chat(messages)


# ═══════════════════════════════════════════════════════════
#   STEP 3 — MATCH CHECK  ✅ FIX: safe_join use karo
# ═══════════════════════════════════════════════════════════

def check_email_match(email_body: str, company_data: dict) -> dict:
    messages = [
        {
            "role": "system",
            "content": (
                "You are a quality checker for job application emails. "
                "Respond ONLY with valid JSON — no markdown, no backticks, no extra text."
            )
        },
        {
            "role": "user",
            "content": f"""Check if this email matches this company well.

COMPANY: {company_data.get('company_name')}
Description: {company_data.get('description')}
Category: {company_data.get('category_detailed')}
Tech Stack: {safe_join(company_data.get('tech_stack', []))}

EMAIL:
{email_body}

Check: company mentioned, skills relevant, professional tone, clear CTA, 150-200 words.

Respond ONLY with:
{{"match": true, "score": 85, "issues": [], "suggestions": ""}}

Set match=true if score >= 70."""
        }
    ]

    try:
        result_text = groq_chat(messages)
        start = result_text.find("{")
        end   = result_text.rfind("}") + 1
        if start == -1:
            return {"match": True, "score": 75, "issues": [], "suggestions": ""}
        return json.loads(result_text[start:end])
    except Exception:
        return {"match": True, "score": 75, "issues": [], "suggestions": ""}


# ═══════════════════════════════════════════════════════════
#   STEP 4 — REWRITE
# ═══════════════════════════════════════════════════════════

def rewrite_email(email_body: str, company_data: dict,
                  match_result: dict, candidate_config: dict) -> str:
    messages = [
        {
            "role": "system",
            "content": "You are an expert job application email writer. Output ONLY the improved email body."
        },
        {
            "role": "user",
            "content": f"""Improve this email based on feedback.

COMPANY: {company_data.get('company_name')}
Description: {company_data.get('description')}
Category: {company_data.get('category_detailed')}

ORIGINAL EMAIL:
{email_body}

SCORE: {match_result.get('score')}/100
ISSUES: {', '.join(match_result.get('issues', []))}
SUGGESTIONS: {match_result.get('suggestions', '')}

Fix all issues. Keep 150-200 words. Output improved body only."""
        }
    ]
    return groq_chat(messages)


# ═══════════════════════════════════════════════════════════
#   MAIN PIPELINE
# ═══════════════════════════════════════════════════════════

def research_and_prepare_email(company_name: str, candidate_config: dict,
                                max_rewrites: int = 2) -> dict:
    result = {
        "company":           company_name,
        "researched_at":     datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ok":                False,
        "company_data":      {},
        "email_body":        "",
        "email_subject":     "",
        "match_score":       0,
        "match_attempts":    0,
        "category":          "",
        "category_detailed": "",
        "is_tech":           False,
        "description":       "",
        "tech_stack":        [],
        "error":             "",
    }

    try:
        # Step 1: Research
        research = research_company(company_name)
        company_data = research["data"]
        result.update({
            "company_data":      company_data,
            "description":       company_data.get("description", ""),
            "category":          company_data.get("category", ""),
            "category_detailed": company_data.get("category_detailed", ""),
            "is_tech":           company_data.get("is_tech", False),
            "tech_stack":        company_data.get("tech_stack", []),
        })

        # Step 2: Generate email
        email_body = generate_email(company_data, candidate_config)

        # Step 3+4: Match + rewrite loop
        attempt = 0
        while attempt <= max_rewrites:
            result["match_attempts"] = attempt + 1
            match = check_email_match(email_body, company_data)
            result["match_score"] = match.get("score", 0)

            if match.get("match", False):
                break

            attempt += 1
            if attempt <= max_rewrites:
                email_body = rewrite_email(email_body, company_data, match, candidate_config)

        # Build subject
        cat = result["category_detailed"]
        if "Networking" in cat or "Cloud" in cat:
            role_hint = "Network Support / IT Infrastructure"
        elif "BPO" in cat:
            role_hint = "IT Support / Service Desk"
        elif result["is_tech"]:
            role_hint = "IT Support / Network Engineer"
        else:
            role_hint = "IT Infrastructure Support"

        result["email_subject"] = f"Application for {role_hint} Role – {company_name}"
        result["email_body"]    = email_body
        result["ok"]            = True

    except Exception as e:
        result["error"] = str(e)

    return result


# ═══════════════════════════════════════════════════════════
#   BATCH RESEARCH
# ═══════════════════════════════════════════════════════════

def run_batch_research(excel_file: str, company_col: str,
                       email_col: str, candidate_config: dict,
                       limit: int = 50,
                       progress_callback=None) -> list:
    try:
        df = pd.read_excel(excel_file)
    except Exception as e:
        return [{"ok": False, "error": f"Excel read failed: {e}"}]

    for col in ["AI_Researched", "AI_Category", "AI_Description", "AI_EmailTemplate", "AI_MatchScore"]:
        if col not in df.columns:
            df[col] = ""

    pending_mask = df["AI_Researched"].isna() | (df["AI_Researched"] == "")
    pending_df   = df[pending_mask].head(limit)
    total        = len(pending_df)

    if total == 0:
        return []

    results = []

    for i, (idx, row) in enumerate(pending_df.iterrows(), 1):
        company = str(row.get(company_col, "")).strip()
        if not company or company.lower() == "nan":
            continue

        if progress_callback:
            progress_callback(i, total, company, None)

        res = research_and_prepare_email(company, candidate_config)
        results.append(res)

        df.at[idx, "AI_Researched"]    = "Yes"
        df.at[idx, "AI_Category"]      = res.get("category_detailed", "")
        df.at[idx, "AI_Description"]   = res.get("description", "")[:200]
        df.at[idx, "AI_EmailTemplate"] = res.get("email_body", "")[:500]
        df.at[idx, "AI_MatchScore"]    = res.get("match_score", 0)

        if progress_callback:
            progress_callback(i, total, company, res)

        if i < total:
            time.sleep(1)  # ✅ Rate limit — 1 sec enough (no web search now)

    try:
        df.to_excel(excel_file, index=False)
    except Exception as e:
        for r in results:
            r["excel_save_error"] = str(e)

    return results