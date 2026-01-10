from flask import Flask, request, jsonify, redirect, make_response, send_file
import requests
from datetime import datetime, timedelta

app = Flask(__name__)

API_KEY = "0ef953667b0b3637e0d99c6444bfcb10"
BASE_URL = "https://apiv3.apifootball.com"

# -------------------------------
# LOGIN CONFIG
# -------------------------------
USERNAME = "admin"
PASSWORD = "1234"

def logged_in(req):
    return req.cookies.get("auth") == "ok"

# -------------------------------
# FUNÇÃO API
# -------------------------------
def fetch(endpoint: str):
    url = f"{BASE_URL}/?APIkey={API_KEY}&{endpoint}"
    r = requests.get(url, timeout=10)
    return r.json()

def format_date(dt):
    return dt.strftime("%Y-%m-%d")

# -------------------------------
# ROTA LOGIN (FORM HTML AQUI MESMO)
# -------------------------------
@app.route("/login", methods=["GET"])
def login_page():
    html = """
    <html>
    <head><title>Login</title></head>
    <body style="font-family: Arial; background: #111; color: #fff; padding: 40px;">
        <h2>Login</h2>
        <form method="POST" action="/login">
            <label>Usuário:</label><br>
            <input name="username" style="padding:8px;"><br><br>
            <label>Senha:</label><br>
            <input name="password" type="password" style="padding:8px;"><br><br>
            <button type="submit" style="padding:10px 20px;">Entrar</button>
        </form>
    </body>
    </html>
    """
    return html

# -------------------------------
# LOGIN SUBMIT
# -------------------------------
@app.route("/login", methods=["POST"])
def login_submit():
    user = request.form.get("username")
    pw = request.form.get("password")

    if user == USERNAME and pw == PASSWORD:
        resp = make_response(redirect("/"))
        resp.set_cookie("auth", "ok", max_age=60*60*24*7)  # 7 dias logado
        return resp
    else:
        return "<h3>Login incorreto</h3>"

# -------------------------------
# DESLOGAR
# -------------------------------
@app.route("/logout")
def logout():
    resp = make_response(redirect("/login"))
    resp.delete_cookie("auth")
    return resp

# -------------------------------
# HOME → precisa estar logado
# -------------------------------
@app.route("/")
def home():
    if not logged_in(request):
        return redirect("/login")

    return send_file("dashboard.html")

# -------------------------------
# ROTAS DAS PARTIDAS
# -------------------------------
@app.route("/matches/today")
def today_matches():
    if not logged_in(request):
        return redirect("/login")
    today = datetime.now().strftime("%Y-%m-%d")
    return jsonify(fetch(f"action=get_events&from={today}&to={today}"))

@app.route("/matches/tomorrow")
def tomorrow_matches():
    if not logged_in(request):
        return redirect("/login")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    return jsonify(fetch(f"action=get_events&from={tomorrow}&to={tomorrow}"))

@app.route("/matches/week")
def week_matches():
    if not logged_in(request):
        return redirect("/login")

    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)

    return jsonify(fetch(
        f"action=get_events&from={format_date(monday)}&to={format_date(sunday)}"
    ))

@app.route("/matches/lastweek")
def last_week_matches():
    if not logged_in(request):
        return redirect("/login")

    today = datetime.now()
    monday_this = today - timedelta(days=today.weekday())
    monday_last = monday_this - timedelta(days=7)
    sunday_last = monday_this - timedelta(days=1)

    return jsonify(fetch(
        f"action=get_events&from={format_date(monday_last)}&to={format_date(sunday_las_
