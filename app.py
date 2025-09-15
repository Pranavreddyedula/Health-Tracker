from flask import Flask, render_template, request, send_file
import sqlite3
from fpdf import FPDF
from io import BytesIO
import os
from datetime import datetime
import matplotlib
matplotlib.use('Agg')  # Headless backend for server
import matplotlib.pyplot as plt

# ---------------- App setup ----------------
app = Flask(__name__)

# Ensure graphs folder exists
GRAPH_DIR = "graphs"
os.makedirs(GRAPH_DIR, exist_ok=True)

# ---------------- Database setup ----------------
DB_NAME = "health_data.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            weight REAL,
            height REAL,
            bp TEXT,
            sugar REAL,
            bmi REAL,
            alert TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ---------------- Helper functions ----------------
def calculate_bmi(weight, height):
    height_m = height / 100
    bmi = weight / (height_m ** 2)
    return round(bmi, 2)

def determine_alert(bmi):
    if bmi < 18.5:
        return "Underweight"
    elif 18.5 <= bmi < 25:
        return "Normal"
    elif 25 <= bmi < 30:
        return "Overweight"
    else:
        return "Obese"

def create_weight_chart(dates, weights, filename="weight_chart.png"):
    plt.figure(figsize=(6,4))
    plt.plot(dates, weights, marker='o', color='blue')
    plt.title("Weight Trend")
    plt.xlabel("Date")
    plt.ylabel("Weight (kg)")
    plt.grid(True)
    path = os.path.join(GRAPH_DIR, filename)
    plt.savefig(path)
    plt.close()
    return path

# ---------------- Routes ----------------
@app.route("/", methods=["GET", "POST"])
def index():
    message = ""
    if request.method == "POST":
        weight = float(request.form["weight"])
        height = float(request.form["height"])
        bp = request.form["bp"]
        sugar = float(request.form["sugar"])
        bmi = calculate_bmi(weight, height)
        alert = determine_alert(bmi)

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('''
            INSERT INTO records (date, weight, height, bp, sugar, bmi, alert)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), weight, height, bp, sugar, bmi, alert))
        conn.commit()
        conn.close()
        message = "Record added successfully!"

    # Fetch all records
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM records")
    data = c.fetchall()
    conn.close()

    return render_template("index.html", data=data, message=message)

@app.route("/download")
def download_pdf():
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT * FROM records")
        data = c.fetchall()
        conn.close()

        # Prepare PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, "Health Tracker Report", ln=True, align="C")
        pdf.ln(10)

        # Table header
        pdf.set_font("Arial", "B", 12)
        headers = ["Date", "Weight", "Height", "BMI", "BP", "Sugar", "Alerts"]
        for header in headers:
            pdf.cell(28, 10, header, border=1, align="C")
        pdf.ln()

        # Table rows
        pdf.set_font("Arial", "", 12)
        for row in data:
            pdf.cell(28, 10, str(row[1]), border=1, align="C")
            pdf.cell(28, 10, str(row[2]), border=1, align="C")
            pdf.cell(28, 10, str(row[3]), border=1, align="C")
            pdf.cell(28, 10, str(row[6]), border=1, align="C")
            pdf.cell(28, 10, str(row[4]), border=1, align="C")
            pdf.cell(28, 10, str(row[5]), border=1, align="C")
            pdf.cell(28, 10, str(row[7]), border=1, align="C")
            pdf.ln()

        # Generate weight chart
        dates = [row[1] for row in data]
        weights = [row[2] for row in data]
        if dates and weights:
            chart_path = create_weight_chart(dates, weights)
            pdf.image(chart_path, x=30, w=150)
        
        # Output PDF
        pdf_output = BytesIO()
        pdf.output(pdf_output)
        pdf_output.seek(0)
        return send_file(pdf_output, download_name="health_report.pdf", as_attachment=True)

    except Exception as e:
        return f"Error generating PDF: {e}"

# ---------------- Run ----------------
if __name__ == "__main__":
    app.run(debug=True)
