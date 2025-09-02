import paramiko
import time
import socket # Import socket for timeout exception

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

        # Set a timeout for command execution
        channel_timeout = 30 # seconds

        # Use get_transport().open_session() to get a channel and set timeout
        transport = client.get_transport()
        if transport is None:
            raise Exception("SSH transport not available.")

        # Command 1: chmod
        channel = transport.open_session()
        channel.settimeout(channel_timeout)
        channel.exec_command("chmod +x /opt/nkn-monitor/setup_monitor_v2.sh")
        # Read stdout/stderr to ensure channel closes and doesn't hang
        stdout_chmod = channel.makefile("rb", -1).read()
        stderr_chmod = channel.makefile_stderr("rb", -1).read()
        exit_status_chmod = channel.recv_exit_status()
        channel.close()

        if exit_status_chmod != 0:
            print(f"⚠️ Erro ao tornar executável em {ip}: {stderr_chmod.decode()}")
            client.close()
            return

        # Command 2: bash script
        channel = transport.open_session()
        channel.settimeout(channel_timeout)
        channel.exec_command("bash /opt/nkn-monitor/setup_monitor_v2.sh")
        # Read stdout/stderr to ensure channel closes and doesn't hang
        std_output = channel.makefile("rb", -1).read().decode()
        error_output = channel.makefile_stderr("rb", -1).read().decode()
        exit_code = channel.recv_exit_status()
        channel.close()

        if exit_code == 0:
            print(f"✅ Sucesso em {ip}")
        else:
            print(f"⚠️ Script executado com erro em {ip} (Exit Code: {exit_code})")
            print("---STDOUT---")
            print(std_output if std_output else "(vazio)")
            print("---STDERR---")
            print(error_output if error_output else "(vazio)")
            print("--------------")

        client.close()

    except socket.timeout:
        print(f"❌ Erro de timeout em {ip}: A operação SSH excedeu o tempo limite.")
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
