import paramiko
import time
import os

def check_server(ip, password, output_file):
    try:
        output_file.write(f"--- Checking {ip} ---\n")
        print(f"--- Checking {ip} ---")

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(ip, username="root", password=password, timeout=10)

        sftp = client.open_sftp()
        log_files = ["/opt/nkn-monitor/cron.log", "/opt/nkn-monitor/cronv_v2.log"]

        for log_file in log_files:
            try:
                with sftp.open(log_file, "r") as f:
                    content = f.read().decode('utf-8', errors='ignore')
                    output_file.write(f"--- Content of {log_file} ---\n")
                    output_file.write(content)
                    output_file.write(f"--- End of {log_file} ---\n\n")
                    print(f"Successfully read {log_file}")
            except FileNotFoundError:
                output_file.write(f"Log file not found: {log_file}\n\n")
                print(f"Log file not found: {log_file}")
            except Exception as e:
                output_file.write(f"Error reading {log_file}: {e}\n\n")
                print(f"Error reading {log_file}: {e}")

        sftp.close()
        client.close()

    except Exception as e:
        error_message = f"Error connecting or checking {ip}: {e}\n\n"
        output_file.write(error_message)
        print(error_message)

def main():
    with open("revisao.txt", "w") as output_file:
        try:
            with open("servers.txt", "r") as f:
                servers = f.readlines()

            for line in servers:
                line = line.strip()
                if not line or "," not in line:
                    continue
                ip, password = line.split(",", 1)
                check_server(ip.strip(), password.strip(), output_file)
                time.sleep(1)

        except FileNotFoundError:
            error_message = "servers.txt not found.\n"
            output_file.write(error_message)
            print(error_message)

if __name__ == "__main__":
    main()