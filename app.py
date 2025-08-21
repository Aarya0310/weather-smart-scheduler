from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
import requests
import time
import os
import random

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
    aqi = db.Column(db.Integer, nullable=False)
    suggestion = db.Column(db.String(200), nullable=False)
    order_id = db.Column(db.String(100), nullable=True)

# Create DB if not exists before request
@app.before_request
def create_tables():
    if not os.path.exists("suggestions.db"):
        with app.app_context():
            db.create_all()

# Suggestion generator with variations
def generate_suggestion(weather, temp, aqi):
    suggestions = []

    # AQI based
    if aqi > 200:
        suggestions += [
            "The air quality is hazardous. Stay indoors and avoid any outdoor activity.",
            "Very unhealthy air today. Consider wearing an N95 mask if going out.",
            "Pollution levels are extremely high — best to stay inside."
        ]
    elif aqi > 150:
        suggestions += [
            "Air quality is poor, minimize outdoor exposure.",
            "Not a great day for outdoor work — pollution levels are concerning.",
            "Avoid strenuous outdoor activities, air quality isn't good."
        ]
    elif aqi > 100:
        suggestions += [
            "Air quality is moderate. Sensitive groups should take precautions.",
            "Pollution is slightly elevated, but manageable for most people.",
            "Not perfect, but okay for outdoor tasks if you're healthy."
        ]
    else:
        suggestions += [
            "Air quality is clean and fresh today — great for outdoor activities!",
            "Pollution levels are low, safe to work outside.",
            "Breathing conditions are excellent, enjoy the outdoors."
        ]

    # Temperature based
    if temp > 35:
        suggestions += [
            "It's extremely hot — stay hydrated and avoid afternoon heat.",
            "High temperature alert — schedule tasks in the early morning or evening.",
            "Scorching heat today, take breaks in shade if working outside."
        ]
    elif 28 <= temp <= 35:
        suggestions += [
            "Warm weather today — good for light outdoor tasks.",
            "Slightly hot, make sure to keep water handy.",
            "Comfortable for outdoor work if started early."
        ]
    elif 15 <= temp < 28:
        suggestions += [
            "Pleasant weather today — perfect for outdoor activities!",
            "Mild temperature makes it ideal to get tasks done outside.",
            "Nice and comfortable outside, great conditions overall."
        ]
    elif 5 <= temp < 15:
        suggestions += [
            "Chilly weather — wear warm clothes before heading out.",
            "Cold day, good for working but keep a jacket handy.",
            "Cool temperatures, stay cozy while outside."
        ]
    else:
        suggestions += [
            "Very cold! Limit outdoor exposure.",
            "Freezing conditions, dress in layers if you must go out.",
            "Dangerously low temperatures — best to avoid outdoor work."
        ]

    # Weather description based
    if "rain" in weather.lower():
        suggestions += [
            "Rain expected — don’t forget your umbrella!",
            "Showers ahead, reschedule outdoor tasks if possible.",
            "Wet conditions — be careful if traveling."
        ]
    if "clear" in weather.lower():
        suggestions += [
            "Clear skies ahead — perfect for outdoor activities.",
            "Sunny and bright today, enjoy the weather.",
            "Clear weather — ideal time to run errands outside."
        ]
    if "cloud" in weather.lower():
        suggestions += [
            "Cloudy skies, but fine for outdoor work.",
            "Overcast today — pleasant but no direct sunlight.",
            "Cloudy conditions, carry a light jacket just in case."
        ]
    if "snow" in weather.lower():
        suggestions += [
            "Snowfall expected — avoid unnecessary travel.",
            "Snowy conditions — wear proper footwear.",
            "Cold and snowy, best to stay indoors if possible."
        ]
    if "wind" in weather.lower():
        suggestions += [
            "Windy conditions — secure outdoor items.",
            "Strong winds ahead, take extra care while traveling.",
            "Breezy weather, not ideal for delicate outdoor work."
        ]

    return random.choice(suggestions)

# Home route
@app.route("/")
def home():
    return render_template("index.html")  # Make sure you have templates/index.html

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
        lat, lon = data['coord']['lat'], data['coord']['lon']

        # AQI API
        aqi_url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={API_KEY}"
        aqi_response = requests.get(aqi_url).json()
        aqi = aqi_response['list'][0]['main']['aqi'] * 50  # AQI 1–5 → scale to 50–250

        # Suggestion
        suggestion_text = generate_suggestion(weather_description, temperature, aqi)

        # Save to DB
        new_suggestion = Suggestion(
            city=city,
            weather=weather_description,
            temperature=temperature,
            aqi=aqi,
            suggestion=suggestion_text
        )
        db.session.add(new_suggestion)
        db.session.commit()

        return jsonify({
            "city": city,
            "weather": weather_description,
            "temperature": temperature,
            "aqi": aqi,
            "suggestion": suggestion_text
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# View all suggestions
@app.route("/suggestions", methods=["GET"])
def view_all_suggestions():
    suggestions = Suggestion.query.all()
    return jsonify([
        {
            "id": s.id,
            "city": s.city,
            "weather": s.weather,
            "temperature": s.temperature,
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
