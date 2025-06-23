# 🔧 Windows Troubleshooting Guide

This guide covers common issues you might encounter when setting up the Local AI RAG system on Windows.

## 🚨 Critical Issues

### Docker Desktop Not Starting

**Symptoms:**

- `docker` command not found
- "Docker is not running" error
- Containers fail to start

**Solutions:**

```powershell
# 1. Check if Docker Desktop is installed
docker --version

# 2. Start Docker Desktop manually
# Look for Docker Desktop in Start Menu or System Tray

# 3. Restart Docker Desktop service
Restart-Service -Name "Docker Desktop Service" -Force

# 4. Reset Docker Desktop (last resort)
# Docker Desktop → Settings → Reset → Reset to factory defaults
```

### PowerShell Execution Policy Issues

**Symptoms:**

- "Execution of scripts is disabled on this system"
- Script won't run even as Administrator

**Solutions:**

```powershell
# Check current execution policy
Get-ExecutionPolicy

# Set execution policy (run as Administrator)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Or temporarily bypass for one script
PowerShell -ExecutionPolicy Bypass -File .\setup_windows_supabase.ps1
```

### Container Port Conflicts

**Symptoms:**

- "Port already in use" errors
- Services fail to start
- Connection refused errors

**Solutions:**

```powershell
# Check what's using specific ports
netstat -ano | findstr :3000
netstat -ano | findstr :5432

# Kill process using port (replace PID with actual process ID)
taskkill /PID 1234 /F

# Or change ports in docker-compose.yml
# Edit the ports section for conflicting services
```

## 🐛 Database Issues

### Vector Extension Missing

**Symptoms:**

- "extension 'vector' does not exist"
- Embedding-related errors

**Solutions:**

```powershell
# Install vector extension manually
docker exec supabase-db psql -U postgres -d postgres -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Verify installation
docker exec supabase-db psql -U postgres -d postgres -c "SELECT * FROM pg_extension WHERE extname = 'vector';"
```

### Database Connection Refused

**Symptoms:**

- "Connection refused" to database
- psql commands fail

**Solutions:**

```powershell
# Check if database container is running
docker ps | findstr supabase-db

# Check container logs
docker logs supabase-db

# Restart database container
docker restart supabase-db

# Wait for container to be healthy
docker exec supabase-db pg_isready -U postgres
```

### CSV Import Failures

**Symptoms:**

- "File not found" errors
- "Permission denied" on CSV import
- Malformed CSV data errors

**Solutions:**

```powershell
# 1. Verify CSV file exists and path is correct
Test-Path "$env:USERPROFILE\Downloads\crawled_pages_rows.csv"

# 2. Check CSV file format (should have headers)
Get-Content "$env:USERPROFILE\Downloads\crawled_pages_rows.csv" | Select-Object -First 3

# 3. Fix file permissions
icacls "$env:USERPROFILE\Downloads\crawled_pages_rows.csv" /grant Everyone:F

# 4. Manual CSV copy if automated fails
docker cp "$env:USERPROFILE\Downloads\crawled_pages_rows.csv" supabase-db:/tmp/crawled_pages_rows.csv
```

## 🌐 Network Issues

### DNS Resolution Problems

**Symptoms:**

- Cannot reach external services
- Docker pull failures
- Supabase CLI connection issues

**Solutions:**

```powershell
# 1. Flush DNS cache
ipconfig /flushdns

# 2. Check DNS settings
nslookup google.com

# 3. Use alternative DNS (Google DNS)
# Network Settings → Change adapter options → Properties → IPv4 → DNS
# Primary: 8.8.8.8, Secondary: 8.8.4.4

# 4. Restart network adapter
ipconfig /release
ipconfig /renew
```

### Firewall Blocking Connections

**Symptoms:**

- Services start but can't be accessed from browser
- Connection timeouts

**Solutions:**

```powershell
# 1. Check Windows Firewall status
Get-NetFirewallProfile

# 2. Add firewall rules for Docker ports
New-NetFirewallRule -DisplayName "Docker-3000" -Direction Inbound -Protocol TCP -LocalPort 3000 -Action Allow
New-NetFirewallRule -DisplayName "Docker-5432" -Direction Inbound -Protocol TCP -LocalPort 5432 -Action Allow

# 3. Temporarily disable firewall (testing only)
Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled False
```

## 💾 Storage Issues

### Insufficient Disk Space

**Symptoms:**

- Docker build failures
- "No space left on device" errors
- Slow performance

**Solutions:**

```powershell
# 1. Check available disk space
Get-WmiObject -Class Win32_LogicalDisk | Select-Object DeviceID, @{Name="Size(GB)";Expression={[math]::Round($_.Size/1GB,2)}}, @{Name="FreeSpace(GB)";Expression={[math]::Round($_.FreeSpace/1GB,2)}}

# 2. Clean Docker system
docker system prune -a --volumes

# 3. Clean Docker build cache
docker builder prune -a

# 4. Move Docker data directory (if needed)
# Docker Desktop → Settings → Resources → Advanced → Disk image location
```

### Docker Volume Issues

**Symptoms:**

- Data not persisting between restarts
- Permission errors with volumes

