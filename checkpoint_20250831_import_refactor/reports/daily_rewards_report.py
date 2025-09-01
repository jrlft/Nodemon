import requests
import smtplib
import time
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()
# reports/daily_rewards_report.py

import requests
import smtplib
import time
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

# --- CONFIGURATIONS ---
# Load environment variables from a .env file in the same directory
load_dotenv()

# Wallet and node settings
WALLET_ADDRESS = os.getenv('WALLET_ADDRESS', 'NKNGeRqGLwUrpeRRmQ4gkVBinVDSy4gRRoFj')
NODE_COUNT = int(os.getenv('NODE_COUNT', 56))

# NKN API settings
BLOCKS_TO_CHECK_24H = 5000
NKN_API_BASE_URL = 'https://openapi.nkn.org/api/v1'
DECIMALS = 1e8
REQUEST_DELAY = 0.2

# Price API (CoinGecko)
PRICE_API_URL = 'https://api.coingecko.com/api/v3/simple/price?ids=nkn&vs_currencies=usd'

# Email Credentials (using App Password for 2FA)
EMAIL_SENDER = os.getenv('EMAIL_SENDER', 'juniorluft@gmail.com')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', 'otvsxaimjommipnx') # App Password
EMAIL_RECIPIENT = os.getenv('EMAIL_RECIPIENT', 'juniorluft@gmail.com')

# --- HELPER FUNCTIONS ---

