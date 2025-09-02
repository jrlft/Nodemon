# Server Deployment Guide - NodeMon SSH Fixes

## ✅ Changes Successfully Committed and Pushed

The SSH WebSocket fixes have been committed to the repository with commit hash: `9788bf6`

**Commit message**: "Fix SSH WebSocket connection issues"

---

## 🚀 How to Deploy on Your Server

### 1. **Navigate to your project directory**
```bash
cd /path/to/your/nodemon-projeto
# Replace with your actual project path
```

### 2. **Pull the latest changes**
```bash
git pull origin main
```
This will download all the SSH fixes including:
- Backend WebSocket authentication
- Frontend protocol detection 
- Enhanced error handling
- Nginx configuration improvements
- Documentation files

### 3. **Run the rebuild script**
```bash
chmod +x rebuild.sh
./rebuild.sh
```

**What the rebuild.sh script does:**
1. **Stops** all running services
2. **Backs up** the PostgreSQL database
3. **Tears down** the current environment
4. **Rebuilds** all Docker images with new code
5. **Restores** the database data
6. **Starts** all services fresh

### 4. **Monitor the deployment**
```bash
# Watch the logs during startup
docker compose logs -f

# Or check specific services
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f nginx
```

### 5. **Verify the deployment**
```bash
# Check all services are running
docker compose ps

# Should show:
# nodemon-backend    Up
# nodemon-frontend   Up  
# nodemon-proxy      Up
# nodemon-db         Up (healthy)
```

---

## 🧪 Testing the SSH Fixes

### 1. **Access the application**
- Open your browser
- Navigate to: `https://your-server-domain.com:8080`
- Or: `https://your-server-ip:8080`

### 2. **Test SSH connection**
1. Login with admin credentials
2. Select a network (NKN, Sentinel, Mysterium)
3. Click the **SSH button** (terminal icon) on any node
4. Enter SSH credentials:
   - Username: `root` or `ubuntu` (depending on your VPS)
   - Password: Your VPS password
5. Click **"Conectar"**
6. Terminal should open and connect successfully

### 3. **Expected improvements**
✅ **No more WebSocket errors** in browser console  
✅ **Proper authentication** for WebSocket connections  
✅ **Clear error messages** if connection fails  
✅ **Loading states** during connection  
✅ **Better timeout handling**  

---

## 🔧 Troubleshooting

### If deployment fails:
```bash
# Check Docker service
sudo systemctl status docker

# Restart Docker if needed
sudo systemctl restart docker

# Check disk space
df -h

# Check memory usage
free -h
```

### If SSH still doesn't work:
```bash
# Check backend logs for SSH errors
docker compose logs backend | grep -i ssh

# Check nginx logs for WebSocket issues  
docker compose logs nginx | grep -i websocket

# Verify firewall settings
sudo ufw status
```

### Common issues:
1. **Port 8080 blocked**: Check firewall rules
2. **SSL certificate issues**: Verify nginx SSL configuration
3. **Memory issues**: Ensure server has enough RAM
4. **Permission issues**: Check file permissions

---

## 📋 Quick Commands Reference

```bash
# Pull latest changes
git pull origin main

# Rebuild everything (preserves database)
./rebuild.sh

# Check service status
docker compose ps

# View logs
docker compose logs -f

# Restart specific service
docker compose restart backend

# Stop everything
docker compose down

# Start everything
docker compose up -d
```

---

## 🔐 Security Notes

The SSH fixes include:
- **WebSocket authentication** - Prevents unauthorized terminal access
- **Credential encryption** - SSH passwords stored securely
- **Connection timeouts** - Prevents hanging connections
- **Error sanitization** - Prevents sensitive info leakage

---

## 📞 Support

If you encounter any issues after deployment:

1. **Check the logs** first:
   ```bash
   docker compose logs backend | tail -50
   ```

2. **Verify the commit** was pulled:
   ```bash
   git log --oneline -5
   # Should show: 9788bf6 Fix SSH WebSocket connection issues
   ```

3. **Test WebSocket** in browser console:
   - F12 → Console
   - Look for WebSocket connection messages
   - Should see "WebSocket connection established"

The rebuild.sh script preserves your database, so all your nodes and settings will remain intact after the update.

---

**🎉 Your NodeMon system should now have fully functional SSH terminals!**