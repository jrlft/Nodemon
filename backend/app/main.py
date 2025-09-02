from fastapi import FastAPI, Depends, HTTPException, status, File, UploadFile, WebSocket
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette.websockets import WebSocketDisconnect
from sqlalchemy.orm import Session
from pydantic import BaseModel, ValidationError
from typing import Optional, List
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import OperationalError
import secrets
import os
import requests
import csv
import io
import time
import logging
import asyncio
import aiohttp
import smtplib
import paramiko
import socket
from . import ssh_manager
from email.mime.text import MIMEText
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timezone

load_dotenv()

logging.basicConfig(level=logging.INFO)

# --- Configurações --- #
DATABASE_URL = os.getenv("DATABASE_URL")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Luftcia125@@")
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")

# --- Base de Dados --- #
Base = declarative_base()
engine = None
MAX_RETRIES = 5
RETRY_DELAY = 5

for i in range(MAX_RETRIES):
    try:
        engine = create_engine(DATABASE_URL, pool_pre_ping=True)
        Base.metadata.create_all(bind=engine)
        logging.info("Conexão com a base de dados estabelecida com sucesso.")
        break  # Se a conexão for bem-sucedida, sai do loop
    except OperationalError as e:
        logging.error(f"Tentativa {i+1}/{MAX_RETRIES} falhou ao conectar na base de dados: {e}")
        if i < MAX_RETRIES - 1:
            logging.info(f"Aguardando {RETRY_DELAY} segundos para a próxima tentativa...")
            time.sleep(RETRY_DELAY)
        else:
            logging.error("Não foi possível conectar à base de dados após várias tentativas.")
            raise

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- Modelos da Base de Dados --- #
class Node(Base):
    __tablename__ = "nodes"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    ip_address = Column(String, unique=True, index=True)
    secondary_ip = Column(String, nullable=True)
    vps_provider = Column(String)
    wallet_address = Column(String, index=True)
    location = Column(String, default="A ser verificado")
    network = Column(String, index=True)
    status = Column(String, default="Aguardando verificação")
    currentBlock = Column(Integer, default=0)
    lastUpdate = Column(DateTime, default=datetime.now(timezone.utc))

# --- Funções de Lógica de Negócio --- #
def get_locations_for_ips_batch(ips: List[str]) -> dict:
    locations = {}
    if not ips:
        return locations
    try:
        # ip-api.com allows up to 100 IPs per batch request
        response = requests.post("http://ip-api.com/batch", json=ips, timeout=15)
        response.raise_for_status()
        data = response.json()
        for item in data:
            query = item.get('query')
            if item.get('status') == 'success':
                city = item.get('city', '')
                country = item.get('country', '')
                locations[query] = f"{city}, {country}"
            else:
                locations[query] = "Localização não encontrada"
    except requests.RequestException as e:
        logging.error(f"Erro ao buscar geolocalização em lote: {e}")
        # On batch failure, mark all as not found
        for ip in ips:
            locations[ip] = "Localização não encontrada"
    return locations

def send_email_alert(node_name: str, ip_address: str):
    if not all([SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, RECIPIENT_EMAIL]):
        logging.warning("Configurações de SMTP não encontradas. Pulando o envio de email.")
        return

    subject = f"Alerta: Nó {node_name} está Offline"
    body = f"O nó {node_name} com o endereço IP {ip_address} foi detectado como offline. Por favor, verifique."
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = SMTP_USER
    msg['To'] = RECIPIENT_EMAIL

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
            logging.info(f"Email de alerta enviado para {RECIPIENT_EMAIL} sobre o nó {node_name}.")
    except Exception as e:
        logging.error(f"Falha ao enviar email de alerta: {e}")

