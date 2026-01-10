from flask import Flask, jsonify
import requests
from datetime import datetime, timedelta

app = Flask(__name__)

API_KEY = "0ef953667b0b3637e0d99c6444bfcb10"
BASE_URL = "https://apiv3.apifootball.com"

def fetch(endpoint: str):
    url = f"{BASE_URL}/?APIkey={API_KEY}&{endpoint}"
    r = requests.get(url, timeout=10)
    return r.json()

def format_date(dt):
    return dt.strftime("%Y-%m-%d")

@app.route("/")
def root():
    return jsonify({"status": "ok", "message": "API rodando!"})

@app.route("/matches/today")
def today_matches():
    today = datetime.now().strftime("%Y-%m-%d")
    return jsonify(fetch(f"action=get_events&from={today}&to={today}"))

@app.route("/matches/tomorrow")
def tomorrow_matches():
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    return jsonify(fetch(f"action=get_events&from={tomorrow}&to={tomorrow}"))

@app.route("/matches/week")
def week_matches():
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)

    return jsonify(fetch(
        f"action=get_events&from={format_date(monday)}&to={format_date(sunday)}"
    ))

@app.route("/matches/lastweek")
def last_week_matches():
    today = datetime.now()
    monday_this = today - timedelta(days=today.weekday())
    monday_last = monday_this - timedelta(days=7)
    sunday_last = monday_this - timedelta(days=1)

    return jsonify(fetch(
        f"action=get_events&from={format_date(monday_last)}&to={format_date(sunday_last)}"
    ))

@app.route("/matches/next")
def next_matches():
    today = datetime.now()
    future = today + timedelta(days=7)

    return jsonify(fetch(
        f"action=get_events&from={format_date(today)}&to={format_date(future)}"
    ))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
