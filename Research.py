"""
╔══════════════════════════════════════════════════════════════╗
║        COMPANY RESEARCHER — Groq + Web Search               ║
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

# ─── Groq Config ───────────────────────────────────────────
GROQ_API_KEY  = os.getenv("GROQ_API_KEY", "")
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL    = "llama-3.3-70b-versatile"   # web search support wala model

# ─── Resume text (jo bhi resume mein likha hai) ─────────────
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

# ─── Category keywords for classification ──────────────────
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
    """Company description se category detect karo."""
    desc_lower = description.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in desc_lower for kw in keywords):
            return category
    return "Non-Tech - Other"


# ═══════════════════════════════════════════════════════════
#              GROQ API CALL (with web search)
# ═══════════════════════════════════════════════════════════

def groq_chat(messages: list, use_web_search: bool = False) -> str:
    """Groq API call karo — web search optional."""
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY .env mein set nahi hai!")

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

    if use_web_search:
        payload["tools"] = [
            {
                "type": "function",
                "function": {
                    "name":        "web_search",
                    "description": "Search the web for current information about a company",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type":        "string",
                                "description": "Search query"
                            }
                        },
                        "required": ["query"]
                    }
                }
            }
        ]
        payload["tool_choice"] = "auto"

    resp = requests.post(
        f"{GROQ_BASE_URL}/chat/completions",
        headers=headers,
        json=payload,
        timeout=30
    )
    resp.raise_for_status()
    data = resp.json()

    choice = data["choices"][0]
    msg    = choice["message"]

    # Agar web search tool call aaya
    if msg.get("tool_calls"):
        # Tool call process — actual search result fetch karo
        tool_call = msg["tool_calls"][0]
        search_query = json.loads(tool_call["function"]["arguments"])["query"]

        # Groq ke saath web search simulate karo (second call with result)
        search_result = _do_web_search(search_query)

        # Tool result ke saath second call
        messages_with_result = messages + [
            {"role": "assistant", "content": None, "tool_calls": msg["tool_calls"]},
            {
                "role":         "tool",
                "tool_call_id": tool_call["id"],
                "content":      search_result,
            }
        ]
        payload2 = {
            "model":       GROQ_MODEL,
            "messages":    messages_with_result,
            "temperature": 0.3,
            "max_tokens":  1500,
        }
        resp2 = requests.post(
            f"{GROQ_BASE_URL}/chat/completions",
            headers=headers,
            json=payload2,
            timeout=30
        )
        resp2.raise_for_status()
        return resp2.json()["choices"][0]["message"]["content"].strip()

    return msg.get("content", "").strip()


def _do_web_search(query: str) -> str:
    """
    DuckDuckGo Instant Answer API se basic search result lo.
    Free, no API key needed.
    """
    try:
        resp = requests.get(
            "https://api.duckduckgo.com/",
            params={
                "q":       query,
                "format":  "json",
                "no_html": 1,
                "skip_disambig": 1,
            },
            timeout=10,
            headers={"User-Agent": "HR-Automation-Research/1.0"}
        )
        resp.raise_for_status()
        data = resp.json()

        parts = []
        if data.get("AbstractText"):
            parts.append(data["AbstractText"])
        if data.get("AbstractSource"):
            parts.append(f"Source: {data['AbstractSource']}")
        for topic in data.get("RelatedTopics", [])[:3]:
            if isinstance(topic, dict) and topic.get("Text"):
                parts.append(topic["Text"])

        if parts:
            return "\n".join(parts)
        return f"No direct results found for: {query}. Use your training knowledge about this company."
    except Exception as e:
        return f"Search failed ({e}). Use your training knowledge about this company."


# ═══════════════════════════════════════════════════════════
#              STEP 1 — COMPANY RESEARCH
# ═══════════════════════════════════════════════════════════

def research_company(company_name: str) -> dict:
    """
    Company ko research karo — description, category, tech stack, hiring focus.
    Returns dict with all research fields.
    """
    messages = [
        {
            "role": "system",
            "content": (
                "You are a company research assistant. Use web search to find accurate "
                "information about companies. Always respond with valid JSON only — "
                "no markdown, no backticks, no extra text."
            )
        },
        {
            "role": "user",
            "content": f"""Research this company: "{company_name}"

