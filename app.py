from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
import requests
import time
import os

app = Flask(__name__)

# SQLite DB config
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///suggestions.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Model
class Suggestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    city = db.Column(db.String(100), nullable=False)
    weather = db.Column(db.String(100), nullable=False)
    temperature = db.Column(db.Float, nullable=False)
    humidity = db.Column(db.Integer, nullable=False)
    wind_speed = db.Column(db.Float, nullable=False)
    aqi = db.Column(db.Integer, nullable=False)
    suggestion = db.Column(db.String(300), nullable=False)
    order_id = db.Column(db.String(100), nullable=True)

# Create DB once
with app.app_context():
    if not os.path.exists("suggestions.db"):
        db.create_all()

# Home route
@app.route("/")
def home():
    return render_template("index.html")

# Suggestion API
@app.route("/suggest", methods=["GET"])
def get_suggestion():
    city = request.args.get("city", "Bangalore")
    API_KEY = "c9e13a16efccc359520cbcfb3c11185c"  # Replace with your OpenWeatherMap API key

    try:
        # Weather API
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"
        response = requests.get(url)
        data = response.json()

        if 'weather' not in data or 'main' not in data:
            return jsonify({"error": "Invalid response. City may be wrong."})

        weather_description = data['weather'][0]['description']
        temperature = data['main']['temp']
        humidity = data['main']['humidity']
        wind_speed = data['wind']['speed']
        lat, lon = data['coord']['lat'], data['coord']['lon']

        # AQI API
        aqi_url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={API_KEY}"
        aqi_response = requests.get(aqi_url).json()
        aqi = aqi_response['list'][0]['main']['aqi'] * 50  # AQI 1–5 → scale to 50–250

        # Curated suggestion logic
        if aqi > 150:
            suggestion_text = "🚫 Air quality is very poor. Limit outdoor activities, especially for sensitive groups."
        elif "rain" in weather_description.lower():
            suggestion_text = "🌧️ Rain expected. Carry an umbrella and plan indoor tasks."
        elif "snow" in weather_description.lower():
            suggestion_text = "❄️ Snowfall likely. Wear warm clothes and avoid unnecessary travel."
        elif temperature > 38:
            suggestion_text = "🥵 Extreme heat. Stay hydrated, avoid outdoor work during noon, and wear light clothes."
        elif temperature < 5:
            suggestion_text = "🧥 Very cold. Wear layers and stay warm if going out."
        elif humidity > 80 and "clear" in weather_description.lower():
            suggestion_text = "🌫️ High humidity despite clear skies — avoid strenuous outdoor work."
        elif wind_speed > 10:
            suggestion_text = "💨 Strong winds. Be cautious if traveling or working outdoors."
        else:
            suggestion_text = "✅ Weather and air quality are suitable for most outdoor tasks."

        # Save to DB
        new_suggestion = Suggestion(
            city=city,
            weather=weather_description,
            temperature=temperature,
            humidity=humidity,
            wind_speed=wind_speed,
            aqi=aqi,
            suggestion=suggestion_text
        )
        db.session.add(new_suggestion)
        db.session.commit()

        return jsonify({
            "city": city,
            "weather": weather_description,
            "temperature": temperature,
            "humidity": humidity,
            "wind_speed": wind_speed,
            "aqi": aqi,
            "suggestion": suggestion_text
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# View all suggestions
@app.route("/suggestions", methods=["GET"])
def view_all_suggestions():
    suggestions = Suggestion.query.order_by(Suggestion.id.desc()).all()
    return jsonify([
        {
            "id": s.id,
            "city": s.city,
            "weather": s.weather,
            "temperature": s.temperature,
            "humidity": s.humidity,
            "wind_speed": s.wind_speed,
            "aqi": s.aqi,
            "suggestion": s.suggestion,
            "order_id": s.order_id
        } for s in suggestions
    ])

# Checkout API
@app.route("/checkout", methods=["POST"])
def checkout():
    data = request.get_json()
    city = data.get("city")
    order_id = f"ORDER-{int(time.time())}"
    last_suggestion = Suggestion.query.filter_by(city=city).order_by(Suggestion.id.desc()).first()
    if last_suggestion:
        last_suggestion.order_id = order_id
        db.session.commit()
    return jsonify({"message": "Tasks scheduled.", "order_id": order_id})

# Run locally
if __name__ == "__main__":
    app.run(debug=True)
