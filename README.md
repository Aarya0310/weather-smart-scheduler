
# 🌤️ Weather-smart-scheduler: Air Quality and Weather Integrated Task Suggestion App

This Capstone Project is a Flask-based web application that integrates **real-time weather and air quality (AQI)** data to generate smart task suggestions for users in different cities. It stores suggestions in a local database and allows mock checkout functionality.

---

## 🚀 Features

- 🔍 `/suggest?city=CityName` — Get weather, AQI, and personalized suggestion
- 📋 `/suggestions` — View all stored suggestions from database
- 🛒 `/checkout` — Simulate task checkout with order ID
- 🗃️ Local database storage using **SQLite + SQLAlchemy**

---

## 🧠 Tech Stack

- **Python 3.12**
- **Flask** (web framework)
- **Flask-SQLAlchemy** (ORM for SQLite)
- **Requests** (to fetch OpenWeatherMap API data)
- **SQLite** (lightweight local DB)

---

## ⚙️ Setup Instructions

1. **Clone this Repository:**

```bash
git clone https://github.com/your-username/smart_scheduler.git
cd smart_scheduler
