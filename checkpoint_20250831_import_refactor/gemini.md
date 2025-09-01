Title:

Node Monitoring and Management System (NKN, Sentinel, Mysterium)

Overview:

I need to build a web-based system to monitor and manage over 1000 nodes from the NKN.org project, with future support for other networks such as Sentinel and Mysterium. The system must allow nodes to be registered manually or via CSV import, storing information such as IP, Node Name, VPS Provider, Secondary IP, and Location (city/state fetched automatically using an IP geolocation API).

Reference:

Use nknx.org as inspiration, but with extended features.

Core Features:

Node Registration and Organization

Manual registration or bulk import via CSV.

Fields: IP, Node Name, wallet address, VPS Provider, Secondary IP, Location (city/state via IP lookup).

Ability to create node groups for organization.

Search and filter by IP, name, wallet, or provider.

Real-Time Monitoring

Integration with openapi.nkn.org to fetch node status (mining, syncing, offline, etc).

Display each node’s current block height (ChainDB).

Show the latest global block height at the top of the dashboard for comparison.

Send email alerts (via Gmail SMTP, sender and recipient: juniorluft@gmail.com, app password otvsxaimjommipnx).

Notify when a node goes offline or enters a critical state.

Automated Reports

Run Python script daily via Crontab to calculate mining rewards for the last 24h. 



Python script tha is working now (use as example or use the same): 



