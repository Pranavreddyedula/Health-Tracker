from flask import Flask, render_template, request, send_file
import sqlite3
from fpdf import FPDF
import matplotlib.pyplot as plt
import io, datetime

app = Flask(__name__)
DB_NAME = "health.db"

# ---------------- Database Init ----------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS health (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            weight REAL,
            height REAL,
            calories REAL,
            steps INTEGER
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ---------------- Home ----------------
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        try:
            weight = float(request.form["weight"])
            height = float(request.form["height"])
            calories = float(request.form["calories"])
            steps = int(request.form["steps"])
            date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO health (date, weight, height, calories, steps) VALUES (?,?,?,?,?)",
                (date, weight, height, calories, steps)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            return f"Error saving data: {e}"

    return render_template("index.html")

# ---------------- Generate PDF ----------------
@app.route("/download")
def download_pdf():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT date, weight, height, calories, steps FROM health")
        rows = cursor.fetchall()
        conn.close()
    except Exception as e:
        return f"Database error: {e}"

    if not rows:
        return "⚠️ No health data available!"

    try:
        # Create PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(200, 10, "🏥 Health Progress Report", ln=True, align="C")
        pdf.ln(5)

        # Table
        pdf.set_font("Arial", size=10)
        for row in rows:
            pdf.multi_cell(
                0, 8,
                f"Date: {row[0]} | Weight: {row[1]} kg | Height: {row[2]} m | Calories: {row[3]} | Steps: {row[4]}"
            )

        # Graphs
        dates = [r[0] for r in rows]
        weights = [r[1] for r in rows]
        calories = [r[3] for r in rows]
        steps = [r[4] for r in rows]

        def add_graph(data, label):
            plt.figure()
            plt.plot(dates, data, marker="o")
            plt.xticks(rotation=45, fontsize=6)
            plt.title(label)
            plt.tight_layout()
            img = io.BytesIO()
            plt.savefig(img, format="png")
            img.seek(0)
            pdf.image(img, x=10, w=180)
            plt.close()

        add_graph(weights, "Weight (kg)")
        add_graph(calories, "Calories")
        add_graph(steps, "Steps")

        # Suggestions
        pdf.set_font("Arial", "B", 14)
        pdf.ln(10)
        pdf.cell(200, 10, "💡 Health Suggestions", ln=True)

        last_weight, last_calories, last_steps = weights[-1], calories[-1], steps[-1]
        suggestions = []

        if last_weight > 80:
            suggestions.append("⚠️ Try reducing weight with balanced diet & daily exercise.")
        elif last_weight < 50:
            suggestions.append("🍲 You may need a calorie surplus diet to gain weight.")
        else:
            suggestions.append("✅ Your weight is in a healthy range. Maintain it!")

        if last_calories > 3000:
            suggestions.append("⚠️ Reduce high-calorie intake, focus on proteins & fibers.")
        elif last_calories < 1500:
            suggestions.append("🍎 Increase calories with healthy foods like nuts & fruits.")

        if last_steps < 5000:
            suggestions.append("🚶 Aim for at least 8,000–10,000 steps per day.")

        pdf.set_font("Arial", size=12)
        for s in suggestions:
            pdf.multi_cell(0, 8, s)

        # Output PDF
        output = io.BytesIO()
        pdf.output(output)
        output.seek(0)
        return send_file(output, as_attachment=True, download_name="Health_Report.pdf", mimetype="application/pdf")

    except Exception as e:
        return f"PDF generation error: {e}"

# ---------------- Run ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
