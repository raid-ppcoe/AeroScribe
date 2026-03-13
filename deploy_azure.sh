#!/bin/bash
set -e

AZ_PATH="/Users/manfredsiew/Library/Python/3.9/bin/az"

echo "====================================================="
echo "  AeroScribe Azure Web App Deployment Script"
echo "====================================================="

# Variables
APP_NAME="aeroscribe-app-i4wbo"
RG_NAME="AeroScribe-Hackathon-RG"

echo "🚀 Deploying to Azure App Service as $APP_NAME..."
echo "This step parses your code and creates a cloud environment. It might take 3-5 minutes!"

$AZ_PATH webapp up \
    --name "$APP_NAME" \
    --resource-group "$RG_NAME" \
    --os-type linux \
    --runtime "PYTHON:3.11" \
    --sku B1 \
    --location southeastasia

echo "⚙️ Setting startup command to run in Simulation Mode..."
$AZ_PATH webapp config set \
    --resource-group "$RG_NAME" \
    --name "$APP_NAME" \
    --startup-file "python main.py --simulate"

echo "====================================================="
echo "✅ DEPLOYMENT SUCCESSFUL!"
echo "Your app is available at: https://$APP_NAME.azurewebsites.net"
echo "Submit this URL to the Hackathon!"
echo "====================================================="
