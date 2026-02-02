# Movement Analysis Webapp - Deployment Guide

Complete solution for continuous video recording with real-time skeleton detection using YOLOv8-Pose.

## Quick Start

### Option 1: One-Click Deployment (Recommended)

```bash
# SSH into your Hetzner server
ssh root@your-hetzner-ip

# Download and run deployment script
wget https://raw.githubusercontent.com/alternative2k/jitsi-pose-coach/feature/movement-analysis/deploy.sh
chmod +x deploy.sh
./deploy.sh your-domain.com  # Replace with your domain or server IP

# Create admin user
curl -X POST http://localhost:8000/auth/users \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your-secure-password"}'

# Access your app at: http://your-server-ip
```

### Option 2: Manual Setup

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for detailed manual setup instructions.

---

## Features

- **Continuous Video Recording**: Records webcam/mobile video with no data loss
- **Real-time Skeleton Detection**: YOLOv8-Pose for live pose tracking
- **Movement Analysis**: Joint coordinates, body lean angle, limb speed metrics
- **Simple Authentication**: User-based login system
- **Modern UI Clean**: Tailwind CSS responsive interface
- **Server Storage**: Videos saved as MP4 on server with FFmpeg

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Frontend                         │
│    HTML/CSS/JS + MediaRecorder + WebSocket Client   │
└──────────────────┬──────────────────────────────────┘
                   │ HTTP (chunks) / WebSocket
                   ▼
┌─────────────────────────────────────────────────────┐
│              FastAPI Backend                         │
│  ┌──────────┬──────────┬──────────┬──────────────┐   │
│  │  Auth    │ Sessions │ WebSocket│ Video Proc   │   │
│  │   Module  │ Manager  │  Manager │   (FFmpeg)   │   │
│  └──────────┴──────────┴──────────┴──────────────┘   │
│         ▼              ▼               ▼             │
│    users.json   sessions/     video_processor.py      │
│                                           ▼           │
│                                    YOLOv8-Pose        │
└─────────────────────────────────────────────────────┘
```

---

## Project Structure

```
fitness-feedback/
├── backend/
│   ├── main.py              # FastAPI app
│   ├── auth.py              # User authentication
│   ├── session_manager.py   # Session handling
│   ├── handlers/
│   │   └── websocket_manager.py
│   ├── pose_detector.py     # YOLOv8-Pose
│   ├── video_processor.py   # FFmpeg handling
│   ├── config.py            # Environment config
│   ├── models/              # YOLOv8 models
│   │   └── yolov8m-pose.pt
│   ├── sessions/            # User session folders
│   │   └── {username}/
│   │       ├── {session_id}/
│   │       │   ├── temp_chunks/    # Video chunks
│   │       │   ├── final/         # Merged MP4s
│   │       │   └── metadata.json
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── index.html          # Main UI
│   ├── styles.css
│   ├── recorder.js         # MediaRecorder logic
│   ├── websocket.js        # WebSocket client
│   └── skeleton.js         # Skeleton display
├── deploy.sh               # Auto deployment script
├── nginx.conf              # Nginx config
├── movement-analysis.service  # Systemd service
└── docs/
    ├── DEPLOYMENT.md       # Detailed deployment guide
    └── plans/
        └── 2026-02-02-movement-analysis-implementation.md
```

---

## Local Development

### Prerequisites

- Python 3.8+
- FFmpeg
- Web browser with camera support

### Setup

```bash
# Clone repository
git clone https://github.com/alternative2k/jitsi-pose-coach.git
cd jitsi-pose-coach

# Install dependencies
pip install -r backend/requirements.txt

# Download YOLOv8 model
mkdir backend/models
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8m-pose.pt \
     -O backend/models/yolov8m-pose.pt

# Start server
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Create admin user (in another terminal)
curl -X POST http://localhost:8000/auth/users \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}'
```

### Test Application

1. Open `http://localhost:8000`
2. Login with admin/password
3. Click "Start Recording"
4. Grant camera permissions
5. Verify skeleton overlay appears
6. Wait 5-10 seconds
7. Check session folder: `ls backend/sessions/admin/`

---

## Server Deployment

