import requests
from datetime import datetime
from db import SoccerDatabase

class APIFutebol:
    def __init__(self):
        self.api_key = "0ef953667b0b3637e0d99c6444bfcb10"
        self.base_url = "https://v3.football.api-sports.io"
        self.headers = {
            'x-rapidapi-key': self.api_key,
            'x-rapidapi-host': 'v3.football.api-sports.io'
        }
        self.db = SoccerDatabase()
    
    def buscar_jogos_hoje(self):
        """Busca todos os jogos de hoje"""
        hoje = datetime.now().strftime('%Y-%m-%d')
        url = f"{self.base_url}/fixtures"
        params = {'date': hoje}
        
        print(f"\n🔍 Buscando jogos de {hoje}...\n")
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            data = response.json()
            
            if data['response']:
                jogos = data['response']
                print(f"✅ {len(jogos)} jogos encontrados!\n")
                print("="*70)
                
                for jogo in jogos[:20]:  # Mostra primeiros 20
                    liga = jogo['league']['name']
                    pais = jogo['league']['country']
                    time_casa = jogo['teams']['home']['name']
                    time_fora = jogo['teams']['away']['name']
                    horario = jogo['fixture']['date'][11:16]
                    status = jogo['fixture']['status']['short']
                    
                    print(f"{horario} | {pais} - {liga}")
                    print(f"       {time_casa} vs {time_fora} [{status}]")
                    print("-"*70)
                
                return jogos
            else:
                print("❌ Nenhum jogo encontrado para hoje.")
                return []
                
        except Exception as e:
            print(f"❌ Erro ao buscar jogos: {e}")
            return []
    
    def buscar_jogos_liga(self, liga_id, temporada=2025):
        """Busca jogos de uma liga específica"""
        url = f"{self.base_url}/fixtures"
        params = {
            'league': liga_id,
            'season': temporada,
            'last': 20  # Últimos 20 jogos
        }
        
        print(f"\n🔍 Buscando últimos jogos da liga {liga_id}...\n")
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            data = response.json()
            
            if data['response']:
                return data['response']
            else:
                print("❌ Nenhum jogo encontrado.")
                return []
                
        except Exception as e:
            print(f"❌ Erro: {e}")
            return []
    
    def buscar_estatisticas_jogo(self, fixture_id):
        """Busca estatísticas detalhadas de um jogo"""
        url = f"{self.base_url}/fixtures/statistics"
        params = {'fixture': fixture_id}
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            data = response.json()
            
            if data['response']:
                return data['response']
            return None
            
        except Exception as e:
            print(f"❌ Erro ao buscar estatísticas: {e}")
            return None
    
    def salvar_jogo_no_banco(self, jogo_data):
        """Salva um jogo e suas estatísticas no banco"""
        try:
            # Dados do jogo
            time_casa_nome = jogo_data['teams']['home']['name']
            time_fora_nome = jogo_data['teams']['away']['name']
            liga = jogo_data['league']['name']
            pais = jogo_data['league']['country']
            
            # Buscar ou criar times
            time_casa = self.db.buscar_time_por_nome(time_casa_nome)
            if not time_casa:
                time_casa_id = self.db.adicionar_time(time_casa_nome, liga, pais)
            else:
                time_casa_id = time_casa[0]
            
            time_fora = self.db.buscar_time_por_nome(time_fora_nome)
            if not time_fora:
                time_fora_id = self.db.adicionar_time(time_fora_nome, liga, pais)
            else:
                time_fora_id = time_fora[0]
            
            # Placar
            placar_casa = jogo_data['goals']['home'] or 0
            placar_fora = jogo_data['goals']['away'] or 0
            
            # Data
            data_jogo = jogo_data['fixture']['date'][:10]
            
            # Salvar jogo
            jogo_id = self.db.adicionar_jogo(
                time_casa_id, time_fora_id, data_jogo,
                placar_casa, placar_fora, liga, None
            )
            
            # Buscar e salvar estatísticas
            fixture_id = jogo_data['fixture']['id']
            stats = self.buscar_estatisticas_jogo(fixture_id)
            
            if stats:
                for time_stats in stats:
                    time_id = time_casa_id if time_stats['team']['name'] == time_casa_nome else time_fora_id
                    
                    # Processar estatísticas
                    stats_dict = {}
                    for stat in time_stats['statistics']:
                        tipo = stat['type']
                        valor = stat['value']
                        
                        if tipo == 'Total Shots':
                            stats_dict['chutes_total'] = int(valor) if valor else 0
                        elif tipo == 'Shots on Goal':
                            stats_dict['chutes_no_gol'] = int(valor) if valor else 0
                        elif tipo == 'Ball Possession':
                            stats_dict['posse_bola'] = float(valor.replace('%', '')) if valor else 0
                        elif tipo == 'Corner Kicks':
                            stats_dict['escanteios'] = int(valor) if valor else 0
                        elif tipo == 'Fouls':
                            stats_dict['faltas'] = int(valor) if valor else 0
                        elif tipo == 'Yellow Cards':
                            stats_dict['cartoes_amarelos'] = int(valor) if valor else 0
                        elif tipo == 'Red Cards':
                            stats_dict['cartoes_vermelhos'] = int(valor) if valor else 0
                        elif tipo == 'Total passes':
                            stats_dict['passes_total'] = int(valor) if valor else 0
                        elif tipo == 'Passes accurate':
                            stats_dict['passes_certos'] = int(valor) if valor else 0
                    
                    # Preencher valores padrão
                    stats_dict.setdefault('chutes_total', 0)
                    stats_dict.setdefault('chutes_no_gol', 0)
                    stats_dict.setdefault('posse_bola', 0)
                    stats_dict.setdefault('escanteios', 0)
                    stats_dict.setdefault('laterais', 0)
                    stats_dict.setdefault('faltas', 0)
                    stats_dict.setdefault('cartoes_amarelos', 0)
                    stats_dict.setdefault('cartoes_vermelhos', 0)
                    stats_dict.setdefault('passes_total', 0)
                    stats_dict.setdefault('passes_certos', 0)
                    stats_dict.setdefault('duelos_ganhos', 0)
                    stats_dict.setdefault('duelos_total', 0)
                    
                    self.db.adicionar_estatisticas(jogo_id, time_id, stats_dict)
            
            print(f"✅ Salvo: {time_casa_nome} {placar_casa} x {placar_fora} {time_fora_nome}")
            return True
            
        except Exception as e:
            print(f"❌ Erro ao salvar jogo: {e}")
            return False
    
    def importar_jogos_finalizados_hoje(self):
        """Importa jogos finalizados de hoje para o banco"""
        jogos = self.buscar_jogos_hoje()
        
        if not jogos:
            return
        
        print("\n🔄 Importando jogos finalizados...\n")
        
        contador = 0
        for jogo in jogos:
            status = jogo['fixture']['status']['short']
            
            # Só importa jogos finalizados
            if status == 'FT':
                if self.salvar_jogo_no_banco(jogo):
                    contador += 1
        
        print(f"\n🎉 {contador} jogos importados com sucesso!")
    
    def listar_ligas_disponiveis(self):
        """Lista as principais ligas disponíveis"""
        ligas = {
            39: "Premier League (Inglaterra)",
            140: "La Liga (Espanha)",
            78: "Bundesliga (Alemanha)",
            135: "Serie A (Itália)",
            61: "Ligue 1 (França)",
            71: "Brasileirão Série A",
            94: "Primeira Liga (Portugal)",
            88: "Eredivisie (Holanda)",
            203: "Super Lig (Turquia)",
            235: "Premier League (Rússia)"
        }
        
        print("\n⚽ LIGAS DISPONÍVEIS:")
        print("="*50)
        for id_liga, nome in ligas.items():
            print(f"{id_liga:3d} - {nome}")
        print("="*50)
        
        return ligas

# MENU PRINCIPAL
if __name__ == '__main__':
    api = APIFutebol()
    
    print("\n⚽ API FUTEBOL - IMPORTADOR DE DADOS REAIS\n")
    print("1 - Ver jogos de hoje")
    print("2 - Importar jogos finalizados de hoje")
    print("3 - Ver ligas disponíveis")
    print("4 - Buscar jogos de uma liga")
    print("5 - Sair")
    
    opcao = input("\nEscolha: ").strip()
    
    if opcao == '1':
        api.buscar_jogos_hoje()
    
    elif opcao == '2':
        api.importar_jogos_finalizados_hoje()
    
    elif opcao == '3':
        api.listar_ligas_disponiveis()
    
    elif opcao == '4':
        api.listar_ligas_disponiveis()
        liga_id = input("\nDigite o ID da liga: ").strip()
        if liga_id.isdigit():
            jogos = api.buscar_jogos_liga(int(liga_id))
            print(f"\n✅ {len(jogos)} jogos encontrados!")
    
    else:
        print("👋 Até logo!")