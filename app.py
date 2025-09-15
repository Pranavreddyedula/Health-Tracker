import os
import sqlite3
from flask import Flask, render_template, request, send_file
from fpdf import FPDF
import matplotlib.pyplot as plt
from datetime import datetime
from io import BytesIO

# ----------------- Setup -----------------
app = Flask(__name__)

# Base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GRAPH_DIR = os.path.join(BASE_DIR, "graphs")
FONTS_DIR = os.path.join(BASE_DIR, "fonts")

# Safe creation of directories
os.makedirs(GRAPH_DIR, exist_ok=True)
os.makedirs(FONTS_DIR, exist_ok=True)

# Database setup
DB_PATH = os.path.join(BASE_DIR, "health.db")
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
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

# ----------------- Helper Functions -----------------
def calculate_bmi(weight, height):
    return round(weight / ((height / 100) ** 2), 2)

def get_alert(bmi):
    if bmi < 18.5:
        return "Underweight ⚠️"
    elif bmi < 25:
        return "Normal"
    elif bmi < 30:
        return "Overweight ⚠️"
    else:
        return "Obese ⚠️"

def generate_graph(data):
    if not data:
        return None
    dates = [datetime.strptime(d[1], "%Y-%m-%d %H:%M:%S") for d in data]
    weights = [d[2] for d in data]
    bmis = [d[6] for d in data]

    plt.figure(figsize=(6, 4))
    plt.plot(dates, weights, label="Weight (kg)", marker='o')
    plt.plot(dates, bmis, label="BMI", marker='x')
    plt.xlabel("Date")
    plt.ylabel("Value")
    plt.title("Weight & BMI Progress")
    plt.legend()
    plt.tight_layout()

    graph_path = os.path.join(GRAPH_DIR, "progress.png")
    plt.savefig(graph_path)
    plt.close()
    return graph_path

# ----------------- Routes -----------------
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        weight = float(request.form["weight"])
        height = float(request.form["height"])
        bp = request.form["bp"]
        sugar = float(request.form["sugar"])
        bmi = calculate_bmi(weight, height)
        alert = get_alert(bmi)
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute(
            "INSERT INTO records (date, weight, height, bp, sugar, bmi, alert) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (date, weight, height, bp, sugar, bmi, alert)
        )
        conn.commit()

    cursor.execute("SELECT * FROM records")
    data = cursor.fetchall()
    return render_template("index.html", data=data)

@app.route("/download")
def download():
    cursor.execute("SELECT * FROM records")
    data = cursor.fetchall()

    pdf = FPDF()
    pdf.add_page()

    # Use Unicode font
    font_path = os.path.join(FONTS_DIR, "DejaVuSans.ttf")
    if not os.path.exists(font_path):
        return "Font not found! Please add DejaVuSans.ttf in the fonts/ folder."
    pdf.add_font("DejaVu", "", font_path, uni=True)
    pdf.set_font("DejaVu", size=12)

    pdf.cell(0, 10, "Health Tracker Report", ln=True, align="C")
    pdf.ln(5)

    # Table headers
    headers = ["Date", "Weight", "Height", "BMI", "BP", "Sugar", "Alerts"]
    for h in headers:
        pdf.cell(28, 8, h, border=1)
    pdf.ln()

    # Table rows
    for r in data:
        for value in r[1:]:
            pdf.cell(28, 8, str(value), border=1)
        pdf.ln()

    # Generate graph and add to PDF
    graph_path = generate_graph(data)
    if graph_path:
        pdf.image(graph_path, x=10, w=pdf.w - 20)

    pdf_buffer = BytesIO()
    pdf.output(pdf_buffer)
    pdf_buffer.seek(0)
    return send_file(pdf_buffer, as_attachment=True, download_name="Health_Report.pdf")

# ----------------- Main -----------------
if __name__ == "__main__":
    app.run(debug=True)