**Solutions:**

```powershell
# 1. List Docker volumes
docker volume ls

# 2. Inspect volume details
docker volume inspect supabase_db_data

# 3. Remove corrupted volumes (WARNING: This deletes data)
docker compose down -v
docker volume prune

# 4. Recreate volumes
docker compose up -d
```

## 🔐 Permission Issues

### Administrator Rights Required

**Symptoms:**

- "Access denied" errors
- Scripts fail to modify system

**Solutions:**

```powershell
# 1. Run PowerShell as Administrator
# Right-click PowerShell → "Run as Administrator"

# 2. Check current user privileges
whoami /priv

# 3. Add user to Docker users group
Add-LocalGroupMember -Group "docker-users" -Member $env:USERNAME
```

### File Permission Errors

**Symptoms:**

- Cannot read/write files
- Docker volume mount failures

**Solutions:**

```powershell
# 1. Check file permissions
Get-Acl "path\to\file" | Format-List

# 2. Grant full access to current user
icacls "path\to\file" /grant "$env:USERNAME:F"

# 3. Take ownership of files
takeown /f "path\to\file" /r /d y
```

## 🔄 Service-Specific Issues

### Supabase Studio Not Loading

**Symptoms:**

- Blank page at localhost:54323
- "Service unavailable" errors

**Solutions:**

```powershell
# 1. Check container status
docker ps | findstr supabase-studio

# 2. Check container logs
docker logs supabase-studio

# 3. Restart Supabase services
docker restart supabase-kong supabase-studio

# 4. Clear browser cache and cookies
```

### n8n Workflow Failures

**Symptoms:**

- Workflows don't execute
- Connection errors to external services

**Solutions:**

```powershell
# 1. Check n8n container logs
docker logs n8n

# 2. Verify environment variables
docker exec n8n env | findstr N8N

# 3. Restart n8n container
docker restart n8n
```

### Langfuse Connection Issues

**Symptoms:**

- Redis authentication errors
- Database connection failures

**Solutions:**

```powershell
# 1. Check Redis container
docker ps | findstr redis

# 2. Check Langfuse environment variables
docker exec langfuse-web env | findstr REDIS

# 3. Fix Redis authentication (if needed)
# Remove REDIS_AUTH from environment or configure Redis with auth
```

## 🧪 Diagnostic Commands

### System Health Check

```powershell
# Complete system check
Write-Host "=== System Information ===" -ForegroundColor Green
Get-ComputerInfo | Select-Object WindowsProductName, WindowsVersion, TotalPhysicalMemory

Write-Host "=== Docker Status ===" -ForegroundColor Green
docker --version
docker compose --version
docker system df

Write-Host "=== Container Status ===" -ForegroundColor Green
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

Write-Host "=== Network Status ===" -ForegroundColor Green
Test-NetConnection -ComputerName localhost -Port 3000
Test-NetConnection -ComputerName localhost -Port 54323

Write-Host "=== Database Status ===" -ForegroundColor Green
docker exec supabase-db pg_isready -U postgres
```

### Log Collection

```powershell
# Collect all service logs
$logDir = ".\logs-$(Get-Date -Format 'yyyy-MM-dd-HH-mm')"
New-Item -ItemType Directory -Path $logDir

# Export container logs
docker compose logs > "$logDir\docker-compose.log"
docker logs supabase-db > "$logDir\supabase-db.log"
docker logs n8n > "$logDir\n8n.log"
docker logs flowise > "$logDir\flowise.log"

Write-Host "Logs exported to: $logDir" -ForegroundColor Green
```

## 🆘 Emergency Recovery

### Complete System Reset

```powershell
# WARNING: This will delete all data and containers
Write-Host "⚠️  This will delete ALL Docker data. Press Ctrl+C to cancel." -ForegroundColor Red
Start-Sleep -Seconds 10

# Stop all containers
docker compose down -v

# Remove all containers and images
docker system prune -a --volumes --force

# Remove all networks
docker network prune --force

# Restart Docker Desktop
Restart-Service -Name "Docker Desktop Service" -Force

# Wait for Docker to start
Start-Sleep -Seconds 30

# Rebuild everything
docker compose up -d --build
```

### Backup and Restore

```powershell
# Backup current database
docker exec supabase-db pg_dump -U postgres -d postgres > "backup-$(Get-Date -Format 'yyyy-MM-dd').sql"

# Restore from backup
Get-Content "backup-yyyy-MM-dd.sql" | docker exec -i supabase-db psql -U postgres -d postgres
```

---

## 📞 Getting Additional Help

If none of these solutions work:

1. **Check Docker Desktop logs**: Docker Desktop → Settings → Troubleshoot → Show logs
2. **Review Windows Event Viewer**: Windows Logs → Application/System
3. **Collect system information**: `Get-ComputerInfo | Out-File system-info.txt`
4. **Create GitHub issue** with:
   - Your Windows version
   - Docker Desktop version
   - Complete error messages
   - Steps to reproduce
   - Log files from diagnostic commands

---

**Remember**: Most issues can be resolved by restarting Docker Desktop and running the setup script again! 🔄
