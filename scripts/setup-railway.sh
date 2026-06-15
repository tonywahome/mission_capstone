#!/bin/bash

# Railway Frontend Environment Variables Setup Script
# This script helps configure Railway environment variables via CLI

set -e

echo "================================================"
echo "TerraFoma Railway Setup Script"
echo "================================================"
echo ""

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI not found!"
    echo ""
    echo "Install it with:"
    echo "  npm install -g @railway/cli"
    echo ""
    echo "Or set variables manually in Railway Dashboard:"
    echo "  https://railway.app/dashboard"
    exit 1
fi

echo "✓ Railway CLI found"
echo ""

# Login check
echo "Checking Railway authentication..."
if ! railway whoami &> /dev/null; then
    echo "❌ Not logged in to Railway"
    echo ""
    echo "Run: railway login"
    exit 1
fi

echo "✓ Logged in to Railway"
echo ""

# Ask for backend URL
echo "Enter your Railway backend URL:"
echo "(Example: https://terrafoma-backend-production.up.railway.app)"
read -p "Backend URL: " BACKEND_URL

if [ -z "$BACKEND_URL" ]; then
    echo "❌ Backend URL is required"
    exit 1
fi

echo ""
echo "================================================"
echo "Setting Frontend Environment Variables..."
echo "================================================"
echo ""

# Read tokens from .env.local if it exists
ENV_FILE="../frontend/.env.local"
if [ -f "$ENV_FILE" ]; then
    echo "Reading tokens from .env.local..."
    source <(grep -E '^(NEXT_PUBLIC_MAPBOX_TOKEN|POLAR_)' "$ENV_FILE" | sed 's/^/export /')
else
    echo "⚠️  .env.local not found. Using placeholder values."
    echo "Edit this script to add your actual tokens."
    NEXT_PUBLIC_MAPBOX_TOKEN="YOUR_MAPBOX_TOKEN_HERE"
    POLAR_ACCESS_TOKEN="YOUR_POLAR_TOKEN"
    POLAR_PRODUCT_ID="YOUR_POLAR_PRODUCT_ID"
    POLAR_WEBHOOK_SECRET="YOUR_POLAR_WEBHOOK_SECRET"
fi

# Set variables
echo "Setting NEXT_PUBLIC_MAPBOX_TOKEN..."
railway variables set NEXT_PUBLIC_MAPBOX_TOKEN="$NEXT_PUBLIC_MAPBOX_TOKEN"

echo "Setting NEXT_PUBLIC_API_URL..."
railway variables set NEXT_PUBLIC_API_URL="$BACKEND_URL"

echo "Setting POLAR_SERVER..."
railway variables set POLAR_SERVER="sandbox"

echo "Setting POLAR_ACCESS_TOKEN..."
railway variables set POLAR_ACCESS_TOKEN="$POLAR_ACCESS_TOKEN"

echo "Setting POLAR_PRODUCT_ID..."
railway variables set POLAR_PRODUCT_ID="$POLAR_PRODUCT_ID"

echo "Setting POLAR_WEBHOOK_SECRET..."
railway variables set POLAR_WEBHOOK_SECRET="$POLAR_WEBHOOK_SECRET"

echo ""
echo "================================================"
echo "✓ All environment variables set successfully!"
echo "================================================"
echo ""
echo "Next steps:"
echo "1. Railway will automatically redeploy"
echo "2. Wait for deployment to complete"
echo "3. Check logs: railway logs"
echo "4. Test your frontend URL"
echo ""
echo "To verify variables:"
echo "  railway variables"
echo ""
