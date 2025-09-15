from flask import Flask, render_template, request, send_file
import sqlite3
from fpdf import FPDF
import matplotlib
matplotlib.use('Agg')  # Prevent GUI issues on Render
import matplotlib.pyplot as plt
import io
import tempfile
import os
from datetime import datetime

app = Flask(__name__)
DB_NAME = "health.db"

# --- Initialize DB ---
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS health (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            weight REAL,
            height REAL,
            bp TEXT,
            sugar REAL
        )
        """)
        conn.commit()

init_db()

# --- Routes ---
@app.route("/", methods=["GET", "POST"])
def index():
    message = ""
    if request.method == "POST":
        try:
            weight = float(request.form.get("weight", "").strip())
            height = float(request.form.get("height", "").strip())
            bp = request.form.get("bp", "").strip()
            sugar = float(request.form.get("sugar", "").strip())
            
            if not bp:
                raise ValueError("Blood Pressure is required")

            date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with sqlite3.connect(DB_NAME) as conn:
                c = conn.cursor()
                c.execute(
                    "INSERT INTO health (date, weight, height, bp, sugar) VALUES (?, ?, ?, ?, ?)",
                    (date, weight, height, bp, sugar)
                )
                conn.commit()
            message = "Record added successfully!"
        except Exception as e:
            message = f"Error saving data: {e}"

    # Fetch all records
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM health ORDER BY date DESC")
        data = c.fetchall()

    return render_template("index.html", data=data, message=message)

@app.route("/download")
def download_pdf():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT date, weight, height, bp, sugar FROM health ORDER BY date")
        records = c.fetchall()

    if not records:
        return "No records found!"

    # --- Generate weight graph ---
    dates = [r[0] for r in records]
    weights = [r[1] for r in records]

    plt.figure(figsize=(6, 4))
    plt.plot(dates, weights, marker="o", label="Weight Progress")
    plt.xticks(rotation=30, ha="right")
    plt.ylabel("Weight (kg)")
    plt.xlabel("Date")
    plt.legend()
    plt.tight_layout()

    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    plt.savefig(tmp_file.name)
    plt.close()

    # --- Create PDF ---
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Health Progress Report", ln=True, align="C")

    pdf.set_font("Arial", size=12)
    pdf.ln(5)
    for r in records:
        pdf.cell(
            0, 10,
            f"Date: {r[0]} | Weight: {r[1]}kg | Height: {r[2]}cm | BP: {r[3]} | Sugar: {r[4]}mg/dl",
            ln=True
        )

    pdf.ln(10)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Health Suggestions:", ln=True)
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(
        0, 10,
        "- Maintain a balanced diet with vegetables, fruits, and proteins.\n"
        "- Exercise at least 30 minutes daily.\n"
        "- Drink enough water.\n"
        "- Reduce sugar and junk food.\n"
        "- Monitor blood pressure and sugar levels regularly."
    )

    # Add graph image
    pdf.image(tmp_file.name, x=40, w=120)
    os.remove(tmp_file.name)

    pdf_bytes = pdf.output(dest="S").encode("latin1")
    return send_file(io.BytesIO(pdf_bytes),
                     download_name="Health_Report.pdf",
                     as_attachment=True)

# --- Run locally ---
if __name__ == "__main__":
    app.run(debug=True)
