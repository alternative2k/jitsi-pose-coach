# Deployment Guide - Hetzner CPX32

## Prerequisites

- Fresh Ubuntu 22.04 LTS server on Hetzner
- SSH access to server
- Domain name (optional, can use IP)

## Quick Setup

### 1. System Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install prerequisites
sudo apt install -y python3-pip ffmpeg nginx git

# Create directory structure
sudo mkdir -p /var/www/movement-analysis
sudo chown -R $USER:$USER /var/www/movement-analysis
```

### 2. Clone Repository

```bash
cd /var/www
git clone <your-repo-url> movement-analysis
cd movement-analysis
```

### 3. Install Python Dependencies

```bash
cd /var/www/movement-analysis
pip3 install -r backend/requirements.txt
```

### 4. Download YOLOv8 Model

```bash
mkdir -p backend/models
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8m-pose.pt -O backend/models/yolov8m-pose.pt
```

### 5. Create First User

```bash
# Start backend temporarily
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 &

# Create user (in another terminal)
curl -X POST http://localhost:8000/auth/users \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your-secure-password"}'

# Stop backend
pkill -f uvicorn
```

### 6. Configure Nginx

```bash
sudo tee /etc/nginx/sites-available/movement-analysis > /dev/null <<EOF
server {
    listen 80;
    server_name your-domain.com;  # Replace with your domain or server IP

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Increase timeout for long video uploads
        proxy_read_timeout 300s;
        proxy_connect_timeout 300s;
    }
}
EOF

# Enable site
sudo ln -s /etc/nginx/sites-available/movement-analysis /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 7. Create Systemd Service

```bash
sudo tee /etc/systemd/system/movement-analysis.service > /dev/null <<EOF
[Unit]
Description=Movement Analysis App
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/var/www/movement-analysis
Environment="PATH=/var/www/movement-analysis/venv/bin"
ExecStart=/usr/bin/python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable movement-analysis
sudo systemctl start movement-analysis
sudo systemctl status movement-analysis
```

### 8. Firewall Configuration

```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable
```

### 9. SSL/TLS (Optional with Let's Encrypt)

```bash
sudo apt install -y certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal (already configured)
sudo certbot renew --dry-run
```

### 10. Monitoring

```bash
# Check logs
sudo journalctl -u movement-analysis -f

# Check disk usage
df -h

# Setup disk space monitoring cron
(crontab -l 2>/dev/null; echo "0 6 * * * df -h | grep '/dev' | awk '{print \$5}' | sed 's/%//' | while read percent; do [ \$percent -gt 80 ] && echo \"Disk usage: \$percent%\" | mail -s 'Disk Warning' admin@example.com; done") | sudo crontab -
```

## Testing

### Test Locally First

```bash
# Run server
python3 -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Test endpoints
curl http://localhost:8000
curl -X POST http://localhost:8000/auth/users -H "Content-Type: application/json" -d '{"username":"test","password":"test"}'
```

### Test on Server

```bash
# Check app is running
curl http://localhost:8000

# Check from external
curl http://your-server-ip/

# Test WebSocket (using wscat)
sudo apt install -y websocat
websocat ws://your-server-ip/ws/skeleton
```

## Troubleshooting

### Restart Service

```bash
sudo systemctl restart movement-analysis
sudo systemctl status movement-analysis
```

### Check Logs

```bash
sudo journalctl -u movement-analysis -n 50
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Common Issues

**Port 8000 in use:**
```bash
sudo lsof -i :8000
sudo kill -9 <PID>
```

**FFmpeg not found:**
```bash
which ffmpeg
sudo apt install -y ffmpeg
```

**Python path issues:**
```bash
which python3
which uvicorn
```

**Permissions:**
```bash
sudo chown -R $USER:$USER /var/www/movement-analysis
sudo chmod +x backend/*.py
```

## Performance Tuning

### For Hetzner CPX32 (2 vCPU, 4GB RAM)

```python
# Optimize uvicorn start command
ExecStart=/usr/bin/python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 2 --loop uvloop
```

### Disk Space Management

```bash
# Create cleanup script
cat > /var/www/movement-analysis/cleanup.sh <<EOF
#!/bin/bash
# Delete sessions older than 7 days
find /var/www/movement-analysis/backend/sessions/ -type d -mtime +7 -exec rm -rf {} \; 2>/dev/null
# Log cleanup
echo "Cleanup completed: $(date)" >> /var/log/movement-analysis-cleanup.log
EOF

chmod +x /var/www/movement-analysis/cleanup.sh

# Add to crontab
(crontab -l 2>/dev/null; echo "0 2 * * * /var/www/movement-analysis/cleanup.sh") | sudo crontab -
```

### Resource Monitoring

```bash
# Install monitoring
sudo apt install -y htop iotop

# Monitor resources
htop
iotop

# Check CPU during recording
ps aux | grep python | grep uvicorn
```

## Updates

### Update Application

```bash
cd /var/www/movement-analysis
git pull origin main  # or your branch
pip3 install -r backend/requirements.txt --upgrade
sudo systemctl restart movement-analysis
```

### Update System

```bash
sudo apt update && sudo apt upgrade -y
sudo apt autoremove -y
```

## Backup Strategy

```bash
# Create backup script
cat > /var/www/movement-analysis/backup.sh <<EOF
#!/bin/bash
BACKUP_DIR="/var/backups/movement-analysis"
DATE=\$(date +%Y%m%d_%H%M%S)
mkdir -p \$BACKUP_DIR

# Backup user sessions
tar -czf \$BACKUP_DIR/sessions_\$DATE.tar.gz backend/sessions/ 2>/dev/null

# Backup config
cp backend/users.json \$BACKUP_DIR/users_\$DATE.json

# Keep last 7 days
find \$BACKUP_DIR/ -type f -mtime +7 -delete
EOF

chmod +x /var/www/movement-analysis/backup.sh

# Add to crontab (daily at 3 AM)
(crontab -l 2>/dev/null; echo "0 3 * * * /var/www/movement-analysis/backup.sh") | sudo crontab -
```

## Security Considerations

1. **Change default password**: Never use the default admin password
2. **Firewall**: Keep minimal open ports
3. **Updates**: Regularly update system and packages
4. **SSL**: Use HTTPS in production
5. **User isolation**: Consider running in Docker (advanced)
6. **Logs**: Review logs periodically

## Access URLs

- Web app: `http://your-server-ip` or `https://your-domain.com`
- API docs: `http://your-server-ip/docs` (Swagger UI)
- WebSocket: `ws://your-server-ip/ws/skeleton`

## Next Steps

1. Test the application thoroughly
2. Set up monitoring (e.g., UptimeRobot)
3. Configure DNS if using a domain
4. Set up automated backups
5. Consider implementing rate limiting
6. Add error tracking (e.g., Sentry)

## Support

If issues arise:
1. Check logs: `sudo journalctl -u movement-analysis -n 100`
2. Check nginx logs: `sudo tail -f /var/log/nginx/error.log`
3. Status: `sudo systemctl status movement-analysis`