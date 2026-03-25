"""
╔══════════════════════════════════════════════════════════════╗
║          HR EMAIL AUTOMATION SYSTEM - Gmail + Excel          ║
╚══════════════════════════════════════════════════════════════╝
"""

import smtplib 
import pandas as pd
import os
import time
import random
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, date
import json
from dotenv import load_dotenv
load_dotenv()

# ============================================================
#                    ⚙️ CONFIGURATION
#         ✅ SIRF YAHAN APNI DETAILS BHARO
# ============================================================

CONFIG = {
    # --- Gmail Settings ---
    "EMAIL_ADDRESS":      os.getenv("EMAIL_ADDRESS", ""),              # ✅ Gmail address
    "EMAIL_APP_PASSWORD": os.getenv("EMAIL_APP_PASSWORD", ""),        # ✅ Gmail App Password (16 chars)

    # --- Files ---
    "EXCEL_FILE":         "Copy_Dataset/Test mail ID's.xlsx",              # Excel file ka naam
    "RESUME_FILE":        "Copy_Dataset/Sharad_kushmariya_resume.pdf",     # Resume PDF ka naam
    "LOG_FILE":           "email_log.json",                           # Progress track file

    # --- Excel Column Names ---
    "EMAIL_COLUMN":       "Email",                            # Excel mein email column header
    "NAME_COLUMN":        "Name",                             # HR name column
    "COMPANY_COLUMN":     "Company",                          # Company column

    # --- Sending Limits ---
    "DAILY_LIMIT":        20,                                 # ✅ Roz 50 emails
    "DELAY_MIN":          60,                                 # Min seconds gap between emails
    "DELAY_MAX":          120,                                # Max seconds gap between emails

    # --- Tumhari Personal Info ---
    # ✅ LinkedIn (optional)
    "YOUR_NAME":          os.getenv("YOUR_NAME", "Your Name"),
    "YOUR_PHONE":         os.getenv("YOUR_PHONE", ""),
    "YOUR_LINKEDIN":      os.getenv("YOUR_LINKEDIN", ""),
    "JOB_ROLE":           "Network Engineer",
}

# ============================================================
#                   📧 EMAIL SUBJECT
# ============================================================

def get_email_subject(company=""):
    if company and company.strip():
        return f"Application for Network Support / IT Infrastructure Role – {company.strip()}"
    return "Application for Network Support / IT Infrastructure Role"


# ============================================================
#                   📝 EMAIL BODY
# ============================================================

def get_email_body(hr_name="", company=""):

    greeting     = f"Dear {hr_name.strip()}," if hr_name and hr_name.strip() else "Dear Hiring Manager,"
    company_line = f"at {company.strip()}" if company and company.strip() else "at your esteemed organization"

    body = f"""
{greeting}

I hope you are doing well.

My name is Sharad Kushmaria and I recently completed my BCA along with IT and networking training 
at NIIT Foundation. I have also completed CCITN networking fundamentals training and I am 
currently preparing for CCNA certification and actively seeking 
opportunities in Network Support, NOC, or IT Infrastructure roles {company_line}.

I have hands-on knowledge of networking fundamentals including TCP/IP, OSI model, IP addressing, 
subnetting, DHCP/DNS, and desktop troubleshooting. I have also practiced network configuration and 
troubleshooting using Cisco Packet Tracer and gained exposure to Windows and Linux system 
administration.
I am particularly interested in contributing to the IT infrastructure team at {company}.

Please find my resume attached for your consideration. I would be grateful for an opportunity to 
discuss how I can contribute to your IT team.

Thank you for your time and consideration.

Warm regards,
{CONFIG['YOUR_NAME']}
📞 {CONFIG['YOUR_PHONE']}
🔗 {CONFIG['YOUR_LINKEDIN']}
""".strip()

    return body


# ============================================================
#                    🔧 CORE FUNCTIONS
#              (Yahan kuch change mat karo)
# ============================================================

# Logging setup — Windows UTF-8 fix
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler("automation.log", encoding="utf-8"),
        logging.StreamHandler(stream=open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1))
    ]
)
log = logging.getLogger(__name__)