async def check_single_node(session: aiohttp.ClientSession, node: Node, semaphore: asyncio.Semaphore):
    async with semaphore:
        ip = node.ip_address
        # Default to the last known status, to avoid flapping
        new_status = {'status': node.status, 'currentBlock': node.currentBlock}
        is_online = False

        try:
            if node.network == 'nkn':
                try:
                    # 1. Quick TCP check
                    conn = asyncio.open_connection(ip, 30003)
                    _, writer = await asyncio.wait_for(conn, timeout=5)
                    writer.close()
                    await writer.wait_closed()
                    is_online = True
                    new_status['status'] = 'Online' # Tentative status
                except (asyncio.TimeoutError, ConnectionRefusedError):
                    is_online = False

                # 2. If TCP check passes, try to get detailed status
                if is_online:
                    try:
                        payload = {"jsonrpc": "2.0", "method": "getnodestate", "params": {}, "id": 1}
                        async with session.post(f"http://{ip}:30003", json=payload, timeout=5) as response:
                            response.raise_for_status()
                            data = await response.json()
                            result = data.get('result', {})
                            new_status['status'] = result.get('syncState', 'Online') # Fallback to Online
                            new_status['currentBlock'] = result.get('height', 0)
                    except (aiohttp.ClientError, asyncio.TimeoutError):
                        # API call failed, but we know the port is open, so we keep it as 'Online'
                        pass

            elif node.network == 'sentinel':
                # For Sentinel, check a few common ports. If any is open, consider it online.
                ports_to_check = [443, 80, 8553, 2624]
                for port in ports_to_check:
                    try:
                        conn = asyncio.open_connection(ip, port)
                        _, writer = await asyncio.wait_for(conn, timeout=3)
                        writer.close()
                        await writer.wait_closed()
                        is_online = True
                        new_status['status'] = 'Online'
                        break # Exit loop if a port is found open
                    except (asyncio.TimeoutError, ConnectionRefusedError):
                        continue # Try next port
            
            elif node.network == 'mysterium':
                try:
                    async with session.get(f"http://{ip}:4050/healthcheck", timeout=5) as response:
                        if response.status == 200:
                            data = await response.json()
                            if data.get('status') == 'UP':
                                is_online = True
                                new_status['status'] = 'Online'
                except (aiohttp.ClientError, asyncio.TimeoutError):
                    # If healthcheck fails, try a simple TCP check as a fallback
                    try:
                        conn = asyncio.open_connection(ip, 4050)
                        _, writer = await asyncio.wait_for(conn, timeout=3)
                        writer.close()
                        await writer.wait_closed()
                        is_online = True
                        new_status['status'] = 'Online'
                    except (asyncio.TimeoutError, ConnectionRefusedError):
                        pass

            else: # Generic check for other networks
                try:
                    conn = asyncio.open_connection(ip, 443)
                    _, writer = await asyncio.wait_for(conn, timeout=5)
                    writer.close()
                    await writer.wait_closed()
                    is_online = True
                    new_status['status'] = 'Online'
                except (asyncio.TimeoutError, ConnectionRefusedError):
                    pass

            if not is_online:
                new_status['status'] = 'Offline'

        except Exception as e:
            logging.error(f"Erro inesperado ao verificar o nó {node.name} ({ip}): {e}")
            new_status['status'] = 'Offline' # Mark as offline on unexpected errors

        return node.id, new_status

async def update_all_nodes_status():
    db = SessionLocal()
    try:
        logging.info("Iniciando a tarefa de atualização de status dos nós...")
        
        all_nodes = db.query(Node).all()
        total_nodes = len(all_nodes)
        
        if total_nodes == 0:
            logging.info("Nenhum nó para atualizar.")
            return

        semaphore = asyncio.Semaphore(100) # Limita a 100 verificações concorrentes
        
        async with aiohttp.ClientSession() as session:
            tasks = [check_single_node(session, node, semaphore) for node in all_nodes]
            results = await asyncio.gather(*tasks)

        updated_count = 0
        for node_id, new_status in results:
            node = db.query(Node).filter(Node.id == node_id).first()
            if node:
                if new_status['status'] == 'Offline' and node.status != 'Offline':
                    send_email_alert(node.name, node.ip_address)
                
                node.status = new_status['status']
                node.currentBlock = new_status['currentBlock']
                node.lastUpdate = datetime.now(timezone.utc)
                updated_count += 1

        db.commit()
        logging.info(f"Tarefa de atualização de status concluída. {updated_count}/{total_nodes} nós atualizados.")
    finally:
        db.close()

# --- Configuração do Scheduler e Lifespan --- #
scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 A iniciar a aplicação...")
    scheduler.add_job(update_all_nodes_status, 'interval', minutes=10, id="update_nodes")
    scheduler.start()
    yield
    print("👋 A encerrar a aplicação...")
    scheduler.shutdown()

# --- Aplicação FastAPI --- #
app = FastAPI(title="NodeMon API", description="API para o Sistema de Monitoramento de Nós", lifespan=lifespan)