import requests import smtplib import time from email.mime.multipart import MIMEMultipart from email.mime.text import MIMEText from datetime import datetime, timedelta, timezone # --- CONFIGURAÇÕES --- # Carteira NKN a ser monitorada WALLET_ADDRESS = 'NKNGeRqGLwUrpeRRmQ4gkVBinVDSy4gRRoFj' # Número de nós em operação NODE_COUNT = 56 # Número de blocos a verificar para cobrir as últimas 24h (aprox. 4320 blocos/dia, 5000 é uma margem segura) BLOCKS_TO_CHECK_24H = 5000 # Configurações da API NKN NKN_API_BASE_URL = 'https://openapi.nkn.org/api/v1' DECIMALS = 1e8 # Fator de conversão para NKN (10^8) REQUEST_DELAY = 0.2 # Segundos de espera entre chamadas da API para evitar limites # Configurações da API de Preço (CoinGecko) PRICE_API_URL = 'https://api.coingecko.com/api/v3/simple/price?ids=nkn&vs_currencies=usd' # Credenciais de E-mail (use uma Senha de App se tiver 2FA) EMAIL_SENDER = 'juniorluft@gmail.com' EMAIL_PASSWORD = 'otvsxaimjommipnx' # Senha de App gerada EMAIL_RECIPIENT = 'juniorluft@gmail.com' # --- FUNÇÕES AUXILIARES --- def get_nkn_price(): """Busca o preço atual do NKN em USD na API do CoinGecko.""" try: response = requests.get(PRICE_API_URL, timeout=10) response.raise_for_status() data = response.json() price = data.get('nkn', {}).get('usd') if price: print(f"Preço do NKN obtido com sucesso: ${price}") return float(price) else: print("Erro: Não foi possível encontrar o preço do NKN na resposta da API.") return None except requests.exceptions.RequestException as e: print(f"Erro ao buscar o preço do NKN: {e}") return None def get_rewards_from_recent_blocks(wallet_address): """ Busca recompensas de mineração iterando através dos blocos mais recentes da blockchain. Esta versão utiliza a lógica validada pelo script de exemplo do usuário. """ print("Iniciando busca de recompensas nos blocos recentes...") # 1. Obter a altura do bloco mais recente (método correto, do script de exemplo) try: print("Buscando a altura do bloco mais recente...") url = f"{NKN_API_BASE_URL}/blocks?per_page=1" response = requests.get(url, timeout=10) response.raise_for_status() data = response.json() latest_block_height = data['blocks']['data'][0]['header']['height'] print(f"Bloco mais recente encontrado: {latest_block_height}") except requests.exceptions.RequestException as e: print(f"Erro de rede ao buscar o bloco mais recente: {e}") return [] except (KeyError, IndexError) as e: print(f"Erro ao analisar a resposta da API para o bloco mais recente: {e}") return [] # 2. Calcular o timestamp de 24 horas atrás para filtrar now_utc = datetime.now(timezone.utc) twenty_four_hours_ago = now_utc - timedelta(hours=24) print(f"Analisando transações desde {twenty_four_hours_ago.strftime('%Y-%m-%d %H:%M:%S')} UTC...") rewards_found = [] # 3. Iterar para trás a partir do bloco mais recente for i in range(latest_block_height, latest_block_height - BLOCKS_TO_CHECK_24H, -1): try: # Usar end='\r' para atualizar a mesma linha no terminal print(f"Verificando transações no bloco: {i}", end='\r') block_tx_url = f"{NKN_API_BASE_URL}/blocks/{i}/transactions" response = requests.get(block_tx_url, timeout=10) if response.status_code != 200: continue transactions = response.json().get('data', []) if not transactions: continue for tx in transactions: # CORREÇÃO CRÍTICA: Usar 'COINBASE_TYPE' e a estrutura de payload correta if tx.get('txType') == 'COINBASE_TYPE': tx_timestamp_str = tx.get('created_at') if not tx_timestamp_str: continue # A API retorna o timestamp como string, é preciso convertê-lo tx_datetime = datetime.strptime(tx_timestamp_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc) # Verificar se a transação está dentro da janela de 24 horas if tx_datetime >= twenty_four_hours_ago: payload = tx.get('payload', {}) recipient = payload.get('recipientWallet', '') # Verificar se a recompensa é para a nossa carteira if recipient == wallet_address: amount = payload.get('amount', 0) rewards_found.append({'amount': amount}) time.sleep(REQUEST_DELAY) except requests.exceptions.RequestException: # Ignorar erros de rede de blocos individuais e continuar continue except Exception as e: print(f"\nOcorreu um erro inesperado ao processar o bloco {i}: {e}") continue # Imprimir uma nova linha para não sobrescrever a última linha do contador de blocos print(f"\nBusca de blocos concluída. {len(rewards_found)} recompensas encontradas no período.") return rewards_found def send_summary_email(summary_data): """Envia o e-mail com o resumo da mineração.""" try: msg = MIMEMultipart('alternative') today_str = datetime.now().strftime('%d/%m/%Y') msg['Subject'] = f"Relatório Diário de Mineração NKN - {today_str}" msg['From'] = EMAIL_SENDER msg['To'] = EMAIL_RECIPIENT html_body = f""" <html> <head> <style> body {{ font-family: Arial, sans-serif; color: #333; }} .container {{ padding: 20px; border: 1px solid #ddd; border-radius: 8px; max-width: 600px; margin: auto; background-color: #f9f9f9; }} h2 {{ color: #007bff; }} p {{ line-height: 1.6; }} strong {{ color: #555; }} .footer {{ font-size: 0.8em; color: #777; margin-top: 20px; }} .highlight {{ background-color: #e7f3fe; padding: 10px; border-radius: 5px; }} </style> </head> <body> <div class="container"> <h2>Relatório de Mineração NKN</h2> <p>Olá! Este é o seu resumo de performance de mineração NKN das <strong>últimas 24 horas</strong>.</p> <hr> <div class="highlight"> <p><strong>Total de Recompensas:</strong> {summary_data['reward_count']}</p> <p><strong>Total NKN Minerado:</strong> {summary_data['total_nkn']:.4f} NKN</p> <p><strong>Cotação Atual (USD):</strong> ${summary_data['nkn_price']:.5f}</p> <p><strong>Valor Total Minerado (USD):</strong> ${summary_data['total_usd']:.2f}</p> </div> <hr> <h3>Projeções</h3> <p>Com base na performance das últimas 24 horas:</p> <p><strong>Projeção Mensal (NKN):</strong> {summary_data['monthly_nkn_projection']:.2f} NKN</p> <p><strong>Projeção Mensal (USD):</strong> ${summary_data['monthly_usd_projection']:.2f}</p> <hr> <p class="footer"> Relatório gerado em: {summary_data['report_time']}<br> Carteira monitorada: {WALLET_ADDRESS}<br> Nós em operação: {NODE_COUNT} </p> </div> </body> </html> """ msg.attach(MIMEText(html_body, 'html')) with smtplib.SMTP('smtp.gmail.com', 587) as server: server.starttls() server.login(EMAIL_SENDER, EMAIL_PASSWORD) server.sendmail(EMAIL_SENDER, EMAIL_RECIPIENT, msg.as_string()) print("E-mail de resumo enviado com sucesso!") except smtplib.SMTPAuthenticationError: print("Erro de autenticação. Verifique seu e-mail e senha de aplicativo.") except Exception as e: print(f"Ocorreu um erro ao enviar o e-mail: {e}") # --- BLOCO DE EXECUÇÃO PRINCIPAL --- if __name__ == "__main__": print("--- Iniciando Script de Monitoramento de Mineração NKN ---") current_price_usd = get_nkn_price() if not current_price_usd: print("Não foi possível obter o preço do NKN. O script será encerrado.") exit() rewards = get_rewards_from_recent_blocks(WALLET_ADDRESS) total_nkn_rewards = 0 for reward_tx in rewards: total_nkn_rewards += reward_tx.get('amount', 0) total_nkn_rewards_converted = total_nkn_rewards / DECIMALS reward_count = len(rewards) print(f"Análise finalizada: {reward_count} recompensas encontradas, totalizando {total_nkn_rewards_converted:.4f} NKN.") total_usd_value = total_nkn_rewards_converted * current_price_usd monthly_nkn_projection = total_nkn_rewards_converted * 30 monthly_usd_projection = total_usd_value * 30 summary = { 'reward_count': reward_count, 'total_nkn': total_nkn_rewards_converted, 'nkn_price': current_price_usd, 'total_usd': total_usd_value, 'monthly_nkn_projection': monthly_nkn_projection, 'monthly_usd_projection': monthly_usd_projection, 'report_time': datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M:%S UTC') } # Só envia o e-mail se houver recompensas, para evitar e-mails vazios if reward_count > 0: send_summary_email(summary) else: print("Nenhuma recompensa encontrada no período. Nenhum e-mail será enviado.") print("--- Script de Monitoramento Finalizado ---")



