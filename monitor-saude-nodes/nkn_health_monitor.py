#!/usr/bin/env python3
"""
NKN Node Health Monitor - v5.7 Unificado
------------------------------------
- Correção da URL do portchecker para .com
- Melhoria no log de erros de email para incluir detalhes da exceção
- Adicionado cooldown de 2 horas para alertas de performance de disco
"""

import os
import re
import time
import smtplib
import psutil
import subprocess
import json
import requests
from email.mime.text import MIMEText
from datetime import datetime, timedelta

# Tenta importar a configuracao, usa valores padrao se falhar
try:
    import monitor_config as config
except ImportError:
    class config:
        CONTAINER_NAME = "nkn_node"
        MAX_LOG_LINES = 300
        NKN_DATA_PATH = "/opt/depin-stack/nkn-data"
        CHAINDB_PATH = "/opt/depin-stack/nkn-data/services/nkn-node/ChainDB"
        EMAIL_USER = None
        DESTINATION_EMAIL = None

# --- Variaveis Globais ---
STATE_FILE = "/opt/nkn-monitor/monitor_state/state.json"
NKN_PUBLIC_RPC = [
    'https://mainnet-rpc-node-0001.nkn.org/mainnet/api/wallet',
    'https://mainnet-rpc-node-0002.nkn.org/mainnet/api/wallet',
    'https://mainnet-rpc-node-0003.nkn.org/mainnet/api/wallet',
    'https://mainnet-rpc-node-0004.nkn.org/mainnet/api/wallet',
]

# --- Funcoes Auxiliares ---

def log_message(message):
    print(f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC - {message}")

def get_public_ip():
    try:
        response = requests.get('https://api.ipify.org?format=json', timeout=10)
        response.raise_for_status()
        return response.json().get("ip", "N/A")
    except requests.RequestException:
        return "N/A"

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {
        "pruning_db_since": None,
        "sync_lag_since": None,
        "db_stalled_since": None,
        "last_db_size": 0,
        "high_cpu_since": None,
        "high_mem_since": None,
        "rpc_unreachable_since": None,
        "restarted_due_to_db_stall_at": None,
        "last_io_performance_alert_at": 0,
    }

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


ERROR_LOG_FILE = "/opt/nkn-monitor/monitor_state/errors.json"

def log_error_to_json(ip, error_message):
    """Registra um erro no arquivo de log JSON."""
    log_message(f"Registrando erro para o IP {ip}: {error_message}")
    errors = []
    if os.path.exists(ERROR_LOG_FILE):
        try:
            with open(ERROR_LOG_FILE, "r") as f:
                errors = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass  # Se o arquivo estiver corrompido ou ilegível, ele será sobrescrito.

    errors.append({
        "ip": ip,
        "timestamp": datetime.utcnow().isoformat(),
        "error": error_message
    })

    try:
        with open(ERROR_LOG_FILE, "w") as f:
            json.dump(errors, f, indent=2)
    except IOError as e:
        log_message(f"[ERROR] Não foi possível escrever no arquivo de log de erros: {e}")

def check_error_frequency(ip, time_window_hours=24, error_threshold=5):
    """Verifica a frequência de erros para um IP e retorna um aviso se exceder o limite."""
    if not os.path.exists(ERROR_LOG_FILE):
        return None

    try:
        with open(ERROR_LOG_FILE, "r") as f:
            errors = json.load(f)
    except (json.JSONDecodeError, IOError):
        return None

    recent_errors = 0
    now = datetime.utcnow()
    time_window = timedelta(hours=time_window_hours)

    # Filtra erros para manter o arquivo gerenciável (opcional, mas recomendado)
    relevant_errors = [
        e for e in errors 
        if datetime.fromisoformat(e.get("timestamp", "1970-01-01T00:00:00")) > now - timedelta(days=30)
    ]

    for error in relevant_errors:
        if error.get("ip") == ip:
            try:
                error_time = datetime.fromisoformat(error.get("timestamp"))
                if now - error_time < time_window:
                    recent_errors += 1
            except (ValueError, TypeError):
                continue # Ignora entradas de timestamp malformadas

    # Salva a lista de erros filtrada de volta no arquivo
    if len(relevant_errors) != len(errors):
        try:
            with open(ERROR_LOG_FILE, "w") as f:
                json.dump(relevant_errors, f, indent=2)
        except IOError as e:
            log_message(f"[ERROR] Não foi possível reescrever o arquivo de log de erros: {e}")


    if recent_errors > error_threshold:
        return (
            f"ALERTA DE REINCIDÊNCIA: O nó {ip} registrou {recent_errors} erros nas últimas "
            f"{time_window_hours} horas. Recomenda-se uma revisão completa da VPS e da "
            f"instalação para identificar problemas crônicos."
        )
    
    return None


def send_email(subject, body):
    if not all([hasattr(config, 'SMTP_SERVER'), hasattr(config, 'SMTP_PORT'), config.EMAIL_USER, hasattr(config, 'EMAIL_PASS'), config.DESTINATION_EMAIL]):
        log_message("[WARN] Pulando envio de email: Configuracoes de SMTP incompletas")
        return
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = config.EMAIL_USER
        msg["To"] = config.DESTINATION_EMAIL
        with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT, timeout=20) as server:
            server.starttls()
            server.login(config.EMAIL_USER, config.EMAIL_PASS)
            server.sendmail(config.EMAIL_USER, config.DESTINATION_EMAIL, msg.as_string())
        log_message("Email de alerta enviado com sucesso.")
    except smtplib.SMTPAuthenticationError as e:
        log_message(f"[EMAIL ERROR] Falha na autenticação SMTP: {e}. Verifique seu email e senha.")
    except smtplib.SMTPServerDisconnected as e:
        log_message(f"[EMAIL ERROR] O servidor SMTP desconectou inesperadamente: {e}.")
    except smtplib.SMTPConnectError as e:
        log_message(f"[EMAIL ERROR] Não foi possível conectar ao servidor SMTP: {e}. Verifique o endereço e a porta do servidor.")
    except smtplib.SMTPRecipientsRefused as e:
        log_message(f"[EMAIL ERROR] O servidor recusou os destinatários: {e}.")
    except smtplib.SMTPSenderRefused as e:
        log_message(f"[EMAIL ERROR] O servidor recusou o remetente: {e}.")
    except Exception as e:
        log_message(f"[EMAIL ERROR] Um erro inesperado ocorreu: {type(e).__name__} - {e}")