# --- Segurança e Dependências --- #
security = HTTPBasic()

def get_current_username(credentials: HTTPBasicCredentials = Depends(security)):
    logging.info("====== AUTHENTICATION ATTEMPT ======")
    logging.info(f"Received username: '{credentials.username}'")
    logging.info(f"Received password: '{credentials.password}'")
    logging.info(f"Expected username from env: '{ADMIN_USERNAME}'")
    logging.info(f"Expected password from env: '{ADMIN_PASSWORD}'")
    
    correct_username = secrets.compare_digest(credentials.username, ADMIN_USERNAME)
    logging.info(f"Username comparison result: {correct_username}")

    correct_password = secrets.compare_digest(credentials.password, ADMIN_PASSWORD)
    logging.info(f"Password comparison result: {correct_password}")

    if not (correct_username and correct_password):
        logging.warning("Authentication failed: username or password incorrect.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
        
    logging.info(f"User '{credentials.username}' authenticated successfully.")
    logging.info("====================================")
    return credentials.username

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Esquemas Pydantic --- #
class NodeBase(BaseModel):
    name: str
    ip_address: str
    secondary_ip: Optional[str] = None
    vps_provider: str
    wallet_address: str
    network: str

class NodeUpdate(NodeBase):
    pass

class NodeIdList(BaseModel):
    node_ids: List[int]

class NodeSchema(NodeBase):
    id: int
    location: str
    status: Optional[str] = None
    currentBlock: Optional[int] = None
    lastUpdate: Optional[datetime] = None
    class Config:
        from_attributes = True

class NodeImportAnalysis(BaseModel):
    new_nodes: List[NodeBase]
    duplicate_nodes: List[NodeBase]
    errors: List[str]

class NodeImportRequest(BaseModel):
    nodes_to_create: List[NodeBase]
    nodes_to_update: List[NodeBase]


# --- Criação das Tabelas --- #
Base.metadata.create_all(bind=engine)

async def check_and_update_node_status(node_id: int):
    db = SessionLocal()
    try:
        node = db.query(Node).filter(Node.id == node_id).first()
        if not node:
            logging.warning(f"Verificação imediata falhou: Nó com ID {node_id} não encontrado.")
            return

        logging.info(f"Iniciando verificação de status imediata para o nó {node.name} ({node.ip_address})...")
        async with aiohttp.ClientSession() as session:
            semaphore = asyncio.Semaphore(1) # Semaphore for a single check
            _, new_status = await check_single_node(session, node, semaphore)

        # Fetch the node again in the session to update it
        node_to_update = db.query(Node).filter(Node.id == node_id).first()
        if node_to_update:
            node_to_update.status = new_status['status']
            node_to_update.currentBlock = new_status['currentBlock']
            node_to_update.lastUpdate = datetime.now(timezone.utc)
            db.commit()
            logging.info(f"Status imediato atualizado para o nó {node.name} ({node.ip_address}): {new_status['status']}")
        else:
            logging.error(f"Não foi possível atualizar o status para o nó com ID {node_id} porque ele não foi encontrado após a verificação.")

    except Exception as e:
        logging.error(f"Erro durante a verificação de status imediata para o nó ID {node_id}: {e}")
    finally:
        db.close()


# --- Endpoints da API --- #
@app.get("/nodes/", response_model=List[NodeSchema], dependencies=[Depends(get_current_username)])
def read_nodes(network: Optional[str] = None, db: Session = Depends(get_db)):
    return db.query(Node).filter(Node.network == network).all() if network else db.query(Node).all()

@app.post("/nodes/", response_model=NodeSchema, status_code=status.HTTP_201_CREATED, dependencies=[Depends(get_current_username)])
def create_node(node: NodeBase, db: Session = Depends(get_db)):
    locations = get_locations_for_ips_batch([node.ip_address])
    location = locations.get(node.ip_address, "Localização não encontrada")
    db_node = Node(**node.dict(), location=location)
    db.add(db_node)
    db.commit()
    db.refresh(db_node)
    return db_node

@app.put("/nodes/{node_id}", response_model=NodeSchema, dependencies=[Depends(get_current_username)])
def update_node(node_id: int, node_update: NodeUpdate, db: Session = Depends(get_db)):
    db_node = db.query(Node).filter(Node.id == node_id).first()
    if db_node is None:
        raise HTTPException(status_code=404, detail="Nó não encontrado")
    for key, value in node_update.dict().items():
        setattr(db_node, key, value)
    db.commit()
    db.refresh(db_node)
    return db_node

@app.delete("/nodes/{node_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(get_current_username)])
def delete_node(node_id: int, db: Session = Depends(get_db)):
    db_node = db.query(Node).filter(Node.id == node_id).first()
    if db_node is None:
        raise HTTPException(status_code=404, detail="Nó não encontrado")
    db.delete(db_node)
    db.commit()
    return

@app.post("/nodes/delete-multiple", status_code=status.HTTP_200_OK, dependencies=[Depends(get_current_username)])
def delete_multiple_nodes(node_ids: NodeIdList, db: Session = Depends(get_db)):
    deleted_count = db.query(Node).filter(Node.id.in_(node_ids.node_ids)).delete(synchronize_session=False)
    db.commit()
    if deleted_count == 0:
        raise HTTPException(status_code=404, detail="Nenhum nó encontrado para os IDs fornecidos")
    return {"message": f"{deleted_count} nós deletados com sucesso."}

@app.post("/nodes/trigger-refresh", status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(get_current_username)])
async def trigger_refresh():
    job = scheduler.get_job("update_nodes")
    if job:
        scheduler.modify_job(job.id, next_run_time=datetime.now(timezone.utc))
        return {"message": "Atualização de status acionada."}
    return HTTPException(status_code=404, detail="Job de atualização não encontrado.")

@app.post("/nodes/upload-csv/analyze", response_model=NodeImportAnalysis, dependencies=[Depends(get_current_username)])
async def analyze_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="O ficheiro deve ser um CSV.")

    content = await file.read()
    try:
        content_decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Não foi possível descodificar o ficheiro. Verifique se está em formato UTF-8.")

    stream = io.StringIO(content_decoded)
    try:
        dialect = csv.Sniffer().sniff(stream.readline(), delimiters=',;')
        stream.seek(0)
    except csv.Error:
        dialect = 'excel'
        stream.seek(0)

    csv_reader = csv.DictReader(stream, dialect=dialect)
    
    if csv_reader.fieldnames:
        csv_reader.fieldnames = [field.strip() for field in csv_reader.fieldnames]

    required_columns = {'name', 'ip_address', 'wallet_address', 'vps_provider', 'network'}
    if not csv_reader.fieldnames or not required_columns.issubset(csv_reader.fieldnames):
        missing = required_columns - set(csv_reader.fieldnames or [])
        raise HTTPException(status_code=400, detail=f"Colunas em falta no CSV: {', '.join(missing)}")

    analysis = {"new_nodes": [], "duplicate_nodes": [], "errors": []}
    existing_ips = {res[0] for res in db.query(Node.ip_address).all()}

    for i, row in enumerate(csv_reader):
        line_num = i + 2
        try:
            cleaned_row = {key.strip() if key else key: value.strip() if isinstance(value, str) else value for key, value in row.items()}

            ip_address = cleaned_row.get('ip_address')
            if not ip_address:
                analysis["errors"].append(f"Linha {line_num}: ip_address em falta.")
                continue

            network = cleaned_row.get('network')
            if network:
                network = network.lower()

            secondary_ip = cleaned_row.get('secondary_ip')
            if secondary_ip == '0':
                secondary_ip = None

            node_data = {
                "name": cleaned_row.get('name'), "ip_address": ip_address,
                "wallet_address": cleaned_row.get('wallet_address'), "vps_provider": cleaned_row.get('vps_provider'),
                "network": network, "secondary_ip": secondary_ip,
            }
            
            node = NodeBase(**node_data)

            if ip_address in existing_ips:
                analysis["duplicate_nodes"].append(node)
            else:
                analysis["new_nodes"].append(node)
                existing_ips.add(ip_address)

        except ValidationError as e:
            analysis["errors"].append(f"Linha {line_num}: Erro de validação - {e}")
        except Exception as e:
            analysis["errors"].append(f"Linha {line_num}: Erro inesperado - {e}")

    return analysis

