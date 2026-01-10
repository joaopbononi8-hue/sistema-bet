def api_request(endpoint, params=None):
    """Função simples para consultar API-Football"""
    headers = {"x-apisports-key": API_KEY}
    url = f"{BASE_URL}/{endpoint}"
    r = requests.get(url, headers=headers, params=params)
    return r.json()


@app.route("/api/matches")
@login_required
def get_matches():
    tipo = request.args.get("tipo", "proximos")

    # ---- TIPOS DE CONSULTA ----
    if tipo == "proximos":
        data = api_request("fixtures", {"next": 20})

    elif tipo == "destaque":
        data = api_request("fixtures", {"next": 10})

    elif tipo == "alta-prob":
        data = api_request("fixtures", {"next": 30})

    else:
        return jsonify([])

    jogos_api = data.get("response", [])

    jogos_formatados = []
    for jogo in jogos_api:
        fixture = jogo["fixture"]
        league = jogo["league"]
        teams = jogo["teams"]

        jogos_formatados.append({
            "id": fixture["id"],
            "league": league["name"],
            "home_team": teams["home"]["name"],
            "away_team": teams["away"]["name"],
            "time": fixture["date"],
            "stats": {
                "corners": {
                    "avg": 9.2,
                    "over_line": 8.5,
                    "over_conf": 87,
                    "over_odd": 1.70,
                },
                "cards": {
                    "avg": 4.3,
                    "over_line": 3.5,
                    "over_conf": 82,
                    "over_odd": 1.65,
                }
            }
        })

    return jsonify(jogos_formatados)



@app.route("/api/update")
@login_required
def update_data():
    """Força atualização (aqui só retorna OK, você pode expandir)"""
    return jsonify({"status": "ok", "message": "Dados atualizados"})


@app.route("/api/acertos")
@login_required
def get_acertos():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT tipo_aposta, odd, confianca, resultado, data_sugestao
        FROM apostas_sugeridas
        WHERE resultado = 'certo'
        ORDER BY data_sugestao DESC
        LIMIT 50
    """)
