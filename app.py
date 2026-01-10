from flask import Flask, jsonify, render_template_string, request
import sqlite3
import os
from datetime import datetime
import requests

app = Flask(__name__)

# Configuração
DATABASE = 'futebol.db'
API_KEY = '0ef953667b0b3637e0d99c6444bfcb10'
BASE_URL = "https://v3.football.api-sports.io"

# HTML do Dashboard (embutido)
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>⚽ Sistema de Apostas</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%);
            color: #fff;
            min-height: 100vh;
        }
        .header {
            background: #1a7f37;
            padding: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .btn-update {
            background: #fff;
            color: #1a7f37;
            border: none;
            padding: 12px 25px;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
            font-size: 14px;
        }
        .btn-update:hover { background: #f0f0f0; }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        .status {
            background: #2d2d2d;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            text-align: center;
        }
        .loading {
            text-align: center;
            padding: 50px;
            font-size: 18px;
            color: #1a7f37;
        }
        .match-card {
            background: #2d2d2d;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 15px;
            border-left: 4px solid #1a7f37;
        }
        .teams {
            font-size: 20px;
            font-weight: bold;
            margin-bottom: 15px;
            text-align: center;
        }
        .bet-option {
            background: #1a1a1a;
            padding: 15px;
            margin: 10px 0;
            border-radius: 8px;
        }
        .confidence {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: bold;
            background: #1a7f37;
            margin-left: 10px;
        }
        .error {
            background: #dc2626;
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>⚽ Sistema de Apostas Esportivas</h1>
        <button class="btn-update" onclick="updateData()">🔄 Buscar Jogos Reais</button>
    </div>

    <div class="container">
        <div class="status" id="status">
            <p>Aguardando atualização... Clique em "Buscar Jogos Reais"</p>
        </div>
        
        <div id="matches"></div>
    </div>

    <script>
        async function updateData() {
            const statusDiv = document.getElementById('status');
            const matchesDiv = document.getElementById('matches');
            
            statusDiv.innerHTML = '<p class="loading">🔄 Buscando jogos da API-Football...</p>';
            matchesDiv.innerHTML = '';
            
            try {
                const response = await fetch('/api/update', { method: 'POST' });
                const data = await response.json();
                
                if (data.error) {
                    statusDiv.innerHTML = `<p class="error">❌ Erro: ${data.error}</p>`;
                    return;
                }
                
                statusDiv.innerHTML = `<p style="color: #1a7f37;">✅ ${data.imported} jogos importados com sucesso!</p>`;
                loadMatches();
                
            } catch (error) {
                statusDiv.innerHTML = `<p class="error">❌ Erro ao conectar: ${error.message}</p>`;
            }
        }
        
        async function loadMatches() {
            const matchesDiv = document.getElementById('matches');
            matchesDiv.innerHTML = '<p class="loading">Carregando jogos...</p>';
            
            try {
                const response = await fetch('/api/matches');
                const data = await response.json();
                
                // Verificar se é um array
                if (!Array.isArray(data)) {
                    matchesDiv.innerHTML = '<p style="text-align:center; color:#aaa;">Nenhum jogo encontrado. Clique em "Buscar Jogos Reais"</p>';
                    return;
                }
                
                if (data.length === 0) {
                    matchesDiv.innerHTML = '<p style="text-align:center; color:#aaa;">Nenhum jogo encontrado. Clique em "Buscar Jogos Reais"</p>';
                    return;
                }
                
                matchesDiv.innerHTML = data.map(match => `
                    <div class="match-card">
                        <div class="teams">${match.home_team} vs ${match.away_team}</div>
                        <div><strong>Liga:</strong> ${match.league}</div>
                        ${match.stats.corners ? `
                            <div class="bet-option">
                                <strong>🚩 Escanteios:</strong> 
                                Over ${match.stats.corners.over_line} 
                                <span class="confidence">${match.stats.corners.over_conf}%</span>
                                <br><small>Média: ${match.stats.corners.avg.toFixed(1)} | Odd: ${match.stats.corners.over_odd}</small>
                            </div>
                        ` : ''}
                        ${match.stats.cards ? `
                            <div class="bet-option">
                                <strong>🟨 Cartões:</strong> 
                                Over ${match.stats.cards.over_line}
                                <span class="confidence">${match.stats.cards.over_conf}%</span>
                                <br><small>Média: ${match.stats.cards.avg.toFixed(1)} | Odd: ${match.stats.cards.over_odd}</small>
                            </div>
                        ` : ''}
                    </div>
                `).join('');
                
            } catch (error) {
                matchesDiv.innerHTML = `<p class="error">❌ Erro ao carregar: ${error.message}</p>`;
            }
        }
        
        // Carregar jogos ao iniciar
        loadMatches();
    </script>
</body>
</html>
"""

def init_db():
    """Inicializa o banco de dados"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS times (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            liga TEXT,
            pais TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS jogos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            time_casa_id INTEGER,
            time_fora_id INTEGER,
            data_jogo DATE,
            placar_casa INTEGER,
            placar_fora INTEGER,
            liga TEXT,
            FOREIGN KEY (time_casa_id) REFERENCES times(id),
            FOREIGN KEY (time_fora_id) REFERENCES times(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS estatisticas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jogo_id INTEGER,
            time_id INTEGER,
            escanteios INTEGER DEFAULT 0,
            chutes_total INTEGER DEFAULT 0,
            chutes_no_gol INTEGER DEFAULT 0,
            cartoes_amarelos INTEGER DEFAULT 0,
            cartoes_vermelhos INTEGER DEFAULT 0,
            FOREIGN KEY (jogo_id) REFERENCES jogos(id),
            FOREIGN KEY (time_id) REFERENCES times(id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Banco de dados inicializado!")

@app.before_request
def before_first_request():
    """Inicializa DB antes da primeira requisição"""
    if not os.path.exists(DATABASE):
        init_db()

@app.route('/')
def index():
    """Página principal"""
    return render_template_string(DASHBOARD_HTML)

@app.route('/api/matches')
def get_matches():
    """Retorna jogos do banco"""
    try:
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM times LIMIT 20')
        times = cursor.fetchall()
        
        matches_data = []
        
        for time in times:
            time_id = time['id']
            
            cursor.execute('''
                SELECT j.*, t1.nome as time_casa, t2.nome as time_fora
                FROM jogos j
                JOIN times t1 ON j.time_casa_id = t1.id
                JOIN times t2 ON j.time_fora_id = t2.id
                WHERE j.time_casa_id = ? OR j.time_fora_id = ?
                ORDER BY j.data_jogo DESC
                LIMIT 3
            ''', (time_id, time_id))
            
            jogos = cursor.fetchall()
            
            if jogos:
                jogo = jogos[0]
                
                cursor.execute('''
                    SELECT AVG(escanteios) as media_escanteios,
                           AVG(cartoes_amarelos) as media_amarelos
                    FROM estatisticas
                    WHERE time_id = ?
                    LIMIT 5
                ''', (time_id,))
                
                medias = cursor.fetchone()
                
                if medias and medias['media_escanteios']:
                    matches_data.append({
                        'league': jogo['liga'] or 'Liga',
                        'home_team': jogo['time_casa'],
                        'away_team': jogo['time_fora'],
                        'stats': {
                            'corners': {
                                'avg': medias['media_escanteios'],
                                'over_line': round(max(0.5, medias['media_escanteios'] - 2), 1),
                                'over_odd': round(1.6 + (medias['media_escanteios'] / 10), 2),
                                'over_conf': min(90, int(medias['media_escanteios'] * 8))
                            },
                            'cards': {
                                'avg': medias['media_amarelos'],
                                'over_line': round(max(0.5, medias['media_amarelos'] - 1), 1),
                                'over_odd': round(1.7 + (medias['media_amarelos'] / 10), 2),
                                'over_conf': min(90, int(medias['media_amarelos'] * 12))
                            }
                        }
                    })
        
        conn.close()
        return jsonify(matches_data)
        
    except Exception as e:
        print(f"Erro: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/update', methods=['POST'])
def update_data():
    """Atualiza dados da API"""
    try:
        headers = {
            'x-rapidapi-key': API_KEY,
            'x-rapidapi-host': 'v3.football.api-sports.io'
        }
        
        hoje = datetime.now().strftime('%Y-%m-%d')
        response = requests.get(
            f"{BASE_URL}/fixtures",
            headers=headers,
            params={'date': hoje},
            timeout=10
        )
        
        data = response.json()
        
        if not data.get('response'):
            return jsonify({'message': 'Nenhum jogo hoje', 'imported': 0})
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        imported = 0
        
        for jogo in data['response'][:10]:
            if jogo['fixture']['status']['short'] != 'FT':
                continue
            
            time_casa = jogo['teams']['home']['name']
            time_fora = jogo['teams']['away']['name']
            liga = jogo['league']['name']
            
            cursor.execute('SELECT id FROM times WHERE nome = ?', (time_casa,))
            result = cursor.fetchone()
            if result:
                time_casa_id = result[0]
            else:
                cursor.execute('INSERT INTO times (nome, liga, pais) VALUES (?, ?, ?)',
                             (time_casa, liga, jogo['league']['country']))
                time_casa_id = cursor.lastrowid
            
            cursor.execute('SELECT id FROM times WHERE nome = ?', (time_fora,))
            result = cursor.fetchone()
            if result:
                time_fora_id = result[0]
            else:
                cursor.execute('INSERT INTO times (nome, liga, pais) VALUES (?, ?, ?)',
                             (time_fora, liga, jogo['league']['country']))
                time_fora_id = cursor.lastrowid
            
            cursor.execute('''
                INSERT INTO jogos (time_casa_id, time_fora_id, data_jogo, placar_casa, placar_fora, liga)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (time_casa_id, time_fora_id, jogo['fixture']['date'][:10],
                  jogo['goals']['home'] or 0, jogo['goals']['away'] or 0, liga))
            
            jogo_id = cursor.lastrowid
            
            # Buscar estatísticas
            stats_resp = requests.get(
                f"{BASE_URL}/fixtures/statistics",
                headers=headers,
                params={'fixture': jogo['fixture']['id']},
                timeout=10
            )
            
            stats_data = stats_resp.json()
            
            if stats_data.get('response'):
                for team_stats in stats_data['response']:
                    time_id = time_casa_id if team_stats['team']['name'] == time_casa else time_fora_id
                    
                    escanteios = 0
                    cartoes = 0
                    chutes = 0
                    chutes_gol = 0
                    
                    for stat in team_stats['statistics']:
                        if stat['type'] == 'Corner Kicks' and stat['value']:
                            escanteios = int(stat['value'])
                        elif stat['type'] == 'Yellow Cards' and stat['value']:
                            cartoes = int(stat['value'])
                        elif stat['type'] == 'Total Shots' and stat['value']:
                            chutes = int(stat['value'])
                        elif stat['type'] == 'Shots on Goal' and stat['value']:
                            chutes_gol = int(stat['value'])
                    
                    cursor.execute('''
                        INSERT INTO estatisticas (jogo_id, time_id, escanteios, chutes_total, 
                                                chutes_no_gol, cartoes_amarelos)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (jogo_id, time_id, escanteios, chutes, chutes_gol, cartoes))
            
            imported += 1
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': f'{imported} jogos importados!', 'imported': imported})
        
    except Exception as e:
        print(f"Erro: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)