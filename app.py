from flask import Flask, jsonify, render_template, send_from_directory, request
import threading
import json
import os
import time

# ── Tumhari script import ──────────────────────────────────
from Emailer import run_daily_batch, CONFIG, load_progress
from Emailer import add_status_log

# Startup pe config.json se load karo
if os.path.exists("config.json"):
    with open("config.json", "r") as f:
        saved = json.load(f)
        CONFIG.update(saved)

os.chdir(os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__, template_folder="frontend", static_folder="frontend")

# ✅ Upload folder — jahan Excel aur Resume save honge
UPLOAD_FOLDER = "Copy_Dataset"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ── Threading controls ─────────────────────────────────────
stop_event  = threading.Event()
pause_event = threading.Event()
campaign_thread = None


# ═══════════════════════════════════════════════════════════
#                    HELPERS
# ═══════════════════════════════════════════════════════════

def _save_config():
    """CONFIG ko config.json mein save karo (password exclude)."""
    save_config = {k: v for k, v in CONFIG.items() if k != "EMAIL_APP_PASSWORD"}
    with open("config.json", "w") as f:
        json.dump(save_config, f, indent=2)


# ── File Session — 24 hour expiry ─────────────────────────
FILE_SESSION = "file_session.json"

def _save_file_session(excel_name: str = "", resume_name: str = ""):
    """File upload ke baad session timestamp save karo."""
    import datetime
    now = datetime.datetime.now()
    # Aaj midnight tak valid
    midnight = datetime.datetime.combine(now.date() + datetime.timedelta(days=1),
                                         datetime.time.min)
    session = {
        "uploaded_at":  now.isoformat(),
        "expires_at":   midnight.isoformat(),
        "excel_name":   excel_name,
        "resume_name":  resume_name,
    }
    with open(FILE_SESSION, "w") as f:
        json.dump(session, f, indent=2)

def _check_file_session() -> dict:
    """
    File session check karo.
    Returns: { "valid": bool, "excel_name": str, "resume_name": str,
                "expires_at": str, "uploaded_at": str }
    """
    import datetime
    if not os.path.exists(FILE_SESSION):
        return {"valid": False}
    try:
        with open(FILE_SESSION, "r") as f:
            session = json.load(f)
        expires_at = datetime.datetime.fromisoformat(session["expires_at"])
        if datetime.datetime.now() >= expires_at:
            # Expire ho gayi — file delete karo
            os.remove(FILE_SESSION)
            return {"valid": False}
        return {
            "valid":        True,
            "excel_name":   session.get("excel_name", ""),
            "resume_name":  session.get("resume_name", ""),
            "expires_at":   session.get("expires_at", ""),
            "uploaded_at":  session.get("uploaded_at", ""),
        }
    except Exception:
        return {"valid": False}


