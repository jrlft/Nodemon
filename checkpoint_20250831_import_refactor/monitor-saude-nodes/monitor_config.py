#!/usr/bin/env python3
"""
Arquivo de configuração para o NKN Health Monitor
Copie este arquivo para monitor_config.py e edite as variáveis
"""

# =============================================================================
# CONFIGURAÇÕES DE EMAIL - OBRIGATÓRIO
# =============================================================================

# Gmail SMTP (recomendado)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_USER = "juniorluft@gmail.com"      # SEU EMAIL GMAIL
EMAIL_PASS = "otvsxaimjommipnx"      # SENHA DE APP DO GMAIL (16 dígitos)
DESTINATION_EMAIL = "juniorluft@gmail.com"  # EMAIL PARA RECEBER ALERTAS

# Outras opções de SMTP (descomente se usar outro provedor)
"""
# Outlook/Hotmail
SMTP_SERVER = "smtp-mail.outlook.com"
SMTP_PORT = 587

# Yahoo
SMTP_SERVER = "smtp.mail.yahoo.com"
SMTP_PORT = 587

# SMTP customizado
SMTP_SERVER = "seu-servidor-smtp.com"
SMTP_PORT = 587
"""

# =============================================================================
# CONFIGURAÇÕES DOS CAMINHOS NKN
# =============================================================================

CONTAINER_NAME = "nkn_node"                                        # Nome do container Docker
NKN_DATA_PATH = "/opt/depin-stack/nkn-data"                       # Caminho dos dados NKN
CHAINDB_PATH = "/opt/depin-stack/nkn-data/services/nkn-node/ChainDB"  # Caminho do ChainDB
CONFIG_JSON_PATH = "/opt/depin-stack/nkn-data/config.json"        # Arquivo de configuração

# =============================================================================
# CONFIGURAÇÕES DE MONITORAMENTO
# =============================================================================

MAX_LOG_LINES = 500              # Máximo de linhas do docker logs para analisar
MEMORY_WARNING_THRESHOLD = 90    # % de uso de memória para alerta
DISK_WARNING_THRESHOLD = 90      # % de uso de disco para alerta
CPU_WARNING_THRESHOLD = 90       # % de uso de CPU para alerta
SYNC_CHECK_INTERVAL = 300        # Segundos para considerar sync travado (5 min)

# Intervalo mínimo entre alertas do mesmo tipo (em horas)
ALERT_COOLDOWN_HOURS = 1         # Não reenviar mesmo alerta por 1 hora

# =============================================================================
# CONFIGURAÇÕES AVANÇADAS
# =============================================================================

# Padrões de erro customizados (regex, severidade, descrição)
CUSTOM_ERROR_PATTERNS = [
    (r'custom.*error.*pattern', 'HIGH', 'Erro customizado detectado'),
    # Adicione seus próprios padrões aqui
]

# Verificações desabilitadas (descomente para desabilitar)
DISABLED_CHECKS = [
    # 'docker_container',    # Pular verificação do container
    # 'docker_logs',         # Pular análise de logs
    # 'nkn_process',         # Pular verificação do processo nknd
    # 'system_resources',    # Pular verificação de recursos
    # 'chaindb_integrity',   # Pular verificação do ChainDB
    # 'config_file',         # Pular verificação do config.json
]

# Debug mode (mais logs detalhados)
DEBUG_MODE = False

# =============================================================================
# CONFIGURAÇÕES DE LOGS
# =============================================================================

LOG_RETENTION_DAYS = 30          # Quantos dias manter os logs
MAX_LOG_SIZE_MB = 100            # Tamanho máximo do arquivo de log (MB)

# =============================================================================
# VALIDAÇÃO DA CONFIGURAÇÃO
# =============================================================================

def validate_config():
    """Validar configuração básica"""
    errors = []
    
    # Verificar configurações obrigatórias
    if EMAIL_USER == "seu-email@gmail.com":
        errors.append("❌ Configure EMAIL_USER com seu email real")
    
    if EMAIL_PASS == "xxxx xxxx xxxx xxxx":
        errors.append("❌ Configure EMAIL_PASS com sua senha de app do Gmail")
    
    if DESTINATION_EMAIL == "destino@gmail.com":
        errors.append("❌ Configure DESTINATION_EMAIL com o email de destino")
    
    if not EMAIL_USER or not EMAIL_PASS or not DESTINATION_EMAIL:
        errors.append("❌ Todos os campos de email são obrigatórios")
    
    # Verificar thresholds
    if not (0 <= MEMORY_WARNING_THRESHOLD <= 100):
        errors.append("❌ MEMORY_WARNING_THRESHOLD deve estar entre 0 e 100")
    
    if not (0 <= DISK_WARNING_THRESHOLD <= 100):
        errors.append("❌ DISK_WARNING_THRESHOLD deve estar entre 0 e 100")
    
    if errors:
        print("🚨 ERROS DE CONFIGURAÇÃO:")
        for error in errors:
            print(f"   {error}")
        print("\n💡 Edite o arquivo monitor_config.py e corrija os erros acima")
        return False
    
    return True

if __name__ == "__main__":
    # Testar configuração quando executado diretamente
    if validate_config():
        print("✅ Configuração válida!")
    else:
        print("❌ Configuração inválida!")
        exit(1)
