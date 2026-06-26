#!/bin/bash
# Check the status of the data collection process

if [ ! -f "backend/ml/collection.pid" ]; then
    echo "No collection process found (PID file missing)"
    exit 1
fi

PID=$(cat backend/ml/collection.pid)

if ps -p $PID > /dev/null 2>&1; then
    echo "✓ Collection is still running (PID: $PID)"
    echo ""
    echo "Last 10 log lines:"
    echo "===================="
    tail -10 backend/ml/collection.log
    echo ""
    echo "To follow live updates: tail -f backend/ml/collection.log"
else
    echo "✗ Collection process has stopped (PID: $PID)"
    echo ""
    echo "Last 20 log lines:"
    echo "===================="
    tail -20 backend/ml/collection.log
fi
