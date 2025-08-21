from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
import requests
import time
import os
from datetime import datetime

app = Flask(__name__)

# --- Config ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///suggestions.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
OWM_API_KEY = os.getenv("OWM_API_KEY", "c9e13a16efccc359520cbcfb3c11185c")  # <-- replace or set env var
REQUEST_TIMEOUT = 12  # seconds

db = SQLAlchemy(app)

# --- Model ---
class Suggestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    city = db.Column(db.String(100), nullable=False)
    weather = db.Column(db.String(100), nullable=False)
    temperature = db.Column(db.Float, nullable=False)
    humidity = db.Column(db.Integer, nullable=False, default=0)       # NEW
    wind_speed = db.Column(db.Float, nullable=False, default=0.0)     # NEW
    aqi = db.Column(db.Integer, nullable=False)
    aqi_label = db.Column(db.String(40), nullable=False, default="")  # NEW
    suggestion = db.Column(db.String(500), nullable=False)
    is_night = db.Column(db.Boolean, nullable=False, default=False)   # NEW
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)  # NEW
    order_id = db.Column(db.String(100), nullable=True)

# --- Light auto-migration for SQLite (adds missing columns safely) ---
def ensure_columns():
    existing_cols = set()
    rows = db.session.execute(text("PRAGMA table_info(suggestion);")).fetchall()
    for r in rows:
        existing_cols.add(r[1])  # column name

    alter_cmds = []
    if "humidity" not in existing_cols:
        alter_cmds.append("ALTER TABLE suggestion ADD COLUMN humidity INTEGER NOT NULL DEFAULT 0;")
    if "wind_speed" not in existing_cols:
        alter_cmds.append("ALTER TABLE suggestion ADD COLUMN wind_speed REAL NOT NULL DEFAULT 0.0;")
    if "aqi_label" not in existing_cols:
        alter_cmds.append("ALTER TABLE suggestion ADD COLUMN aqi_label TEXT NOT NULL DEFAULT '';")
    if "is_night" not in existing_cols:
        alter_cmds.append("ALTER TABLE suggestion ADD COLUMN is_night INTEGER NOT NULL DEFAULT 0;")
    if "created_at" not in existing_cols:
        alter_cmds.append("ALTER TABLE suggestion ADD COLUMN created_at TEXT NOT NULL DEFAULT '1970-01-01T00:00:00';")

    for cmd in alter_cmds:
        db.session.execute(text(cmd))
    if alter_cmds:
        db.session.commit()

with app.app_context():
    db.create_all()
    ensure_columns()

# --- Helpers ---

def map_aqi_index_to_value_and_label(idx: int):
    """
    OWM Air Pollution index: 1..5 = [Good, Fair, Moderate, Poor, Very Poor]
    Map to an approximate US AQI midpoints and a label.
    """
    mapping = {
        1: (40,  "Good"),
        2: (75,  "Fair"),
        3: (125, "Moderate"),
        4: (175, "Poor"),
        5: (225, "Very Poor"),
    }
    return mapping.get(int(idx), (0, "Unknown"))

def curated_suggestion(weather_desc, temp, humidity, wind_speed, aqi_val, aqi_label, is_night):
    w = (weather_desc or "").lower()

    # Priority by health risks first
    if aqi_val >= 200 or aqi_label == "Very Poor":
        return "🚫 Air quality is very poor — avoid outdoor tasks, use N95 if you must step out, prefer rescheduling."

    if "thunderstorm" in w:
        return "⛈️ Thunderstorms expected. Stay indoors, avoid open areas/trees, and reschedule outdoor work."

    if "rain" in w or "drizzle" in w:
        if wind_speed >= 10:
            return "🌧️💨 Windy & rainy — carry rain gear, secure loose items, and move critical outdoor tasks."
        return "🌧️ Rain likely — carry an umbrella and shift non-urgent outdoor work to a dry window."

    if "snow" in w or "sleet" in w:
        return "❄️ Wintry conditions — wear insulated layers and avoid non-essential travel."

    # Heat / cold stress (uses humidity for apparent discomfort)
    if temp >= 40 or (temp >= 36 and humidity >= 60):
        return "🥵 Heat stress risk — hydrate often, avoid 11am–4pm outdoors, choose light clothing and shade."

    if temp <= 5 or ("freez" in w and temp <= 8):
        return "🧥 Very cold — layer up, protect extremities, and keep outdoor sessions short."

    # Wind advisories
    if wind_speed >= 14:
        return "💨 Strong winds — caution with ladders/rooftops, secure materials, and avoid light canopies."

    # Humidity discomfort
    if humidity >= 85 and "clear" in w:
        return "🌫️ Humid and muggy despite clear skies — schedule intense tasks in the early morning/evening."

    # Night-time nudge
    if is_night and temp >= 28 and aqi_val <= 125:
        return "🌙 Warm night but acceptable AQI — it’s okay to run light outdoor errands; heavy work can wait till dawn."

    # Mild default
    if aqi_val <= 125 and 18 <= temp <= 32 and wind_speed < 10:
        return "✅ Comfortable conditions — good window for outdoor tasks. Keep water handy."

    # Catch-all
    return "ℹ️ Mixed conditions — proceed with caution and prefer shorter outdoor slots with breaks."

# --- Routes ---

