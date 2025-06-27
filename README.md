
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

---

## **🚀 Live Deployment**

👉 [Click here to access the live app](https://weather-smart-scheduler.onrender.com)

---

## **📸 Screenshots / Demo GIF**

![Home Page Screenshot](screenshots/homepage.png)![Screenshot 2025-06-27 165530](https://github.com/user-attachments/assets/80779b21-a3d5-4faa-a8e9-517483b08285)

![Suggestion Page](screenshots/suggestion.png)![Screenshot 2025-06-27 165520](https://github.com/user-attachments/assets/152d2af7-f17c-4148-bec0-1bfd9a864852)



