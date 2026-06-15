# TerraFoma Development Setup Guide

This guide will walk you through setting up the TerraFoma development environment from scratch.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [System Requirements](#system-requirements)
3. [Environment Setup](#environment-setup)
4. [Backend Setup](#backend-setup)
5. [Frontend Setup](#frontend-setup)
6. [Google Earth Engine Setup](#google-earth-engine-setup)
7. [Running the Application](#running-the-application)
8. [Troubleshooting](#troubleshooting)
9. [Optional: GPU Acceleration](#optional-gpu-acceleration)
10. [Optional: Model Retraining](#optional-model-retraining)

## Prerequisites

### Required Software

1. **Python 3.11 or higher** (3.13 recommended)
   - Download from: https://www.python.org/downloads/
   - Verify: `python3 --version`

2. **Node.js 18 or higher** (v22.1.0 tested)
   - Download from: https://nodejs.org/
   - Verify: `node --version`

3. **npm** (comes with Node.js)
   - Verify: `npm --version`

4. **Git**
   - Download from: https://git-scm.com/
   - Verify: `git --version`

5. **Text Editor/IDE**
   - Recommended: VS Code, PyCharm, or Cursor

### Required Accounts

1. **Google Earth Engine**
   - Sign up: https://earthengine.google.com/
   - Free for research and education
   - Processing time: 1-2 days for approval

2. **Mapbox**
   - Sign up: https://account.mapbox.com/auth/signup/
   - Free tier: 50,000 map loads/month
   - Used for: Interactive maps in frontend

### Optional Accounts

1. **Supabase** (for future database integration)
   - Sign up: https://supabase.com/
   - Currently using in-memory database

## System Requirements

### Minimum Requirements
- **CPU:** 2+ cores
- **RAM:** 4 GB
- **Disk:** 2 GB free space
- **OS:** macOS, Linux, or Windows 10+

### Recommended Requirements
- **CPU:** 4+ cores
- **RAM:** 8 GB
- **Disk:** 5 GB free space
- **GPU:** NVIDIA GPU (for faster model training)

## Environment Setup

### 1. Clone the Repository

```bash
# Clone the repository
git clone <repository-url>
cd terrafoma

# Verify the structure
ls -la
```

You should see:
```
.env.example
README.md
backend/
frontend/
docs/
.gitignore
cleanup.sh
```

### 2. Create Python Virtual Environment

```bash
# Create virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate  # macOS/Linux
# OR
.venv\Scripts\activate     # Windows
```

Your terminal prompt should now show `(.venv)`.

### 3. Verify Virtual Environment

```bash
# Check Python is from virtual environment
which python3  # Should show path with .venv

# Check pip is from virtual environment
which pip      # Should show path with .venv
```

## Backend Setup

### 1. Navigate to Backend Directory

```bash
cd backend
```

### 2. Install Python Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install all dependencies
pip install -r requirements.txt

# This will install:
# - fastapi, uvicorn (web server)
# - earthengine-api (satellite data)
# - scikit-learn, joblib (ML)
# - numpy, pandas (data processing)
# - python-dotenv (environment variables)
```

**Expected installation time:** 2-5 minutes

### 3. Configure Environment Variables

```bash
# Copy the example environment file
cp ../.env.example .env

# Open .env in your editor
nano .env  # or vim, code, etc.
```

**Add your configuration:**

```bash
# Google Earth Engine Configuration
EARTHENGINE_PROJECT_ID=your-project-id-here

# Google Cloud Service Account (if using service account)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# Optional: Supabase (not required for initial setup)
# SUPABASE_URL=https://xxx.supabase.co
# SUPABASE_KEY=your-key-here
```

**How to get your Earth Engine Project ID:**
1. Go to https://code.earthengine.google.com/
2. Click on your project name in top-left
3. Copy the project ID (format: `ee-username` or `project-name`)

### 4. Authenticate with Google Earth Engine

```bash
# Authenticate (opens browser)
earthengine authenticate

# Follow the authentication flow:
# 1. Click "Generate Token"
# 2. Sign in with your Google account
# 3. Copy the authorization code
# 4. Paste it into the terminal

# Verify authentication
python3 -c "import ee; ee.Initialize(project='your-project-id'); print('✓ Earth Engine authenticated')"
```

### 5. Verify Backend Setup

```bash
# Check if the model file exists
ls -lh ml/models/biomass_model_v1.pkl

# Should show: ~15MB file

# If missing, you'll need to train the model (see Optional: Model Retraining)
```

### 6. Test Backend Startup

```bash
# Start the backend server
uvicorn main:app --reload --port 8002

# You should see:
# INFO:     Uvicorn running on http://127.0.0.1:8002
# INFO:     Application startup complete
# INFO:     Initialized in-memory DB with 5 sample credits
```

**Test the API:**

Open a new terminal and run:

```bash
# Test health endpoint
curl http://localhost:8002/

# Test credits endpoint
curl http://localhost:8002/api/credits?status=listed

# Should return JSON with 5 sample credits
```

**View API documentation:**
- Open browser: http://localhost:8002/docs
- Interactive Swagger UI with all endpoints

**Stop the server:** Press `Ctrl+C`

## Frontend Setup

### 1. Navigate to Frontend Directory

```bash
# From backend directory
cd ../frontend

# Or from root
cd frontend
```

### 2. Install Node.js Dependencies

```bash
# Install all dependencies
npm install

# This will install:
# - next, react (framework)
# - typescript (type safety)
# - tailwindcss (styling)
# - mapbox-gl (maps)
# - various UI libraries
```

**Expected installation time:** 2-5 minutes
**Expected size:** ~200-300 MB in node_modules/

### 3. Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env.local

# Open .env.local in your editor
nano .env.local
```

**Add your configuration:**

```bash
# Mapbox Configuration
NEXT_PUBLIC_MAPBOX_TOKEN=pk.your_mapbox_token_here

# Backend API URL
NEXT_PUBLIC_API_URL=http://localhost:8002
```

**How to get your Mapbox token:**
1. Go to https://account.mapbox.com/
2. Log in or create account
3. Go to "Access tokens"
4. Copy your "Default public token" or create a new one
5. Token should start with `pk.`

### 4. Verify Frontend Setup

```bash
# Check Next.js configuration
cat next.config.js

# Check Tailwind configuration
cat tailwind.config.js
```

### 5. Test Frontend Build

```bash
# Test that everything compiles
npm run build

# Should complete without errors
# May take 1-2 minutes on first build
```

### 6. Test Frontend Development Server

```bash
# Start the development server
npm run dev

# You should see:
#   ▲ Next.js 14.2.21
#   - Local:        http://localhost:3001
#   - ready in 2.5s
```

**Test the frontend:**
- Open browser: http://localhost:3001
- You should see the TerraFoma landing page

**Stop the server:** Press `Ctrl+C`

## Google Earth Engine Setup

### Service Account (Optional, for Production)

For development, user authentication is sufficient. For production deployment:

1. **Create a Service Account**
   - Go to: https://console.cloud.google.com/
   - Select your Earth Engine project
   - Navigate to: IAM & Admin > Service Accounts
   - Click "Create Service Account"
   - Grant "Earth Engine Resource Reader" role

2. **Download Service Account Key**
   - Click on the service account
   - Keys tab > Add Key > Create new key
   - Choose JSON format
   - Save the file securely (DO NOT commit to git)

3. **Configure Backend**
   ```bash
   # In backend/.env
   GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
   ```

### Test Earth Engine Access

```bash
cd backend
source ../.venv/bin/activate

# Test script
python3 -c "
import ee
ee.Initialize(project='your-project-id')
image = ee.Image('COPERNICUS/S2_SR/20200101T000000_20200101T000000_T01AAA')
print('✓ Earth Engine is working!')
"
```

## Running the Application

### Start Both Servers

**Terminal 1 - Backend:**
```bash
cd backend
source ../.venv/bin/activate
uvicorn main:app --reload --port 8002
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

### Verify Everything is Running

```bash
# Terminal 3 - Check both servers
lsof -ti:8002,3001

# Should output process IDs (e.g., 12345, 67890)

# Test backend
curl http://localhost:8002/api/credits?status=listed | python3 -m json.tool

# Open frontend
open http://localhost:3001  # macOS
# or just visit in browser
```

### Using the Application

1. **Landing Page** (http://localhost:3001)
   - View features and overview

2. **Dashboard** (http://localhost:3001/dashboard)
   - Click on the map to scan a plot
   - Select location in Kenya or Congo Basin
   - View biomass estimation results

3. **Marketplace** (http://localhost:3001/marketplace)
   - Browse 5 sample carbon credits
   - View project details
   - See community benefit calculations
   - Click "Purchase Credit" to simulate purchase

4. **Registry** (http://localhost:3001/registry)
   - View all carbon credits
   - See status and details

## Troubleshooting

### Backend Issues

**Issue: `ModuleNotFoundError: No module named 'fastapi'`**
```bash
# Solution: Activate virtual environment
source .venv/bin/activate
cd backend
pip install -r requirements.txt
```

**Issue: `earthengine.EEException: Authentication failed`**
```bash
# Solution: Re-authenticate
earthengine authenticate

# Or check project ID
python3 -c "import ee; print(ee.data.getProjects())"
```

**Issue: `FileNotFoundError: biomass_model_v1.pkl`**
```bash
# Solution: Check model location
ls backend/ml/models/biomass_model_v1.pkl

# If missing, model needs to be trained (see Optional section)
```

**Issue: Port 8002 already in use**
```bash
# Solution: Kill existing process
lsof -ti:8002 | xargs kill -9

# Or use different port
uvicorn main:app --reload --port 8003
```

### Frontend Issues

**Issue: `Cannot find module 'next'`**
```bash
# Solution: Install dependencies
cd frontend
npm install
```

**Issue: `Error: Invalid Mapbox access token`**
```bash
# Solution: Check .env.local
cat .env.local

# Verify token starts with 'pk.'
# Get new token from: https://account.mapbox.com/
```

**Issue: Port 3001 already in use**
```bash
# Solution: Kill existing process
lsof -ti:3001 | xargs kill -9

# Or Next.js will automatically use 3002
```

**Issue: `Failed to fetch API`**
```bash
# Solution: Verify backend is running
curl http://localhost:8002/

# Check CORS settings in backend/main.py
# Verify NEXT_PUBLIC_API_URL in frontend/.env.local
```

### Earth Engine Issues

**Issue: `Earth Engine Quota Exceeded`**
- Free tier: 25,000 requests/day
- Solution: Wait 24 hours or upgrade plan
- Monitor usage: https://code.earthengine.google.com/

**Issue: `Earth Engine Timeout`**
- Satellite queries can take 2-5 seconds
- Temporary server issues are common
- Solution: Retry the request

### General Issues

**Issue: `Connection Refused`**
```bash
# Check both servers are running
lsof -ti:8002,3001

# Restart servers if needed
```

**Issue: Slow performance**
- Earth Engine queries: 2-5s (normal)
- Frontend compilation: 1-2s on first load (normal)
- Check network connection
- Check system resources (CPU, RAM)

## Optional: GPU Acceleration

For faster model training (not required for running the application):

### NVIDIA GPU Setup

1. **Install CUDA Toolkit**
   - Download from: https://developer.nvidia.com/cuda-downloads
   - Version: CUDA 11.8 or 12.x

2. **Install cuDNN**
   - Download from: https://developer.nvidia.com/cudnn
   - Follow installation instructions

3. **Install GPU Libraries**
   ```bash
   pip install xgboost[gpu]
   pip install cupy-cuda11x  # or cupy-cuda12x
   pip install cuml-cu11      # RAPIDS cuML
   ```

4. **Verify GPU**
   ```bash
   nvidia-smi  # Should show GPU info
   
   python3 -c "
   import torch
   print('CUDA available:', torch.cuda.is_available())
   "
   ```

5. **Use GPU in Training Notebook**
   - Open: `backend/ml/train_biomass_model.ipynb`
   - GPU sections are already included
   - 10-50x faster training with GPU

## Optional: Model Retraining

If you want to train your own biomass estimation model:

### Prerequisites

- Completed Backend Setup
- Earth Engine authenticated
- Jupyter Notebook installed:
  ```bash
  pip install jupyter ipykernel
  ```

### Steps

1. **Launch Jupyter Notebook**
   ```bash
   cd backend/ml
   jupyter notebook
   ```

2. **Open Training Notebook**
   - Navigate to: `train_biomass_model.ipynb`
   - Click to open

3. **Run All Cells**
   - Cell > Run All
   - Or run cells one by one

4. **Training Process**
   - Cell 1-3: Setup and imports
   - Cell 4-10: Load and explore data
   - Cell 11-15: Baseline model training
   - Cell 16-40: 5 improvement strategies
   - Cell 41-48: Save best model

5. **Expected Results**
   - Training time: 5-15 minutes (CPU) or 1-3 minutes (GPU)
   - Model saved to: `models/biomass_model_v1.pkl`
   - Test R² score: ~0.50-0.55
   - MAE: ~18-22 tonnes/ha

### Data Collection (Advanced)

To collect new training data:

```bash
cd backend/ml

# Collect Sentinel-2 features
python3 collect_sentinel_data.py

# Collect GEDI biomass measurements
python3 collect_gedi_data.py

# This will:
# - Query Earth Engine for satellite data
# - Extract features for each location
# - Save to: data/sentinel_gedi_training.csv
# - Can take several hours for 10,000+ samples
```

## Next Steps

Once setup is complete:

1. **Explore the Application**
   - Try scanning different locations
   - Browse the marketplace
   - View sample credits

2. **Read the Documentation**
   - [README.md](../README.md) - Project overview
   - [ARCHITECTURE.md](ARCHITECTURE.md) - System design
   - Backend API docs: http://localhost:8002/docs

3. **Start Developing**
   - Make changes to code
   - See changes live (hot reload enabled)
   - Test your changes

4. **Contribute**
   - Follow code style guidelines
   - Write tests for new features
   - Submit pull requests

## Development Tools

### Recommended VS Code Extensions

- Python (Microsoft)
- Pylance (Microsoft)
- ESLint (Microsoft)
- Prettier (Prettier)
- Tailwind CSS IntelliSense (Tailwind Labs)

### Code Formatting

**Backend (Python):**
```bash
cd backend
pip install black isort
black .
isort .
```

**Frontend (TypeScript/React):**
```bash
cd frontend
npm run format  # If script exists
# or
npx prettier --write .
```

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

## Clean Up

If you need to start fresh:

```bash
# Run cleanup script
./cleanup.sh

# Or manually:
# Remove Python cache
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

# Remove Node modules (frontend only)
rm -rf frontend/node_modules

# Remove build artifacts
rm -rf frontend/.next
rm -rf backend/dist
```

## Support

If you encounter issues not covered in this guide:

1. Check error messages carefully
2. Search for similar issues online
3. Review the [ARCHITECTURE.md](ARCHITECTURE.md) for system details
4. Check logs:
   - Backend: Terminal output
   - Frontend: Browser console (F12)
5. Contact the development team

## Summary

You should now have:
- ✅ Python 3.13 virtual environment
- ✅ Backend FastAPI server running on port 8002
- ✅ Frontend Next.js app running on port 3001
- ✅ Google Earth Engine authenticated
- ✅ Mapbox maps configured
- ✅ 5 sample carbon credits loaded
- ✅ Biomass estimation model ready

**Happy coding! 🌍**
