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
    humidity = db.Column(db.Float, nullable=True)
    wind_speed = db.Column(db.Float, nullable=True)
    aqi = db.Column(db.Integer, nullable=False)
    suggestion = db.Column(db.String(300), nullable=False)
    order_id = db.Column(db.String(100), nullable=True)

# Create DB if not exists before request
@app.before_request
def create_tables():
    if not os.path.exists("suggestions.db"):
        with app.app_context():
            db.create_all()

# Home route
@app.route("/")
def home():
    return render_template("index.html")  # Assumes templates/index.html exists

# Suggestion API
@app.route("/suggest", methods=["GET"])
def get_suggestion():
    city = request.args.get("city", "Bangalore")
    API_KEY = "c9e13a16efccc359520cbcfb3c11185c"  

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
        aqi = aqi_response['list'][0]['main']['aqi']  # 1=Good, 5=Very Poor

        # Rule-based + randomized suggestions
        if aqi >= 4:
            options = [
                "Air quality is very poor — best to stay indoors.",
                "Unhealthy air detected. Avoid outdoor exercise.",
                "Limit outdoor time today; pollution is high."
            ]
        elif "rain" in weather_description:
            options = [
                "Looks rainy — don’t forget your umbrella.",
                "Rain expected. Carry a raincoat if you head out.",
                "Wet weather ahead, plan accordingly!"
            ]
        elif "clear" in weather_description and temperature > 30:
            options = [
                "Hot and sunny! Stay hydrated and wear light clothes.",
                "Clear skies but high heat — avoid going out in the afternoon.",
                "Perfect for a sunny walk, just carry water."
            ]
        elif temperature < 10:
            options = [
                "Chilly weather — wear warm clothes.",
                "It’s cold outside, take a jacket with you.",
                "Bundle up, it’s freezing out there!"
            ]
        elif wind_speed > 10:
            options = [
                "It’s quite windy — secure outdoor items.",
                "Strong winds expected, be cautious outside.",
                "Windy day — avoid loose umbrellas!"
            ]
        elif humidity > 80:
            options = [
                "Humidity is high, drink plenty of water.",
                "Sticky and humid — wear breathable clothes.",
                "High humidity today, take it slow outdoors."
            ]
        else:
            options = [
                "Weather looks pleasant, enjoy your day outside!",
                "Good conditions for outdoor activities today.",
                "Mild weather — a great time to step out."
            ]

        suggestion_text = random.choice(options)

        # Save suggestion
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
    suggestions = Suggestion.query.all()
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