def read_status() -> dict:
    if os.path.exists("status.json"):
        with open("status.json", "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                pass

    progress   = load_progress()
    failed_log = progress.get("failed_log", [])
    dup_n      = sum(1 for e in failed_log if e.get("reason") == "Duplicate email")
    real_fail  = progress.get("failed_total", 0) - dup_n

    return {
        "status":     "idle",
        "total":      0,
        "sent":       progress.get("total_sent", 0),
        "failed":     real_fail,
        "duplicates": dup_n,
        "pending":    0,
        "today_sent": 0,
        "timer":      0,
        "current":    "",
        "batch":      [],
        "last_run":   progress.get("last_run", "Never"),
    }


_excel_cache: dict = {"stats": None, "ts": 0.0}

def get_excel_stats() -> dict:
    if time.time() - _excel_cache["ts"] < 5 and _excel_cache["stats"]:
        return _excel_cache["stats"]
    try:
        import pandas as pd
        progress  = load_progress()
        sent_set  = set(progress.get("sent", []))
        df        = pd.read_excel(CONFIG["EXCEL_FILE"])
        df        = df.dropna(subset=[CONFIG["EMAIL_COLUMN"]])
        df_unique = df.drop_duplicates(subset=[CONFIG["EMAIL_COLUMN"]])
        total     = len(df)
        valid     = set(df_unique[CONFIG["EMAIL_COLUMN"]].str.strip().str.lower())
        sent_n     = len(sent_set & valid)
        failed_log = progress.get("failed_log", [])
        dup_n      = sum(1 for e in failed_log if e.get("reason") == "Duplicate email")
        failed_n   = progress.get("failed_total", 0)
        real_fail  = failed_n - dup_n
        real_sent  = sent_n - dup_n
        stats = {
            "total":      total,
            "sent":       real_sent,
            "failed":     real_fail,
            "duplicates": dup_n,
            "pending":    max(0, len(df_unique) - real_sent - real_fail - dup_n),
        }
        _excel_cache["stats"] = stats
        _excel_cache["ts"]    = time.time()
        return stats
    except Exception:
        return {}


# ═══════════════════════════════════════════════════════════
#                    ROUTES
# ═══════════════════════════════════════════════════════════

@app.route("/")
def index():
    return render_template("dashboard.html")


@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory("frontend", filename)


# ── GET: live status ───────────────────────────────────────
@app.route("/api/status")
def api_status():
    data = read_status()

    if data.get("status") == "done":
        _excel_cache["stats"] = None
        _excel_cache["ts"]    = 0.0

    if not data.get("total"):
        stats = get_excel_stats()
        if stats:
            data.update(stats)

    data["config"] = {
        "email_address": CONFIG["EMAIL_ADDRESS"],
        "your_name":     CONFIG["YOUR_NAME"],
        "daily_limit":   CONFIG["DAILY_LIMIT"],
        "delay_min":     CONFIG["DELAY_MIN"],
        "delay_max":     CONFIG["DELAY_MAX"],
        "resume_file":   CONFIG["RESUME_FILE"],
        "excel_file":    CONFIG["EXCEL_FILE"],
    }

    # ✅ File session status — dashboard ko batao files valid hain ya expire
    data["file_session"] = _check_file_session()

    return jsonify(data)


# ── POST: config update ────────────────────────────────────
@app.route("/api/config", methods=["POST"])
def api_config():
    data = request.json or {}
    try:
        for key, cfg_key in [
            ("email_address",  "EMAIL_ADDRESS"),
            ("email_password", "EMAIL_APP_PASSWORD"),
            ("your_name",      "YOUR_NAME"),
            ("your_phone",     "YOUR_PHONE"),
            ("your_linkedin",  "YOUR_LINKEDIN"),
            ("excel_file",     "EXCEL_FILE"),
            ("resume_file",    "RESUME_FILE"),
            ("daily_limit",    "DAILY_LIMIT"),
            ("delay_min",      "DELAY_MIN"),
            ("delay_max",      "DELAY_MAX"),
        ]:
            if key in data and data[key] != "":
                if cfg_key in ("DAILY_LIMIT", "DELAY_MIN", "DELAY_MAX"):
                    try:
                        CONFIG[cfg_key] = int(data[key])
                    except ValueError:
                        return jsonify({"ok": False, "msg": f"{cfg_key} must be a number"})
                else:
                    CONFIG[cfg_key] = data[key]

        _save_config()
        add_status_log("info", "Config Updated",
            f"Limit: {CONFIG['DAILY_LIMIT']}/day | Delay: {CONFIG['DELAY_MIN']}-{CONFIG['DELAY_MAX']}s")
        return jsonify({"ok": True, "msg": "Config saved!"})
    except Exception as e:
        return jsonify({"ok": False, "msg": f"Error saving config: {str(e)}"})


# ✅ POST: File Upload ──────────────────────────────────────
@app.route("/api/upload", methods=["POST"])
def api_upload():
    """
    Dashboard se Excel (.xlsx) ya Resume (.pdf) upload karo.
    Form field names:  'excel'   ya   'resume'
    """
    try:
        saved = {}

        # ── Excel ─────────────────────────────────────────
        if "excel" in request.files:
            f = request.files["excel"]
            if not f.filename:
                return jsonify({"ok": False, "msg": "Koi Excel file select nahi ki"})
            if not (f.filename or "").lower().endswith((".xlsx", ".xls")):
                return jsonify({"ok": False, "msg": "Sirf .xlsx ya .xls file allowed hai"})

            orig_name = f.filename
            save_path = os.path.join(UPLOAD_FOLDER, "hr_contacts.xlsx")
            f.save(save_path)

            CONFIG["EXCEL_FILE"] = save_path
            _excel_cache["stats"] = None
            _excel_cache["ts"]    = 0.0
            _save_config()

            row_count = 0
            try:
                import pandas as pd
                df = pd.read_excel(save_path)
                df = df.dropna(subset=[CONFIG["EMAIL_COLUMN"]])
                row_count = len(df)
            except Exception:
                pass

            add_status_log("info", "Excel Uploaded",
                f"{orig_name} → {row_count} contacts loaded ✅")
            saved["excel"] = {
                "original_name": orig_name,
                "path":          save_path,
                "rows":          row_count,
            }

        # ── Resume ────────────────────────────────────────
        if "resume" in request.files:
            f = request.files["resume"]
            if not f.filename:
                return jsonify({"ok": False, "msg": "Koi Resume file select nahi ki"})
            if not (f.filename or "").lower().endswith(".pdf"):
                return jsonify({"ok": False, "msg": "Sirf .pdf file allowed hai"})

            orig_name = f.filename
            save_path = os.path.join(UPLOAD_FOLDER, "resume.pdf")
            f.save(save_path)

            CONFIG["RESUME_FILE"] = save_path
            _save_config()

            add_status_log("info", "Resume Uploaded",
                f"{orig_name} saved successfully ✅")
            saved["resume"] = {
                "original_name": orig_name,
                "path":          save_path,
            }

        if not saved:
            return jsonify({"ok": False, "msg": "Request mein koi file nahi mili"})

        # ✅ File session save karo — 24 ghante valid (midnight tak)
        existing = _check_file_session()
        excel_name  = saved.get("excel",  {}).get("original_name", existing.get("excel_name",  ""))
        resume_name = saved.get("resume", {}).get("original_name", existing.get("resume_name", ""))
        _save_file_session(excel_name=excel_name, resume_name=resume_name)

        return jsonify({"ok": True, "saved": saved})

    except Exception as e:
        return jsonify({"ok": False, "msg": f"Upload error: {str(e)}"})


# ── GET: records ───────────────────────────────────────────
@app.route("/api/records")
def api_records():
    from Emailer import load_progress, CONFIG
    import pandas as pd

    page     = int(request.args.get("page", 1))
    per_page = int(request.args.get("per", 50))
    search   = request.args.get("q", "").lower().strip()

    try:
        df = pd.read_excel(CONFIG["EXCEL_FILE"])
        df = df.dropna(subset=[CONFIG["EMAIL_COLUMN"]])
        df[CONFIG["EMAIL_COLUMN"]] = df[CONFIG["EMAIL_COLUMN"]].str.strip().str.lower()
        records = df.to_dict("records")
    except Exception:
        return jsonify({"records": [], "total": 0, "page": 1, "per_page": per_page})

    progress   = load_progress()
    sent_set   = set(progress.get("sent", []))
    failed_set = set(progress.get("failed", []))

    seen_emails = {}
    for r in records:
        em = r.get(CONFIG["EMAIL_COLUMN"], "")
        seen_emails[em] = seen_emails.get(em, 0) + 1

    if search:
        records = [r for r in records if
                   search in str(r.get(CONFIG["EMAIL_COLUMN"], "")).lower() or
                   search in str(r.get(CONFIG["NAME_COLUMN"], "")).lower() or
                   search in str(r.get(CONFIG["COMPANY_COLUMN"], "")).lower()]

    total  = len(records)
    start  = (page - 1) * per_page
    result = []
    _dup_shown = {}

    failed_log = {
        entry["email"]: entry["reason"]
        for entry in progress.get("failed_log", [])
    }

    for r in records[start: start + per_page]:
        em     = str(r.get(CONFIG["EMAIL_COLUMN"], "")).lower()
        is_dup = seen_emails.get(em, 1) > 1

        if is_dup:
            if em not in _dup_shown:
                _dup_shown[em] = True
                if em in sent_set:       status = "sent"
                elif em in failed_set:   status = "failed"
                else:                    status = "pending"
            else:
                status = "failed"
        elif em in sent_set:    status = "sent"
        elif em in failed_set:  status = "failed"
        else:                   status = "pending"

        result.append({
            "email":   r.get(CONFIG["EMAIL_COLUMN"], ""),
            "name":    r.get(CONFIG["NAME_COLUMN"], ""),
            "company": r.get(CONFIG["COMPANY_COLUMN"], ""),
            "status":  status,
            "reason":  "Duplicate email — skipped" if (is_dup and status == "failed")
                       else failed_log.get(em, "Could not deliver") if status == "failed"
                       else ""
        })

    return jsonify({"records": result, "total": total, "page": page, "per_page": per_page})


# ── POST: start ────────────────────────────────────────────
@app.route("/api/start", methods=["POST"])
def api_start():
    global campaign_thread

    current = read_status().get("status", "idle")
    if current == "running":
        return jsonify({"ok": False, "msg": "Campaign already chal rahi hai"})

    if os.path.exists("status.json"):
        os.remove("status.json")

    _excel_cache["stats"] = None
    _excel_cache["ts"]    = 0.0

    stop_event.set()
    if campaign_thread and campaign_thread.is_alive():
        campaign_thread.join(timeout=2)

    stop_event.clear()
    pause_event.clear()

    def _run():
        run_daily_batch(_stop_flag=stop_event, _pause_flag=pause_event)

    campaign_thread = threading.Thread(target=_run, daemon=True)
    campaign_thread.start()
    time.sleep(0.5)

    return jsonify({"ok": True, "msg": "Campaign shuru ho gayi!"})


# ── POST: pause / resume ───────────────────────────────────
@app.route("/api/pause", methods=["POST"])
def api_pause():
    if pause_event.is_set():
        pause_event.clear()
        return jsonify({"ok": True, "msg": "Resumed"})
    else:
        pause_event.set()
        return jsonify({"ok": True, "msg": "Paused"})


# ── POST: stop ─────────────────────────────────────────────
@app.route("/api/stop", methods=["POST"])
def api_stop():
    stop_event.set()
    pause_event.clear()
    time.sleep(0.3)
    if os.path.exists("status.json"):
        try:
            with open("status.json", "r", encoding="utf-8") as f:
                s = json.load(f)
            s["status"]  = "idle"
            s["current"] = ""
            s["timer"]   = 0
            with open("status.json", "w", encoding="utf-8") as f:
                json.dump(s, f)
        except Exception:
            pass
    return jsonify({"ok": True, "msg": "Stopped"})


# ── POST: reset ────────────────────────────────────────────
@app.route("/api/reset", methods=["POST"])
def api_reset():
    stop_event.set()
    for fname in ["email_log.json", "status.json"]:
        if os.path.exists(fname):
            os.remove(fname)
    _excel_cache["stats"] = None
    _excel_cache["ts"]    = 0.0
    stop_event.clear()
    return jsonify({"ok": True, "msg": "Reset done"})


# ═══════════════════════════════════════════════════════════
#                       MAIN
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════╗
║         HR AUTOMATION — Dashboard Server                 ║
╠══════════════════════════════════════════════════════════╣
║   Browser: http://localhost:5000                         ║
╚══════════════════════════════════════════════════════════╝
    """)
    app.run(debug=False, port=5000, threaded=True)