from flask import Flask, request, redirect, url_for, render_template_string, session
from datetime import datetime, timedelta
import requests

app = Flask(__name__)
app.secret_key = "supersecreto123"  # necessário para sessões

API_KEY = "0ef953667b0b3637e0d99c6444bfcb10"
BASE_URL = "https://apiv3.apifootball.com"

# HTML do login e dashboard
LOGIN_HTML = """
<!doctype html>
<title>Login</title>
<h2>⚽ Sistema de Apostas - Login</h2>
<form method="post">
  Usuário: <input type="text" name="username"><br>
  Senha: <input type="password" name="password"><br><br>
  <input type="submit" value="Entrar">
</form>
{% if erro %}
<p style="color:red">{{ erro }}</p>
{% endif %}
"""

DASHBOARD_HTML = """
<!doctype html>
<title>Dashboard</title>
<h2>🎉 Bem-vindo, {{ user }}!</h2>
<p>Escolha uma opção:</p>
<ul>
  <li><a href="{{ url_for('today_matches') }}">Jogos de Hoje</a></li>
  <li><a href="{{ url_for('tomorrow_matches') }}">Jogos de Amanhã</a></li>
  <li><a href="{{ url_for('week_matches') }}">Jogos da Semana</a></li>
  <li><a href="{{ url_for('logout') }}">Sair</a></li>
</ul>
<pre>{{ dados|safe }}</pre>
"""

# Usuário de teste
USUARIOS = {"admin": "1234"}

def fetch(endpoint: str):
    url = f"{BASE_URL}/?APIkey={API_KEY}&{endpoint}"
    r = requests.get(url, timeout=10)
    return r.json()

def format_date(dt):
    return dt.strftime("%Y-%m-%d")

@app.route("/", methods=["GET", "POST"])
def login():
    if "user" in session:
        return redirect(url_for("dashboard"))
    
    erro = None
    if request.method == "POST":
        username = request.form.get("username")
        senha = request.form.get("password")
        if username in USUARIOS and USUARIOS[username] == senha:
            session["user"] = username
            return redirect(url_for("dashboard"))
        else:
            erro = "Usuário ou senha incorretos!"
    
    return render_template_string(LOGIN_HTML, erro=erro)

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template_string(DASHBOARD_HTML, user=session["user"], dados="Aqui você verá os dados do futebol.")

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

@app.route("/matches/today")
def today_matches():
    if "user" not in session:
        return redirect(url_for("login"))
    today = datetime.now().strftime("%Y-%m-%d")
    dados = fetch(f"action=get_events&from={today}&to={today}")
    return render_template_string(DASHBOARD_HTML, user=session["user"], dados=dados)

@app.route("/matches/tomorrow")
def tomorrow_matches():
    if "user" not in session:
        return redirect(url_for("login"))
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    dados = fetch(f"action=get_events&from={tomorrow}&to={tomorrow}")
    return render_template_string(DASHBOARD_HTML, user=session["user"], dados=dados)

@app.route("/matches/week")
def week_matches():
    if "user" not in session:
        return redirect(url_for("login"))
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    dados = fetch(f"action=get_events&from={format_date(monday)}&to={format_date(sunday)}")
    return render_template_string(DASHBOARD_HTML, user=session["user"], dados=dados)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
