from flask import Flask, jsonify, render_template_string, request, session, redirect, url_for
import sqlite3
import os
from datetime import datetime, timedelta
import requests
from functools import wraps

app = Flask(__name__)
app.secret_key = 'sua-chave-secreta-super-segura-123'

DATABASE = 'futebol.db'
API_KEY = '0ef953667b0b3637e0d99c6444bfcb10'
BASE_URL = "https://v3.football.api-sports.io"
ADMIN_USER = 'admin'
ADMIN_PASS = '123456'

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
            data_jogo DATETIME,
            placar_casa INTEGER,
            placar_fora INTEGER,
            liga TEXT,
            status TEXT DEFAULT 'agendado',
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
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS apostas_sugeridas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jogo_id INTEGER,
            tipo_aposta TEXT,
            linha REAL,
            odd REAL,
            confianca INTEGER,
            resultado TEXT DEFAULT 'pendente',
            data_sugestao DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (jogo_id) REFERENCES jogos(id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Banco de dados inicializado!")

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# HTML - Login Page
LOGIN_HTML = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - Sistema de Apostas</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #1a7f37 0%, #134d24 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .login-container {
            background: white;
            padding: 40px;
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            width: 100%;
            max-width: 400px;
        }
        .logo {
            text-align: center;
            margin-bottom: 30px;
        }
        .logo h1 {
            color: #1a7f37;
            font-size: 28px;
            margin-bottom: 5px;
        }
        .logo p {
            color: #666;
            font-size: 14px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            color: #333;
            font-weight: 500;
            margin-bottom: 8px;
        }
        input {
            width: 100%;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-size: 14px;
            transition: border 0.3s;
        }
        input:focus {
            outline: none;
            border-color: #1a7f37;
        }
        .btn-login {
            width: 100%;
            padding: 14px;
            background: #1a7f37;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: background 0.3s;
        }
        .btn-login:hover {
            background: #145c2a;
        }
        .error {
            background: #fee;
            color: #c33;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 20px;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="logo">
            <h1>⚽ Sistema de Apostas</h1>
            <p>Análise Profissional de Jogos</p>
        </div>
        
        {% if error %}
        <div class="error">{{ error }}</div>
        {% endif %}
        
        <form method="POST">
            <div class="form-group">
                <label>Usuário</label>
                <input type="text" name="username" placeholder="Digite seu usuário" required autofocus>
            </div>
            
            <div class="form-group">
                <label>Senha</label>
                <input type="password" name="password" placeholder="Digite sua senha" required>
            </div>
            
            <button type="submit" class="btn-login">Entrar</button>
        </form>
    </div>
</body>
</html>
"""

# HTML - Dashboard Principal
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard - Sistema de Apostas</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', sans-serif;
            background: #f5f5f5;
            color: #333;
        }
        
        /* Header */
        .header {
            background: linear-gradient(135deg, #1a7f37 0%, #145c2a 100%);
            color: white;
            padding: 20px 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header h1 {
            font-size: 24px;
        }
        .header-actions {
            display: flex;
            gap: 15px;
            align-items: center;
        }
        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.3s;
        }
        .btn-update {
            background: white;
            color: #1a7f37;
        }
        .btn-update:hover {
            background: #f0f0f0;
        }
        .btn-logout {
            background: rgba(255,255,255,0.2);
            color: white;
        }
        .btn-logout:hover {
            background: rgba(255,255,255,0.3);
        }
        
        /* Layout */
        .container {
            display: flex;
            min-height: calc(100vh - 80px);
        }
        
        /* Sidebar */
        .sidebar {
            width: 250px;
            background: white;
            box-shadow: 2px 0 10px rgba(0,0,0,0.05);
            padding: 20px 0;
        }
        .nav-item {
            padding: 15px 25px;
            cursor: pointer;
            transition: all 0.3s;
            border-left: 3px solid transparent;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .nav-item:hover {
            background: #f5f5f5;
            border-left-color: #1a7f37;
        }
        .nav-item.active {
            background: #e8f5e9;
            border-left-color: #1a7f37;
            color: #1a7f37;
            font-weight: 600;
        }
        
        /* Main Content */
        .main-content {
            flex: 1;
            padding: 30px;
            overflow-y: auto;
        }
        
        /* Stats Cards */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }
        .stat-card h3 {
            color: #666;
            font-size: 14px;
            font-weight: 500;
            margin-bottom: 10px;
        }
        .stat-card .value {
            font-size: 32px;
            font-weight: bold;
            color: #1a7f37;
        }
        
        /* Match Cards */
        .match-card {
            background: white;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 15px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            transition: transform 0.3s;
        }
        .match-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }
        .match-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            padding-bottom: 15px;
            border-bottom: 1px solid #eee;
        }
        .league-badge {
            background: #1a7f37;
            color: white;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }
        .teams {
            font-size: 18px;
            font-weight: bold;
            text-align: center;
            margin-bottom: 15px;
        }
        .bet-options {
            display: grid;
            gap: 10px;
        }
        .bet-option {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .bet-info {
            flex: 1;
        }
        .bet-type {
            font-weight: 600;
            margin-bottom: 5px;
        }
        .bet-stats {
            font-size: 12px;
            color: #666;
        }
        .confidence {
            display: inline-block;
            padding: 5px 12px;
            border-radius: 15px;
            font-size: 12px;
            font-weight: bold;
            margin-left: 10px;
        }
        .confidence.high {
            background: #1a7f37;
            color: white;
        }
        .confidence.medium {
            background: #ffa726;
            color: white;
        }
        .odd-badge {
            background: #333;
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: bold;
        }
        
        /* Empty State */
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            background: white;
            border-radius: 10px;
        }
        .empty-state h2 {
            color: #1a7f37;
            margin-bottom: 15px;
        }
        .empty-state p {
            color: #666;
            margin-bottom: 25px;
        }
        
        /* Loading */
        .loading {
            text-align: center;
            padding: 40px;
        }
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #1a7f37;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            animation: spin 1s linear infinite;
            margin: 20px auto;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        /* Tabs Content */
        .tab-content {
            display: none;
        }
        .tab-content.active {
            display: block;
        }
        
        @media (max-width: 768px) {
            .container {
                flex-direction: column;
            }
            .sidebar {
                width: 100%;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>⚽ Sistema de Apostas - Dashboard</h1>
        <div class="header-actions">
            <button class="btn btn-update" onclick="updateData()">🔄 Atualizar Dados</button>
            <button class="btn btn-logout" onclick="logout()">🚪 Sair</button>
        </div>
    </div>
    
    <div class="container">
        <div class="sidebar">
            <div class="nav-item active" onclick="showTab('destaque')">
                🔥 Jogos em Destaque
            </div>
            <div class="nav-item" onclick="showTab('proximos')">
                ⏰ Próximos Jogos
            </div>
            <div class="nav-item" onclick="showTab('alta-prob')">
                🎯 Alta Probabilidade
            </div>
            <div class="nav-item" onclick="showTab('acertos')">
                ✅ Análises Certas
            </div>
            <div class="nav-item" onclick="showTab('erros')">
                ❌ Análises Erradas
            </div>
            <div class="nav-item" onclick="showTab('stats')">
                📊 Estatísticas
            </div>
        </div>
        
        <div class="main-content">
            <!-- Tab: Jogos em Destaque -->
            <div id="tab-destaque" class="tab-content active">
                <div class="stats-grid">
                    <div class="stat-card">
                        <h3>Total de Jogos</h3>
                        <div class="value" id="total-jogos">0</div>
                    </div>
                    <div class="stat-card">
                        <h3>Sugestões Hoje</h3>
                        <div class="value" id="sugestoes-hoje">0</div>
                    </div>
                    <div class="stat-card">
                        <h3>Taxa de Acerto</h3>
                        <div class="value" id="taxa-acerto">0%</div>
                    </div>
                </div>
                
                <h2 style="margin-bottom: 20px;">🔥 Jogos em Destaque</h2>
                <div id="matches-destaque"></div>
            </div>
            
            <!-- Tab: Próximos Jogos -->
            <div id="tab-proximos" class="tab-content">
                <h2 style="margin-bottom: 20px;">⏰ Próximos Jogos</h2>
                <div id="matches-proximos"></div>
            </div>
            
            <!-- Tab: Alta Probabilidade -->
            <div id="tab-alta-prob" class="tab-content">
                <h2 style="margin-bottom: 20px;">🎯 Alta Probabilidade (85%+)</h2>
                <div id="matches-alta-prob"></div>
            </div>
            
            <!-- Tab: Acertos -->
            <div id="tab-acertos" class="tab-content">
                <h2 style="margin-bottom: 20px;">✅ Análises que Bateram</h2>
                <div id="acertos-list"></div>
            </div>
            
            <!-- Tab: Erros -->
            <div id="tab-erros" class="tab-content">
                <h2 style="margin-bottom: 20px;">❌ Análises que Não Bateram</h2>
                <div id="erros-list"></div>
            </div>
            
            <!-- Tab: Estatísticas -->
            <div id="tab-stats" class="tab-content">
                <h2 style="margin-bottom: 20px;">📊 Estatísticas Gerais</h2>
                <div class="stats-grid">
                    <div class="stat-card">
                        <h3>Total de Apostas Sugeridas</h3>
                        <div class="value" id="total-apostas">0</div>
                    </div>
                    <div class="stat-card">
                        <h3>Apostas Certas</h3>
                        <div class="value" style="color: #28a745;" id="apostas-certas">0</div>
                    </div>
                    <div class="stat-card">
                        <h3>Apostas Erradas</h3>
                        <div class="value" style="color: #dc3545;" id="apostas-erradas">0</div>
                    </div>
                    <div class="stat-card">
                        <h3>Taxa de Acerto Geral</h3>
                        <div class="value" id="taxa-geral">0%</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        function showTab(tabName) {
            // Remove active de todos
            document.querySelectorAll('.nav-item').forEach(item => {
                item.classList.remove('active');
            });
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            
            // Adiciona active no clicado
            event.target.classList.add('active');
            document.getElementById('tab-' + tabName).classList.add('active');
            
            // Carrega dados específicos da aba
            loadTabData(tabName);
        }
        
        function loadTabData(tabName) {
            if (tabName === 'destaque') {
                loadMatches('destaque');
            } else if (tabName === 'proximos') {
                loadMatches('proximos');
            } else if (tabName === 'alta-prob') {
                loadMatches('alta-prob');
            } else if (tabName === 'acertos') {
                loadAcertos();
            } else if (tabName === 'erros') {
                loadErros();
            } else if (tabName === 'stats') {
                loadStats();
            }
        }
        
        async function loadMatches(tipo) {
            const containerId = 'matches-' + tipo;
            const container = document.getElementById(containerId);
            container.innerHTML = '<div class="loading"><div class="spinner"></div><p>Carregando...</p></div>';
            
            try {
                const response = await fetch('/api/matches?tipo=' + tipo);
                const data = await response.json();
                
                if (!Array.isArray(data) || data.length === 0) {
                    container.innerHTML = `
                        <div class="empty-state">
                            <h2>Nenhum jogo encontrado</h2>
                            <p>Clique em "Atualizar Dados" para buscar jogos</p>
                        </div>
                    `;
                    return;
                }
                
                container.innerHTML = data.map(match => `
                    <div class="match-card">
                        <div class="match-header">
                            <span class="league-badge">${match.league}</span>
                            <span style="color: #666; font-size: 14px;">${match.time || 'Data TBD'}</span>
                        </div>
                        <div class="teams">${match.home_team} vs ${match.away_team}</div>
                        <div class="bet-options">
                            ${match.stats.corners ? `
                                <div class="bet-option">
                                    <div class="bet-info">
                                        <div class="bet-type">
                                            🚩 Escanteios: Over ${match.stats.corners.over_line}
                                            <span class="confidence ${match.stats.corners.over_conf >= 85 ? 'high' : 'medium'}">
                                                ${match.stats.corners.over_conf}%
                                            </span>
                                        </div>
                                        <div class="bet-stats">
                                            Média: ${match.stats.corners.avg.toFixed(1)} | Margem: ${(match.stats.corners.avg - match.stats.corners.over_line).toFixed(1)}
                                        </div>
                                    </div>
                                    <div class="odd-badge">${match.stats.corners.over_odd}</div>
                                </div>
                            ` : ''}
                            ${match.stats.cards ? `
                                <div class="bet-option">
                                    <div class="bet-info">
                                        <div class="bet-type">
                                            🟨 Cartões: Over ${match.stats.cards.over_line}
                                            <span class="confidence ${match.stats.cards.over_conf >= 85 ? 'high' : 'medium'}">
                                                ${match.stats.cards.over_conf}%
                                            </span>
                                        </div>
                                        <div class="bet-stats">
                                            Média: ${match.stats.cards.avg.toFixed(1)} | Margem: ${(match.stats.cards.avg - match.stats.cards.over_line).toFixed(1)}
                                        </div>
                                    </div>
                                    <div class="odd-badge">${match.stats.cards.over_odd}</div>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                `).join('');
                
                // Atualizar stats
                document.getElementById('total-jogos').textContent = data.length;
                
            } catch (error) {
                container.innerHTML = `<div class="empty-state"><h2>Erro ao carregar</h2><p>${error.message}</p></div>`;
            }
        }
        
        async function loadAcertos() {
            document.getElementById('acertos-list').innerHTML = '<div class="empty-state"><p>Em desenvolvimento...</p></div>';
        }
        
        async function loadErros() {
            document.getElementById('erros-list').innerHTML = '<div class="empty-state"><p>Em desenvolvimento...</p></div>';
        }
        
        async function loadStats() {
            // Stats já carregadas
        }
        
        async function updateData() {
            if (!confirm('Isso vai buscar novos jogos da API-Football. Continuar?')) return;
            
            try {
                const response = await fetch('/api/update', { method: 'POST' });
                const data = await response.json();
                alert(data.message || 'Dados atualizados!');
                loadMatches('destaque');
            } catch (error) {
                alert('Erro: ' + error.message);
            }
        }
        
        function logout() {
            if (confirm('Deseja realmente sair?')) {
                window.location.href = '/logout';
            }
        }
        
        // Carregar ao iniciar
        loadMatches('destaque');
    </script>
</body>
</html>
"""

@app.before_request
def before_first_request():
    """Inicializa DB antes da primeira requisição"""
    if not os.path.exists(DATABASE):
        init_db()

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Página de login"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == ADMIN_USER and password == ADMIN_PASS:
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            return render_template_string(LOGIN_HTML, error='Usuário ou senha inválidos')
    
    return render_template_string(LOGIN_HTML)

@app.route('/logout')
def logout():
    """Logout"""
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    """Dashboard principal"""
    return render_template_string(DASHBOARD_HTML)

@app.route('/api/matches')
@login_required
def get_matches():
    """Retorna jogos do banco"""
    tipo = request.args.get('tipo', 'destaque')
    
    try:
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT DISTINCT j.id, j.*, t1.nome as time_casa, t2.nome as time_fora
            FROM jogos j
            JOIN times t1 ON j.time_casa_id = t1.id
            JOIN times t2 ON j.time_fora_id = t2.id
            ORDER BY j.data_jogo DESC
            LIMIT 50
        ''')
        
        jogos = cursor.fetchall()
        matches_data = []
        
        for jogo in jogos:
            jogo_id = jogo['id']
            time_casa_id = jogo['time_casa_id']
            time_fora_id = jogo['time_fora_id']
            
            cursor.execute('''
                SELECT AVG(escanteios) as media_escanteios,
                       AVG(cartoes_amarelos) as media_amarelos
                FROM estatisticas
                WHERE time_id IN (?, ?)
            ''', (time_casa_id, time_fora_id))
            
            medias = cursor.fetchone()
            
            if medias and medias['media_escanteios']:
                media_escanteios = medias['media_escanteios']
                media_amarelos = medias['media_amarelos']
                conf_escanteios = min(92, int(media_escanteios * 8))
                conf_cartoes = min(88, int(media_amarelos * 12))
                
                # Filtro por tipo
                if tipo == 'alta-prob' and conf_escanteios < 85 and conf_cartoes < 85:
                    continue
                
                matches_data.append({
                    'league': jogo['liga'] or 'Liga',
                    'home_team': jogo['time_casa'],
                    'away_team': jogo['time_fora'],
                    'time': str(jogo['data_jogo'])[:10] if jogo['data_jogo'] else '',
                    'stats': {
                        'corners': {
                            'avg': media_escanteios,
                            'over_line': round(max(0.5, media_escanteios - 2), 1),
                            'over_odd': round(1.6 + (media_escanteios / 10), 2),
                            'over_conf': conf_escanteios
                        },
                        'cards': {
                            'avg': media_amarelos,
                            'over_line': round(max(0.5, media_amarelos - 1), 1),
                            'over_odd': round(1.7 + (media_amarelos / 10), 2),
                            'over_conf': conf_cartoes
                        }
                    }
                })
        
        conn.close()
        return jsonify(matches_data)
        
    except Exception as e:
        print(f"Erro: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/update', methods=['POST'])
@login_required
def update_data():
    try:
        headers = {'x-rapidapi-key': API_KEY, 'x-rapidapi-host': 'v3.football.api-sports.io'}
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        imported = 0
        data_inicio = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        data_fim = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        data_atual = datetime.strptime(data_inicio, '%Y-%m-%d')
        data_final = datetime.strptime(data_fim, '%Y-%m-%d')
        dias_processados = 0
        max_dias = 10
        
        while data_atual <= data_final and dias_processados < max_dias:
            data_str = data_atual.strftime('%Y-%m-%d')
            response = requests.get(f"{BASE_URL}/fixtures", headers=headers, params={'date': data_str}, timeout=10)
            data = response.json()
            
            if data.get('response'):
                for jogo in data['response'][:5]:
                    status_jogo = jogo['fixture']['status']['short']
                    if status_jogo not in ['FT', 'NS', '1H', '2H', 'HT']:
                        continue
                    
                    time_casa = jogo['teams']['home']['name']
                    time_fora = jogo['teams']['away']['name']
                    liga = jogo['league']['name']
                    
                    cursor.execute('SELECT id FROM times WHERE nome = ?', (time_casa,))
                    result = cursor.fetchone()
                    time_casa_id = result[0] if result else None
                    if not time_casa_id:
                        cursor.execute('INSERT INTO times (nome, liga, pais) VALUES (?, ?, ?)', (time_casa, liga, jogo['league']['country']))
                        time_casa_id = cursor.lastrowid
                    
                    cursor.execute('SELECT id FROM times WHERE nome = ?', (time_fora,))
                    result = cursor.fetchone()
                    time_fora_id = result[0] if result else None
                    if not time_fora_id:
                        cursor.execute('INSERT INTO times (nome, liga, pais) VALUES (?, ?, ?)', (time_fora, liga, jogo['league']['country']))
                        time_fora_id = cursor.lastrowid
                    
                    status_bd = 'finalizado' if status_jogo == 'FT' else 'agendado'
                    cursor.execute('INSERT INTO jogos (time_casa_id, time_fora_id, data_jogo, placar_casa, placar_fora, liga, status) VALUES (?, ?, ?, ?, ?, ?, ?)',
                                 (time_casa_id, time_fora_id, jogo['fixture']['date'], jogo['goals']['home'] or 0, jogo['goals']['away'] or 0, liga, status_bd))
                    jogo_id = cursor.lastrowid
                    
                    if status_jogo == 'FT':
                        stats_resp = requests.get(f"{BASE_URL}/fixtures/statistics", headers=headers, params={'fixture': jogo['fixture']['id']}, timeout=10)
                        stats_data = stats_resp.json()
                        if stats_data.get('response'):
                            for team_stats in stats_data['response']:
                                time_id = time_casa_id if team_stats['team']['name'] == time_casa else time_fora_id
                                escanteios = cartoes = chutes = chutes_gol = 0
                                for stat in team_stats['statistics']:
                                    if stat['type'] == 'Corner Kicks' and stat['value']: escanteios = int(stat['value'])
                                    elif stat['type'] == 'Yellow Cards' and stat['value']: cartoes = int(stat['value'])
                                    elif stat['type'] == 'Total Shots' and stat['value']: chutes = int(stat['value'])
                                    elif stat['type'] == 'Shots on Goal' and stat['value']: chutes_gol = int(stat['value'])
                                cursor.execute('INSERT INTO estatisticas (jogo_id, time_id, escanteios, chutes_total, chutes_no_gol, cartoes_amarelos) VALUES (?, ?, ?, ?, ?, ?)',
                                             (jogo_id, time_id, escanteios, chutes, chutes_gol, cartoes))
                    imported += 1
            
            data_atual += timedelta(days=1)
            dias_processados += 1
        
        conn.commit()
        conn.close()
        return jsonify({'message': f'{imported} jogos importados!', 'imported': imported})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
        
if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
