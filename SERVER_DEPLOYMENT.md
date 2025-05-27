# Server Deployment Guide for EML Editor

## Quick Deployment (Recommended)

SSH into your server and run these commands:

```bash
ssh root@138.199.149.235

# Once logged in, run:
cd /opt
git clone https://github.com/musarad/eml-editor.git
cd eml-editor
chmod +x deploy_to_server.sh
./deploy_to_server.sh
```

## Manual Deployment Steps

If you prefer to deploy manually, follow these steps:

### 1. Connect to your server
```bash
ssh root@138.199.149.235
```

### 2. Install required packages
```bash
apt-get update
apt-get install -y python3 python3-pip python3-venv git
```

### 3. Clone the repository
```bash
cd /opt
git clone https://github.com/musarad/eml-editor.git
cd eml-editor
```

### 4. Set up Python virtual environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 5. Install Python dependencies
```bash
pip install --upgrade pip
pip install -r requirements_web.txt
```

### 6. Create necessary directories
```bash
mkdir -p uploads outputs dkim_keys
```

### 7. Run the application (for testing)
```bash
python web_app.py
```

The application will be available at: http://138.199.149.235:8080

### 8. Set up as a system service (for production)

Create a systemd service file:

```bash
nano /etc/systemd/system/eml-editor.service
```

Add this content:

```ini
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
```

Enable and start the service:

```bash
systemctl daemon-reload
systemctl enable eml-editor
systemctl start eml-editor
```

## Managing the Service

- **Check status**: `systemctl status eml-editor`
- **View logs**: `journalctl -u eml-editor -f`
- **Restart**: `systemctl restart eml-editor`
- **Stop**: `systemctl stop eml-editor`
- **Start**: `systemctl start eml-editor`

## Updating the Application

To update to the latest version:

```bash
cd /opt/eml-editor
git pull
systemctl restart eml-editor
```

## Firewall Configuration

If you have a firewall enabled, allow port 8080:

```bash
ufw allow 8080/tcp
```

## Nginx Reverse Proxy (Optional)

If you want to use Nginx as a reverse proxy:

1. Install Nginx:
```bash
apt-get install -y nginx
```

2. Create Nginx configuration:
```bash
nano /etc/nginx/sites-available/eml-editor
```

Add:
```nginx
server {
    listen 80;
    server_name 138.199.149.235;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

3. Enable the site:
```bash
ln -s /etc/nginx/sites-available/eml-editor /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

Then access the application at: http://138.199.149.235

## Troubleshooting

1. **Port already in use**: 
   - Check what's using port 8080: `netstat -tlnp | grep 8080`
   - Kill the process or change the port in `web_app.py`

2. **Permission issues**:
   - Ensure directories have correct permissions: `chmod -R 755 /opt/eml-editor`

3. **Module not found errors**:
   - Ensure virtual environment is activated: `source /opt/eml-editor/venv/bin/activate`
   - Reinstall dependencies: `pip install -r requirements_web.txt`

## Security Notes

- Change the Flask secret key in `web_app.py` for production
- Consider using HTTPS with SSL certificates
- Implement authentication if needed
- Regular updates for security patches 