#!/bin/bash
set -e

echo "=== Movement Analysis Deployment Script ==="

# Update system
echo "Updating system..."
sudo apt update && sudo apt upgrade -y

# Install dependencies
echo "Installing dependencies..."
sudo apt install -y python3-pip ffmpeg nginx git ufw certbot python3-certbot-nginx

# Create directory
mkdir -p /var/www/movement-analysis
cd /var/www

# Clone repo (update with your repo URL)
if [ ! -d "movement-analysis" ]; then
    echo "Cloning repository..."
    git clone <YOUR_REPO_URL> movement-analysis
else
    echo "Repository exists, pulling latest..."
    cd movement-analysis
    git pull origin main
fi

cd movement-analysis

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install -r backend/requirements.txt

# Download YOLOv8 model
echo "Downloading YOLOv8 model..."
mkdir -p backend/models
if [ ! -f "backend/models/yolov8m-pose.pt" ]; then
    wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8m-pose.pt -O backend/models/yolov8m-pose.pt
else
    echo "Model already exists"
fi

# Setup Nginx
echo "Setting up Nginx..."
sudo tee /etc/nginx/sites-available/movement-analysis > /dev/null <<NGXCONFIG
server {
    listen 80;
    server_name $1;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300s;
    }
}
NGXCONFIG

sudo ln -sf /etc/nginx/sites-available/movement-analysis /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Setup Systemd service
echo "Setting up Systemd service..."
sudo tee /etc/systemd/system/movement-analysis.service > /dev/null <<SVC
[Unit]
Description=Movement Analysis App
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/var/www/movement-analysis
ExecStart=/usr/bin/python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always

[Install]
WantedBy=multi-user.target
SVC

sudo systemctl daemon-reload
sudo systemctl enable movement-analysis
sudo systemctl start movement-analysis

# Setup firewall
echo "Configuring firewall..."
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

# Create cleanup script
echo "Creating cleanup script..."
cat > /var/www/movement-analysis/cleanup.sh <<'CLEANUP'
#!/bin/bash
find /var/www/movement-analysis/backend/sessions/ -type d -mtime +7 -exec rm -rf {} \; 2>/dev/null
echo "Cleanup completed: $(date)" >> /var/log/movement-analysis-cleanup.log
CLEANUP

chmod +x /var/www/movement-analysis/cleanup.sh
(crontab -l 2>/dev/null; echo "0 2 * * * /var/www/movement-analysis/cleanup.sh") | crontab -

echo ""
echo "=== Deployment Complete! ==="
echo ""
echo "Next steps:"
echo "1. Create first user via API:"
echo "   curl -X POST http://localhost:8000/auth/users \\"
echo "     -H \"Content-Type: application/json\" \\"
echo "     -d '{\"username\": \"admin\", \"password\": \"your-password\"}'"
echo ""
echo "2. Access at: http://$1"
echo "3. Check status: sudo systemctl status movement-analysis"
echo "4. View logs: sudo journalctl -u movement-analysis -f"
echo ""
echo "Optional: Setup SSL with:"
echo "  sudo certbot --nginx -d $1"