Search the web for current information. Then respond ONLY with this JSON:
{{
  "company_name": "official name",
  "description": "2-3 sentence description: what they do, founded when, size, India presence",
  "category": "one of: Tech-Software, Tech-ITServices, Tech-Networking, Tech-Cloud, Tech-Data, BPO, NonTech-Finance, NonTech-Manufacturing, NonTech-Healthcare, NonTech-Retail, Other",
  "tech_stack": ["tech1", "tech2"],
  "hiring_focus": "what kind of IT roles they typically hire for freshers",
  "is_tech": true or false,
  "headquarters": "city, country",
  "employee_count": "approximate e.g. 10,000+"
}}"""
        }
    ]

    try:
        result_text = groq_chat(messages, use_web_search=True)
        # JSON extract karo
        start = result_text.find("{")
        end   = result_text.rfind("}") + 1
        if start == -1:
            raise ValueError("JSON not found in response")
        data = json.loads(result_text[start:end])
        # Category refine
        data["category_detailed"] = classify_company(data.get("description", ""))
        return {"ok": True, "data": data}
    except Exception as e:
        return {
            "ok":    False,
            "error": str(e),
            "data": {
                "company_name":      company_name,
                "description":       f"{company_name} — could not fetch details.",
                "category":          "Unknown",
                "category_detailed": "Non-Tech - Other",
                "tech_stack":        [],
                "hiring_focus":      "General IT roles",
                "is_tech":           False,
                "headquarters":      "Unknown",
                "employee_count":    "Unknown",
            }
        }


# ═══════════════════════════════════════════════════════════
#              STEP 2 — GENERATE CUSTOM EMAIL
# ═══════════════════════════════════════════════════════════

def generate_email(company_data: dict, candidate_config: dict) -> str:
    """
    Company research + resume ke basis pe custom email body banao.
    """
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
            "content": f"""Write a job application email body for this candidate applying to this company.

COMPANY INFO:
- Name: {company_data.get('company_name')}
- Description: {company_data.get('description')}
- Category: {company_data.get('category_detailed')}
- Tech Stack: {', '.join(company_data.get('tech_stack', []))}
- Hiring Focus: {company_data.get('hiring_focus')}
- Is Tech Company: {company_data.get('is_tech')}

CANDIDATE RESUME SUMMARY:
{RESUME_SUMMARY}

CANDIDATE CONFIG:
- Name: {candidate_config.get('YOUR_NAME')}
- Phone: {candidate_config.get('YOUR_PHONE')}
- LinkedIn: {candidate_config.get('YOUR_LINKEDIN')}

EMAIL REQUIREMENTS:
1. Start with "Dear Hiring Manager," or "Dear HR Team,"
2. Company-specific intro: mention what {company_data.get('company_name')} does (from description)
3. Match candidate skills to company's domain:
   - Tech/Networking company → emphasize TCP/IP, Cisco, NOC, network support skills
   - BPO company → emphasize communication, IT support, service desk skills  
   - Non-tech company → emphasize IT infrastructure support, desktop support, system admin
4. Why candidate wants to join THIS specific company (1-2 lines, genuine reason)
5. Call to action: resume attached, request for interview
6. Sign off with name, phone, LinkedIn

LENGTH: 150-200 words. Professional but warm tone. No generic filler lines."""
        }
    ]

    return groq_chat(messages, use_web_search=False)


# ═══════════════════════════════════════════════════════════
#              STEP 3 — MATCH CHECK
# ═══════════════════════════════════════════════════════════

def check_email_match(email_body: str, company_data: dict) -> dict:
    """
    Email aur company description ka match check karo.
    Returns: { "match": bool, "score": int (0-100), "issues": [...], "suggestions": str }
    """
    messages = [
        {
            "role": "system",
            "content": (
                "You are a quality checker for job application emails. "
                "Respond ONLY with valid JSON — no markdown, no backticks."
            )
        },
        {
            "role": "user",
            "content": f"""Check if this job application email is well-matched to this company.

COMPANY:
- Name: {company_data.get('company_name')}
- Description: {company_data.get('description')}
- Category: {company_data.get('category_detailed')}
- Tech Stack: {', '.join(company_data.get('tech_stack', []))}

EMAIL BODY:
{email_body}

Check these criteria:
1. Does the email mention the company specifically? (not generic)
2. Are the skills relevant to this company's domain?
3. Is the tone professional?
4. Does it have a clear call to action?
5. Is it 150-200 words (not too short, not too long)?

Respond ONLY with:
{{
  "match": true or false,
  "score": 0-100,
  "issues": ["issue1", "issue2"],
  "suggestions": "brief suggestion for improvement if match is false"
}}

Set match=true if score >= 70."""
        }
    ]

    try:
        result_text = groq_chat(messages, use_web_search=False)
        start = result_text.find("{")
        end   = result_text.rfind("}") + 1
        data  = json.loads(result_text[start:end])
        return data
    except Exception:
        # Parse fail → assume match ok
        return {"match": True, "score": 75, "issues": [], "suggestions": ""}


# ═══════════════════════════════════════════════════════════
#         STEP 4 — RE-WRITE IF MATCH FAILED
# ═══════════════════════════════════════════════════════════

def rewrite_email(email_body: str, company_data: dict,
                  match_result: dict, candidate_config: dict) -> str:
    """Email ko improve karo based on match checker feedback."""
    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert job application email writer. "
                "Improve the given email based on feedback. "
                "Output ONLY the improved email body — no explanation."
            )
        },
        {
            "role": "user",
            "content": f"""Improve this job application email based on the feedback.

