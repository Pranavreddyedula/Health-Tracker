from flask import Flask, render_template, request, send_file
import sqlite3
from fpdf import FPDF
from io import BytesIO
from datetime import datetime
import matplotlib.pyplot as plt

app = Flask(__name__)
DB_NAME = "health.db"

# ---------------- Database Setup ----------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
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
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    if request.method == "POST":
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

    c.execute("SELECT * FROM records ORDER BY date ASC")
    records = c.fetchall()
    conn.close()

    return render_template("index.html", records=records)

# ---------------- Fancy Graph Function ----------------
def create_fancy_graph(dates, y_values, ylabel, filename, thresholds=None):
    dates_dt = [datetime.strptime(d, "%Y-%m-%d %H:%M:%S") for d in dates]
    plt.figure(figsize=(6,4))
    plt.plot(dates_dt, y_values, marker='o', linestyle='-', color='green', label=ylabel)

    if thresholds:
        for i, val in enumerate(y_values):
            if val < thresholds.get('low', float('-inf')) or val > thresholds.get('high', float('inf')):
                plt.plot(dates_dt[i], val, marker='o', color='red', markersize=10)  # alert

    plt.xlabel("Date")
    plt.ylabel(ylabel)
    plt.title(f"{ylabel} Trend")
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.legend()
    plt.gcf().autofmt_xdate()
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()

# ---------------- PDF Download ----------------
@app.route("/download_pdf")
def download_pdf():
    conn = sqlite3.connect(DB_NAME)
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

    # Generate fancy graphs
    create_fancy_graph(weights, weights, "Weight (kg)", "weight.png", thresholds={'low': 40, 'high': 80})
    create_fancy_graph(dates, bmis, "BMI", "bmi.png", thresholds={'low': 18.5, 'high': 25})
    create_fancy_graph(dates, sugars, "Sugar (mg/dl)", "sugar.png", thresholds={'low': 70, 'high': 140})

    # Add records with alerts
    for rec in records:
        pdf.cell(0, 8, f"Date: {rec[1]} | Weight: {rec[2]} kg | Height: {rec[3]} cm | BMI: {rec[4]} | BP: {rec[5]} | Sugar: {rec[6]} mg/dl", 0, 1)
        alerts = []
        systolic, diastolic = map(int, rec[5].split('/'))
        if systolic > 140 or diastolic > 90:
            alerts.append("High BP")
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

    # Add fancy graphs to PDF
    pdf.add_page()
    pdf.cell(0, 10, "📈 Weight Trend", 0, 1, 'C')
    pdf.image("weight.png", x=10, y=20, w=180)

    pdf.add_page()
    pdf.cell(0, 10, "📈 BMI Trend", 0, 1, 'C')
    pdf.image("bmi.png", x=10, y=20, w=180)

    pdf.add_page()
    pdf.cell(0, 10, "📈 Sugar Trend", 0, 1, 'C')
    pdf.image("sugar.png", x=10, y=20, w=180)

    pdf_output = BytesIO()
    pdf.output(pdf_output)
    pdf_output.seek(0)
    return send_file(pdf_output, download_name="health_report.pdf", as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
