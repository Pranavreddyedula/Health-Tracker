# 🏥 Health Tracker

A Flask-based **Health Tracking Web App** that records weight, height, calories, and steps.  
It generates a **downloadable PDF report** with progress graphs and personalized health suggestions.

---

## 🚀 Features
- Record **weight, height, calories, steps**
- Stores data in **SQLite (`health.db`)**
- Download **PDF report** with:
  - Clean data table
  - Progress graphs
  - Health & diet suggestions
- Deploy-ready on **Render**

---

## 📂 Project Structure
Health-Tracker/
│── app.py
│── requirements.txt
│── README.md
│── .gitignore
│── templates/
│ └── index.html

yaml
Copy code

---

## ⚡ Run Locally
```bash
git clone https://github.com/<your-username>/Health-Tracker.git
cd Health-Tracker
pip install -r requirements.txt
python app.py
Visit 👉 http://127.0.0.1:5000/

🌐 Deploy on Render



