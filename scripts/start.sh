#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PID_FILE="$PROJECT_DIR/sandbox.pid"
LOG_FILE="$PROJECT_DIR/sandbox.log"

cd "$PROJECT_DIR"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "Sandbox is already running (PID: $PID)"
        exit 1
    else
        echo "Removing stale PID file"
        rm -f "$PID_FILE"
    fi
fi

echo "Checking dependencies..."
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed. Please install Docker first."
    exit 1
fi

if ! docker info &> /dev/null; then
    echo "Error: Docker daemon is not running. Please start Docker first."
    exit 1
fi

echo "Installing Python dependencies..."
uv sync

echo "Cleaning up any orphaned containers..."
docker ps -a --filter "name=sandbox-exec-" --format "{{.ID}}" | xargs -r docker rm -f 2>/dev/null || true

echo "Starting sandbox server on 0.0.0.0:4444..."

if [ "$1" = "--dev" ] || [ "$1" = "-d" ]; then
    echo "Running in development mode (with reload)"
    uv run uvicorn main:app --host 0.0.0.0 --port 4444 --reload
else
    nohup uv run uvicorn main:app --host 0.0.0.0 --port 4444 > "$LOG_FILE" 2>&1 &
    PID=$!
    echo $PID > "$PID_FILE"
    echo "Sandbox server started (PID: $PID)"
    echo "Log file: $LOG_FILE"
    echo "PID file: $PID_FILE"
    echo ""
    echo "Access the sandbox at: http://localhost:4444"
fi
