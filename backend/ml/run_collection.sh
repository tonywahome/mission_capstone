#!/bin/bash
# Run Sentinel data collection in the background

echo "Starting Sentinel-2 data collection..."
echo "This will collect 4000 samples (~4 hours)"
echo "Logs will be saved to: backend/ml/collection.log"
echo ""

# Change to project directory
cd "$(dirname "$0")/../.." || exit 1

# Use the currently active Python (conda base or venv)
PYTHON_BIN=$(which python)

echo "Using Python: $PYTHON_BIN"

# Run in background with nohup, redirecting output to log file
nohup "$PYTHON_BIN" backend/ml/collect_sentinel_data.py > backend/ml/collection.log 2>&1 &

# Get the process ID
PID=$!
echo "Process started with PID: $PID"
echo $PID > backend/ml/collection.pid

echo ""
echo "Collection is running in the background!"
echo ""
echo "To monitor progress:"
echo "  tail -f backend/ml/collection.log"
echo ""
echo "To check if it's still running:"
echo "  ps -p $PID"
echo ""
echo "To stop the process:"
echo "  kill $PID"
echo ""