### Hetzner CPX32 Setup

**Minimum specs:** 2 vCPU, 4GB RAM, 80GB SSD

### Quick Deployment

```bash
# SSH into server
ssh root@your-hetzner-ip

# Download and run
wget https://raw.githubusercontent.com/alternative2k/jitsi-pose-coach/feature/movement-analysis/deploy.sh
chmod +x deploy.sh
./deploy.sh your-domain.com

# Access at: http://your-hetzner-ip
```

### What Gets Installed

- **System**: Python 3, FFmpeg, Nginx
- **Service**: Systemd auto-restart
- **Firewall**: Ports 22, 80, 443
- **Cleanup**: Auto-delete sessions >7 days
- **Logs**: Journalctl + nginx logs

### Service Management

```bash
# Check status
sudo systemctl status movement-analysis

# View logs
sudo journalctl -u movement-analysis -f

# Restart
sudo systemctl restart movement-analysis

# Enable auto-start
sudo systemctl enable movement-analysis
```

### SSL/TLS (Optional)

```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d your-domain.com

# Auto-renew (configured automatically)
sudo certbot renew --dry-run
```

---

## Usage Guide

### First Time Setup

1. **Deploy the application** (see Quick Start above)
2. **Create admin user**:
   ```bash
   curl -X POST http://your-server/auth/users \
     -H "Content-Type: application/json" \
     -d '{"username": "admin", "password": "secure-password"}'
   ```
3. **Access the UI** at `http://your-server-ip`
4. **Login** with credentials

### Recording Process

1. Login to dashboard
2. Click "Start Recording"
3. Grant camera permissions
4. Skeleton overlay appears automatically
5. Toggle "Detailed/Simplified" view for movement data
6. Click "Logout" to stop recording
7. Final MP4 saved to: `backend/sessions/{username}/{session_id}/final/`

### Movement Data

**Detailed View:**
- Joint coordinates (x, y, confidence)
- Real-time updates (every 100ms)
- Shows first 10 joints

**Simplified View:**
- Body Lean Angle (degrees)
- Limb Speed (m/s)
- Range of Motion (degrees)

---

## API Documentation

### Authentication

**Create User (one-time setup)**
```bash
POST /auth/users
Content-Type: application/json

{"username": "admin", "password": "password"}

Response: {"message": "User created successfully"}
```

**Login**
```bash
POST /auth/login
Content-Type: application/json

{"username": "admin", "password": "password"}

Response: {"session_id": "uuid", "username": "admin"}
```

### Video Upload

**Upload Chunk**
```bash
POST /video/chunk
Content-Type: multipart/form-data

chunk: [video blob]
chunk_index: 0
session_id: uuid

Response: {"status": "success", "chunk_index": 0}
```

### WebSocket

**Skeleton Detection**
```javascript
WebSocket URL: ws://your-server/ws/skeleton

// Connect
{
  "action": "connect",
  "sessionId": "uuid",
  "username": "admin"
}

// Send frame
{
  "action": "frame",
  "image": "base64_jpeg"
}

// Response
{
  "action": "skeleton",
  "joints": [...],
  "metrics": {...}
}
```

**API Docs**: `http://your-server:8000/docs` (Swagger UI)

---

## Troubleshooting

### Service Won't Start

```bash
# Check errors
sudo journalctl -u movement-analysis -n 50

# Check port conflicts
sudo lsof -i :8000

# Restart
sudo systemctl restart movement-analysis
```

### Camera Not Working

- Check browser permissions
- Ensure HTTPS (required for mobile)
- Check browser console for errors
- Test with `https://webcamtests.com/`

### Video Issues

```bash
# Check FFmpeg
which ffmpeg
sudo apt install -y ffmpeg

# Check disk space
df -h

# Check session folders
ls backend/sessions/admin/
```

### WebSocket Connection Failed

- Check firewall: `sudo ufw status`
- Check nginx config: `sudo nginx -t`
- Check service: `sudo systemctl status movement-analysis`
- View logs: `sudo tail -f /var/log/nginx/error.log`

---

## Performance Tuning

### Hetzner CPX32 (2 vCPU, 4GB RAM)

