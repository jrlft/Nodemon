#!/bin/bash
# setup_monitor.sh
# Script para instalar o ambiente de monitoramento NKN com venv e configurar o crontab.

set -e # Encerra o script se um comando falhar

TARGET_DIR="/opt/nkn-monitor"
LOG_FILE="${TARGET_DIR}/cron.log"
VENV_PATH="${TARGET_DIR}/venv"
MONITOR_SCRIPT="nkn_health_monitor.py"

echo "🚀 Iniciando configuração do NKN Health Monitor em ${TARGET_DIR}"

# 1. Instalar dependências do sistema
echo "📦 Instalando dependências do sistema (python3, pip, venv, curl, grep)..."
apt-get update -qq
apt-get install -y python3 python3-pip python3-venv curl grep -qq >/dev/null

# 2. Criar diretório de destino
mkdir -p ${TARGET_DIR}
cd ${TARGET_DIR}

# 3. Criar Ambiente Virtual (venv)
if [ ! -d "${VENV_PATH}" ]; then
    echo "🐍 Criando ambiente virtual em ${VENV_PATH}..."
    python3 -m venv ${VENV_PATH}
else
    echo "🐍 Ambiente virtual já existe."
fi

# 4. Instalar dependências Python no venv
echo "📦 Instalando dependências Python (psutil, requests) dentro do venv..."
${VENV_PATH}/bin/python -m ensurepip --upgrade
${VENV_PATH}/bin/python -m pip install psutil requests

# 5. Dar permissão de execução ao script de monitoramento
# (O script deve ser copiado para cá pelo deployer)
if [ -f "${MONITOR_SCRIPT}" ]; then
    chmod +x ${MONITOR_SCRIPT}
    echo "🔑 Permissão de execução concedida para ${MONITOR_SCRIPT}."
else
    echo "⚠️ ALERTA: O script ${MONITOR_SCRIPT} não foi encontrado em ${TARGET_DIR}."
    echo "O script de deploy precisa copiá-lo."
fi

# 6. Configurar Crontab de forma segura e verificada
CRON_COMMAND="${VENV_PATH}/bin/python ${TARGET_DIR}/${MONITOR_SCRIPT}"
CRON_JOB="*/10 * * * * ${CRON_COMMAND} >> ${LOG_FILE} 2>&1"
TMP_CRON_FILE="/tmp/my_cron_jobs"

echo "⏰ Configurando crontab..."

# Adicionando verificacao de comandos
if ! command -v crontab &> /dev/null || ! command -v grep &> /dev/null; then
    echo "   ❌ ERRO: Os comandos 'crontab' ou 'grep' não foram encontrados no PATH."
    exit 1
fi
echo "   - Comandos 'crontab' e 'grep' encontrados."

# Escreve o novo crontab em um arquivo temporário, removendo todas as versoes antigas conhecidas
(crontab -l 2>/dev/null | grep -v "nkn_health_monitor.py" || true | grep -v "nkn-monitor/monitor.sh" || true ; echo "${CRON_JOB}") > "${TMP_CRON_FILE}"

echo "   - Conteúdo do novo crontab a ser instalado:"
cat "${TMP_CRON_FILE}"

# Instala o novo crontab a partir do arquivo
crontab "${TMP_CRON_FILE}"

# Verifica se a instalação foi bem-sucedida
if crontab -l | grep -q -F "${CRON_COMMAND}"; then
    echo "   ✅ Crontab verificado e instalado com sucesso."
else
    echo "   ❌ ERRO: Falha ao instalar o novo crontab. O comando 'crontab ${TMP_CRON_FILE}' pode ter falhado."
    rm "${TMP_CRON_FILE}"
    exit 1 # Força um código de saída de erro
fi

# Limpa o arquivo temporário
rm "${TMP_CRON_FILE}"

echo "✅ Configuração do Crontab concluída!"
echo "   - O monitor será executado a cada 10 minutos."
echo "   - Logs serão salvos em: ${LOG_FILE}"

echo "🎉 Instalação concluída com sucesso!"
exit 0