def get_nkn_price():
    """Fetches the current NKN price in USD from the CoinGecko API."""
    try:
        response = requests.get(PRICE_API_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        price = data.get('nkn', {}).get('usd')
        if price:
            print(f"Successfully fetched NKN price: ${price}")
            return float(price)
        else:
            print("Error: Could not find NKN price in API response.")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching NKN price: {e}")
        return None

def get_rewards_from_recent_blocks(wallet_address):
    """
    Searches for mining rewards by iterating through the most recent blocks.
    """
    print("Starting search for rewards in recent blocks...")
    try:
        print("Fetching the latest block height...")
        url = f"{NKN_API_BASE_URL}/blocks?per_page=1"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        latest_block_height = data['blocks']['data'][0]['header']['height']
        print(f"Latest block found: {latest_block_height}")
    except requests.exceptions.RequestException as e:
        print(f"Network error fetching latest block: {e}")
        return []
    except (KeyError, IndexError) as e:
        print(f"Error parsing API response for latest block: {e}")
        return []

    now_utc = datetime.now(timezone.utc)
    twenty_four_hours_ago = now_utc - timedelta(hours=24)
    print(f"Analyzing transactions since {twenty_four_hours_ago.strftime('%Y-%m-%d %H:%M:%S')} UTC...")
    
    rewards_found = []
    
    for i in range(latest_block_height, latest_block_height - BLOCKS_TO_CHECK_24H, -1):
        try:
            print(f"Checking transactions in block: {i}", end='\r')
            block_tx_url = f"{NKN_API_BASE_URL}/blocks/{i}/transactions"
            response = requests.get(block_tx_url, timeout=10)
            if response.status_code != 200:
                continue
            
            transactions = response.json().get('data', [])
            if not transactions:
                continue

            for tx in transactions:
                if tx.get('txType') == 'COINBASE_TYPE':
                    tx_timestamp_str = tx.get('created_at')
                    if not tx_timestamp_str:
                        continue
                    
                    tx_datetime = datetime.strptime(tx_timestamp_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
                    
                    if tx_datetime >= twenty_four_hours_ago:
                        payload = tx.get('payload', {})
                        recipient = payload.get('recipientWallet', '')
                        if recipient == wallet_address:
                            amount = payload.get('amount', 0)
                            rewards_found.append({'amount': amount})
            time.sleep(REQUEST_DELAY)
        except requests.exceptions.RequestException:
            continue
        except Exception as e:
            print(f"\nAn unexpected error occurred while processing block {i}: {e}")
            continue
            
    print(f"\nBlock search complete. {len(rewards_found)} rewards found in the period.")
    return rewards_found

def send_summary_email(summary_data):
    """Sends the summary email."""
    try:
        msg = MIMEMultipart('alternative')
        today_str = datetime.now().strftime('%d/%m/%Y')
        msg['Subject'] = f"Relatório Diário de Mineração NKN - {today_str}"
        msg['From'] = EMAIL_SENDER
        msg['To'] = EMAIL_RECIPIENT
        
        html_body = f"""
        <html>
          <head>
            <style>
              body {{ font-family: Arial, sans-serif; color: #333; }}
              .container {{ padding: 20px; border: 1px solid #ddd; border-radius: 8px; max-width: 600px; margin: auto; background-color: #f9f9f9; }}
              h2 {{ color: #007bff; }}
              .highlight {{ background-color: #e7f3fe; padding: 10px; border-radius: 5px; }}
            </style>
          </head>
          <body>
            <div class="container">
              <h2>Relatório de Mineração NKN</h2>
              <p>Este é o seu resumo de performance de mineração NKN das <strong>últimas 24 horas</strong>.</p>
              <hr>
              <div class="highlight">
                <p><strong>Total de Recompensas:</strong> {summary_data['reward_count']}</p>
                <p><strong>Total NKN Minerado:</strong> {summary_data['total_nkn']:.4f} NKN</p>
                <p><strong>Cotação Atual (USD):</strong> ${summary_data['nkn_price']:.5f}</p>
                <p><strong>Valor Total Minerado (USD):</strong> ${summary_data['total_usd']:.2f}</p>
              </div>
              <hr>
              <h3>Projeções</h3>
              <p><strong>Projeção Mensal (NKN):</strong> {summary_data['monthly_nkn_projection']:.2f} NKN</p>
              <p><strong>Projeção Mensal (USD):</strong> ${summary_data['monthly_usd_projection']:.2f}</p>
              <hr>
              <p style="font-size: 0.8em; color: #777;">
                Relatório gerado em: {summary_data['report_time']}<br>
                Carteira monitorada: {WALLET_ADDRESS}<br>
                Nós em operação: {NODE_COUNT}
              </p>
            </div>
          </body>
        </html>
        """
        msg.attach(MIMEText(html_body, 'html'))
        
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, EMAIL_RECIPIENT, msg.as_string())
        print("Summary email sent successfully!")
    except smtplib.SMTPAuthenticationError:
        print("Authentication error. Check your email and app password.")
    except Exception as e:
        print(f"An error occurred while sending the email: {e}")

# --- MAIN EXECUTION BLOCK ---
if __name__ == "__main__":
    print("--- Starting NKN Mining Monitoring Script ---")
    current_price_usd = get_nkn_price()
    if not current_price_usd:
        print("Could not get NKN price. Exiting script.")
        exit()
        
    rewards = get_rewards_from_recent_blocks(WALLET_ADDRESS)
    
    total_nkn_rewards = sum(reward.get('amount', 0) for reward in rewards)
    total_nkn_rewards_converted = total_nkn_rewards / DECIMALS
    reward_count = len(rewards)
    
    print(f"Final analysis: {reward_count} rewards found, totaling {total_nkn_rewards_converted:.4f} NKN.")
    
    total_usd_value = total_nkn_rewards_converted * current_price_usd
    monthly_nkn_projection = total_nkn_rewards_converted * 30
    monthly_usd_projection = total_usd_value * 30
    
    summary = {
        'reward_count': reward_count,
        'total_nkn': total_nkn_rewards_converted,
        'nkn_price': current_price_usd,
        'total_usd': total_usd_value,
        'monthly_nkn_projection': monthly_nkn_projection,
        'monthly_usd_projection': monthly_usd_projection,
        'report_time': datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M:%S UTC')
    }
    
    if reward_count > 0:
        send_summary_email(summary)
    else:
        print("No rewards found in the period. No email will be sent.")
        
    print("--- Monitoring Script Finished ---")
