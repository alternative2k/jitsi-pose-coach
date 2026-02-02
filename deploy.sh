#!/bin/bash
# One-click VPS deployment script for Jitsi Pose Coach

set -e

echo "🚀 Deploying Jitsi Pose Coach..."

# Install dependencies
apt-get update
apt-get install -y docker docker-compose nginx git

# Clone and setup Jitsi with Pose Coach
cd /opt
git clone https://github.com/jitsi/docker.git
cd docker
docker-compose up -d

# Configure Nginx
cp nginx.conf /etc/nginx/sites-available/pose-coach
ln -sf /etc/nginx/sites-available/pose-coach /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

echo "✅ Deployment complete!"
echo "📊 Access at: http://$(curl -s ifconfig.me)"