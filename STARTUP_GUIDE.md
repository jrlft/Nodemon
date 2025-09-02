# Guia de Inicialização - NodeMon SSH Fix

## Instruções para Testar as Correções

### 1. Iniciar o Sistema

```bash
# Na pasta do projeto
cd /Users/jrlft/Downloads/nodemon-projeto

# Iniciar todos os serviços
docker-compose up -d

# Ou se usando Docker Compose v2
docker compose up -d
```

### 2. Verificar os Logs

```bash
# Verificar logs do backend
docker logs nodemon-backend -f

# Verificar logs do nginx
docker logs nodemon-proxy -f
```

### 3. Acessar a Interface

1. Abra o navegador em: `https://localhost:8080`
2. Faça login com as credenciais de administrador
3. Selecione uma rede (NKN, Sentinel, ou Mysterium)

### 4. Testar a Conexão SSH

1. **Clique no botão SSH** (ícone de terminal) de qualquer nó na lista
2. **Insira as credenciais SSH**:
   - Usuário: (ex: root, ubuntu, etc.)
   - Senha: (senha do VPS)
3. **Clique em "Conectar"**
4. **Aguarde a conexão**: O terminal deve abrir em alguns segundos

### 5. Verificar Funcionamento

✅ **Sucesso** - O terminal SSH deve:
- Mostrar o prompt do servidor remoto
- Responder a comandos digitados
- Exibir a saída dos comandos em tempo real

❌ **Erro** - Se houver problemas:
- Verifique as mensagens de erro exibidas
- Consulte os logs do backend
- Verifique se as credenciais estão corretas

## Principais Melhorias Implementadas

### 🔐 Autenticação WebSocket
- WebSocket agora requer autenticação adequada
- Credenciais são passadas via query parameters
- Validação de credenciais no backend

### 🌐 Compatibilidade de Protocolo
- Detecção automática de protocolo (ws/wss)
- Suporte adequado para HTTPS/WSS
- Configuração melhorada do nginx

### 🛠️ Tratamento de Erros
- Mensagens de erro mais claras
- Estados de carregamento visíveis
- Recuperação automática de erros

### ⚡ Performance
- Operações não-bloqueantes
- Timeouts adequados
- Limpeza automática de recursos

## Solução de Problemas Comuns

### Erro de Autenticação
- **Causa**: Credenciais inválidas ou não salvas
- **Solução**: Re-digite as credenciais SSH corretas

### Conexão WebSocket Falha
- **Causa**: Problemas de rede ou configuração
- **Solução**: Verifique logs do nginx e backend

### Terminal Não Responde
- **Causa**: Servidor SSH remoto não acessível
- **Solução**: Verifique conectividade com o IP do VPS

### Timeout de Conexão
- **Causa**: Firewall ou rede lenta
- **Solução**: Verifique regras de firewall do VPS

## Logs Importantes

### Backend (SSH)
```bash
# Logs de conexão SSH
docker logs nodemon-backend | grep -i ssh

# Logs de WebSocket
docker logs nodemon-backend | grep -i websocket
```

### Frontend (Browser Console)
- F12 → Console
- Procure por erros de WebSocket
- Verifique mensagens de conexão

## Contato

Se os problemas persistirem após essas correções:

1. ✅ Verifique se todos os arquivos foram atualizados
2. ✅ Reinicie os containers: `docker-compose restart`
3. ✅ Limpe o cache do navegador
4. ✅ Teste com diferentes navegadores

As correções implementadas resolvem os principais problemas de:
- Autenticação WebSocket
- Compatibilidade HTTPS/WSS  
- Tratamento de erros
- Timeouts e performance