**Optimized uvicorn command:**
```
python3 -m uvicorn backend.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 2 \
  --loop uvloop
```

**Monitoring:**
```bash
# Install tools
sudo apt install -y htop iotop

# Monitor resources
htop
iotop

# Check CPU
ps aux | grep python | grep uvicorn

# Check memory
free -h
```

### Disk Space Management

Auto-cleanup configured to delete sessions >7 days. Manual cleanup:
```bash
# Delete old sessions
find backend/sessions/ -type d -mtime +7 -exec rm -rf {} \;

# Check disk usage
df -h

# Large files
du -h --max-depth=1 backend/sessions/ | sort -hr
```

---

## Security

**Best Practices:**
1. Change default admin password
2. Use HTTPS in production (Let's Encrypt)
3. Keep system updated: `sudo apt update && sudo apt upgrade`
4. Check logs regularly
5. Use strong passwords
6. Limit user creation endpoint (already protected)

**Firewall:**
```bash
# Current rules
sudo ufw status

# Add new rules
sudo ufw allow from your-ip to any port 8000
```

---

## Backup Strategy

**Backup script** (auto-created by deploy.sh):
```bash
/var/www/movement-analysis/backup.sh
# Backs up sessions and user data
# Runs daily at 3 AM
# Keeps 7 days
```

**Manual backup:**
```bash
# Backup sessions
tar -czf backup-$(date +%Y%m%d).tar.gz backend/sessions/

# Backup users
cp backend/users.json users-backup.json
```

**Restore:**
```bash
tar -xzf backup-20260202.tar.gz
cp users-backup.json backend/users.json
```

---

## Updates

### Update Application

```bash
cd /var/www/movement-analysis
git pull origin main
pip3 install -r backend/requirements.txt --upgrade
sudo systemctl restart movement-analysis
```

### Update System

```bash
sudo apt update && sudo apt upgrade -y
sudo apt autoremove -y
```

---

## Support

### Useful Commands

```bash
# Status check
sudo systemctl status movement-analysis

# Logs
sudo journalctl -u movement-analysis -f

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# Restart
sudo systemctl restart movement-analysis

# Port check
sudo netstat -tuln | grep 8000

# Disk usage
df -h

# Process check
ps aux | grep movement

# Test app
curl http://localhost:8000
```

### Common Issues

| Issue | Solution |
|-------|----------|
| Won't start | `sudo journalctl -u movement-analysis` |
| 502 Bad Gateway | Check uvicorn running on port 8000 |
| No camera | Try HTTPS, check browser permissions |
| Recording stops | Check disk space, logs |
| WebSocket fails | Check firewall, nginx config |

---

## Directory Structure After Deployment

```
/var/www/movement-analysis/
├── backend/
│   ├── main.py
│   ├── sessions/
│   │   └── admin/
│   │       └── session-12345/
│   │           ├── temp_chunks/
│   │           │   ├── chunk_0.webm
│   │           │   └── chunk_1.webm
│   │           └── final/
│   │               └── session_abc123.mp4
│   ├── models/
│   │   └── yolov8m-pose.pt
│   └── users.json
├── frontend/
│   ├── index.html
│   ├── styles.css
│   └── *.js
└── docs/
    └── DEPLOYMENT.md
```

---

## Next Steps

1. **Test Thoroughly**: Try recording 5-10 minute sessions
2. **SSL Setup**: `sudo certbot --nginx -d your-domain.com`
3. **Monitoring**: Set up uptime monitoring
4. **DNS**: Point domain to server IP
5. **Backup**: Verify cron jobs working
6. **Documentation**: Update this guide with your settings

---

## License

MIT License - See repository for details.

---

## Contributing

Contributions welcome! Fork, change, submit PR.

---

## Questions?

- Check **docs/DEPLOYMENT.md** for detailed guide
- Review **docs/plans/** for implementation details
- Check logs: `sudo journalctl -u movement-analysis -f`
- Test endpoints: `http://your-server:8000/docs`

---

**Version**: 1.0.0
**Last Updated**: 2026-02-02
**Repository**: https://github.com/alternative2k/jitsi-pose-coach/tree/feature/movement-analysis