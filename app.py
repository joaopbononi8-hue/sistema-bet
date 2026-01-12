from flask import Flask, jsonify, render_template_string, request, session, redirect, url_for
import sqlite3
import os
from datetime import datetime, timedelta
import requests
from functools import wraps
import time

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
            nome TEXT NOT NULL UNIQUE,
            liga TEXT,
            pais TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS jogos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fixture_id INTEGER UNIQUE,
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
        .btn-update:disabled {
            background: #ccc;
            cursor: not-allowed;
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

        /* Alert */
        .alert {
            padding: 15px 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-weight: 500;
        }
        .alert-success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .alert-error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        .alert-info {
            background: #d1ecf1;
            color: #0c5460;
            border: 1px solid #bee5eb;
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
            <button class="btn btn-update" id="btnUpdate" onclick="updateData()">🔄 Atualizar Dados</button>
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
            <div class="nav-item" onclick="showTab('stats')">
                📊 Estatísticas
            </div>
        </div>
        
        <div class="main-content">
            <div id="alertContainer"></div>
            
            <!-- Tab: Jogos em Destaque -->
            <div id="tab-destaque" class="tab-content active">
                <div class="stats-grid">
                    <div class="stat-card">
                        <h3>Total de Jogos</h3>
                        <div class="value" id="total-jogos">0</div>
                    </div>
                    <div class="stat-card">
                        <h3>Jogos Finalizados</h3>
                        <div class="value" id="jogos-finalizados">0</div>
                    </div>
                    <div class="stat-card">
                        <h3>Estatísticas Registradas</h3>
                        <div class="value" id="stats-registradas">0</div>
                    </div>
                </div>
                
                <h2 style="margin-bottom: 20px;">🔥 Jogos Recentes</h2>
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
            
            <!-- Tab: Estatísticas -->
            <div id="tab-stats" class="tab-content">
                <h2 style="margin-bottom: 20px;">📊 Estatísticas Gerais</h2>
                <div class="stats-grid">
                    <div class="stat-card">
                        <h3>Total de Times</h3>
                        <div class="value" id="total-times">0</div>
                    </div>
                    <div class="stat-card">
                        <h3>Total de Jogos</h3>
                        <div class="value" id="total-jogos-stats">0</div>
                    </div>
                    <div class="stat-card">
                        <h3>Jogos com Estatísticas</h3>
                        <div class="value" id="jogos-com-stats">0</div>
                    </div>
                    <div class="stat-card">
                        <h3>Última Atualização</h3>
                        <div class="value" style="font-size: 18px;" id="ultima-atualizacao">-</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        function showAlert(message, type = 'info') {
            const container = document.getElementById('alertContainer');
            const alert = document.createElement('div');
            alert.className = `alert alert-${type}`;
            alert.textContent = message;
            container.appendChild(alert);
            
            setTimeout(() => {
                alert.remove();
            }, 5000);
        }

        function showTab(tabName) {
            document.querySelectorAll('.nav-item').forEach(item => {
                item.classList.remove('active');
            });
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            
            event.target.classList.add('active');
            document.getElementById('tab-' + tabName).classList.add('active');
            
            loadTabData(tabName);
        }
        
        function loadTabData(tabName) {
            if (tabName === 'destaque') {
                loadMatches('destaque');
                loadStats();
            } else if (tabName === 'proximos') {
                loadMatches('proximos');
            } else if (tabName === 'alta-prob') {
                loadMatches('alta-prob');
            } else if (tabName === 'stats') {
                loadStats();
            }
        }
        
        async function loadMatches(tipo) {
            const containerId = 'matches-' + tipo;
            const container = document.getElementById(containerId);
            container.innerHTML = '<div class="loading"><div class="spinner"></div><p>Carregando jogos...</p></div>';
            
            try {
                const response = await fetch('/api/matches?tipo=' + tipo);
                const data = await response.json();
                
                if (!Array.isArray(data) || data.length === 0) {
                    container.innerHTML = `
                        <div class="empty-state">
                            <h2>Nenhum jogo encontrado</h2>
                            <p>Clique em "Atualizar Dados" para buscar jogos da API</p>
                            <p style="font-size: 12px; color: #999; margin-top: 10px;">
                                Isso pode acontecer se não houver jogos hoje ou se for necessário atualizar os dados
                            </p>
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
                            ${match.stats.shots ? `
                                <div class="bet-option">
                                    <div class="bet-info">
                                        <div class="bet-type">
                                            🎯 Chutes no Gol: Over ${match.stats.shots.over_line}
                                            <span class="confidence ${match.stats.shots.over_conf >= 85 ? 'high' : 'medium'}">
                                                ${match.stats.shots.over_conf}%
                                            </span>
                                        </div>
                                        <div class="bet-stats">
                                            Média: ${match.stats.shots.avg.toFixed(1)} | Margem: ${(match.stats.shots.avg - match.stats.shots.over_line).toFixed(1)}
                                        </div>
                                    </div>
                                    <div class="odd-badge">${match.stats.shots.over_odd}</div>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                `).join('');
                
                // Atualizar stats
                document.getElementById('total-jogos').textContent = data.length;
                
            } catch (error) {
                container.innerHTML = `
                    <div class="empty-state">
                        <h2>❌ Erro ao carregar</h2>
                        <p>${error.message}</p>
                    </div>
                `;
            }
        }
        
        async function loadStats() {
            try {
                const response = await fetch('/api/stats');
                const data = await response.json();
                
                document.getElementById('total-jogos').textContent = data.total_jogos || 0;
                document.getElementById('jogos-finalizados').textContent = data.jogos_finalizados || 0;
                document.getElementById('stats-registradas').textContent = data.stats_count || 0;
                document.getElementById('total-times').textContent = data.total_times || 0;
                document.getElementById('total-jogos-stats').textContent = data.total_jogos || 0;
                document.getElementById('jogos-com-stats').textContent = data.jogos_com_stats || 0;
                document.getElementById('ultima-atualizacao').textContent = data.ultima_atualizacao || 'Nunca';
            } catch (error) {
                console.error('Erro ao carregar estatísticas:', error);
            }
        }
        
        async function updateData() {
            const btn = document.getElementById('btnUpdate');
            btn.disabled = true;
            btn.textContent = '⏳ Atualizando...';
            
            try {
                showAlert('🔄 Buscando jogos da API-Football... Isso pode levar alguns minutos.', 'info');
                
                const response = await fetch('/api/update', { method: 'POST' });
                const data = await response.json();
                
                btn.disabled = false;
                btn.textContent = '🔄 Atualizar Dados';
                
                if (data.error) {
                    showAlert('❌ Erro: ' + data.error, 'error');
                } else {
                    showAlert('✅ ' + data.message, 'success');
                    loadMatches('destaque');
                    loadStats();
                }
            } catch (error) {
                btn.disabled = false;
                btn.textContent = '🔄 Atualizar Dados';
                showAlert('❌ Erro de conexão: ' + error.message, 'error');
            }
        }
        
        function logout() {
            if (confirm('Deseja realmente sair?')) {
                window.location.href = '/logout';
            }
        }
        
        // Carregar ao iniciar
        loadMatches('destaque');
        loadStats();
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

@app.route('/api/stats')
@login_required
def get_stats():
    """Retorna estatísticas gerais"""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Total de times
        cursor.execute('SELECT COUNT(*) FROM times')
        total_times = cursor.fetchone()[0]
        
        # Total de jogos
        cursor.execute('SELECT COUNT(*) FROM jogos')
        total_jogos = cursor.fetchone()[0]
        
        # Jogos finalizados
        cursor.execute("SELECT COUNT(*) FROM jogos WHERE status = 'finalizado'")
        jogos_finalizados = cursor.fetchone()[0]
        
        # Total de estatísticas
        cursor.execute('SELECT COUNT(*) FROM estatisticas')
        stats_count = cursor.fetchone()[0]
        
        # Jogos com estatísticas
        cursor.execute('SELECT COUNT(DISTINCT jogo_id) FROM estatisticas')
        jogos_com_stats = cursor.fetchone()[0]
        
        # Última atualização
        cursor.execute('SELECT MAX(data_jogo) FROM jogos')
        ultima = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'total_times': total_times,
            'total_jogos': total_jogos,
            'jogos_finalizados': jogos_finalizados,
            'stats_count': stats_count,
            'jogos_com_stats': jogos_com_stats,
            'ultima_atualizacao': ultima[:10] if ultima else 'Nunca'
        })
        
