#!/bin/bash

# Quick deployment commands for EML Editor on server
# Copy and paste these commands after SSH login to root@138.199.149.235

# One-liner to download and run the deployment script
curl -s https://raw.githubusercontent.com/musarad/eml-editor/main/deploy_to_server.sh -o deploy.sh && chmod +x deploy.sh && ./deploy.sh 