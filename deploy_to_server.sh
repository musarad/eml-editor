#!/bin/bash

# Server deployment script for EML Editor
# Run this on your server after SSH login

echo "==================================="
echo "EML Editor Server Deployment Script"
echo "==================================="

# Update system packages
echo "1. Updating system packages..."
apt-get update -y

# Install Python 3 and pip if not already installed
echo "2. Installing Python 3 and pip..."
apt-get install -y python3 python3-pip git

# Install virtual environment package
echo "3. Installing virtual environment..."
apt-get install -y python3-venv

# Clone the repository
echo "4. Cloning the repository..."
cd /opt
if [ -d "eml-editor" ]; then
    echo "Repository already exists, pulling latest changes..."
    cd eml-editor
    git pull
else
    git clone https://github.com/musarad/eml-editor.git
    cd eml-editor
fi

# Create virtual environment
echo "5. Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "6. Installing dependencies..."
pip install --upgrade pip
pip install -r requirements_web.txt

# Create necessary directories
echo "7. Creating necessary directories..."
mkdir -p uploads outputs dkim_keys

# Create systemd service file
echo "8. Creating systemd service..."
cat > /etc/systemd/system/eml-editor.service << EOF
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

# Reload systemd
systemctl daemon-reload

# Enable and start the service
echo "9. Starting the service..."
systemctl enable eml-editor
systemctl start eml-editor

# Check service status
systemctl status eml-editor

echo ""
echo "==================================="
echo "Deployment Complete!"
echo "==================================="
echo "The EML Editor is now running on port 8080"
echo "Access it at: http://138.199.149.235:8080"
echo ""
echo "Useful commands:"
echo "- Check status: systemctl status eml-editor"
echo "- View logs: journalctl -u eml-editor -f"
echo "- Restart: systemctl restart eml-editor"
echo "- Stop: systemctl stop eml-editor" 