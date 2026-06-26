#!/bin/bash
# Stop the data collection process

if [ ! -f "backend/ml/collection.pid" ]; then
    echo "No collection process found (PID file missing)"
    exit 1
fi

PID=$(cat backend/ml/collection.pid)

if ps -p $PID > /dev/null 2>&1; then
    echo "Stopping collection process (PID: $PID)..."
    kill $PID
    sleep 2
    
    if ps -p $PID > /dev/null 2>&1; then
        echo "Process still running, forcing stop..."
        kill -9 $PID
    fi
    
    echo "✓ Collection stopped"
    rm backend/ml/collection.pid
else
    echo "Process is not running (PID: $PID)"
    rm backend/ml/collection.pid
fi
