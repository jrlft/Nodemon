#!/usr/bin/env python3
"""
Script para verificar status dos monitores instalados
Conecta em todas as VPS e verifica se o monitoramento está funcionando
"""

import csv
import paramiko
import os
import sys
import threading
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import json

# Configurações
CSV_FILE = "vps_list.csv"
TARGET_MONITOR_PATH = "/opt/nkn-monitor"
MAX_CONCURRENT_CHECKS = 15
RESULTS_FILE = f"monitor_status_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

class MonitorStatusChecker:
    def __init__(self):
        self.results = {}
        self.lock = threading.Lock()
        
    def load_vps_list(self):
        """Carregar lista de VPS"""
        if not os.path.exists(CSV_FILE):
            print(f"❌ Arquivo {CSV_FILE} não encontrado!")
            return []
        
        vps_list = []
        try:
            with open(CSV_FILE, 'r') as f:
                reader = csv.reader(f)
                for linha in reader:
                    if len(linha) >= 2:
                        vps_list.append((linha[0].strip(), linha[1].strip()))
        except Exception as e:
            print(f"❌ Erro ao ler arquivo: {e}")
            return []
        
        print(f"📋 Carregadas {len(vps_list)} VPS(s) para verificação")
        return vps_list
    
    def ssh_connect(self, ip, senha):
        """Conectar SSH"""
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            ssh.connect(
                hostname=ip,
                username="root", 
                password=senha,
                timeout=20,
                look_for_keys=False,
                allow_agent=False
            )
            return ssh
        except Exception as e:
            raise Exception(f"SSH failed: {str(e)}")
    
    def check_monitor_status(self, ssh, ip):
        """Verificar status completo do monitor"""
        status = {
            'ip': ip,
            'timestamp': datetime.now().isoformat(),
            'installation': {'status': 'unknown', 'details': {}},
            'crontab': {'status': 'unknown', 'details': {}},
            'last_execution': {'status': 'unknown', 'details': {}},
            'monitor_health': {'status': 'unknown', 'details': {}},
            'recent_alerts': {'status': 'unknown', 'details': {}},
            'overall_status': 'unknown'
        }
        
        try:
            # 1. Verificar instalação
            stdin, stdout, stderr = ssh.exec_command(f"ls -la {TARGET_MONITOR_PATH}/")
            exit_code = stdout.channel.recv_exit_status()
            
            if exit_code == 0:
                files_output = stdout.read().decode('utf-8', errors='ignore')
                python_files = [line for line in files_output.split('\n') if '.py' in line and 'monitor' in line]
                
                status['installation'] = {
                    'status': 'installed' if python_files else 'partial',
                    'details': {
                        'path_exists': True,
                        'python_files': len(python_files),
                        'files': python_files
                    }
                }
            else:
                status['installation'] = {
                    'status': 'not_installed',
                    'details': {'path_exists': False, 'error': stderr.read().decode('utf-8', errors='ignore')}
                }
            
            # 2. Verificar crontab
            stdin, stdout, stderr = ssh.exec_command("crontab -l 2>/dev/null | grep nkn_health_monitor || echo 'NOT_FOUND'")
            crontab_output = stdout.read().decode('utf-8', errors='ignore').strip()
            
            if 'NOT_FOUND' not in crontab_output and crontab_output:
                status['crontab'] = {
                    'status': 'configured',
                    'details': {'entry': crontab_output}
                }
            else:
                status['crontab'] = {
                    'status': 'not_configured',
                    'details': {'output': crontab_output}
                }
            
            # 3. Verificar última execução
            stdin, stdout, stderr = ssh.exec_command(f"ls -la {TARGET_MONITOR_PATH}/monitor_state/ 2>/dev/null || echo 'NO_STATE_DIR'")
            state_output = stdout.read().decode('utf-8', errors='ignore')
            
            if 'NO_STATE_DIR' not in state_output:
                # Verificar log de execução
                stdin, stdout, stderr = ssh.exec_command(f"tail -20 {TARGET_MONITOR_PATH}/monitor_state/monitor.log 2>/dev/null || echo 'NO_LOG'")
                log_output = stdout.read().decode('utf-8', errors='ignore')
                
                if 'NO_LOG' not in log_output:
                    log_lines = [line for line in log_output.strip().split('\n') if line.strip()]
                    if log_lines:
                        last_line = log_lines[-1]
                        # Extrair timestamp do último log
                        try:
                            timestamp_part = last_line.split(']')[0] + ']'
                            last_run = timestamp_part.replace('[', '').replace(']', '')
                            last_run_time = datetime.fromisoformat(last_run.split('.')[0])
                            time_diff = datetime.now() - last_run_time
                            
                            status['last_execution'] = {
                                'status': 'recent' if time_diff < timedelta(minutes=15) else 'old',
                                'details': {
                                    'last_run': last_run,
                                    'minutes_ago': int(time_diff.total_seconds() / 60),
                                    'last_log_line': last_line[-100:]
                                }
                            }
                        except:
                            status['last_execution'] = {
                                'status': 'unknown',
                                'details': {'parse_error': True, 'last_line': last_line[-100:]}
                            }
            
            # 4. Testar execução do monitor
            stdin, stdout, stderr = ssh.exec_command(f"cd {TARGET_MONITOR_PATH} && timeout 60 python3 nkn_health_monitor.py 2>&1 || echo 'TEST_FAILED'")
            exit_code = stdout.channel.recv_exit_status()
            test_output = stdout.read().decode('utf-8', errors='ignore')
            
            if exit_code == 0 and 'TEST_FAILED' not in test_output:
                # Analisar output para determinar saúde
                if '✅' in test_output:
                    status['monitor_health'] = {
                        'status': 'healthy',
                        'details': {'test_passed': True, 'output_preview': test_output[-200:]}
                    }
                elif '❌' in test_output or '🚨' in test_output:
                    status['monitor_health'] = {
                        'status': 'issues_detected',
                        'details': {'test_passed': True, 'has_alerts': True, 'output_preview': test_output[-200:]}
                    }
                else:
                    status['monitor_health'] = {
                        'status': 'running',
                        'details': {'test_passed': True, 'output_preview': test_output[-200:]}
                    }
            else:
                status['monitor_health'] = {
                    'status': 'failed',
                    'details': {'test_passed': False, 'error': test_output[-200:]}
                }
            
            # 5. Verificar alertas recentes
            stdin, stdout, stderr = ssh.exec_command(f"find {TARGET_MONITOR_PATH}/monitor_state/ -name '*.json' -exec cat {{}} \\; 2>/dev/null || echo 'NO_STATE_FILES'")
            state_files_output = stdout.read().decode('utf-8', errors='ignore')
            
            if 'NO_STATE_FILES' not in state_files_output:
                try:
                    # Tentar parsear arquivos de estado
                    alert_info = {'recent_alerts': 0, 'last_alert_types': []}
                    for line in state_files_output.split('\n'):
                        if line.strip() and '{' in line:
                            try:
                                data = json.loads(line.strip())
                                if isinstance(data, dict) and data:
                                    alert_info['state_data'] = True
                                    break
                            except:
                                continue
                    
                    status['recent_alerts'] = {
                        'status': 'monitored',
                        'details': alert_info
                    }
                except:
                    status['recent_alerts'] = {
                        'status': 'unknown',
                        'details': {'parse_error': True}
                    }
            
            # 6. Determinar status geral
            if (status['installation']['status'] == 'installed' and 
                status['crontab']['status'] == 'configured' and
                status['monitor_health']['status'] in ['healthy', 'running']):
                status['overall_status'] = 'operational'
            elif status['monitor_health']['status'] == 'issues_detected':
                status['overall_status'] = 'operational_with_alerts'
            elif status['installation']['status'] == 'installed':
                status['overall_status'] = 'installed_with_issues'
            else:
                status['overall_status
