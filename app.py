from flask import Flask, render_template, request, redirect, url_for, session, send_file
import random
import smtplib
from email.mime.text import MIMEText
import threading
import io
from datetime import datetime
from openpyxl import Workbook
from database.models import add_user
from database.models import get_user
from database.models import add_blast_log
from database.models import get_blast_logs
from database.models import delete_blast_log
from database.models import get_dashboard_stats
from openpyxl import Workbook
from openpyxl.styles import Font
import re
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

# Gmail Credentials
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
APP_PASSWORD = os.getenv("APP_PASSWORD")


@app.route("/")
def home():
    return render_template("login.html")


def send_otp(receiver_email, otp):
    try:
        subject = "Email Verification OTP"

        body = f"""
Hello,

Your OTP for registration is: {otp}

This OTP is valid for 5 minutes.

Do not share this OTP with anyone.

Thank You.
"""

        message = MIMEText(body)
        message["Subject"] = subject
        message["From"] = EMAIL_ADDRESS
        message["To"] = receiver_email

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL_ADDRESS, APP_PASSWORD)
        server.sendmail(
            EMAIL_ADDRESS,
            receiver_email,
            message.as_string()
        )
        server.quit()

        print("OTP sent successfully.")

    except Exception as e:
        print("Email Error:", e)


@app.route("/register", methods=["POST"])
def register():

    empid = request.form["Employee ID"]
    email = request.form["email"]
    username = request.form["username"]
    password = request.form["password"]

    # Generate 6-digit OTP
    otp = random.randint(100000, 999999)

    print("Generated OTP:", otp)

    # Store data temporarily
    session["otp"] = str(otp)
    session["empid"] = empid
    session["email"] = email
    session["username"] = username
    session["password"] = password

    # Send OTP email
    threading.Thread(target=send_otp, args=(email,otp)).start()

    # Redirect to OTP page
    return redirect(url_for("otp"))


@app.route("/otp")
def otp():
    return render_template("otp_verification.html")


@app.route("/verify-otp", methods=["POST"])
def verify_otp():

    entered_otp = request.form["otp"]

    if entered_otp == session["otp"]:

        add_user(
            session["empid"],
            session["email"],
            session["username"],
            session["password"]
        )

        return redirect(url_for("home"))

    return "Invalid OTP"


@app.route("/login", methods=["POST"])
def login():

    username = request.form["username"]
    password = request.form["password"]

    user = get_user(username)

    if user is None:
        return render_template(
            "login.html",
            login_error="Account doesn't exist."
        )

    if user["password"] != password:
        return render_template(
            "login.html",
            login_error="Incorrect password."
        )
    session["username"] = user["username"]
    session["employee_id"] = user["employee_id"]
    return redirect(url_for("dashboard"))

