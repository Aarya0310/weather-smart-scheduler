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
    suggestion = db.Column(db.String(200), nullable=False)
    order_id = db.Column(db.String(100), nullable=True)

# Create DB if not exists before request
@app.before_request
def create_tables():
    if not os.path.exists("suggestions.db"):
        with app.app_context():
            db.create_all()

# Home route (renders animated frontend)
@app.route("/")
def home():
    return render_template("index.html")  # Assumes templates/index.html exists

# Suggestion API
@app.route("/suggest", methods=["GET"])
def get_suggestion():
    city = request.args.get("city", "Bangalore")
    API_KEY = "c9e13a16efccc359520cbcfb3c11185c"  # Replace with your OpenWeatherMap API key

    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"
        response = requests.get(url)
        data = response.json()

        if 'weather' not in data or 'main' not in data:
            return jsonify({"error": "Invalid response. City may be wrong."})

        weather_description = data['weather'][0]['description']
        temperature = data['main']['temp']
        aqi = 90 if temperature > 30 else 60

        if aqi > 100:
            suggestion_text = "Avoid outdoor activities. Air quality is poor."
        elif "rain" in weather_description:
            suggestion_text = "Carry an umbrella."
        elif temperature > 35:
            suggestion_text = "Stay hydrated and avoid going out in the afternoon."
        else:
            suggestion_text = "Weather and air quality are suitable for outdoor tasks."

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
