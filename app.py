import os
import matplotlib
matplotlib.use('Agg')  # Headless backend for Render
import matplotlib.pyplot as plt
from flask import Flask, render_template, request, send_file
import sqlite3
from fpdf import FPDF
from io import BytesIO
from datetime import datetime

app = Flask(__name__)

# ---------------- Paths ----------------
BASE_DIR = os.getcwd()
DB_PATH = os.path.join(BASE_DIR, "health.db")
GRAPH_DIR = os.path.join(BASE_DIR, "graphs")
os.makedirs(GRAPH_DIR, exist_ok=True)  # Ensure folder exists

# ---------------- Database Setup ----------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS records
                 (id INTEGER PRIMARY KEY,
                  date TEXT,
                  weight REAL,
                  height REAL,
                  bmi REAL,
                  bp TEXT,
                  sugar REAL)''')
    conn.commit()
    conn.close()

init_db()

# ---------------- Routes ----------------
@app.route("/", methods=["GET", "POST"])
def index():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    message = ""
    if request.method == "POST":
        try:
            weight = float(request.form["weight"])
            height = float(request.form["height"])
            bp = request.form["bp"]
            sugar = float(request.form["sugar"])
            height_m = height / 100
            bmi = round(weight / (height_m**2), 2)
            date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            c.execute("INSERT INTO records (date, weight, height, bmi, bp, sugar) VALUES (?, ?, ?, ?, ?, ?)",
                      (date, weight, height, bmi, bp, sugar))
            conn.commit()
            message = "Record added successfully!"
        except Exception as e:
            message = f"Error: {str(e)}"

    c.execute("SELECT * FROM records ORDER BY date DESC")
    records = c.fetchall()
    conn.close()

    # Add alerts
    records_with_alerts = []
    for r in records:
        alerts = []
        try:
            systolic, diastolic = map(int, r[5].split('/'))
            if systolic > 140 or diastolic > 90:
                alerts.append("High BP")
        except:
            pass
        if r[6] < 70:
            alerts.append("Low Sugar")
        elif r[6] > 140:
            alerts.append("High Sugar")
        if r[4] >= 25:
            alerts.append("Overweight")
        records_with_alerts.append((r[0], r[1], r[2], r[3], r[5], r[6], ", ".join(alerts)))

    return render_template("index.html", data=records_with_alerts, message=message)

# ---------------- Graph Function ----------------
def create_graph(dates, values, ylabel, filename):
    try:
        if not dates or not values:
            return
        dates_dt = [datetime.strptime(d, "%Y-%m-%d %H:%M:%S") for d in dates]
        plt.figure(figsize=(6,4))
        plt.plot(dates_dt, values, marker='o', linestyle='-', color='green', label=ylabel)
        plt.xlabel("Date")
        plt.ylabel(ylabel)
        plt.title(f"{ylabel} Trend")
        plt.grid(True, linestyle='--', alpha=0.5)
        plt.legend()
        plt.gcf().autofmt_xdate()
        plt.tight_layout()
        plt.savefig(os.path.join(GRAPH_DIR, filename))
        plt.close()
    except Exception as e:
        print("Graph generation error:", e)

# ---------------- PDF Download ----------------
@app.route("/download")
def download_pdf():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT * FROM records ORDER BY date ASC")
        records = c.fetchall()
        conn.close()

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, "Health Tracker Report", 0, 1, 'C')
        pdf.ln(5)
        pdf.set_font("Arial", '', 12)

        # Extract data for graphs
        dates = [r[1] for r in records]
        weights = [r[2] for r in records]
        bmis = [r[4] for r in records]
        sugars = [r[6] for r in records]

        # Create graphs
        create_graph(dates, weights, "Weight (kg)", "weight.png")
        create_graph(dates, bmis, "BMI", "bmi.png")
        create_graph(dates, sugars, "Sugar (mg/dl)", "sugar.png")

        # Add records and alerts
        for rec in records:
            pdf.cell(0, 8, f"Date: {rec[1]} | Weight: {rec[2]} kg | Height: {rec[3]} cm | BMI: {rec[4]} | BP: {rec[5]} | Sugar: {rec[6]} mg/dl", 0, 1)
            alerts = []
            try:
                systolic, diastolic = map(int, rec[5].split('/'))
                if systolic > 140 or diastolic > 90:
                    alerts.append("High BP")
            except:
                pass
            if rec[6] < 70:
                alerts.append("Low Sugar")
            elif rec[6] > 140:
                alerts.append("High Sugar")
            if rec[4] >= 25:
                alerts.append("Overweight")
            if alerts:
                pdf.set_text_color(255, 0, 0)
                pdf.cell(0, 8, f"⚠ Alerts: {', '.join(alerts)}", 0, 1)
                pdf.set_text_color(0, 0, 0)
            pdf.ln(2)

        # Add graphs to PDF
        if dates:
            pdf.add_page()
            pdf.cell(0,10,"📈 Weight Trend",0,1,'C')
            pdf.image(os.path.join(GRAPH_DIR,"weight.png"), x=10, y=20, w=180)
            pdf.add_page()
            pdf.cell(0,10,"📈 BMI Trend",0,1,'C')
            pdf.image(os.path.join(GRAPH_DIR,"bmi.png"), x=10, y=20, w=180)
            pdf.add_page()
            pdf.cell(0,10,"📈 Sugar Trend",0,1,'C')
            pdf.image(os.path.join(GRAPH_DIR,"sugar.png"), x=10, y=20, w=180)

        pdf_output = BytesIO()
        pdf.output(pdf_output)
        pdf_output.seek(0)
        return send_file(pdf_output, download_name="health_report.pdf", as_attachment=True)
    except Exception as e:
        return f"Error generating PDF: {str(e)}", 500

# ---------------- Run App ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
