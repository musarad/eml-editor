#!/bin/bash

# Remote deployment script for EML Editor
# This script connects to your server and deploys the application

SERVER_IP="138.199.149.235"
SERVER_USER="root"

echo "======================================"
echo "Remote Deployment to $SERVER_IP"
echo "======================================"

# Execute deployment commands on the remote server
ssh $SERVER_USER@$SERVER_IP << 'ENDSSH'

echo "Connected to server. Starting deployment..."

# Update system packages
echo "1. Updating system packages..."
apt-get update -y

# Install required packages
echo "2. Installing Python 3, pip, git..."
apt-get install -y python3 python3-pip python3-venv git curl

# Go to /opt directory
cd /opt

# Clone or update repository
echo "3. Cloning/updating repository..."
if [ -d "eml-editor" ]; then
    echo "Repository exists, pulling latest changes..."
    cd eml-editor
    git pull origin main
else
    echo "Cloning repository..."
    git clone https://github.com/musarad/eml-editor.git
    cd eml-editor
fi

# Create virtual environment
echo "4. Setting up virtual environment..."
python3 -m venv venv

# Activate virtual environment and install dependencies
echo "5. Installing dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements_web.txt

# Create necessary directories
echo "6. Creating directories..."
mkdir -p uploads outputs dkim_keys

# Create systemd service
echo "7. Setting up systemd service..."
cat > /etc/systemd/system/eml-editor.service << 'EOF'
[Unit]
Description=EML Editor Web Application
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/eml-editor
Environment="PATH=/opt/eml-editor/venv/bin"
ExecStart=/opt/eml-editor/venv/bin/python /opt/eml-editor/web_app.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and start service
echo "8. Starting the service..."
systemctl daemon-reload
systemctl enable eml-editor
systemctl stop eml-editor 2>/dev/null || true
systemctl start eml-editor

# Check service status
echo "9. Checking service status..."
systemctl status eml-editor --no-pager

echo ""
echo "======================================"
echo "Deployment Complete!"
echo "======================================"
echo "EML Editor is running at: http://$SERVER_IP:8080"
echo ""
echo "To check logs: journalctl -u eml-editor -f"

ENDSSH

echo ""
echo "Remote deployment finished!"
echo "Access your application at: http://$SERVER_IP:8080" 