@app.post("/nodes/import-processed-nodes/", status_code=status.HTTP_201_CREATED, dependencies=[Depends(get_current_username)])
async def import_processed_nodes(payload: NodeImportRequest, db: Session = Depends(get_db)):
    nodes_added = 0
    nodes_updated = 0

    # Process nodes to create
    if payload.nodes_to_create:
        nodes_to_create_data = [node.dict() for node in payload.nodes_to_create]
        
        batch_size = 100
        for i in range(0, len(nodes_to_create_data), batch_size):
            batch_data = nodes_to_create_data[i:i + batch_size]
            ips_in_batch = [node['ip_address'] for node in batch_data]
            
            locations = get_locations_for_ips_batch(ips_in_batch)

            for node_data in batch_data:
                location = locations.get(node_data['ip_address'], "Localização não encontrada")
                db_node = Node(**node_data, location=location)
                db.add(db_node)
                nodes_added += 1
            
            db.commit()
            logging.info(f"Lote de {len(batch_data)} nós novos salvo no banco de dados.")

    # Process nodes to update
    if payload.nodes_to_update:
        for node_update_data in payload.nodes_to_update:
            db_node = db.query(Node).filter(Node.ip_address == node_update_data.ip_address).first()
            if db_node:
                for key, value in node_update_data.dict().items():
                    setattr(db_node, key, value)
                nodes_updated += 1
        db.commit()
        logging.info(f"{nodes_updated} nós atualizados no banco de dados.")

    return {
        "message": f"{nodes_added} nós adicionados, {nodes_updated} nós atualizados com sucesso."
    }


