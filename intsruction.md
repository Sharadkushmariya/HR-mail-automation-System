1. Project Overview

This project is an automation system that sends personalized job outreach emails using an HR contact database. It includes a Flask-based dashboard to monitor email campaigns, view statistics, and manage automation.

2. Requirements

Before running the project, make sure the following tools are installed:

Python 3.8 or higher

pip (Python package manager)

Install required Python libraries:

pip install flask pandas openpyxl

3. Project Folder Structure

Example project structure:

Mail Automation
│
├── .env
│
├── Copy_Dataset
│   ├── your_resume.pdf
│   └── Test mail ID.xlsx
│
|
├── frontend
│   ├── dashboard.html
│   ├── dashboard.js
│   └── style.css
|
├── app.py
├── Emailer.py
│
├── automation.log
├── config.json
├── email_log.json
├── status.json
│
└── instruction.md

When you run the script, some files will be created automatically.

4. Excel File Format

The HR contact database must be stored in an Excel file.

Required columns:

Name	Email	Company
Rahul Sharma	hr@company.com
	ABC Technologies

Make sure the column names match exactly:

Name
Email
Company

5. Setup Configuration

Open the script and update the CONFIG section with your details.

Example:

EMAIL_ADDRESS = "yourgmail@gmail.com"
EMAIL_APP_PASSWORD = "xxxx xxxx xxxx xxxx"
YOUR_NAME = "Your Name"
YOUR_PHONE = "+91XXXXXXXXXX"
YOUR_LINKEDIN = "linkedin.com/in/yourprofile"

6. Gmail App Password Setup

To allow the script to send emails using Gmail:

Go to: https://myaccount.google.com

Open Security settings

Enable 2-Step Verification

Go to App Passwords

Select Mail

Generate a password

Copy the 16-character password

Example:

abcd efgh ijkl mnop

Paste this password in:

EMAIL_APP_PASSWORD

7. Running the Application

Start the Flask dashboard:

python app.py

Run the email automation script:

python hr_email_automation.py

Open the dashboard in your browser:

http://127.0.0.1:5000

8. Safety Recommendations

To avoid Gmail spam restrictions:

Limit emails to 50 per day

Use random delay between 60–120 seconds

Avoid sending bulk emails instantly

9. Troubleshooting
Server not connecting

Make sure Flask server is running:

python app.py
Emails not sending

Check:

Gmail App Password

Internet connection

Excel file format

10. Disclaimer

This project is intended for educational and automation learning purposes. Please ensure responsible usage and follow email sending policies.