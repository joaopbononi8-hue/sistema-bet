from fastapi import FastAPI
import requests
from datetime import datetime, timedelta

app = FastAPI()

API_KEY = "0ef953667b0b3637e0d99c6444bfcb10"  # coloque a sua
BASE_URL = "https://apiv3.apifootball.com"

def fetch(endpoint: str):
    url = f"{BASE_URL}/?APIkey={API_KEY}&{endpoint}"
    r = requests.get(url, timeout=10)
    return r.json()

# -------------------------------
# FUNÇÃO PARA FORMATAR DATAS
# -------------------------------
def format_date(dt):
    return dt.strftime("%Y-%m-%d")

# -------------------------------
# HOME
# -------------------------------
@app.get("/")
def root():
    return {"status": "ok", "message": "API rodando!"}

# ----------------------------------------
# PARTIDAS DE HOJE
# ----------------------------------------
@app.get("/matches/today")
def today_matches():
    today = datetime.now().strftime("%Y-%m-%d")
    return fetch(f"action=get_events&from={today}&to={today}")

# ----------------------------------------
# PARTIDAS DE AMANHÃ
# ----------------------------------------
@app.get("/matches/tomorrow")
def tomorrow_matches():
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    return fetch(f"action=get_events&from={tomorrow}&to={tomorrow}")

# ---------------------------------------------------
# PARTIDAS DA SEMANA ATUAL (SEGUNDA → DOMINGO)
# ---------------------------------------------------
@app.get("/matches/week")
def week_matches():
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())  
    sunday = monday + timedelta(days=6)

    return fetch(f"action=get_events&from={format_date(monday)}&to={format_date(sunday)}")

# ---------------------------------------------------
# PARTIDAS DA SEMANA PASSADA
# ---------------------------------------------------
@app.get("/matches/lastweek")
def last_week_matches():
    today = datetime.now()
    monday_this = today - timedelta(days=today.weekday())
    monday_last = monday_this - timedelta(days=7)
    sunday_last = monday_this - timedelta(days=1)

    return fetch(f"action=get_events&from={format_date(monday_last)}&to={format_date(sunday_last)}")

# ----------------------------------------
# PARTIDAS FUTURAS (7 DIAS À FRENTE)
# ----------------------------------------
@app.get("/matches/next")
def next_matches():
    today = datetime.now()
    future = today + timedelta(days=7)

    return fetch(f"action=get_events&from={format_date(today)}&to={format_date(future)}")
