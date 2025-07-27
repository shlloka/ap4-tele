import sqlite3
import requests

DB_PATH = "digipin.db"
API_HOST = "http://localhost:5004"  # your server


def init_db(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
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
    return conn

def fetch_and_store(lat, lon, conn):
    resp = requests.get(f"{API_HOST}/api/digipin/encode", params={"latitude": lat, "longitude": lon})
    resp.raise_for_status()
    data = resp.json()
    digipin = data.get("digipin")
    conn.execute(
        "INSERT INTO records (latitude, longitude, digipin) VALUES (?, ?, ?)",
        (lat, lon, digipin)
    )
    conn.commit()
    return digipin

#saved records 
def show_records(conn, limit=10):
    print(f"\nLast {limit} saved records:")
    for row in conn.execute(
        "SELECT id, latitude, longitude, digipin, timestamp FROM records ORDER BY timestamp DESC LIMIT ?",
        (limit,)
    ):
        print(f"#{row[0]} | Lat: {row[1]} | Lon: {row[2]} | DigiPIN: {row[3]} | At: {row[4]}")

def main():
    conn = init_db()
    print("Enter coordinates to get DigiPIN (type 'q' to quit):")
    while True:
        lat_input = input("Latitude (or 'q'): ").strip()
        if lat_input.lower().startswith('q'):
            break
        lon_input = input("Longitude: ").strip()
        try:
            lat = float(lat_input)
            lon = float(lon_input)
        except ValueError:
            print("Invalid coordinate. Please enter numeric values.\n")
            continue

        try:
            pin = fetch_and_store(lat, lon, conn)
            print(f"DigiPIN: {pin}\nSaved successfully.\n")
        except requests.RequestException as e:
            print(f"Error calling API: {e}")
            break

    show_records(conn, limit=5)
    conn.close()

if __name__ == "__main__":
    main()
