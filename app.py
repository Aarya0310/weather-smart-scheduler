from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__)

# Replace with your OpenWeatherMap API key
API_KEY = "c9e13a16efccc359520cbcfb3c11185c"

# Function to get weather data
def get_weather(city):
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        weather = data["weather"][0]["description"]
        temperature = data["main"]["temp"]
        return weather, temperature
    return None, None

# Function to generate suggestion
def generate_suggestion(weather, temp):
    if "rain" in weather:
        return "Carry an umbrella ☔"
    elif "clear" in weather:
        return "Great day for outdoor activities 🌞"
    elif "cloud" in weather:
        return "It might be gloomy, keep a light jacket ☁️"
    elif "snow" in weather:
        return "Wear warm clothes ❄️"
    elif temp > 35:
        return "Stay hydrated, it’s very hot 🥵"
    elif temp < 10:
        return "Wear extra layers, it’s chilly 🧥"
    else:
        return "Normal day, enjoy your schedule 🙂"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/get_suggestions", methods=["POST"])
def get_suggestions():
    try:
        data = request.get_json()
        city = data.get("city")
        print("DEBUG: Received city =", city)

        weather, temp = get_weather(city)
        if weather is None:
            return jsonify({"error": "City not found or API error"}), 400

        suggestion = generate_suggestion(weather, temp)

        return jsonify({
            "city": city,
            "weather": weather,
            "temperature": temp,
            "suggestion": suggestion
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)