@app.route("/dashboard")
def dashboard():

    if "username" not in session:
        return redirect(url_for("home"))

    stats = get_dashboard_stats(session["employee_id"])

    return render_template(
        "dashboard.html",
        username=session["username"],
        stats=stats
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/insights")
def insights():

    if "username" not in session:
        return redirect(url_for("home"))

    # Get logged-in employee's blast data
    logs = get_blast_logs(session["employee_id"])

    # -----------------------------------------
    # BASIC TOTALS
    # -----------------------------------------

    total_reports = len(logs)

    total_holes = sum(
        float(log["holes"] or 0)
        for log in logs
    )

    total_explosives = sum(
        float(log["explosives"] or 0)
        for log in logs
    )

    # -----------------------------------------
    # LOCATION-WISE DATA
    # -----------------------------------------

    location_data = {}

    for log in logs:

        location = log["location"]

        if not location:
            continue

        if location not in location_data:
            location_data[location] = {
                "reports": 0,
                "holes": 0,
                "explosives": 0
            }

        location_data[location]["reports"] += 1

        location_data[location]["holes"] += float(
            log["holes"] or 0
        )

        location_data[location]["explosives"] += float(
            log["explosives"] or 0
        )

    # Convert dictionary into list
    location_stats = []

    for location, data in location_data.items():

        location_stats.append({
            "location": location,
            "reports": data["reports"],
            "holes": data["holes"],
            "explosives": data["explosives"]
        })

    # Sort locations by explosives
    location_stats.sort(
        key=lambda x: x["explosives"],
        reverse=True
    )

    # -----------------------------------------
    # FIND MAX VALUES FOR BAR HEIGHT
    # -----------------------------------------

    max_explosives = max(
        [x["explosives"] for x in location_stats],
        default=1
    )

    max_holes = max(
        [x["holes"] for x in location_stats],
        default=1
    )

    # Calculate percentage height for bars
    for item in location_stats:

        item["explosives_height"] = (
            item["explosives"] / max_explosives
        ) * 100

        item["holes_height"] = (
            item["holes"] / max_holes
        ) * 100

    # -----------------------------------------
    # MONTH-WISE BLAST ACTIVITY
    # -----------------------------------------

    month_names = [
        "Jan", "Feb", "Mar", "Apr",
        "May", "Jun", "Jul", "Aug",
        "Sep", "Oct", "Nov", "Dec"
    ]

    month_counts = [0] * 12

    for log in logs:

        blast_date = log["blast_date"]

        if blast_date:

            month_number = blast_date.month

            month_counts[month_number - 1] += 1

    # -----------------------------------------
    # CREATE DYNAMIC SVG POINTS
    # -----------------------------------------

    max_month_count = max(
        month_counts,
        default=1
    )

    if max_month_count == 0:
        max_month_count = 1

    activity_points = []

    for i, count in enumerate(month_counts):

        x = (i / 11) * 800

        y = 160 - (
            (count / max_month_count) * 130
        )

        activity_points.append(
            f"{x:.2f},{y:.2f}"
        )

    activity_points = " ".join(
        activity_points
    )

    # -----------------------------------------
    # SEND DATA TO insight.html
    # -----------------------------------------

    return render_template(
        "insight.html",

        username=session["username"],

        total_reports=total_reports,

        total_holes=total_holes,

        total_explosives=total_explosives,

        location_stats=location_stats,

        month_names=month_names,

        month_counts=month_counts,

        activity_points=activity_points
    )


def _current_month_key():
    now = datetime.now()
    return f"{now.year}-{now.month}"


def _get_visible_logs(employee_id):

    logs = get_blast_logs(employee_id)

    cleared_ids = session.get("cleared_ids", [])

    visible_logs = [
        log for log in logs
        if log["blast_id"] not in cleared_ids
    ]

    return visible_logs


@app.route("/add_data")
def add_data():

    if "username" not in session:
        return redirect(url_for("home"))

    logs = _get_visible_logs(session["employee_id"])

    return render_template(
        "add_data.html",
        username=session["username"],
        logs=logs
    )

@app.route("/save-blast", methods=["POST"])
def save_blast():

    employee_id = session["employee_id"]

    blast_date = request.form["date"]
    location = request.form["location"]
    holes = request.form["holes"]
    depth = request.form["depth"]
    burden = request.form["burden"]
    spacing = request.form["spacing"]
    explosives = request.form["explosives"]
    volume = request.form["volume"]
    pf = request.form["pf"]

    add_blast_log(
        employee_id,
        blast_date,
        location,
        holes,
        depth,
        burden,
        spacing,
        explosives,
        volume,
        pf
    )

    return redirect(url_for("add_data"))


@app.route("/delete-blast/<int:blast_id>", methods=["POST"])
def delete_blast(blast_id):

    if "employee_id" not in session:
        return redirect(url_for("home"))

    delete_blast_log(
        blast_id,
        session["employee_id"]
    )

    return redirect(url_for("add_data"))


@app.route("/clear-month", methods=["POST"])
def clear_month():

    if "employee_id" not in session:
        return redirect(url_for("home"))

    # Get all currently visible records
    logs = get_blast_logs(session["employee_id"])

    # Remember their IDs
    cleared_ids = [
        log["blast_id"]
        for log in logs
    ]

    session["cleared_ids"] = cleared_ids

    return redirect(url_for("add_data"))


@app.route("/export-excel")
def export_excel():

    if "employee_id" not in session:
        return redirect(url_for("home"))

    logs = _get_visible_logs(session["employee_id"])

    wb = Workbook()
    ws = wb.active
    ws.title = "Blast Reports"

    # -----------------------------------------
    # 5 BLANK ROWS BEFORE HEADER
    # -----------------------------------------

    for _ in range(5):
        ws.append([])

    # -----------------------------------------
    # HEADER - ROW 6
    # -----------------------------------------

    headers = [
        "DATE",
        "LOCATION",
        "HOLES",
        "DEPTH",
        "BURDEN",
        "SPACING",
        "EXPLOSIVES",
        "VOLUME",
        "PF"
    ]

    ws.append(headers)

    # Make headers bold
    for cell in ws[6]:
        cell.font = Font(bold=True)

    # -----------------------------------------
    # BLAST DATA
    # -----------------------------------------

    for log in logs:
        ws.append([
            log["blast_date"],
            log["location"],
            log["holes"],
            log["depth"],
            log["burden"],
            log["spacing"],
            log["explosives"],
            log["volume"],
            log["pf"],
        ])

    # -----------------------------------------
    # GRAND TOTAL EXPLOSIVES
    # -----------------------------------------

    total_explosives = sum(
        float(log["explosives"] or 0)
        for log in logs
    )

    # Last data row
    last_data_row = ws.max_row

    # One blank row before total
    total_row = last_data_row + 1

    # Label
    ws.cell(
        row=total_row,
        column=6,
        value="GRAND TOTAL"
    )

    # Total explosives
    ws.cell(
        row=total_row,
        column=7,
        value=total_explosives
    )

    # Bold
    ws.cell(
        row=total_row,
        column=6
    ).font = Font(bold=True)

    ws.cell(
        row=total_row,
        column=7
    ).font = Font(bold=True)

    # -----------------------------------------
    # CREATE EXCEL FILE
    # -----------------------------------------

    buffer = io.BytesIO()

    wb.save(buffer)

    buffer.seek(0)

    filename = f"Blast_Report_{datetime.now().strftime('%B_%Y')}.xlsx"

    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
if __name__ == "__main__":
    app.run(debug=True)