end of script above.



Generate mining summary (total NKN, USD price via CoinGecko, daily and monthly projections).

Send HTML report to the configured email.

User Interface:

Modern and responsive dashboard (dark mode).

Left sidebar menu for easy navigation.

Main screen with node list and filters.

Columns: Name, IP, Provider, Wallet, Location, Status, Current Block, Last Update.

Project separation in the menu (NKN, Sentinel, Mysterium).

Authentication:

Single admin user only.

Credentials stored in .env file (username: admin, password: Luftcia125@@).

Explain how to configure .env during deployment.

Security:

Store email credentials and authentication in .env.

Use TLS for email sending.

Technical Requirements:

Frontend: React.js / Next.js (dark mode, responsive, optimized UX).

Backend: Python (FastAPI).

Database: PostgreSQL.

Integrations:

openapi.nkn.org (node status).

IP Geolocation API.

CoinGecko API (NKN/USD price).

Gmail SMTP (alerts and reports).

Deployment:

Provide full directory structure.

Step-by-step deployment guide (preferably with Docker).

Language of the app/UX: Brazillian Portuguese



Generate in modules, frontend, backend, middle if needed, in a way that I can change the app without breaking it. i will use to monitor sentinel nodes $P2P token (do a module with what needed to monitor the nodes, get information on https://docs.sentinel.co/ and mainly dvpn nodes), and mysterium nodes $MYST token (get information to manage nodes on https://docs.mysterium.network/ for vpn nodes)
