from flask import Flask, jsonify, send_from_directory, request
import sqlite3
import os
from datetime import datetime
import requests

app = Flask(__name__, static_folder='.')

# Configuração do banco de dados
DATABASE = 'futebol.db'
API_KEY = '0ef953667b0b3637e0d99c6444bfcb10'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Inicializa o banco de dados se não existir"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Tabela de Times
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS times (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            liga TEXT,
            pais TEXT,
            data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabela de Jogos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS jogos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            time_casa_id INTEGER,
            time_fora_id INTEGER,
            data_jogo DATE,
            placar_casa INTEGER,
            placar_fora INTEGER,
            liga TEXT,
            rodada INTEGER,
            FOREIGN KEY (time_casa_id) REFERENCES times(id),
            FOREIGN KEY (time_fora_id) REFERENCES times(id)
        )
    ''')
    
    # Tabela de Estatísticas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS estatisticas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jogo_id INTEGER,
            time_id INTEGER,
            chutes_total INTEGER DEFAULT 0,
            chutes_no_gol INTEGER DEFAULT 0,
            posse_bola REAL DEFAULT 0,
            escanteios INTEGER DEFAULT 0,
            laterais INTEGER DEFAULT 0,
            faltas INTEGER DEFAULT 0,
            cartoes_amarelos INTEGER DEFAULT 0,
            cartoes_vermelhos INTEGER DEFAULT 0,
            passes_total INTEGER DEFAULT 0,
            passes_certos INTEGER DEFAULT 0,
            duelos_ganhos INTEGER DEFAULT 0,
            duelos_total INTEGER DEFAULT 0,
            FOREIGN KEY (jogo_id) REFERENCES jogos(id),
            FOREIGN KEY (time_id) REFERENCES times(id)
        )
    ''')
    
    conn.commit()
    conn.close()

@app.route('/')
def index():
    """Redireciona para o dashboard"""
    return send_from_directory('.', 'dashboard.html')

@app.route('/dashboard.html')
def dashboard():
    """Serve o dashboard"""
    return send_from_directory('.', 'dashboard.html')