@app.route("/")
def home():
    return render_template("index.html")  # keep your existing HTML file

@app.route("/suggest", methods=["GET"])
def get_suggestion():
    city = (request.args.get("city") or "Bangalore").strip()
    if not city:
        return jsonify({"error": "City is required."}), 400

    try:
        # 1) Weather
        w_url = f"http://api.openweathermap.org/data/2.5/weather"
        w_params = {"q": city, "appid": OWM_API_KEY, "units": "metric"}
        w_resp = requests.get(w_url, params=w_params, timeout=REQUEST_TIMEOUT)
        if w_resp.status_code != 200:
            return jsonify({"error": f"Weather API failed: {w_resp.status_code}"}), 502

        w_data = w_resp.json()
        if not w_data or "weather" not in w_data or "main" not in w_data:
            return jsonify({"error": "Invalid weather response. Check city name."}), 400

        weather_desc = w_data["weather"][0]["description"]
        temp = float(w_data["main"]["temp"])
        humidity = int(w_data["main"].get("humidity", 0))
        wind_speed = float(w_data.get("wind", {}).get("speed", 0.0))
        lat = w_data["coord"]["lat"]
        lon = w_data["coord"]["lon"]

        # Day/Night detection using sunrise/sunset vs current time + timezone offset
        now_utc = int(time.time())
        tz_shift = int(w_data.get("timezone", 0))  # seconds
        local_now = now_utc + tz_shift
        sunrise = int(w_data.get("sys", {}).get("sunrise", now_utc)) + tz_shift
        sunset  = int(w_data.get("sys", {}).get("sunset",  now_utc)) + tz_shift
        is_night = not (sunrise <= local_now <= sunset)

        # 2) AQI
        aqi_url = "http://api.openweathermap.org/data/2.5/air_pollution"
        aqi_params = {"lat": lat, "lon": lon, "appid": OWM_API_KEY}
        aqi_resp = requests.get(aqi_url, params=aqi_params, timeout=REQUEST_TIMEOUT)
        if aqi_resp.status_code != 200:
            # fallback if AQI fails
            aqi_val, aqi_label = (125, "Moderate")
        else:
            aqi_json = aqi_resp.json()
            idx = int(aqi_json["list"][0]["main"]["aqi"])
            aqi_val, aqi_label = map_aqi_index_to_value_and_label(idx)

        # 3) Curated text
        suggestion_text = curated_suggestion(
            weather_desc, temp, humidity, wind_speed, aqi_val, aqi_label, is_night
        )

        # 4) Save
        rec = Suggestion(
            city=city.title(),
            weather=weather_desc,
            temperature=temp,
            humidity=humidity,
            wind_speed=wind_speed,
            aqi=aqi_val,
            aqi_label=aqi_label,
            is_night=bool(is_night),
            suggestion=suggestion_text,
            created_at=datetime.utcnow()
        )
        db.session.add(rec)
        db.session.commit()

        return jsonify({
            "id": rec.id,
            "city": rec.city,
            "weather": rec.weather,
            "temperature": rec.temperature,
            "humidity": rec.humidity,
            "wind_speed": rec.wind_speed,
            "aqi": rec.aqi,
            "aqi_label": rec.aqi_label,
            "is_night": rec.is_night,
            "suggestion": rec.suggestion,
            "created_at": rec.created_at.isoformat() + "Z"
        }), 200

    except requests.Timeout:
        return jsonify({"error": "Upstream API timeout."}), 504
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/suggestions", methods=["GET"])
def view_all_suggestions():
    limit = min(int(request.args.get("limit", 50)), 200)
    rows = Suggestion.query.order_by(Suggestion.id.desc()).limit(limit).all()
    return jsonify([
        {
            "id": s.id,
            "city": s.city,
            "weather": s.weather,
            "temperature": s.temperature,
            "humidity": s.humidity,
            "wind_speed": s.wind_speed,
            "aqi": s.aqi,
            "aqi_label": s.aqi_label,
            "is_night": bool(s.is_night),
            "suggestion": s.suggestion,
            "order_id": s.order_id,
            "created_at": (s.created_at.isoformat() + "Z") if isinstance(s.created_at, datetime) else str(s.created_at)
        } for s in rows
    ])

@app.route("/checkout", methods=["POST"])
def checkout():
    """
    Accepts either:
      - {"suggestion_id": 123}
      - {"city": "Pune"}  -> falls back to latest suggestion for that city
    """
    data = request.get_json(force=True, silent=True) or {}
    suggestion_id = data.get("suggestion_id")
    city = data.get("city")

    q = None
    if suggestion_id:
        q = Suggestion.query.filter_by(id=int(suggestion_id)).first()
    elif city:
        q = Suggestion.query.filter_by(city=city.title()).order_by(Suggestion.id.desc()).first()

    if not q:
        return jsonify({"error": "No matching suggestion found."}), 404

    order_id = f"ORDER-{int(time.time())}"
    q.order_id = order_id
    db.session.commit()

    return jsonify({
        "message": "Tasks scheduled.",
        "order_id": order_id,
        "suggestion_id": q.id,
        "city": q.city
    }), 200

# --- Main ---
if __name__ == "__main__":
    # Set use_reloader=False to avoid duplicate inserts on debug reload
    app.run(debug=True, use_reloader=False)
