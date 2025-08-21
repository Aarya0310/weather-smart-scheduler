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
    aqi = db.Column(db.Integer, nullable=False)
    suggestion = db.Column(db.String(300), nullable=False)
    order_id = db.Column(db.String(100), nullable=True)

# Create DB if not exists
@app.before_request
def create_tables():
    if not os.path.exists("suggestions.db"):
        with app.app_context():
            db.create_all()

# Home route
@app.route("/")
def home():
    return render_template("index.html")

# City-specific rules
CITY_RULES = {
    "Bangalore": "Traffic is heavy, so plan tasks in the morning or evening.",
    "Delhi": "AQI is usually high, limit outdoor exposure.",
    "Mumbai": "Humidity is high, carry water.",
    "Chennai": "Sun is strong, avoid afternoon outdoor tasks.",
    "Pune": "Weather is pleasant, good for most activities."
}

# Generate suggestion
def generate_suggestion(city, weather, temp, aqi):
    city_rule = CITY_RULES.get(city, "")

    if aqi > 150:
        return f"Air quality is poor in {city}. {city_rule}"
    elif "rain" in weather.lower():
        return f"Rain expected in {city}, carry an umbrella. {city_rule}"
    elif temp > 35:
        return f"Very hot in {city}, stay hydrated. {city_rule}"
    elif temp < 10:
        return f"Cold weather in {city}, wear warm clothes. {city_rule}"
    else:
        return f"Weather and air quality are suitable in {city}. {city_rule}"

# Suggestion API
@app.route("/suggest", methods=["GET"])
def get_suggestion():
    city = request.args.get("city", "Bangalore")
    API_KEY = "c9e13a16efccc359520cbcfb3c11185c"  # Replace with your OpenWeatherMap API key

    try:
        # Weather API
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"
        response = requests.get(url).json()

        if 'weather' not in response or 'main' not in response:
            return jsonify({"error": "Invalid city or API response."})

        weather_description = response['weather'][0]['description']
        temperature = response['main']['temp']
        lat, lon = response['coord']['lat'], response['coord']['lon']

        # AQI API
        aqi_url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={API_KEY}"
        aqi_response = requests.get(aqi_url).json()
        aqi = aqi_response['list'][0]['main']['aqi'] * 50  # AQI 1–5 → scale to 50–250

        # Generate better suggestion
        suggestion_text = generate_suggestion(city, weather_description, temperature, aqi)

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
