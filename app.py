from flask import Flask, render_template, request, jsonify
import requests
import random

app = Flask(__name__)

# Replace with your actual OpenWeatherMap API key
API_KEY = "c9e13a16efccc359520cbcfb3c11185c"
WEATHER_URL = "http://api.openweathermap.org/data/2.5/weather"

# Function to fetch weather data
def get_weather(city):
    params = {
        "q": city,
        "appid": API_KEY,
        "units": "metric"
    }
    response = requests.get(WEATHER_URL, params=params)
    if response.status_code == 200:
        data = response.json()
        weather = data["weather"][0]["description"]
        temperature = data["main"]["temp"]
        return weather, temperature
    return None, None

# Function to generate suggestion based on city + weather
def generate_suggestion(city, weather, temperature, aqi):
    suggestions = []

    if "rain" in weather.lower():
        suggestions.append("Carry an umbrella if heading out.")
        suggestions.append("Good time to do indoor activities.")
    elif "clear" in weather.lower():
        suggestions.append("Perfect day for outdoor tasks.")
        suggestions.append("Consider exercising outside.")
    elif "cloud" in weather.lower():
        suggestions.append("Good for casual walks or light outdoor work.")
        suggestions.append("Keep a jacket handy, might get cooler.")
    elif "storm" in weather.lower():
        suggestions.append("Better to stay indoors, avoid travel.")
        suggestions.append("Ensure electronic devices are safe from power surges.")
    elif "snow" in weather.lower():
        suggestions.append("Dress warmly before going outside.")
        suggestions.append("Indoor reading or work is ideal.")
    else:
        suggestions.append("Conditions are moderate, proceed with planned activities.")

    # Add AQI-related advice
    if aqi > 150:
        suggestions.append("Air quality is poor. Avoid outdoor physical activity.")
    elif aqi > 80:
        suggestions.append("Air quality is moderate. Sensitive groups take precautions.")
    else:
        suggestions.append("Air quality is good for outdoor activities.")

    # Pick a random suggestion so each city feels dynamic
    return random.choice(suggestions)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/get_suggestions", methods=["POST"])
def get_suggestions():
    city = request.form.get("city")
    if not city:
        return jsonify({"error": "City is required"}), 400

    weather, temperature = get_weather(city)
    if weather is None:
        return jsonify({"error": "City not found"}), 404

    # Simulated AQI (for demo), you can connect to real AQI API later
    aqi = random.randint(30, 180)

    suggestion = generate_suggestion(city, weather, temperature, aqi)

    return jsonify({
        "city": city,
        "weather": weather,
        "temperature": temperature,
        "aqi": aqi,
        "suggestion": suggestion
    })

if __name__ == "__main__":
    app.run(debug=True)
