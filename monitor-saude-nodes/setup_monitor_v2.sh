#!/bin/bash
# setup_monitor_v2.sh
# Script aprimorado para instalar e corrigir o ambiente de monitoramento NKN.

set -e

TARGET_DIR="/opt/nkn-monitor"
LOG_FILE_V2="${TARGET_DIR}/monitor_state/cron_v2.log" # Novo arquivo de log para a versão 2
VENV_PATH="${TARGET_DIR}/venv"
MONITOR_SCRIPT="nkn_health_monitor.py"
MONITOR_SH="monitor.sh"

echo "🚀 Iniciando correção e configuração do NKN Health Monitor (v2)..."

# 1. Instalar dependências do sistema
echo "📦 Instalando dependências do sistema..."
apt-get update -qq
apt-get install -y python3 python3-pip python3-venv curl -qq

# 2. Criar diretórios necessários
mkdir -p "${TARGET_DIR}/monitor_state"
cd ${TARGET_DIR}

# 3. Criar ou recriar Ambiente Virtual
echo "🐍 Configurando ambiente virtual..."
rm -rf ${VENV_PATH} # Remove o venv antigo para garantir uma instalação limpa
python3 -m venv ${VENV_PATH}

# 4. Instalar dependências Python no venv
echo "📦 Instalando dependências Python (psutil, requests) no venv..."
${VENV_PATH}/bin/pip install --upgrade pip
${VENV_PATH}/bin/pip install psutil requests

# 5. Verificar a instalação do 'requests'
echo "🔍 Verificando a instalação da biblioteca 'requests'..."
if ! ${VENV_PATH}/bin/python -c "import requests" &>/dev/null; then
    echo "❌ ERRO: A instalação da biblioteca 'requests' falhou."
    exit 1
fi
echo "   ✅ Biblioteca 'requests' instalada com sucesso."

# 6. Limpeza robusta e configuração do Crontab
echo "⏰ Limpando e configurando o crontab..."
CRON_COMMAND="${VENV_PATH}/bin/python ${TARGET_DIR}/${MONITOR_SCRIPT}"
CRON_JOB="*/10 * * * * ${CRON_COMMAND} >> ${LOG_FILE_V2} 2>&1"
TMP_CRON_FILE="/tmp/new_cron_jobs.txt"

# Remove todas as entradas de crontab antigas conhecidas de forma segura
(crontab -l 2>/dev/null | grep -v -E "nkn_health_monitor.py|nkn-monitor/monitor.sh" || true) > "${TMP_CRON_FILE}"

# Adiciona a nova entrada correta
echo "${CRON_JOB}" >> "${TMP_CRON_FILE}"

# Instala o novo crontab
crontab "${TMP_CRON_FILE}"
rm "${TMP_CRON_FILE}"

echo "   ✅ Crontab configurado para executar a cada 10 minutos."
echo "   - Logs serão salvos em: ${LOG_FILE_V2}"

# 7. Remover o script monitor.sh antigo, se existir
if [ -f "${TARGET_DIR}/${MONITOR_SH}" ]; then
    rm -f "${TARGET_DIR}/${MONITOR_SH}"
    echo "🗑️ Script antigo '${MONITOR_SH}' removido."
fi

echo "🎉 Correção e instalação concluídas com sucesso!"
exit 0