@app.get("/status/global/{network}", dependencies=[Depends(get_current_username)])
def get_global_status(network: str):
    if network == 'nkn':
        rpc_endpoints = [
            'https://mainnet-rpc-node-0001.nkn.org/mainnet/api/wallet',
            'https://mainnet-rpc-node-0002.nkn.org/mainnet/api/wallet',
            'https://mainnet-rpc-node-0003.nkn.org/mainnet/api/wallet',
            'https://mainnet-rpc-node-0004.nkn.org/mainnet/api/wallet',
        ]
        heights = []
        payload = {"jsonrpc": "2.0", "method": "getlatestblockheight", "params": {}, "id": 1}
        
        for endpoint in rpc_endpoints:
            try:
                response = requests.post(endpoint, json=payload, timeout=5)
                response.raise_for_status()
                height = response.json().get('result', 0)
                if height and isinstance(height, int):
                    heights.append(height)
            except requests.RequestException as e:
                logging.warning(f"Falha ao contatar o endpoint RPC {endpoint}: {e}")
                continue
        
        if heights:
            max_height = max(heights)
            return {"label": "Altura Global do Bloco", "value": f"{max_height:,}"}
        else:
            logging.error("Não foi possível obter a altura do bloco de nenhum endpoint RPC da NKN.")
            return {"label": "Altura Global do Bloco", "value": "API Indisponível"}

    if network == 'sentinel':
        return {"label": "Altura Global do Bloco", "value": "9,876,543 (Mock)"}
    if network == 'mysterium':
        try:
            response = requests.get('https://discovery.mysterium.network/api/v3/nodes?limit=1', timeout=10)
            response.raise_for_status()
            total_nodes = response.json().get('total', 0)
            return {"label": "Total de Nós na Rede", "value": f"{total_nodes:,}"}
        except requests.RequestException:
            return {"label": "Total de Nós na Rede", "value": "API Indisponível"}
    raise HTTPException(status_code=404, detail="Rede desconhecida")


class SshCredentials(BaseModel):
    username: str
    password: str

@app.post("/ssh/connect/{node_ip}", status_code=status.HTTP_200_OK, dependencies=[Depends(get_current_username)])
def ssh_connect(node_ip: str, creds: SshCredentials):
    """
    Testa a conexão SSH e salva as credenciais se a conexão for bem-sucedida.
    """
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(node_ip, username=creds.username, password=creds.password, timeout=10)
        client.close()

        # Se a conexão for bem-sucedida, salva as credenciais
        ssh_manager.save_credentials(node_ip, creds.username, creds.password)
        return {"message": "Conexão SSH bem-sucedida e credenciais salvas."}
    except paramiko.AuthenticationException:
        raise HTTPException(status_code=401, detail="Falha na autenticação SSH.")
    except paramiko.SSHException as e:
        raise HTTPException(status_code=500, detail=f"Erro de SSH: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro inesperado: {e}")

