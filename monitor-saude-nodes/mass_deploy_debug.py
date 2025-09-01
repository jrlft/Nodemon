import paramiko
import time

def deploy_to_server(ip, password):
    try:
        print(f"\n🚀 Deploy em {ip}")

        # Configuração do cliente SSH
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Conexão via senha
        client.connect(ip, username="root", password=password, timeout=10)

        # Iniciar sessão SFTP
        sftp = client.open_sftp()
        print("📤 Copiando arquivos...")
        sftp.put("setup_monitor_v2.sh", "/opt/nkn-monitor/setup_monitor_v2.sh")
        print("   -> setup_monitor_v2.sh")
        sftp.put("nkn_health_monitor.py", "/opt/nkn-monitor/nkn_health_monitor.py")
        print("   -> nkn_health_monitor.py")
        sftp.put("monitor_config.py", "/opt/nkn-monitor/monitor_config.py")
        print("   -> monitor_config.py")
        sftp.close()
        print("✅ Arquivos copiados.")

        # Tornar executável
        stdin, stdout, stderr = client.exec_command("chmod +x /opt/nkn-monitor/setup_monitor_v2.sh")
        stdout.channel.recv_exit_status()

        # Executar script remoto
        stdin, stdout, stderr = client.exec_command("bash /opt/nkn-monitor/setup_monitor_v2.sh")
        exit_code = stdout.channel.recv_exit_status()

        if exit_code == 0:
            print(f"✅ Sucesso em {ip}")
        else:
            print(f"⚠️ Script executado com erro em {ip} (Exit Code: {exit_code})")
            error_output = stderr.read().decode()
            std_output = stdout.read().decode()
            print("--- STDOUT ---")
            print(std_output if std_output else "(vazio)")
            print("--- STDERR ---")
            print(error_output if error_output else "(vazio)")
            print("--------------")

        client.close()

    except Exception as e:
        print(f"❌ Erro em {ip}: {e}")


def main():
    try:
        with open("servers.txt", "r") as f:
            servers = f.readlines()

        for line in servers:
            line = line.strip()
            if not line or "," not in line:
                continue
            ip, password = line.split(",", 1)
            deploy_to_server(ip.strip(), password.strip())
            time.sleep(1)  # pequeno intervalo entre os servidores

    except FileNotFoundError:
        print("❌ Arquivo servers.txt não encontrado.")


if __name__ == "__main__":
    main()
