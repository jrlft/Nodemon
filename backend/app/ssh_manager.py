import os
import json
from cryptography.fernet import Fernet
from dotenv import load_dotenv
from typing import Union

# Carregar variáveis de ambiente do arquivo .env
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

# Carregar a chave de criptografia
CRYPTO_KEY = os.getenv("CRYPTO_KEY")
if not CRYPTO_KEY:
    raise ValueError("CRYPTO_KEY não encontrada no arquivo .env")

fernet = Fernet(CRYPTO_KEY.encode())

# Arquivo para armazenar as credenciais
CREDENTIALS_FILE = os.path.join("/code", 'ssh_credentials.json')

def encrypt_password(password: str) -> str:
    """Criptografa a senha."""
    return fernet.encrypt(password.encode()).decode()

def decrypt_password(encrypted_password: str) -> str:
    """Descriptografa a senha."""
    return fernet.decrypt(encrypted_password.encode()).decode()

def save_credentials(host: str, username: str, password: str):
    """Salva as credenciais de SSH de forma segura."""
    credentials = {}
    if os.path.exists(CREDENTIALS_FILE):
        with open(CREDENTIALS_FILE, 'r') as f:
            try:
                credentials = json.load(f)
            except json.JSONDecodeError:
                pass  # O arquivo está vazio ou corrompido

    credentials[host] = {
        "username": username,
        "password": encrypt_password(password)
    }

    with open(CREDENTIALS_FILE, 'w') as f:
        json.dump(credentials, f, indent=4)

def get_credentials(host: str) -> Union[dict, None]:
    """Recupera as credenciais de SSH."""
    if not os.path.exists(CREDENTIALS_FILE):
        return None

    with open(CREDENTIALS_FILE, 'r') as f:
        try:
            credentials = json.load(f)
            if host in credentials:
                host_creds = credentials[host]
                return {
                    "username": host_creds["username"],
                    "password": decrypt_password(host_creds["password"])
                }
        except (json.JSONDecodeError, KeyError):
            return None
    return None