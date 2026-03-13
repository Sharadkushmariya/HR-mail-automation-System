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

# ── Threading controls ─────────────────────────────────────
stop_event  = threading.Event()
pause_event = threading.Event()
campaign_thread = None


# ═══════════════════════════════════════════════════════════
#                    HELPER
# ═══════════════════════════════════════════════════════════

def read_status() -> dict:
    """status.json padhkar dashboard ko deta hai."""
    if os.path.exists("status.json"):
        with open("status.json", "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                pass

    # File nahi hai ya corrupt hai — progress se base banao
    progress = load_progress()
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

# ── Excel cache (30 sec) ──────────────────────────────
_excel_cache: dict = {"stats": None, "ts": 0.0}

def get_excel_stats() -> dict:
    """Excel stats cache karo — har poll pe file mat padhо"""
    if time.time() - _excel_cache["ts"] < 5 and _excel_cache["stats"]:
        return _excel_cache["stats"]
    try:
        import pandas as pd
        progress  = load_progress()
        sent_set  = set(progress.get("sent", []))
        df = pd.read_excel(CONFIG["EXCEL_FILE"])
        df = df.dropna(subset=[CONFIG["EMAIL_COLUMN"]])
        df_unique = df.drop_duplicates(subset=[CONFIG["EMAIL_COLUMN"]])
        total     = len(df)
        valid     = set(df_unique[CONFIG["EMAIL_COLUMN"]].str.strip().str.lower())
        sent_n     = len(sent_set & valid)
        failed_log = progress.get("failed_log", [])
        dup_n      = sum(1 for e in failed_log if e.get("reason") == "Duplicate email")
        failed_n   = progress.get("failed_total", 0)  # ← YEH PEHLE CHAHIYE
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
    """style.css aur dashboard.js same folder se serve karo"""
    return send_from_directory("frontend", filename)


# ── GET: live status for dashboard ────────────────────────
@app.route("/api/status")
def api_status():
    data = read_status()

    # Done hone pe cache invalidate karo
    if data.get("status") == "done":
        _excel_cache["stats"] = None
        _excel_cache["ts"]    = 0.0

    if not data.get("total"):
        stats = get_excel_stats()
        if stats:
            data.update(stats)

    # Config bhi bhejo (for display in dashboard)
    data["config"] = {
        "email_address": CONFIG["EMAIL_ADDRESS"],
        "your_name":     CONFIG["YOUR_NAME"],
        "daily_limit":   CONFIG["DAILY_LIMIT"],
        "delay_min":     CONFIG["DELAY_MIN"],
        "delay_max":     CONFIG["DELAY_MAX"],
        "resume_file":   CONFIG["RESUME_FILE"],
        "excel_file":    CONFIG["EXCEL_FILE"],
    }
    return jsonify(data)

@app.route("/api/config", methods=["POST"])
def api_config():
    from flask import request
    data = request.json or {}
    
    try:
        # CONFIG update karo
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
                # Numbers ko int mein convert karo
                if cfg_key in ("DAILY_LIMIT", "DELAY_MIN", "DELAY_MAX"):
                    try:
                        CONFIG[cfg_key] = int(data[key])
                    except ValueError:
                        return jsonify({"ok": False, "msg": f"{cfg_key} must be a number"})
                else:
                    CONFIG[cfg_key] = data[key]
        
        # Config ko file mein save karo (permanent)
        save_config = {k: v for k, v in CONFIG.items() 
                      if k != "EMAIL_APP_PASSWORD"}
        with open("config.json", "w") as f:
             json.dump(save_config, f, indent=2)

        add_status_log("info", "Config Updated", 
    f"Limit: {CONFIG['DAILY_LIMIT']}/day | Delay: {CONFIG['DELAY_MIN']}-{CONFIG['DELAY_MAX']}s")

        return jsonify({"ok": True, "msg": "Config saved!"})
    except Exception as e:
        return jsonify({"ok": False, "msg": f"Error saving config: {str(e)}"})

# ── GET: records with pagination & search ────────────────
@app.route("/api/records")
def api_records():
    from Emailer import load_progress, CONFIG
    import pandas as pd

    page     = int(request.args.get("page", 1))
    per_page = int(request.args.get("per", 50))
    search   = request.args.get("q", "").lower().strip()

    # ── Duplicate remove MAT karo — sab rows rakho ──
    try:
        df = pd.read_excel(CONFIG["EXCEL_FILE"])
        df = df.dropna(subset=[CONFIG["EMAIL_COLUMN"]])
        df[CONFIG["EMAIL_COLUMN"]] = df[CONFIG["EMAIL_COLUMN"]].str.strip().str.lower()
        records = df.to_dict("records")
    except Exception as e:
        return jsonify({"records": [], "total": 0, "page": 1, "per_page": per_page})

    progress   = load_progress()
    sent_set   = set(progress.get("sent", []))
    failed_set = set(progress.get("failed", []))

    # ── Apply search filter first ──
    seen_emails = {}
    for r in records:
        em = r.get(CONFIG["EMAIL_COLUMN"], "")
        seen_emails[em] = seen_emails.get(em, 0) + 1

    # Phir search filter lagao
    if search:
        records = [r for r in records if
                   search in str(r.get(CONFIG["EMAIL_COLUMN"], "")).lower() or
                   search in str(r.get(CONFIG["NAME_COLUMN"], "")).lower() or
                   search in str(r.get(CONFIG["COMPANY_COLUMN"], "")).lower()]

    total = len(records)
    start = (page - 1) * per_page
    result = []

    # track first-visible duplicates so we only mark later ones as failed
    _dup_shown = {}  # loop se pehle add karo

    failed_log = {
        entry["email"]: entry["reason"] 
        for entry in progress.get("failed_log", [])
        }
    
    for r in records[start: start + per_page]:
        em = str(r.get(CONFIG["EMAIL_COLUMN"], "")).lower()
        is_dup = seen_emails.get(em, 1) > 1

        if is_dup:
            if em not in _dup_shown:
                _dup_shown[em] = True
                # Pehli occurrence — normal status check
                if em in sent_set:
                    status = "sent"
                elif em in failed_set:
                    status = "failed"
                else:
                    status = "pending"
            else:
                # Duplicate occurrence — hamesha failed
                status = "failed"
        elif em in sent_set:
            status = "sent"
        elif em in failed_set:
            status = "failed"
        else:
            status = "pending"

        result.append({
            "email":   r.get(CONFIG["EMAIL_COLUMN"], ""),
            "name":    r.get(CONFIG["NAME_COLUMN"], ""),
            "company": r.get(CONFIG["COMPANY_COLUMN"], ""),
            "status":  status,
            "reason": "Duplicate email — skipped" if (is_dup and status == "failed")else failed_log.get(em, "Could not deliver") if status == "failed"
            else ""})

    return jsonify({"records": result, "total": total, "page": page, "per_page": per_page})


# ── POST: start campaign ──────────────────────────────────
@app.route("/api/start", methods=["POST"])
def api_start():
    global campaign_thread

    current = read_status().get("status", "idle")
    if current == "running":
        return jsonify({"ok": False, "msg": "Campaign already chal rahi hai"})
    
    # ── YEH ADD KARO — fresh start ke liye status reset ──
    if os.path.exists("status.json"):
        os.remove("status.json")

    _excel_cache["stats"] = None
    _excel_cache["ts"]    = 0.0

    # Stop kisi purani run ko
    stop_event.set()
    if campaign_thread and campaign_thread.is_alive():
        campaign_thread.join(timeout=2)

    stop_event.clear()
    pause_event.clear()

    def _run():
        run_daily_batch(_stop_flag=stop_event, _pause_flag=pause_event)

    campaign_thread = threading.Thread(target=_run, daemon=True)
    campaign_thread.start()

    # Turant initial status likho:
    time.sleep(0.5)

    return jsonify({"ok": True, "msg": "Campaign shuru ho gayi!"})


# ── POST: pause / resume ──────────────────────────────────
@app.route("/api/pause", methods=["POST"])
def api_pause():
    if pause_event.is_set():
        pause_event.clear()
        return jsonify({"ok": True, "msg": "Resumed"})
    else:
        pause_event.set()
        return jsonify({"ok": True, "msg": "Paused"})


# ── POST: stop ────────────────────────────────────────────
@app.route("/api/stop", methods=["POST"])
def api_stop():
    stop_event.set()
    pause_event.clear()
    # Status file update karo taaki dashboard idle ho jaye
    import time
    time.sleep(0.3)
    if os.path.exists("status.json"):
        try:
            with open("status.json", "r", encoding="utf-8") as f:
                s = json.load(f)
            s["status"] = "idle"
            s["current"] = ""
            s["timer"] = 0
            with open("status.json", "w", encoding="utf-8") as f:
                json.dump(s, f)
        except:
            pass
    return jsonify({"ok": True, "msg": "Stopped"})


# ── POST: reset all progress ──────────────────────────────
@app.route("/api/reset", methods=["POST"])
def api_reset():
    stop_event.set()

    for f in ["email_log.json", "status.json"]:
        if os.path.exists(f):
            os.remove(f)

    _excel_cache["stats"] = None  # ← YEH ADD KARO
    _excel_cache["ts"]    = 0.0   # ← YEH ADD KARO

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