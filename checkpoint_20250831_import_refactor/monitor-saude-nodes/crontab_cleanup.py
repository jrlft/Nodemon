#!/usr/bin/env python3
"""
Crontab Cleanup Script
----------------------

Este script se conecta a uma lista de servidores para limpar o crontab,
 garantindo que apenas a entrada correta para o nkn_health_monitor exista,
 e então reinicia a VPS.

"""

import paramiko
import time

def get_servers():
    """Lê a lista de servidores do arquivo servers.txt."""
    try:
        with open("servers.txt", "r") as f:
            servers = f.readlines()
        
        valid_servers = []
        for line in servers:
            line = line.strip()
            if not line or "," not in line:
                continue
            ip, password = line.split(",", 1)
            valid_servers.append((ip.strip(), password.strip()))
        return valid_servers
    except FileNotFoundError:
        print("❌ Arquivo servers.txt não encontrado.")
        return []

def cleanup_server_crontab(ip, password):
    """Conecta a um servidor, limpa o crontab e reinicia."""
    print(f"\n🚀 Processando {ip}...")
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(ip, username="root", password=password, timeout=15)

        # Comando para remover todas as entradas antigas e garantir que a correta exista
        correct_job = "*/10 * * * * /opt/nkn-monitor/venv/bin/python /opt/nkn-monitor/nkn_health_monitor.py >> /opt/nkn-monitor/cron.log 2>&1"
        
        # Usamos `grep -v` para remover todas as linhas que contenham os padrões antigos/incorretos
        # e então adicionamos a linha correta. Isso garante a idempotência.
        cleanup_command = f'''(crontab -l 2>/dev/null || true | grep -v "nkn_health_monitor.py" | grep -v "nkn-monitor/monitor.sh"; echo "{correct_job}") | crontab -'''

        print(f"   - Limpando crontab em {ip}...")
        stdin, stdout, stderr = client.exec_command(cleanup_command)
        exit_code = stdout.channel.recv_exit_status()

        if exit_code != 0:
            print(f"   ⚠️  Falha ao limpar o crontab em {ip}.")
            print(stderr.read().decode())
            client.close()
            return
        
        print(f"   ✅ Crontab limpo com sucesso.")

        # Reiniciar a VPS
        print(f"   - Enviando comando de reinicialização para {ip}...")
        try:
            client.exec_command("reboot", timeout=5) # Timeout curto, pois a conexão cairá
        except Exception:
            # É esperado que a conexão caia, então ignoramos exceções aqui
            pass
        
        print(f"   ✅ Comando de reinicialização enviado.")
        client.close()

    except Exception as e:
        print(f"❌ Erro ao conectar ou processar {ip}: {e}")

def main():
    print("--- INICIANDO SCRIPT DE LIMPEZA DE CRONTAB ---")
    servers = get_servers()
    if not servers:
        print("Nenhum servidor para processar. Encerrando.")
        return

    print(f"{len(servers)} servidores para limpar.")
    resp = input("Este script irá limpar o crontab e REINICIAR cada servidor. Deseja continuar? (s/N): ").strip().lower()
    if resp not in ['s', 'sim', 'y', 'yes']:
        print("Operação cancelada pelo usuário.")
        return

    for ip, password in servers:
        cleanup_server_crontab(ip, password)
        time.sleep(2) # Pausa entre os servidores
    
    print("\n🎉 Limpeza concluída em todos os servidores.")

if __name__ == "__main__":
    main()
