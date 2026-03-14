# 📬 HR Mail Automation Dashboard

> A smart, self-hosted job application email automation system with a real-time web dashboard — built for fresher IT/Network Engineers to send personalized emails to HR contacts at scale.

---

## ✨ Features

- **📊 Live Dashboard** — Real-time stats, progress bar, activity log, and today's batch tracker
- **📁 File Upload** — Upload HR Excel contacts & Resume PDF directly from the dashboard
- **🔐 24-Hour File Session** — Uploaded files stay active till midnight; auto-expiry with re-upload prompt
- **⚙️ In-Dashboard Config** — Update Gmail, daily limit, delays, and files without touching code
- **⏸ Pause / Resume / Stop** — Full campaign control with live status updates
- **🔁 Duplicate Detection** — Automatically skips duplicate emails, tracked separately from failures
- **📈 All-Time Stats** — Total sent, failed, duplicates, and remaining contacts tracked persistently
- **🌙 Dark Theme UI** — Professional Dark Navy + Gold design, fully responsive

---

## 🗂️ Project Structure

```
Mail-Automation/
├── app.py                  ← Flask backend (API + file upload + session)
├── Emailer.py              ← Core email sending script
├── frontend/
│   ├── dashboard.html      ← Main dashboard UI
│   ├── dashboard.js        ← Live polling, upload logic, session handling
│   └── style.css           ← Dark Navy + Gold theme
├── Copy_Dataset/           ← Uploaded files stored here (gitignored)
│   ├── hr_contacts.xlsx    ← HR contacts (auto-saved on upload)
│   └── resume.pdf          ← Resume (auto-saved on upload)
├── .env                    ← Gmail credentials (gitignored)
├── .env.example            ← Template for setup
├── .gitignore
├── email_log.json          ← Persistent send/fail/duplicate tracking
├── file_session.json       ← 24hr file session tracker
├── config.json             ← Saved settings (password excluded)
└── status.json             ← Live campaign status (auto-generated)
```

---

## ⚡ Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/yourusername/hr-mail-automation.git
cd hr-mail-automation
```

### 2. Install dependencies

```bash
pip install flask pandas openpyxl python-dotenv
```

### 3. Setup credentials

```bash
cp .env.example .env
```

Edit `.env`:

```env
EMAIL_ADDRESS=your@gmail.com
EMAIL_APP_PASSWORD=abcdefghijklmnop
YOUR_NAME=Your Full Name
YOUR_PHONE=+91-XXXXXXXXXX
YOUR_LINKEDIN=linkedin.com/in/yourprofile
```

> **Note:** Use a [Gmail App Password](https://myaccount.google.com/apppasswords), not your regular Gmail password. Requires 2-Step Verification to be enabled.

### 4. Run the server

```bash
python app.py
```

### 5. Open dashboard

```
http://localhost:5000
```

---

## 🖥️ Dashboard Overview

| Section | Description |
|---|---|
| **Stat Cards** | Total contacts, sent, failed, duplicates, remaining, today's count |
| **Progress Bar** | Overall campaign progress with estimated finish date |
| **Live Log** | Real-time activity feed (sent, failed, waiting, info) |
| **Today's Batch** | Per-email status for current day's sending queue |
| **Configuration** | Quick view of current settings with Edit button |
| **Campaign Controls** | Start / Pause / Resume / Stop / Reset |
| **All Records Tab** | Paginated, searchable table of all HR contacts with status |

---

## ⚙️ Configuration

All settings are managed from the dashboard **Settings modal** (⚙️ Edit button):

| Setting | Description |
|---|---|
| Gmail Address | Your Gmail account |
| App Password | 16-character Google App Password |
| Full Name | Your name used in email signature |
| Phone / LinkedIn | Contact details in email footer |
| Daily Limit | Max emails per day (recommended: 20–50) |
| Delay Min / Max | Random delay between emails in seconds |
| Excel File | HR contacts spreadsheet (upload via dashboard) |
| Resume PDF | Your resume attached to every email (upload via dashboard) |

---

## 📋 Excel Format

Your HR contacts Excel file must have these columns:

| Column | Description |
|---|---|
| `Name` | HR contact's name |
| `Email` | HR email address |
| `Company` | Company name |

> Column names are configurable in `Emailer.py` via `CONFIG["EMAIL_COLUMN"]`, `NAME_COLUMN`, `COMPANY_COLUMN`.

---

## 🔐 File Session System

Uploaded files (Excel + Resume) are valid for **one session per day** (until midnight):

- ✅ **Session active** — file preview shown with `✓ valid till midnight`; no re-upload needed
- ✕ **Remove button** — click to swap file without restarting
- ⚠️ **Session expired** — dashboard log shows warning; Settings prompts re-upload
- Files are saved as `Copy_Dataset/hr_contacts.xlsx` and `Copy_Dataset/resume.pdf`

---

## 🛡️ Safety & Limits

- Emails sent with **random delay** (configurable) to avoid spam filters
- **Daily limit** enforced — campaign auto-stops when limit is reached
- **Duplicate detection** — same email in Excel won't be sent twice
- **Already-sent tracking** — restarts always skip previously sent contacts
- Gmail App Password used — main account password never stored

---

## 📦 Dependencies

```
flask
pandas
openpyxl
python-dotenv
```

Install all:

```bash
pip install flask pandas openpyxl python-dotenv
```

---

## 🚀 Deployment Tips

- Run on a **Windows/Linux local machine** — no cloud needed
- Keep the terminal open while campaign is running
- Use **Task Scheduler** (Windows) or **cron** (Linux) to auto-start daily
- Check `email_log.json` for full send history

---

## 📄 License

MIT License — free to use and modify.

---

## 👤 Author

**Sharad Kushmariya**
Fresher — Network Engineer | Desktop Support | Service Desk
📧 sharadkushmariya0@gmail.com | 🔗 linkedin.com/in/sharadkushmariya

---

> Built with ❤️ to automate the grind of job hunting — one email at a time.
