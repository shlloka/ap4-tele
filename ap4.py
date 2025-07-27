from flask import Flask, request, render_template
import sqlite3
import requests

app = Flask(__name__)

DB_PATH = "digipin.db"
API_HOST = "http://localhost:5004"  

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            latitude REAL,
            longitude REAL,
            digipin TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def fetch_and_store(lat, lon):
    conn = sqlite3.connect(DB_PATH)
    resp = requests.get(f"{API_HOST}/api/digipin/encode", params={"latitude": lat, "longitude": lon})
    resp.raise_for_status()
    data = resp.json()
    digipin = data.get("digipin")
    conn.execute(
        "INSERT INTO records (latitude, longitude, digipin) VALUES (?, ?, ?)",
        (lat, lon, digipin)
    )
    conn.commit()
    conn.close()
    return digipin

@app.route("/", methods=["GET", "POST"])
def index():
    digipin = None
    error = None
    if request.method == "POST":
        try:
            lat = float(request.form["latitude"])
            lon = float(request.form["longitude"])
            digipin = fetch_and_store(lat, lon)
        except ValueError:
            error = "Please enter valid numeric coordinates."
        except requests.RequestException as e:
            error = f"API error: {e}"
    return render_template("index.html", digipin=digipin, error=error)

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