@app.websocket("/ws/ssh/{node_ip}")
async def websocket_ssh_endpoint(websocket: WebSocket, node_ip: str):
    """
    Endpoint WebSocket para o terminal SSH interativo.
    """
    # Check authorization from query parameters
    try:
        # Get authorization from query parameters
        auth_header = websocket.query_params.get('authorization')
        
        # Basic authentication validation
        if not auth_header or not auth_header.startswith('Basic '):
            await websocket.close(code=1008, reason="Unauthorized: Missing authentication")
            return
            
        # Validate credentials
        import base64
        try:
            encoded_credentials = auth_header.split('Basic ')[1]
            decoded_credentials = base64.b64decode(encoded_credentials).decode('utf-8')
            username, password = decoded_credentials.split(':', 1)
            
            # Validate against admin credentials
            if not (secrets.compare_digest(username, ADMIN_USERNAME) and 
                   secrets.compare_digest(password, ADMIN_PASSWORD)):
                await websocket.close(code=1008, reason="Unauthorized: Invalid credentials")
                return
        except Exception:
            await websocket.close(code=1008, reason="Unauthorized: Invalid authorization format")
            return
            
    except Exception as e:
        logging.error(f"WebSocket authentication error: {e}")
        await websocket.close(code=1008, reason="Authentication error")
        return

    await websocket.accept()

    creds = ssh_manager.get_credentials(node_ip)
    if not creds:
        await websocket.send_text(f"\r\nERRO: Credenciais para o node {node_ip} não encontradas. Por favor, configure-as primeiro.\r\n")
        await websocket.close(code=1008) # Policy Violation
        return

    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Set more reasonable timeouts and connection parameters
        client.connect(
            node_ip, 
            username=creds['username'], 
            password=creds['password'], 
            timeout=15,
            auth_timeout=10,
            banner_timeout=10
        )

        channel = client.invoke_shell(term='xterm-256color')
        channel.settimeout(0.1)  # Non-blocking reads

        async def read_from_channel():
            try:
                while not channel.exit_status_ready():
                    try:
                        if channel.recv_ready():
                            data = channel.recv(4096)
                            if data:
                                await websocket.send_text(data.decode('utf-8', 'ignore'))
                    except socket.timeout:
                        pass  # Expected for non-blocking operation
                    except Exception as e:
                        logging.error(f"Error reading from SSH channel: {e}")
                        break
                    await asyncio.sleep(0.01)
                
                # Send final data if any
                try:
                    if channel.recv_ready():
                        data = channel.recv(4096)
                        if data:
                            await websocket.send_text(data.decode('utf-8', 'ignore'))
                except:
                    pass
                    
                # Close the connection
                await websocket.close()
            except Exception as e:
                logging.error(f"Error in read_from_channel: {e}")
            finally:
                try:
                    client.close()
                except:
                    pass


        async def write_to_channel():
            try:
                while True:
                    data = await websocket.receive_text()
                    if channel and not channel.closed:
                        channel.send(data)
                    else:
                        break
            except WebSocketDisconnect:
                logging.info("WebSocket disconnected.")
            except Exception as e:
                logging.error(f"Error in write_to_channel: {e}")
            finally:
                try:
                    if client:
                        client.close()
                except:
                    pass

        # Run reader and writer tasks with proper cancellation
        reader_task = asyncio.create_task(read_from_channel())
        writer_task = asyncio.create_task(write_to_channel())

        try:
            done, pending = await asyncio.wait(
                [reader_task, writer_task],
                return_when=asyncio.FIRST_COMPLETED,
                timeout=3600  # 1 hour timeout
            )
        finally:
            # Clean up tasks
            for task in [reader_task, writer_task]:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

    except paramiko.AuthenticationException:
        error_message = f"\r\nERRO: Falha na autenticação SSH para {node_ip}. Verifique as credenciais.\r\n"
        await websocket.send_text(error_message)
        await websocket.close(code=1008)
    except paramiko.SSHException as ssh_error:
        error_message = f"\r\nERRO: Falha na conexão SSH: {str(ssh_error)}\r\n"
        await websocket.send_text(error_message)
        await websocket.close(code=1011)
    except Exception as e:
        error_message = f"\r\nERRO: Falha ao conectar via SSH: {str(e)}\r\n"
        logging.error(f"SSH WebSocket error for {node_ip}: {e}")
        try:
            await websocket.send_text(error_message)
            await websocket.close(code=1011)
        except:
            pass  # Connection might already be closed