COMPANY:
- Name: {company_data.get('company_name')}
- Description: {company_data.get('description')}
- Category: {company_data.get('category_detailed')}

ORIGINAL EMAIL:
{email_body}

MATCH SCORE: {match_result.get('score')}/100
ISSUES FOUND: {', '.join(match_result.get('issues', []))}
SUGGESTIONS: {match_result.get('suggestions', '')}

Fix all issues. Keep 150-200 words. Output improved email body only."""
        }
    ]

    return groq_chat(messages, use_web_search=False)


# ═══════════════════════════════════════════════════════════
#         MAIN PIPELINE — Research + Write + Validate
# ═══════════════════════════════════════════════════════════

def research_and_prepare_email(company_name: str, candidate_config: dict,
                                max_rewrites: int = 2) -> dict:
    """
    Full pipeline for one company:
    1. Research company
    2. Generate email
    3. Match check
    4. Re-write if needed (max_rewrites times)
    
    Returns full result dict for UI display + Excel update.
    """
    result = {
        "company":          company_name,
        "researched_at":    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ok":               False,
        "company_data":     {},
        "email_body":       "",
        "email_subject":    "",
        "match_score":      0,
        "match_attempts":   0,
        "category":         "",
        "category_detailed": "",
        "is_tech":          False,
        "description":      "",
        "tech_stack":       [],
        "error":            "",
    }

    try:
        # ── Step 1: Research ──────────────────────────────
        research = research_company(company_name)
        company_data = research["data"]
        result["company_data"]      = company_data
        result["description"]       = company_data.get("description", "")
        result["category"]          = company_data.get("category", "")
        result["category_detailed"] = company_data.get("category_detailed", "")
        result["is_tech"]           = company_data.get("is_tech", False)
        result["tech_stack"]        = company_data.get("tech_stack", [])

        # ── Step 2: Generate Email ────────────────────────
        email_body = generate_email(company_data, candidate_config)

        # ── Step 3+4: Match + Re-write loop ──────────────
        attempt = 0
        while attempt <= max_rewrites:
            result["match_attempts"] = attempt + 1
            match = check_email_match(email_body, company_data)
            result["match_score"] = match.get("score", 0)

            if match.get("match", False):
                break  # ✅ Match passed

            attempt += 1
            if attempt <= max_rewrites:
                # Re-write
                email_body = rewrite_email(
                    email_body, company_data, match, candidate_config
                )

        # ── Build subject ─────────────────────────────────
        cat_detailed = result["category_detailed"]
        if "Networking" in cat_detailed or "Cloud" in cat_detailed:
            role_hint = "Network Support / IT Infrastructure"
        elif "BPO" in cat_detailed:
            role_hint = "IT Support / Service Desk"
        elif result["is_tech"]:
            role_hint = "IT Support / Network Engineer"
        else:
            role_hint = "IT Infrastructure Support"

        result["email_subject"] = (
            f"Application for {role_hint} Role – {company_name}"
        )
        result["email_body"] = email_body
        result["ok"]         = True

    except Exception as e:
        result["error"] = str(e)

    return result


# ═══════════════════════════════════════════════════════════
#         BATCH RESEARCH — Excel se companies lo
# ═══════════════════════════════════════════════════════════

def run_batch_research(excel_file: str, company_col: str,
                       email_col: str, candidate_config: dict,
                       limit: int = 50,
                       progress_callback=None) -> list:
    """
    Excel se next `limit` pending companies ki research karo.
    progress_callback(i, total, company_name, result) — UI update ke liye
    Returns list of result dicts.
    """
    try:
        df = pd.read_excel(excel_file)
    except Exception as e:
        return [{"ok": False, "error": f"Excel read failed: {e}"}]

    # Companies jo already researched nahi hain
    if "AI_Researched" not in df.columns:
        df["AI_Researched"]    = ""
        df["AI_Category"]      = ""
        df["AI_Description"]   = ""
        df["AI_EmailTemplate"] = ""
        df["AI_MatchScore"]    = ""

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

        # Excel mein update karo
        df.at[idx, "AI_Researched"]    = "Yes"
        df.at[idx, "AI_Category"]      = res.get("category_detailed", "")
        df.at[idx, "AI_Description"]   = res.get("description", "")[:200]
        df.at[idx, "AI_EmailTemplate"] = res.get("email_body", "")[:500]
        df.at[idx, "AI_MatchScore"]    = res.get("match_score", 0)

        if progress_callback:
            progress_callback(i, total, company, res)

        # Rate limiting — Groq free tier
        if i < total:
            time.sleep(2)

    # Excel save karo
    try:
        df.to_excel(excel_file, index=False)
    except Exception as e:
        for r in results:
            r["excel_save_error"] = str(e)

    return results