@app.route('/api/matches')
def get_matches():
    """Retorna jogos do banco de dados"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Buscar todos os times
        cursor.execute('SELECT * FROM times LIMIT 20')
        times = cursor.fetchall()
        
        matches_data = []
        times_processados = set()
        
        for time in times:
            time_id = time['id']
            time_nome = time['nome']
            liga = time['liga'] or "Liga"
            
            if time_id in times_processados:
                continue
            
            # Buscar últimos jogos
            cursor.execute('''
                SELECT j.*, 
                       t1.nome as time_casa, 
                       t2.nome as time_fora
                FROM jogos j
                JOIN times t1 ON j.time_casa_id = t1.id
                JOIN times t2 ON j.time_fora_id = t2.id
                WHERE j.time_casa_id = ? OR j.time_fora_id = ?
                ORDER BY j.data_jogo DESC
                LIMIT 5
            ''', (time_id, time_id))
            jogos = cursor.fetchall()
            
            if jogos:
                ultimo_jogo = jogos[0]
                jogo_id = ultimo_jogo['id']
                
                # Calcular médias
                cursor.execute('''
                    SELECT 
                        AVG(chutes_total) as media_chutes,
                        AVG(chutes_no_gol) as media_chutes_gol,
                        AVG(CAST(chutes_no_gol AS FLOAT) / NULLIF(chutes_total, 0) * 100) as precisao,
                        AVG(escanteios) as media_escanteios,
                        AVG(cartoes_amarelos) as media_amarelos,
                        AVG(posse_bola) as media_posse
                    FROM estatisticas
                    WHERE time_id = ?
                    ORDER BY id DESC
                    LIMIT 5
                ''', (time_id,))
                
                medias = cursor.fetchone()
                
                if medias and medias['media_escanteios']:
                    match_info = {
                        'league': liga,
                        'time': ultimo_jogo['data_jogo'][:10] if ultimo_jogo['data_jogo'] else "Data",
                        'home_team': ultimo_jogo['time_casa'],
                        'away_team': ultimo_jogo['time_fora'],
                        'stats': {
                            'corners': {
                                'avg': round(medias['media_escanteios'] or 0, 1),
                                'over_line': round(max(0.5, (medias['media_escanteios'] or 0) - 2), 1),
                                'over_odd': round(1.5 + ((medias['media_escanteios'] or 0) / 10), 2),
                                'over_conf': min(95, int((medias['media_escanteios'] or 0) * 8)),
                                'under_line': round((medias['media_escanteios'] or 0) + 3, 1),
                                'under_odd': round(1.4 + ((medias['media_escanteios'] or 0) / 15), 2),
                                'under_conf': min(90, int((medias['media_escanteios'] or 0) * 6))
                            },
                            'shots_on_target': {
                                'avg': round(medias['media_chutes_gol'] or 0, 1),
                                'over_line': round(max(0.5, (medias['media_chutes_gol'] or 0) - 3), 1),
                                'over_odd': round(1.6 + ((medias['media_chutes_gol'] or 0) / 20), 2),
                                'over_conf': min(95, int(medias['precisao'] or 0)),
                                'margin': round((medias['media_chutes_gol'] or 0) - max(0.5, (medias['media_chutes_gol'] or 0) - 3), 1)
                            },
                            'cards': {
                                'avg': round(medias['media_amarelos'] or 0, 1),
                                'over_line': round(max(0.5, (medias['media_amarelos'] or 0) - 1), 1),
                                'over_odd': round(1.65 + ((medias['media_amarelos'] or 0) / 10), 2),
                                'over_conf': min(95, int((medias['media_amarelos'] or 0) * 15)),
                                'margin': round((medias['media_amarelos'] or 0) - max(0.5, (medias['media_amarelos'] or 0) - 1), 1)
                            }
                        }
                    }
                    
                    matches_data.append(match_info)
                    times_processados.add(time_id)
        
        conn.close()
        return jsonify(matches_data)
        
    except Exception as e:
        print(f"Erro ao buscar jogos: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/update', methods=['POST'])
def update_data():
    """Atualiza dados da API Football"""
    try:
        base_url = "https://v3.football.api-sports.io"
        headers = {
            'x-rapidapi-key': API_KEY,
            'x-rapidapi-host': 'v3.football.api-sports.io'
        }
        
        # Buscar jogos de hoje
        hoje = datetime.now().strftime('%Y-%m-%d')
        response = requests.get(
            f"{base_url}/fixtures",
            headers=headers,
            params={'date': hoje}
        )
        
        data = response.json()
        
        if not data.get('response'):
            return jsonify({'message': 'Nenhum jogo encontrado', 'imported': 0})
        
        conn = get_db_connection()
        cursor = conn.cursor()
        imported = 0
        
        for jogo in data['response'][:20]:  # Limitar a 20 jogos
            if jogo['fixture']['status']['short'] == 'FT':  # Só jogos finalizados
                # Adicionar times
                time_casa_nome = jogo['teams']['home']['name']
                time_fora_nome = jogo['teams']['away']['name']
                liga = jogo['league']['name']
                pais = jogo['league']['country']
                
                # Buscar ou criar time casa
                cursor.execute('SELECT id FROM times WHERE nome = ?', (time_casa_nome,))
                time_casa = cursor.fetchone()
                if not time_casa:
                    cursor.execute('INSERT INTO times (nome, liga, pais) VALUES (?, ?, ?)',
                                 (time_casa_nome, liga, pais))
                    time_casa_id = cursor.lastrowid
                else:
                    time_casa_id = time_casa['id']
                
                # Buscar ou criar time fora
                cursor.execute('SELECT id FROM times WHERE nome = ?', (time_fora_nome,))
                time_fora = cursor.fetchone()
                if not time_fora:
                    cursor.execute('INSERT INTO times (nome, liga, pais) VALUES (?, ?, ?)',
                                 (time_fora_nome, liga, pais))
                    time_fora_id = cursor.lastrowid
                else:
                    time_fora_id = time_fora['id']
                
                # Adicionar jogo
                placar_casa = jogo['goals']['home'] or 0
                placar_fora = jogo['goals']['away'] or 0
                data_jogo = jogo['fixture']['date'][:10]
                
                cursor.execute('''
                    INSERT INTO jogos (time_casa_id, time_fora_id, data_jogo, placar_casa, placar_fora, liga)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (time_casa_id, time_fora_id, data_jogo, placar_casa, placar_fora, liga))
                
                jogo_id = cursor.lastrowid
                imported += 1
                
                # Buscar estatísticas
                stats_response = requests.get(
                    f"{base_url}/fixtures/statistics",
                    headers=headers,
                    params={'fixture': jogo['fixture']['id']}
                )
                
                stats_data = stats_response.json()
                
                if stats_data.get('response'):
                    for time_stats in stats_data['response']:
                        time_id = time_casa_id if time_stats['team']['name'] == time_casa_nome else time_fora_id
                        
                        stats_dict = {
                            'chutes_total': 0,
                            'chutes_no_gol': 0,
                            'posse_bola': 0,
                            'escanteios': 0,
                            'faltas': 0,
                            'cartoes_amarelos': 0,
                            'cartoes_vermelhos': 0,
                            'passes_total': 0,
                            'passes_certos': 0
                        }
                        
                        for stat in time_stats['statistics']:
                            tipo = stat['type']
                            valor = stat['value']
                            
                            if tipo == 'Total Shots' and valor:
                                stats_dict['chutes_total'] = int(valor)
                            elif tipo == 'Shots on Goal' and valor:
                                stats_dict['chutes_no_gol'] = int(valor)
                            elif tipo == 'Ball Possession' and valor:
                                stats_dict['posse_bola'] = float(valor.replace('%', ''))
                            elif tipo == 'Corner Kicks' and valor:
                                stats_dict['escanteios'] = int(valor)
                            elif tipo == 'Fouls' and valor:
                                stats_dict['faltas'] = int(valor)
                            elif tipo == 'Yellow Cards' and valor:
                                stats_dict['cartoes_amarelos'] = int(valor)
                            elif tipo == 'Red Cards' and valor:
                                stats_dict['cartoes_vermelhos'] = int(valor)
                            elif tipo == 'Total passes' and valor:
                                stats_dict['passes_total'] = int(valor)
                            elif tipo == 'Passes accurate' and valor:
                                stats_dict['passes_certos'] = int(valor)
                        
                        cursor.execute('''
                            INSERT INTO estatisticas 
                            (jogo_id, time_id, chutes_total, chutes_no_gol, posse_bola,
                             escanteios, faltas, cartoes_amarelos, cartoes_vermelhos,
                             passes_total, passes_certos, laterais, duelos_ganhos, duelos_total)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0)
                        ''', (jogo_id, time_id, stats_dict['chutes_total'],
                              stats_dict['chutes_no_gol'], stats_dict['posse_bola'],
                              stats_dict['escanteios'], stats_dict['faltas'],
                              stats_dict['cartoes_amarelos'], stats_dict['cartoes_vermelhos'],
                              stats_dict['passes_total'], stats_dict['passes_certos']))
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': f'{imported} jogos importados com sucesso!', 'imported': imported})
        
    except Exception as e:
        print(f"Erro ao atualizar: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)