import paramiko
import os

def deploy_to_server(ip, password):
    try:
        print(f"--- Deploying to {ip} ---")
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(ip, username="root", password=password, timeout=10)

        sftp = client.open_sftp()
        
        local_script_path = "nkn_health_monitor.py"
        remote_script_path = "/opt/nkn-monitor/nkn_health_monitor.py"
        
        local_config_path = "monitor_config.py"
        remote_config_path = "/opt/nkn-monitor/monitor_config.py"

        if os.path.exists(local_script_path):
            sftp.put(local_script_path, remote_script_path)
            print(f"Successfully uploaded {local_script_path} to {remote_script_path}")
        else:
            print(f"Local file not found: {local_script_path}")

        if os.path.exists(local_config_path):
            sftp.put(local_config_path, remote_config_path)
            print(f"Successfully uploaded {local_config_path} to {remote_config_path}")
        else:
            print(f"Local file not found: {local_config_path}")

        sftp.close()
        client.close()
        print(f"--- Deployment to {ip} finished ---")

    except Exception as e:
        print(f"Error deploying to {ip}: {e}")

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

    except FileNotFoundError:
        print("servers.txt not found.")

if __name__ == "__main__":
    main()