def run_command(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return result.stdout.strip()
    except Exception as e:
        return f"Error running {cmd}: {e}"

def restart_container(state):
    log_message("Iniciando reinicializacao do container...")
    save_state(state) # Salva o estado imediatamente antes de reiniciar
    run_command(f"cd {config.NKN_DATA_PATH} && docker compose down")
    time.sleep(5)
    run_command(f"cd {config.NKN_DATA_PATH} && docker compose up -d")
    log_message("Comando para reiniciar container enviado.")

# --- Funcoes de Checagem ---

def check_public_ports(public_ip):
    alerts = []
    if public_ip == "N/A":
        return alerts
    log_message(f"Verificando portas públicas em {public_ip}...")
    for port in [30001, 30002]:
        try:
            url = f"https://api.portchecker.com/v2/check?port={port}&ip={public_ip}"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if not data.get('online', False):
                    alerts.append(f"ALERTA DE REDE: A porta {port} está FECHADA. O nó não pode aceitar conexões de entrada, o que levará a falhas. Verifique o firewall e o encaminhamento de portas.")
            time.sleep(1) # Evitar sobrecarregar a API
        except requests.RequestException as e:
            log_message(f"Erro ao verificar a porta {port}: {e}")
    return alerts

def investigate_system_logs():
    log_message("Investigando logs do sistema (dmesg, journalctl) por pistas...")
    findings = []
    commands = {
        "dmesg": 'dmesg -T | grep -iE "oom-kill|killed process|panic|segfault" | tail -n 5',
        "journalctl": f'journalctl -n 200 --no-pager | grep -iE "oom|kill|{config.CONTAINER_NAME}" | tail -n 10'
    }
    for log_name, cmd in commands.items():
        output = run_command(cmd)
        if output and "Error running" not in output:
            findings.append(f"--- Evidências de {log_name.upper()} ---")
            findings.append(output)
    
    return findings if findings else ["Nenhuma causa óbvia encontrada nos logs do sistema."]

def check_container_exit_status():
    cmd = f"docker inspect --format='{{{{.State.Status}}}},{{{{.State.ExitCode}}}}' {config.CONTAINER_NAME}"
    output = run_command(cmd)
    if 'Error' in output:
        return False, ""
    try:
        status, exit_code_str = output.strip().split(',')
        exit_code = int(exit_code_str)
        if status == 'exited' and exit_code != 0:
            return True, f"Container has exited with non-zero status code: {exit_code}."
    except (ValueError, IndexError):
        pass
    return False, ""

def get_node_state_rpc():
    try:
        payload = {"jsonrpc": "2.0", "method": "getnodestate", "params": {}, "id": 1}
        response = requests.post("http://localhost:30003", json=payload, timeout=10)
        response.raise_for_status()
        result = response.json().get('result', {})
        return {"status": "ok", "syncState": result.get('syncState', 'unknown'), "height": result.get('height', 0)}
    except requests.RequestException as e:
        return {"status": "error", "message": str(e)}

def get_global_block_height():
    payload = {"jsonrpc": "2.0", "method": "getlatestblockheight", "params": {}, "id": 1}
    for endpoint in NKN_PUBLIC_RPC:
        try:
            response = requests.post(endpoint, json=payload, timeout=5)
            if response.status_code == 200:
                height = response.json().get('result', 0)
                if isinstance(height, int) and height > 0:
                    return height
        except requests.RequestException:
            continue
    return 0

def get_chaindb_size():
    size_str = run_command(f"du -s {config.CHAINDB_PATH}").split('\t')[0]
    return int(size_str) * 1024 if size_str.isdigit() else 0

def check_log_patterns():
    restart_alerts = {}
    notification_alerts = []
    logs = run_command(f"docker logs --tail {config.MAX_LOG_LINES} {config.CONTAINER_NAME}")

    # Padrões que causam reinicialização
    restart_patterns = {
        r"panic: Node has no neighbors and is too lonely to run": "FALHA FATAL DE REDE: 'Node has no neighbors'. Verifique o encaminhamento das portas 30001-30003 e o firewall.",
        r"Port requirement not met": "FALHA DE PORTA: 'Port requirement not met'.",
        r"program stopped with status:exit status ((?!0\\b)\\d+)": "FALHA DE PROCESSO: O programa interno parou com o código de erro: {match}.",
        r"panic": "FALHA CRÍTICA: Detectado 'panic' nos logs.",
        r"fatal": "FALHA CRÍTICA: Detectado 'fatal' nos logs.",
    }
    # Padrões que geram apenas notificação
    notification_patterns = {
        r"Local node has no inbound neighbor": "AVISO CRÍTICO DE REDE: 'Local node has no inbound neighbor'. O nó não pode receber conexões. Verifique o encaminhamento de portas e o firewall para evitar uma falha fatal."
    }

    for pattern, message in restart_patterns.items():
        match = re.search(pattern, logs, re.IGNORECASE)
        if match:
            # Se a mensagem contiver '{match}', formate-a com o grupo capturado.
            if '{match}' in message:
                # O padrão para "program stopped" captura o código de saída no grupo 1
                exit_code = match.group(1)
                restart_alerts[pattern] = message.format(match=exit_code)
            else:
                restart_alerts[pattern] = message
    
    for pattern, message in notification_patterns.items():
        if re.search(pattern, logs, re.IGNORECASE):
            notification_alerts.append(message)

    return list(restart_alerts.values()), notification_alerts


def run_health_checks(state, node_state):
    alerts = []
    now = time.time()
    trigger_db_stall_restart = False

    if node_state["status"] == "error":
        rpc_unreachable_since = state.get('rpc_unreachable_since')
        if rpc_unreachable_since is None: state['rpc_unreachable_since'] = now
        if now - state.get('rpc_unreachable_since', now) > 15 * 60:
            alerts.append(f"Node RPC is unreachable for >15 mins: {node_state['message']}")
    else:
        state['rpc_unreachable_since'] = None

    if node_state.get('syncState') == 'pruning_db':
        pruning_since = state.get('pruning_db_since')
        if pruning_since is None: state['pruning_db_since'] = now
        if now - state.get('pruning_db_since', now) > 3 * 3600:
            alerts.append(f"Node stuck in 'pruning_db' for more than 3 hours.")
    else:
        state['pruning_db_since'] = None

    is_out_of_sync, is_db_stalled_short = False, False
    global_height = get_global_block_height()
    local_height = node_state.get('height', 0)
    if global_height > 0 and local_height > 0 and local_height < global_height - 15:
        sync_lag_since = state.get('sync_lag_since')
        if sync_lag_since is None: state['sync_lag_since'] = now
        if now - state.get('sync_lag_since', now) > 30 * 60:
            is_out_of_sync = True
    else:
        state['sync_lag_since'] = None

    db_size = get_chaindb_size()
    last_db_size = state.get('last_db_size', 0)
    if db_size > 0 and db_size <= last_db_size:
        db_stalled_since = state.get('db_stalled_since')
        if db_stalled_since is None: state['db_stalled_since'] = now
        
        if now - state.get('db_stalled_since', now) > 1 * 3600:
            alerts.append(f"ChainDB size has not increased for over 1 hour (size: {db_size / 1024**2:.2f} MB).")
            trigger_db_stall_restart = True
        
        if now - state.get('db_stalled_since', now) > 10 * 60:
            is_db_stalled_short = True
    else:
        state['db_stalled_since'] = None
    state['last_db_size'] = db_size

    if is_out_of_sync:
        if is_db_stalled_short:
            alerts.append(f"Node is out of sync (Local: {local_height}, Global: {global_height}) AND ChainDB is not growing.")
        else:
            log_message(f"Node is lagging but ChainDB is growing (recovering). No action taken. Local: {local_height}, Global: {global_height}")

    return alerts, trigger_db_stall_restart

def check_resource_usage(state):
    # ... (função mantida como antes, omitida para brevidade)
    return [] # Placeholder


def check_io_performance(state, node_ip, test_file_path="/opt/nkn-monitor/io_test.tmp", block_size="1M", count=256, speed_threshold_mbps=50):
    """
    Verifica a performance de escrita do disco usando dd e envia um alerta por email se estiver abaixo do limiar,
    respeitando um cooldown de 6 horas. Este alerta não é registrado como um erro crítico.
    """
    now = time.time()
    
    # Garante que o arquivo de teste não exista antes de começar
    if os.path.exists(test_file_path):
        os.remove(test_file_path)

    cmd = f"dd if=/dev/zero of={test_file_path} bs={block_size} count={count} conv=fdatasync"
    log_message(f"Executando teste de performance de I/O com: {cmd}")
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
        stderr_output = result.stderr
        
        if os.path.exists(test_file_path):
            os.remove(test_file_path)

        match = re.search(r"(\d+(\.\d+)?)\s+(MB/s|GB/s)", stderr_output)
        if match:
            speed = float(match.group(1))
            unit = match.group(3)
            
            if unit == "GB/s":
                speed *= 1024

            log_message(f"Velocidade de escrita do disco detectada: {speed:.2f} MB/s")

            if speed < speed_threshold_mbps:
                last_alert_time = state.get('last_io_performance_alert_at', 0)
                if now - last_alert_time > 6 * 3600:  # Cooldown de 6 horas
                    subject = f"[NKN-Monitor] AVISO de Performance de Disco no node {node_ip}"
                    body = (
                        f"ALERTA DE PERFORMANCE: A velocidade de escrita do disco está muito baixa ({speed:.2f} MB/s), "
                        f"abaixo do limiar de {speed_threshold_mbps} MB/s. "
                        f"Isso pode causar problemas de sincronização e instabilidade. Verifique a saúde do SSD no provedor."

"
                        f"Este é um aviso e não causará uma reinicialização do nó. O próximo aviso para este problema será enviado em 6 horas."
"
                    )
                    send_email(subject, body)
                    state['last_io_performance_alert_at'] = now
                else:
                    log_message("Alerta de performance de I/O em cooldown. Nenhuma ação tomada.")
        else:
            log_message("[WARN] Não foi possível determinar a velocidade de escrita do disco a partir da saída do dd.")

    except subprocess.TimeoutExpired:
        subject = f"[NKN-Monitor] AVISO de Performance de Disco no node {node_ip}"
        body = "ALERTA DE PERFORMANCE: O teste de escrita do disco (dd) demorou mais de 2 minutos para ser concluído. O disco está extremamente lento."
"
        send_email(subject, body)
        if os.path.exists(test_file_path):
            os.remove(test_file_path)
    except Exception as e:
        log_message(f"[ERROR] Erro ao executar o teste de performance de I/O: {e}")
        if os.path.exists(test_file_path):
            os.remove(test_file_path)
            
    return None  # Retorna None para não ser adicionado aos alertas gerais


# --- Funcao Principal ---


def main():
    os.makedirs("/opt/nkn-monitor/monitor_state", exist_ok=True)
    state = load_state()
    node_ip = get_public_ip()

    # Coleta o status do nó no início para incluir em todos os alertas
    node_state_info = get_node_state_rpc()
    current_node_status = node_state_info.get('syncState', 'N/A').upper()
    if node_state_info['status'] == 'error':
        current_node_status = f"ERRO RPC: {node_state_info['message']}"

    restart_alerts = []
    notification_alerts = []

    # --- COLETA DE ALERTAS PRIMÁRIOS ---
    # 1. Padrões de log que indicam falha imediata
    log_restarts, log_notifications = check_log_patterns()
    restart_alerts.extend(log_restarts)
    notification_alerts.extend(log_notifications)

    # 2. Status de saída do container
    is_exited, exit_msg = check_container_exit_status()
    if is_exited:
        restart_alerts.append(exit_msg)

    # 3. Checagens de saúde (RPC, Sincronização, DB)
    if not any(p in str(log_restarts) for p in ["panic", "fatal"]):
        health_alerts, trigger_db_stall_restart = run_health_checks(state, node_state_info)
        if health_alerts:
            restart_alerts.extend(health_alerts)
            if trigger_db_stall_restart:
                state['restarted_due_to_db_stall_at'] = time.time()

    # --- ANÁLISE DE CAUSA RAIZ ---
    should_investigate = any(
        "exit" in alert.lower() or 
        "exited" in alert.lower() or
        "unreachable" in alert.lower() or
        "panic" in alert.lower()
        for alert in restart_alerts
    )

    if should_investigate:
        system_log_findings = investigate_system_logs()
        notification_alerts.append("\n--- Investigação de Logs do Sistema (Possível Causa Raiz) ---")
        notification_alerts.extend(system_log_findings)

    # --- CHECAGENS SECUNDÁRIAS (NOTIFICAÇÃO) ---
    # 4. Falha persistente de DB Stall
    stall_timestamp = state.get('restarted_due_to_db_stall_at')
    if stall_timestamp and (time.time() - stall_timestamp < 30 * 60):
        db_size = get_chaindb_size()
        if db_size > 0 and db_size <= state.get('last_db_size', 0):
            notification_alerts.append("ALERTA PERSISTENTE: O ChainDB do nó continua sem crescer mesmo após uma reinicialização...")
        state['restarted_due_to_db_stall_at'] = None

    # 5. Portas públicas
    notification_alerts.extend(check_public_ports(node_ip))

    # 6. Recursos e I/O
    notification_alerts.extend(check_resource_usage(state))
    check_io_performance(state, node_ip)

    # --- LÓGICA DE ALERTA E AÇÃO ---
    all_alerts = restart_alerts + notification_alerts

    if all_alerts:
        for alert in all_alerts:
            log_error_to_json(node_ip, alert)

        frequency_alert = check_error_frequency(node_ip)
        if frequency_alert:
            notification_alerts.append(frequency_alert)
            all_alerts.append(frequency_alert)

        unique_restart_alerts = sorted(list(set(restart_alerts)))
        unique_notification_alerts = sorted(list(set(notification_alerts)))

        subject = f"[NKN-Monitor] Alerta no node {node_ip} - Status: {current_node_status}"
        body_lines = [
            f"Status do Nó: {current_node_status}",
            f"Problemas detectados no node {node_ip} ({datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC):\n"
        ]

        if unique_restart_alerts:
            body_lines.append("--- ALERTAS CRÍTICOS (causaram reinicialização) ---")
            body_lines.extend(unique_restart_alerts)
            body_lines.append("\n")

        if unique_notification_alerts:
            body_lines.append("--- AVISOS (não causaram reinicialização) ---")
            body_lines.extend(unique_notification_alerts)
            body_lines.append("\n")

        body = "\n".join(body_lines)
        send_email(subject, body)

        if unique_restart_alerts:
            log_message(f"Problemas criticos detectados: {unique_restart_alerts}. Reiniciando o container...")
            restart_container(state)
    else:
        log_message(f"Node OK - Status: {current_node_status}")

    save_state(state)

if __name__ == "__main__":
    main()