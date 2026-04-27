#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PID_FILE="$PROJECT_DIR/sandbox.pid"

echo "=== Stopping Sandbox Server ==="

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "Sending SIGTERM to process $PID..."
        kill -TERM "$PID" 2>/dev/null || true
        
        for i in {1..10}; do
            if kill -0 "$PID" 2>/dev/null; then
                echo "Waiting for process to stop... ($i/10)"
                sleep 1
            else
                break
            fi
        done
        
        if kill -0 "$PID" 2>/dev/null; then
            echo "Process still running, sending SIGKILL..."
            kill -KILL "$PID" 2>/dev/null || true
            sleep 1
        fi
        
        echo "Server process stopped."
    else
        echo "PID file exists but process is not running. Removing stale PID file."
    fi
    rm -f "$PID_FILE"
else
    echo "PID file not found. Server may not be running."
fi

echo ""
echo "=== Cleaning Up All Sandbox Containers ==="

echo "Stopping and removing all sandbox containers..."
docker ps -a --filter "name=sandbox-exec-" --format "{{.ID}}" | while read -r CONTAINER_ID; do
    if [ -n "$CONTAINER_ID" ]; then
        echo "Stopping container: $CONTAINER_ID"
        docker stop -t 2 "$CONTAINER_ID" 2>/dev/null || true
        echo "Removing container: $CONTAINER_ID"
        docker rm -f "$CONTAINER_ID" 2>/dev/null || true
    fi
done

ORPHANED_COUNT=$(docker ps -a --filter "name=sandbox-exec-" --format "{{.ID}}" | wc -l)
if [ "$ORPHANED_COUNT" -gt 0 ]; then
    echo "Force removing remaining $ORPHANED_COUNT containers..."
    docker ps -a --filter "name=sandbox-exec-" --format "{{.ID}}" | xargs -r docker rm -f 2>/dev/null || true
else
    echo "No sandbox containers found."
fi

echo ""
echo "=== Cleaning Up Temporary Directories ==="

echo "Removing sandbox temporary directories..."
rm -rf /tmp/sandbox-* 2>/dev/null || true

echo ""
echo "=== Done ==="
echo "Sandbox server has been stopped and all containers have been cleaned up."
