from flask import Flask, Request, request, render_template, redirect, url_for, jsonify
import sqlite3
import requests
from datetime import datetime, timedelta

app = Flask(__name__)

DB_PATH = "digipin.db"
API_HOST = "http://localhost:5004"  

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DROP TABLE IF EXISTS bookings")
    conn.execute("""
        CREATE TABLE bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT,
            email TEXT,
            vehicle_model TEXT,
            license_plate TEXT,
            last_service_date TEXT,
            service_type TEXT,
            warranty_status TEXT,
            pickup_drop TEXT,
            slot TEXT,
            next_service_due_in_X_days TEXT,
            digipin TEXT,
            marked_as_completed INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

def calculate_next_service_due_in_days(last_service_date_str, service_type):
    if not last_service_date_str:
        return None
    try:
        last_date = datetime.strptime(last_service_date_str, "%Y-%m-%d")
    except Exception:
        return None

    service_type_lower = service_type.lower() if service_type else ""
    days_map = {
        "free": 180,            # 6 months
        "paid": 180,            # 6 months or 7000 km
        "running repairs": 30,
    }
    days_to_add = days_map.get(service_type_lower, 180)
    next_due_date = last_date + timedelta(days=days_to_add)
    remaining_days = (next_due_date - datetime.now()).days
    return str(max(remaining_days, 0))


@app.route("/", methods=["GET", "POST"])
def index():
    digipin = None
    error = None
    latitude = None
    longitude = None
    if request.method == "POST":
        try:
            lat = float(request.form["latitude"])
            lon = float(request.form["longitude"])
            digipin = fetch_and_store(lat, lon)
        except ValueError:
            error = "Please enter valid numeric coordinates."
        except requests.RequestException as e:
            error = f"API error: {e}"
    return render_template("index.html", digipin=digipin, error=error, latitude=latitude, longitude=longitude)



# @app.route("/bookings", methods=["GET", "POST"])
# def bookings():
#     if request.method == "POST":
#         # Get all form fields
#         customer_name = request.form.get("customer_name")
#         email = request.form.get("email")
#         vehicle_model = request.form.get("vehicle_model")
#         license_plate = request.form.get("license_plate")
#         last_service_date = request.form.get("last_service_date")
#         service_type = request.form.get("service_type")
#         warranty_status = request.form.get("warranty_status")
#         pickup_drop = request.form.get("pickup_drop")
#         slot = request.form.get("slot")
#         digipin = request.form.get("digipin")
#         marked_as_completed = int(request.form.get("marked_as_completed", "0"))

#         # Calculate next_service_due_in_X_days
#         next_service_due = calculate_next_service_due_in_days(last_service_date, service_type)

#         data = (
#             customer_name,
#             email,
#             vehicle_model,
#             license_plate,
#             last_service_date,
#             service_type,
#             warranty_status,
#             pickup_drop,
#             slot,
#             next_service_due,
#             digipin,
#             marked_as_completed,
#         )

#         # Insert into DB
#         conn = sqlite3.connect(DB_PATH)
#         conn.execute(
#             """
#             INSERT INTO bookings
#             (customer_name, email, vehicle_model, license_plate, last_service_date, service_type, warranty_status,
#              pickup_drop, slot, next_service_due_in_X_days, digipin, marked_as_completed)
#             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#             """,
#             data,
#         )
#         conn.commit()
#         conn.close()
#         return redirect(url_for("bookings"))

#     # GET: Show all bookings ordered by created_at desc
#     conn = sqlite3.connect(DB_PATH)
#     conn.row_factory = sqlite3.Row
#     cur = conn.execute("SELECT * FROM bookings ORDER BY created_at DESC")
#     bookings_list = cur.fetchall()
#     conn.close()

#     return render_template("bookings.html", bookings=bookings_list)

@app.route("/bookings", methods=["GET", "POST"])
def bookings():
    if request.method == "POST":
        # Get all form fields
        customer_name = request.form.get("customer_name")
        email = request.form.get("email")
        vehicle_model = request.form.get("vehicle_model")
        license_plate = request.form.get("license_plate")
        last_service_date = request.form.get("last_service_date")
        service_type = request.form.get("service_type")
        warranty_status = request.form.get("warranty_status")
        pickup_drop = request.form.get("pickup_drop")
        slot = request.form.get("slot")
        digipin = request.form.get("digipin")
        marked_as_completed = int(request.form.get("marked_as_completed", "0"))

        # Calculate next_service_due_in_X_days
        next_service_due = calculate_next_service_due_in_days(last_service_date, service_type)

        data = (
            customer_name,
            email,
            vehicle_model,
            license_plate,
            last_service_date,
            service_type,
            warranty_status,
            pickup_drop,
            slot,
            next_service_due,
            digipin,
            marked_as_completed,
        )

        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                """
                INSERT INTO bookings
                (customer_name, email, vehicle_model, license_plate, last_service_date, service_type, warranty_status,
                 pickup_drop, slot, next_service_due_in_X_days, digipin, marked_as_completed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                data,
            )
        return redirect(url_for("bookings"))

    # GET: Show filtered bookings ordered by created_at desc
    service_type_filter = request.args.get("service_type", "").strip()
    next_due_filter = request.args.get("next_due", "").strip()
    marked_completed_filter = request.args.get("marked_completed", "").strip()

    query = "SELECT * FROM bookings WHERE 1=1"
    params = []

    if service_type_filter:
        query += " AND service_type = ?"
        params.append(service_type_filter)

    if next_due_filter:
        if next_due_filter == "due":
            query += " AND CAST(next_service_due_in_X_days AS INTEGER) <= 0"
        elif next_due_filter == "not_due":
            query += " AND CAST(next_service_due_in_X_days AS INTEGER) > 0"

    if marked_completed_filter in ("0", "1"):
        query += " AND marked_as_completed = ?"
        params.append(int(marked_completed_filter))

    query += " ORDER BY created_at DESC"

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(query, params)
        bookings_list = cur.fetchall()

    print("Filters received:", service_type_filter, next_due_filter, marked_completed_filter)    
    return render_template(
        "bookings.html",
        bookings=bookings_list,
        service_type_filter=service_type_filter,
        next_due_filter=next_due_filter,
        marked_completed_filter=marked_completed_filter,
    )
    


@app.route("/getdigipin")
def getdigipin():
    lat = request.args.get("latitude")
    lon = request.args.get("longitude")
    if lat and lon:
        try:
            digipin = fetch_and_store(float(lat), float(lon))
            return jsonify({"digipin": digipin})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
        return jsonify({"error": "Missing latitude or longitude"}), 400

@app.route("/update_completion/<int:booking_id>", methods=["POST"])
def update_completion(booking_id):
    marked = request.form.get("marked_as_completed", "0")
    marked_int = 1 if marked == "1" else 0

    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "UPDATE bookings SET marked_as_completed = ? WHERE id = ?",
                (marked_int, booking_id)
            )
            conn.commit()
        return jsonify({"success": True, "marked_as_completed": marked_int})
    except Exception as e:
        print(f"Error updating booking {booking_id}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