def load_progress():
    default = {
        "sent": [], "failed": [], "total_sent": 0,
        "last_run": "", "today_date": "", "today_count": 0,
        "failed_total": 0,
        "failed_log": []
    }
    if os.path.exists(CONFIG["LOG_FILE"]):
        try:
            with open(CONFIG["LOG_FILE"], "r") as f:
                data = json.load(f)
                # Naye fields add karo agar purana file hai
                for k, v in default.items():
                    data.setdefault(k, v)
                return data
        except (json.JSONDecodeError, IOError) as e:
            log.warning(f"⚠️  Could not load progress file: {e}")
            return default.copy()
    return default.copy()

print(f"DEBUG: {os.getenv('EMAIL_APP_PASSWORD')}")
def save_progress(progress):
    """Save progress to JSON file"""
    progress["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(CONFIG["LOG_FILE"], "w") as f:
        json.dump(progress, f, indent=2)


_logs: list = []

def write_status(data: dict):
    data["logs"] = _logs[-60:]
    try:
        with open("status.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        log.warning(f"⚠️  Status write failed: {e}")

def add_status_log(log_type, title, msg="", email=""):
    _logs.insert(0, {
        "type":  log_type,
        "title": title,
        "msg":   msg,
        "email": email,
        "time":  datetime.now().strftime("%H:%M:%S"),
    })
    if len(_logs) > 100:
        _logs.pop()


def load_hr_emails():
    """Excel se HR emails load karo"""
    try:
        df = pd.read_excel(CONFIG["EXCEL_FILE"])
        log.info(f"✅ Excel loaded: {len(df)} total records")

        if CONFIG["EMAIL_COLUMN"] not in df.columns:
            log.error(f"❌ Column '{CONFIG['EMAIL_COLUMN']}' not found!")
            log.error(f"   Available columns: {list(df.columns)}")
            return []

        df = df.dropna(subset=[CONFIG["EMAIL_COLUMN"]])
        df[CONFIG["EMAIL_COLUMN"]] = df[CONFIG["EMAIL_COLUMN"]].str.strip().str.lower()

        log.info(f"✅ Valid unique emails: {len(df)}")
        return df.to_dict("records")

    except FileNotFoundError:
        log.error(f"❌ Excel file '{CONFIG['EXCEL_FILE']}' nahi mila!")
        return []
    except Exception as e:
        log.error(f"❌ Excel load error: {e}")
        return []


def send_email(to_email, hr_name="", company=""):
    """Single email bhejo with resume attached — 3 retries"""
    for attempt in range(3):
        try:
            msg = MIMEMultipart()  # ← har attempt pe fresh msg banta hai ✅
            msg["From"]    = f"{CONFIG['YOUR_NAME']} <{CONFIG['EMAIL_ADDRESS']}>"
            msg["To"]      = to_email
            msg["Subject"] = get_email_subject(company)

            body = get_email_body(hr_name, company)
            msg.attach(MIMEText(body, "plain"))

            if os.path.exists(CONFIG["RESUME_FILE"]):
                with open(CONFIG["RESUME_FILE"], "rb") as f:
                    resume = MIMEBase("application", "octet-stream")
                    resume.set_payload(f.read())
                    encoders.encode_base64(resume)
                    resume_filename = os.path.basename(CONFIG["RESUME_FILE"])
                    resume.add_header(
                        "Content-Disposition",
                        f"attachment; filename={resume_filename}"
                    )
                    msg.attach(resume)
            else:
                log.warning(f"⚠️  Resume file nahi mila: {CONFIG['RESUME_FILE']}")

            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as server:
                server.login(CONFIG["EMAIL_ADDRESS"], CONFIG["EMAIL_APP_PASSWORD"])
                server.send_message(msg)

            return True  # ✅ success

        except smtplib.SMTPRecipientsRefused:
            log.error(f"❌ Invalid email: {to_email}")
            return False  # retry mat karo — invalid email hai

        except smtplib.SMTPAuthenticationError:
            log.error("❌ Gmail Authentication FAILED!")
            raise  # retry mat karo — password galat hai

        except Exception as e:
            log.warning(f"⚠️  Attempt {attempt+1}/3 failed for {to_email}: {e}")
            if attempt < 2:
                log.info(f"   Retrying in 5 seconds...")
                time.sleep(5)
            else:
                log.error(f"❌ All 3 attempts failed for {to_email}")
                return False


def run_daily_batch(_stop_flag=None, _pause_flag=None):
    """Daily batch of emails bhejo"""

    print("\n" + "="*60)
    print(f"  📬 HR EMAIL AUTOMATION - {date.today()}")
    print("="*60)

    progress    = load_progress()
    all_records = load_hr_emails()

    if not all_records:
        log.error("No emails to send. Excel file check karo.")
        return

    already_sent = set(progress["sent"])

    # ── Daily limit restart pe yaad rahe ──
    today_str = date.today().isoformat()
    if progress["today_date"] != today_str:
        # Naya din — reset karo
        progress["today_date"]  = today_str
        progress["today_count"] = 0
        save_progress(progress)

    remaining_today = CONFIG["DAILY_LIMIT"] - progress["today_count"]
    if remaining_today <= 0:
        log.info("✅ Aaj ka daily limit poora ho gaya. Kal dobara chalao.")
        add_status_log("info", "Daily Limit Done", "Aaj ka quota poora ho gaya ✅")
        write_status({
            "status": "done", "total": len(all_records),
            "sent": progress["total_sent"],
            "failed": len(progress.get("failed", [])),
            "pending": len(all_records) - len(already_sent),
            "today_sent": progress["today_count"],
            "timer": 0, "current": "", "batch": [], "last_run": progress.get("last_run", ""),
        })
        return

    # Step 1 — pehle ALL records mein duplicates mark karo
    seen_all = set()
    for r in all_records:
        em = r[CONFIG["EMAIL_COLUMN"]]
        r["_duplicate"] = em in seen_all
        if not r["_duplicate"]:
            seen_all.add(em)

    # Step 2 — pending: jo sent nahi hue AND duplicate nahi hain
    pending = [r for r in all_records if r[CONFIG["EMAIL_COLUMN"]] not in already_sent]

    print(f"\n📊 Status:")
    print(f"   Total HR emails   : {len(all_records)}")
    print(f"   Already sent      : {len(already_sent)}")
    print(f"   Remaining         : {len(pending)}")
    print(f"   Today's batch     : {min(CONFIG['DAILY_LIMIT'], len(pending))}")
    print(f"   Resume file       : {CONFIG['RESUME_FILE']}")
    print()

    if not pending:
        print("🎉 Sabko email bhej diya gaya! Koi pending nahi.")
        add_status_log("info", "Campaign Complete!", "Sabko email bhej diya gaya")
        return

    def get_remaining():
        return CONFIG["DAILY_LIMIT"] - progress["today_count"]

    todays_batch = pending[:get_remaining()]
        
    sent_count      = 0
    failed_count    = 0
    duplicate_count = 0

    batch_status = [
        {
            "email":   r[CONFIG["EMAIL_COLUMN"]],
            "company": r.get(CONFIG["COMPANY_COLUMN"], ""),
            "status":  "duplicate" if r.get("_duplicate") else "pending"
        }
        for r in todays_batch
    ]

    # Campaign start pe:
    add_status_log("info", "Campaign Started", f"Aaj {len(todays_batch)} emails bhejenge")

    for i, record in enumerate(todays_batch, 1):
        email   = record.get(CONFIG["EMAIL_COLUMN"], "")
        name    = record.get(CONFIG["NAME_COLUMN"], "")
        company = record.get(CONFIG["COMPANY_COLUMN"], "")

        # Stop check
        if _stop_flag and _stop_flag.is_set():
            add_status_log("info", "Stopped", f"{i-1}/{len(todays_batch)} pe ruk gaya")
            break

        # Stop check ke baad:
        if record.get("_duplicate"):
            add_status_log("info", "Duplicate Skipped", 
                          f"Duplicate email — skipping: {email}", email)
            batch_status[i-1]["status"] = "duplicate"
            write_status({
                "status":     "running",
                "total":      len(all_records),
                "sent":       progress["total_sent"],
                "failed":     len(progress.get("failed", [])),
                "duplicates": sum(1 for e in progress.get("failed_log", []) if e.get("reason") == "Duplicate email"),  # ← all time
                "pending":    len(pending) - sent_count,
                "today_sent": sent_count,
                "timer":      0,
                "current":    email,
                "batch":      batch_status,
                "last_run":   progress.get("last_run", ""),
            })
            progress["failed_total"] = progress.get("failed_total", 0) + 1
            progress["failed_log"].append({
                "email":  email,
                "reason": "Duplicate email",
                "date":   date.today().isoformat()
            })
            save_progress(progress)
            duplicate_count += 1
            continue

        # Pause check
        if _pause_flag and _pause_flag.is_set():
            add_status_log("info", "Paused", "Campaign paused")
            while _pause_flag.is_set():
                write_status({
                    "status":     "paused",
                    "total":      len(all_records),
                    "sent":       progress["total_sent"],
                    "failed":     len(progress.get("failed", [])),
                    "duplicates": sum(1 for e in progress.get("failed_log", []) 
                            if e.get("reason") == "Duplicate email"),
                    "pending":    len(pending) - sent_count,
                    "today_sent": sent_count,
                    "timer":      0,
                    "current":    email,
                    "batch":      batch_status,
                    "last_run":   progress.get("last_run", ""),
                })
                time.sleep(0.5)
                if _stop_flag and _stop_flag.is_set():
                    break
            if _stop_flag and _stop_flag.is_set():
                break

        batch_status[i-1]["status"] = "active"
        
        # ← YEH ADD KARO
        write_status({
            "status":     "running",
            "total":      len(all_records),
            "sent":       progress["total_sent"],
            "failed":     len(progress.get("failed", [])),
            "duplicates": sum(1 for e in progress.get("failed_log", []) 
                            if e.get("reason") == "Duplicate email"),
            "pending":    len(pending) - sent_count,
            "today_sent": sent_count,
            "timer":      0,
            "current":    email,
            "batch":      batch_status,
            "last_run":   progress.get("last_run", ""),
        })

        print(f"[{i}/{len(todays_batch)}] Sending to: {email}", end=" ... ")

        try:
            success = send_email(email, name, company)

            if success:
                print("✅ Sent!")
                progress["sent"].append(email)
                progress["total_sent"] = progress["total_sent"] + 1
                progress["today_count"] += 1
                sent_count += 1

                # Email sent hone pe:
                add_status_log("success", "Sent!", email, email)
                batch_status[i-1]["status"] = "sent"
            else:
                print("❌ Failed")
                if email not in progress["failed"]:
                    progress["failed"].append(email)
                progress["failed_total"] = progress.get("failed_total", 0) + 1
                progress["failed_log"].append({
                    "email":  email,                                 
                    "reason": "Could not deliver",                             
                    "date":   date.today().isoformat()    
                })
                failed_count += 1
                add_status_log("fail", "Failed", email, email)
                batch_status[i-1]["status"] = "failed"

            save_progress(progress)

            if i < len(todays_batch):
                delay = random.randint(CONFIG["DELAY_MIN"], CONFIG["DELAY_MAX"])
                next_email = todays_batch[i][CONFIG["EMAIL_COLUMN"]]
                print(f"   ⏳ Next email in {delay} seconds...")
                # Delay pe:
                add_status_log("wait", f"Waiting {delay}s", f"Next: {next_email}")
                for tick in range(delay):
                    if _stop_flag and _stop_flag.is_set():
                        break
                    if _pause_flag and _pause_flag.is_set():
                        break
                    write_status({
                        "status":     "running",
                        "total":      len(all_records),
                        "sent":       progress["total_sent"],
                        "failed":     len(progress.get("failed", [])),
                        "duplicates": sum(1 for e in progress.get("failed_log", []) 
                            if e.get("reason") == "Duplicate email"),
                        "pending":    len(pending) - sent_count,
                        "today_sent": sent_count,
                        "timer":      delay - tick,
                        "current":    email,
                        "batch":      batch_status,
                        "last_run":   progress.get("last_run", ""),
                    })
                    time.sleep(1)

        except smtplib.SMTPAuthenticationError:
            print("\n🔴 Authentication error - Stopping!")
            break

    # Summary
    print("\n" + "="*60)
    print(f"  📊 TODAY'S SUMMARY - {datetime.now().strftime('%H:%M:%S')}")
    print("="*60)
    print(f"  ✅ Sent today       : {sent_count}")
    print(f"  ❌ Failed           : {failed_count}")
    print(f"  ⊘ Duplicates skip  : {duplicate_count}")
    print(f"  📬 Total sent ever  : {progress['total_sent']}")
    print(f"  📋 Still remaining  : {len(pending) - sent_count}")
    days_left = (len(pending) - sent_count) // CONFIG["DAILY_LIMIT"] if CONFIG["DAILY_LIMIT"] > 0 else 0
    print(f"  📅 Days to complete : ~{days_left} more days")
    print("="*60)

    log.info(f"Batch complete. Sent: {sent_count}, Failed: {failed_count}")

    # Batch done pe:
    add_status_log("info", "Batch Done!", f"Sent: {sent_count} | Failed: {failed_count} | Duplicates: {duplicate_count}")
    
    # Sirf tab "All Done" aaye jab stop nahi hua ho
    if not (_stop_flag and _stop_flag.is_set()):
        add_status_log("info", "All Done!", "Aaj ke saare emails send ho gaye ✅")


    all_failed_log = progress.get("failed_log", [])
    all_dup_count  = sum(1 for e in all_failed_log if e.get("reason") == "Duplicate email")
    all_real_fail  = len(progress.get("failed", []))
    
    write_status({
        "status":     "done",
        "total":      len(all_records),
        "sent":       progress["total_sent"],
        "failed":     all_real_fail,       # ← all time real failed
        "duplicates": all_dup_count,       # ← all time duplicates
        "pending":    max(0, len(pending) - sent_count),
        "today_sent": sent_count,
        "timer":      0,
        "current":    "",
        "batch":      batch_status,
        "last_run":   progress.get("last_run", ""),
    })


def check_setup():
    """Setup verify karo before running"""
    print("\n🔍 Setup Check...")
    issues = []

    if not CONFIG["EMAIL_ADDRESS"]:
        issues.append("❌ EMAIL_ADDRESS .env mein set nahi kiya")
    if not CONFIG["EMAIL_APP_PASSWORD"]:
        issues.append("❌ EMAIL_APP_PASSWORD .env mein set nahi kiya")
    if not CONFIG["YOUR_NAME"] or CONFIG["YOUR_NAME"] == "Your Name":
        issues.append("❌ YOUR_NAME .env mein set nahi kiya")
    if not CONFIG["YOUR_PHONE"]:
        issues.append("❌ YOUR_PHONE .env mein set nahi kiya")
    if not os.path.exists(CONFIG["EXCEL_FILE"]):
        issues.append(f"❌ Excel file nahi mili: {CONFIG['EXCEL_FILE']}")
    if not os.path.exists(CONFIG["RESUME_FILE"]):
        issues.append(f"❌ Resume file nahi mili: {CONFIG['RESUME_FILE']}")

    if issues:
        print("\n⚠️  Pehle yeh fix karo:\n")
        for issue in issues:
            print(f"   {issue}")
        print("\n📝 Script ke upar CONFIG section mein apni details bharo.\n")
        return False

    print("✅ Sab kuch ready hai! Starting...\n")
    return True


# ============================================================
#                        🚀 MAIN
# ============================================================


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════╗
║      HR EMAIL AUTOMATION — Network Engineer Edition      ║
╚══════════════════════════════════════════════════════════╝
    """)

    if check_setup():
        run_daily_batch()
    else:
        print("Setup complete karo phir dobara run karo.")
