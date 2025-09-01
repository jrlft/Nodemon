Olá. Estou a tentar fazer o deploy de uma aplicação full-stack no meu servidor Ubuntu usando Docker Compose e preciso da sua ajuda para resolver um problema de ligação persistente.

**O Problema:**
O meu contentor do backend (FastAPI) não consegue ligar-se ao meu contentor da base de dados (PostgreSQL). Ele falha com o erro `psycopg2.OperationalError: Connection refused`, mesmo depois de o contentor da base de dados estar a correr e saudável.

**A Minha Configuração:**
Estou a usar um frontend em React, um backend em FastAPI, uma base de dados PostgreSQL, e um Nginx como reverse proxy.

Por favor, analise os seguintes ficheiros e o log de erro, identifique a causa raiz do problema e forneça as versões corrigidas dos ficheiros para que o sistema funcione.

**1. `docker-compose.yml`:**
```yaml
services:
  backend:
    build: ./backend
    container_name: nodemon-backend
    env_file:
      - ./backend/.env
    ports:
      - "127.0.0.1:8000:8000"
    networks: # <-- Adicionado
      - nodemon-net
    depends_on:
      db:
        condition: service_healthy

  frontend:
    build: ./frontend
    container_name: nodemon-frontend
    env_file:
      - ./frontend/.env
    ports:
      - "127.0.0.1:3000:3000"
    networks: # <-- Adicionado
      - nodemon-net
    depends_on:
      - backend

  db:
    image: postgres:13
    container_name: nodemon-db
    environment:
      POSTGRES_DB: nodemon_db
      POSTGRES_USER: nodemon_user
      POSTGRES_PASSWORD: Luftcia125@@
    volumes:
      - postgres_data:/var/lib/postgresql/data/
    networks: # <-- Adicionado
      - nodemon-net
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U nodemon_user -d nodemon_db"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:

networks: # <-- Secção nova adicionada
  nodemon-net:
    driver: bridge


2. backend/.env:
# Credenciais da Base de Dados (para a aplicação)
POSTGRES_DB=nodemon_db
POSTGRES_USER=nodemon_user
POSTGRES_PASSWORD=Luftcia125@@
DATABASE_URL=postgresql+psycopg2://nodemon_user:Luftcia125@@@db:5432/nodemon_db

# Credenciais do Admin da Aplicação
ADMIN_USERNAME=admin
ADMIN_PASSWORD=Luftcia125@@

3. backend/app/main.py:
from fastapi import FastAPI, Depends, HTTPException, status, File, UploadFile
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import OperationalError
import secrets
import os
import requests
import csv
import io
import time
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

# --- Configuração da Base de Dados ---
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 A iniciar a aplicação... a tentar ligar à base de dados.")
    retries = 10
    while retries > 0:
        try:
            # Tenta fazer uma ligação simples para verificar se a BD está pronta
            connection = engine.connect()
            connection.close()
            print("✅ Ligação à base de dados estabelecida com sucesso.")
            Base.metadata.create_all(bind=engine)
            print("📚 Tabelas da base de dados verificadas/criadas.")
            break
        except OperationalError:
            retries -= 1
            print(f"❌ A base de dados não está pronta. A tentar novamente em 5 segundos... ({retries} tentativas restantes)")
            time.sleep(5)

    if retries == 0:
        print("🚨 Não foi possível estabelecer ligação à base de dados após várias tentativas. A aplicação pode não funcionar corretamente.")

    yield
    print("👋 A encerrar a aplicação...")

# --- Configuração da App e Segurança ---
app = FastAPI(title="NodeMon API", description="API para o Sistema de Monitoramento de Nós", lifespan=lifespan)

security = HTTPBasic()
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Luftcia125@@")

def get_current_username(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, ADMIN_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, ADMIN_PASSWORD)
    if not (correct_username and correct_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais incorretas", headers={"WWW-Authenticate": "Basic"})
    return credentials.username

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Modelos e Esquemas ---
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

class NodeBase(BaseModel):
    name: str
    ip_address: str
    secondary_ip: Optional[str] = None
    vps_provider: str
    wallet_address: str
    network: str

class NodeCreate(NodeBase):
    pass

class NodeSchema(NodeBase):
    id: int
    location: str
    class Config:
        from_attributes = True

# --- Rotas da API ---
@app.get("/")
def read_root():
    return {"message": "Bem-vindo à API do NodeMon"}

@app.get("/nodes/", response_model=List[NodeSchema])
def read_nodes(network: Optional[str] = None, db: Session = Depends(get_db), username: str = Depends(get_current_username)):
    return db.query(Node).filter(Node.network == network).all() if network else db.query(Node).all()

@app.post("/nodes/", response_model=NodeSchema, status_code=status.HTTP_201_CREATED)
def create_node(node: NodeCreate, db: Session = Depends(get_db), username: str = Depends(get_current_username)):
    db_node = Node(**node.dict())
    db.add(db_node)
    db.commit()
    db.refresh(db_node)
    return db_node

@app.post("/nodes/upload-csv/", status_code=status.HTTP_201_CREATED)
async def upload_csv(file: UploadFile = File(...), db: Session = Depends(get_db), username: str = Depends(get_current_username)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="O ficheiro deve ser um CSV.")
    content = await file.read()
    stream = io.StringIO(content.decode("utf-8"))
    csv_reader = csv.DictReader(stream)
    nodes_added = 0
    for row in csv_reader:
        try:
            node_data = NodeCreate(**row)
            existing_node = db.query(Node).filter(Node.ip_address == node_data.ip_address).first()
            if not existing_node:
                db_node = Node(**node_data.dict())
                db.add(db_node)
                nodes_added += 1
        except Exception:
            continue
    db.commit()
    return {"message": f"{nodes_added} nós adicionados com sucesso."}

@app.get("/status/global/{network}")
def get_global_status(network: str, username: str = Depends(get_current_username)):
    if network == 'nkn':
        try:
            response = requests.get('https://openapi.nkn.org/api/v1/block/latest', timeout=5)
            response.raise_for_status()
            height = response.json().get('header', {}).get('height', 0)
            return {"label": "Altura Global do Bloco", "value": f"{height:,}"}
        except requests.RequestException:
            return {"label": "Altura Global do Bloco", "value": "API Indisponível"}
    if network == 'sentinel':
        return {"label": "Altura Global do Bloco", "value": "9,876,543 (Mock)"}
    if network == 'mysterium':
        try:
            response = requests.get('https://discovery.mysterium.network/api/v3/nodes?limit=1', timeout=5)
            response.raise_for_status()
            total_nodes = response.json().get('total', 0)
            return {"label": "Total de Nós na Rede", "value": f"{total_nodes:,}"}
        except requests.RequestException:
            return {"label": "Total de Nós na Rede", "value": "API Indisponível"}
    raise HTTPException(status_code=404, detail="Rede desconhecida")


4. Configuração do Nginx (/etc/nginx/sites-available/nodes.linkti.info):
server {
    server_name nodes.linkti.info;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    listen 443 ssl; # managed by Certbot
    ssl_certificate /etc/letsencrypt/live/nodes.linkti.info/fullchain.pem; # managed by Certbot
    ssl_certificate_key /etc/letsencrypt/live/nodes.linkti.info/privkey.pem; # managed by Certbot
    include /etc/letsencrypt/options-ssl-nginx.conf; # managed by Certbot
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem; # managed by Certbot

}
server {
    if ($host = nodes.linkti.info) {
        return 301 https://$host$request_uri;
    } # managed by Certbot


    listen 80;
    server_name nodes.linkti.info;
    return 404; # managed by Certbot

5. Log de Erro do Backend (docker compose logs nodemon-backend):
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
🚀 A iniciar a aplicação... a tentar ligar à base de dados.
❌ A base de dados não está pronta. A tentar novamente em 5 segundos... (9 tentativas restantes)
❌ A base de dados não está pronta. A tentar novamente em 5 segundos... (8 tentativas restantes)
❌ A base de dados não está pronta. A tentar novamente em 5 segundos... (7 tentativas restantes)
❌ A base de dados não está pronta. A tentar novamente em 5 segundos... (6 tentativas restantes)
❌ A base de dados não está pronta. A tentar novamente em 5 segundos... (5 tentativas restantes)
❌ A base de dados não está pronta. A tentar novamente em 5 segundos... (4 tentativas restantes)
❌ A base de dados não está pronta. A tentar novamente em 5 segundos... (3 tentativas restantes)
❌ A base de dados não está pronta. A tentar novamente em 5 segundos... (2 tentativas restantes)
❌ A base de dados não está pronta. A tentar novamente em 5 segundos... (1 tentativas restantes)
❌ A base de dados não está pronta. A tentar novamente em 5 segundos... (0 tentativas restantes)
🚨 Não foi possível estabelecer ligação à base de dados após várias tentativas. A aplicação pode não funcionar corretamente.
INFO:     172.20.0.1:52276 - "GET /nodes/?network=nkn HTTP/1.0" 500 Internal Server Error
ERROR:    Exception in ASGI application
Traceback (most recent call last):
  File "/usr/local/lib/python3.9/site-packages/sqlalchemy/engine/base.py", line 143, in __init__
    self._dbapi_connection = engine.raw_connection()
  File "/usr/local/lib/python3.9/site-packages/sqlalchemy/engine/base.py", line 3301, in raw_connection
    return self.pool.connect()
  File "/usr/local/lib/python3.9/site-packages/sqlalchemy/pool/base.py", line 447, in connect
    return _ConnectionFairy._checkout(self)
  File "/usr/local/lib/python3.9/site-packages/sqlalchemy/pool/base.py", line 1264, in _checkout
    fairy = _ConnectionRecord.checkout(pool)
  File "/usr/local/lib/python3.9/site-packages/sqlalchemy/pool/base.py", line 711, in checkout
    rec = pool._do_get()
  File "/usr/local/lib/python3.9/site-packages/sqlalchemy/pool/impl.py", line 178, in _do_get
    self._dec_overflow()
  File "/usr/local/lib/python3.9/site-packages/sqlalchemy/util/langhelpers.py", line 224, in __exit__
    raise exc_value.with_traceback(exc_tb)
  File "/usr/local/lib/python3.9/site-packages/sqlalchemy/pool/impl.py", line 175, in _do_get
    return self._create_connection()
  File "/usr/local/lib/python3.9/site-packages/sqlalchemy/pool/base.py", line 388, in _create_connection
    return _ConnectionRecord(self)
  File "/usr/local/lib/python3.9/site-packages/sqlalchemy/pool/base.py", line 673, in __init__
    self.__connect()
  File "/usr/local/lib/python3.9/site-packages/sqlalchemy/pool/base.py", line 900, in __connect
    pool.logger.debug("Error on connect(): %s", e)
  File "/usr/local/lib/python3.9/site-packages/sqlalchemy/util/langhelpers.py", line 224, in __exit__
    raise exc_value.with_traceback(exc_tb)
  File "/usr/local/lib/python3.9/site-packages/sqlalchemy/pool/base.py", line 895, in __connect
    self.dbapi_connection = connection = pool._invoke_creator(self)
  File "/usr/local/lib/python3.9/site-packages/sqlalchemy/engine/create.py", line 661, in connect
    return dialect.connect(*cargs, **cparams)
  File "/usr/local/lib/python3.9/site-packages/sqlalchemy/engine/default.py", line 629, in connect
    return self.loaded_dbapi.connect(*cargs, **cparams)  # type: ignore[no-any-return]  # NOQA: E501
  File "/usr/local/lib/python3.9/site-packages/psycopg2/__init__.py", line 122, in connect
    conn = _connect(dsn, connection_factory=connection_factory, **kwasync)
psycopg2.OperationalError: connection to server on socket "@@db/.s.PGSQL.5432" failed: Connection refused
        Is the server running locally and accepting connections on that socket?


The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/usr/local/lib/python3.9/site-packages/uvicorn/protocols/http/h11_impl.py", line 403, in run_asgi
    result = await app(  # type: ignore[func-returns-value]
  File "/usr/local/lib/python3.9/site-packages/uvicorn/middleware/proxy_headers.py", line 60, in __call__
    return await self.app(scope, receive, send)
  File "/usr/local/lib/python3.9/site-packages/fastapi/applications.py", line 1054, in __call__
    await super().__call__(scope, receive, send)
  File "/usr/local/lib/python3.9/site-packages/starlette/applications.py", line 113, in __call__
    await self.middleware_stack(scope, receive, send)
  File "/usr/local/lib/python3.9/site-packages/starlette/middleware/errors.py", line 186, in __call__
    raise exc
  File "/usr/local/lib/python3.9/site-packages/starlette/middleware/errors.py", line 164, in __call__
    await self.app(scope, receive, _send)
  File "/usr/local/lib/python3.9/site-packages/starlette/middleware/exceptions.py", line 63, in __call__
    await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
  File "/usr/local/lib/python3.9/site-packages/starlette/_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "/usr/local/lib/python3.9/site-packages/starlette/_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "/usr/local/lib/python3.9/site-packages/starlette/routing.py", line 716, in __call__
    await self.middleware_stack(scope, receive, send)
  File "/usr/local/lib/python3.9/site-packages/starlette/routing.py", line 736, in app
    await route.handle(scope, receive, send)
  File "/usr/local/lib/python3.9/site-packages/starlette/routing.py", line 290, in handle
    await self.app(scope, receive, send)
  File "/usr/local/lib/python3.9/site-packages/starlette/routing.py", line 78, in app
    await wrap_app_handling_exceptions(app, request)(scope, receive, send)
  File "/usr/local/lib/python3.9/site-packages/starlette/_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "/usr/local/lib/python3.9/site-packages/starlette/_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "/usr/local/lib/python3.9/site-packages/starlette/routing.py", line 75, in app
    response = await f(request)
  File "/usr/local/lib/python3.9/site-packages/fastapi/routing.py", line 302, in app
    raw_response = await run_endpoint_function(
  File "/usr/local/lib/python3.9/site-packages/fastapi/routing.py", line 215, in run_endpoint_function
    return await run_in_threadpool(dependant.call, **values)
  File "/usr/local/lib/python3.9/site-packages/starlette/concurrency.py", line 38, in run_in_threadpool
    return await anyio.to_thread.run_sync(func)
  File "/usr/local/lib/python3.9/site-packages/anyio/to_thread.py", line 56, in run_sync
    return await get_async_backend().run_sync_in_worker_thread(
  File "/usr/local/lib/python3.9/site-packages/anyio/_backends/_asyncio.py", line 2476, in run_sync_in_worker_thread
    return await future
  File "/usr/local/lib/python3.9/site-packages/anyio/_backends/_asyncio.py", line 967, in run
    result = context.run(func, *args)
  File "/code/app/main.py", line 107, in read_nodes
    return db.query(Node).filter(Node.network == network).all() if network else db.query(Node).all()
  File "/usr/local/lib/python3.9/site-packages/sqlalchemy/orm/query.py", line 2704, in all
    return self._iter().all()  # type: ignore
  File "/usr/local/lib/python3.9/site-packages/sqlalchemy/orm/query.py", line 2857, in _iter
    result: Union[ScalarResult[_T], Result[_T]] = self.session.execute(
  File "/usr/local/lib/python3.9/site-packages/sqlalchemy/orm/session.py", line 2365, in execute
    return self._execute_internal(
  File "/usr/local/lib/python3.9/site-packages/sqlalchemy/orm/session.py", line 2241, in _execute_internal
    conn = self._connection_for_bind(bind)
  File "/usr/local/lib/python3.9/site-packages/sqlalchemy/orm/session.py", line 2110, in _connection_for_bind
    return trans._connection_for_bind(engine, execution_options)
  File "<string>", line 2, in _connection_for_bind
  File "/usr/local/lib/python3.9/site-packages/sqlalchemy/orm/state_changes.py", line 137, in _go
    ret_value = fn(self, *arg, **kw)
  File "/usr/local/lib/python3.9/site-packages/sqlalchemy/orm/session.py", line 1189, in _connection_for_bind
    conn = bind.connect()
  File "/usr/local/lib/python3.9/site-packages/sqlalchemy/engine/base.py", line 3277, in connect
    return self._connection_cls(self)
  File "/usr/local/lib/python3.9/site-packages/sqlalchemy/engine/base.py", line 145, in __init__
    Connection._handle_dbapi_exception_noconnection(
  File "/usr/local/lib/python3.9/site-packages/sqlalchemy/engine/base.py", line 2440, in _handle_dbapi_exception_noconnection
    raise sqlalchemy_exception.with_traceback(exc_info[2]) from e
  File "/usr/local/lib/python3.9/site-packages/sqlalchemy/engine/base.py", line 143, in __init__
    self._dbapi_connection = engine.raw_connection()
  File "/usr/local/lib/python3.9/site-packages/sqlalchemy/engine/base.py", line 3301, in raw_connection
    return self.pool.connect()
  File "/usr/local/lib/python3.9/site-packages/sqlalchemy/pool/base.py", line 447, in connect
    return _ConnectionFairy._checkout(self)
  File "/usr/local/lib/python3.9/site-packages/sqlalchemy/pool/base.py", line 1264, in _checkout
    fairy = _ConnectionRecord.checkout(pool)
  File "/usr/local/lib/python3.9/site-packages/sqlalchemy/pool/base.py", line 711, in checkout
    rec = pool._do_get()
  File "/usr/local/lib/python3.9/site-packages/sqlalchemy/pool/impl.py", line 178, in _do_get
    self._dec_overflow()
  File "/usr/local/lib/python3.9/site-packages/sqlalchemy/util/langhelpers.py", line 224, in __exit__
    raise exc_value.with_traceback(exc_tb)
  File "/usr/local/lib/python3.9/site-packages/sqlalchemy/pool/impl.py", line 175, in _do_get
    return self._create_connection()
  File "/usr/local/lib/python3.9/site-packages/sqlalchemy/pool/base.py", line 388, in _create_connection
    return _ConnectionRecord(self)
  File "/usr/local/lib/python3.9/site-packages/sqlalchemy/pool/base.py", line 673, in __init__
    self.__connect()
  File "/usr/local/lib/python3.9/site-packages/sqlalchemy/pool/base.py", line 900, in __connect
    pool.logger.debug("Error on connect(): %s", e)
  File "/usr/local/lib/python3.9/site-packages/sqlalchemy/util/langhelpers.py", line 224, in __exit__
    raise exc_value.with_traceback(exc_tb)
  File "/usr/local/lib/python3.9/site-packages/sqlalchemy/pool/base.py", line 895, in __connect
    self.dbapi_connection = connection = pool._invoke_creator(self)
  File "/usr/local/lib/python3.9/site-packages/sqlalchemy/engine/create.py", line 661, in connect
    return dialect.connect(*cargs, **cparams)
  File "/usr/local/lib/python3.9/site-packages/sqlalchemy/engine/default.py", line 629, in connect
    return self.loaded_dbapi.connect(*cargs, **cparams)  # type: ignore[no-any-return]  # NOQA: E501
  File "/usr/local/lib/python3.9/site-packages/psycopg2/__init__.py", line 122, in connect
    conn = _connect(dsn, connection_factory=connection_factory, **kwasync)
sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) connection to server on socket "@@db/.s.PGSQL.5432" failed: Connection refused
        Is the server running locally and accepting connections on that socket?

(Background on this error at: https://sqlalche.me/e/20/e3q8)
INFO:     172.20.0.1:52290 - "GET /status/global/nkn HTTP/1.0" 200 OK


log do frontend para referecia:
INFO  Accepting connections at http://localhost:3000
 HTTP  8/20/2025 7:44:51 PM 172.20.0.1 GET /
 HTTP  8/20/2025 7:44:51 PM 172.20.0.1 Returned 200 in 53 ms
 HTTP  8/20/2025 7:44:51 PM 172.20.0.1 GET /static/js/main.1ce7da14.js
 HTTP  8/20/2025 7:44:51 PM 172.20.0.1 GET /static/css/main.93a0497a.css
 HTTP  8/20/2025 7:44:51 PM 172.20.0.1 Returned 304 in 9 ms
 HTTP  8/20/2025 7:44:51 PM 172.20.0.1 Returned 304 in 22 ms

log do db:
The files belonging to this database system will be owned by user "postgres".
This user must also own the server process.

The database cluster will be initialized with locale "en_US.utf8".
The default database encoding has accordingly been set to "UTF8".
The default text search configuration will be set to "english".

Data page checksums are disabled.

fixing permissions on existing directory /var/lib/postgresql/data ... ok
creating subdirectories ... ok
selecting dynamic shared memory implementation ... posix
selecting default max_connections ... 100
selecting default shared_buffers ... 128MB
selecting default time zone ... Etc/UTC
creating configuration files ... ok
running bootstrap script ... ok
performing post-bootstrap initialization ... ok
syncing data to disk ... ok

initdb: warning: enabling "trust" authentication for local connections
You can change this by editing pg_hba.conf or using the option -A, or
--auth-local and --auth-host, the next time you run initdb.

Success. You can now start the database server using:

    pg_ctl -D /var/lib/postgresql/data -l logfile start

waiting for server to start....2025-08-20 19:43:02.680 UTC [55] LOG:  starting PostgreSQL 13.22 (Debian 13.22-1.pgdg13+1) on x86_64-pc-linux-gnu, compiled by gcc (Debian 14.2.0-19) 14.2.0, 64-bit
2025-08-20 19:43:02.682 UTC [55] LOG:  listening on Unix socket "/var/run/postgresql/.s.PGSQL.5432"
2025-08-20 19:43:02.687 UTC [56] LOG:  database system was shut down at 2025-08-20 19:42:59 UTC
2025-08-20 19:43:02.692 UTC [55] LOG:  database system is ready to accept connections
 done
server started
CREATE DATABASE


/usr/local/bin/docker-entrypoint.sh: ignoring /docker-entrypoint-initdb.d/*

waiting for server to shut down...2025-08-20 19:43:04.122 UTC [55] LOG:  received fast shutdown request
.2025-08-20 19:43:04.124 UTC [55] LOG:  aborting any active transactions
2025-08-20 19:43:04.126 UTC [55] LOG:  background worker "logical replication launcher" (PID 62) exited with exit code 1
2025-08-20 19:43:04.126 UTC [57] LOG:  shutting down
2025-08-20 19:43:04.137 UTC [55] LOG:  database system is shut down
 done
server stopped

PostgreSQL init process complete; ready for start up.

2025-08-20 19:43:04.316 UTC [1] LOG:  starting PostgreSQL 13.22 (Debian 13.22-1.pgdg13+1) on x86_64-pc-linux-gnu, compiled by gcc (Debian 14.2.0-19) 14.2.0, 64-bit
2025-08-20 19:43:04.316 UTC [1] LOG:  listening on IPv4 address "0.0.0.0", port 5432
2025-08-20 19:43:04.317 UTC [1] LOG:  listening on IPv6 address "::", port 5432
2025-08-20 19:43:04.319 UTC [1] LOG:  listening on Unix socket "/var/run/postgresql/.s.PGSQL.5432"
2025-08-20 19:43:04.324 UTC [70] LOG:  database system was shut down at 2025-08-20 19:43:04 UTC
2025-08-20 19:43:04.330 UTC [1] LOG:  database system is ready to accept connections

¨

O que eu preciso:
Analise todos os ficheiros e o log em conjunto, encontre a inconsistência ou o erro de configuração e forneça as versões corrigidas dos ficheiros necessários para resolver o problema de ligação de uma vez por todas.
