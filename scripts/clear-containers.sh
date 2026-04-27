#!/bin/bash

echo "=== Clearing All Sandbox Containers ==="

echo "Stopping and removing all sandbox containers..."

CONTAINERS=$(docker ps -a --filter "name=sandbox-exec-" --format "{{.ID}}")

if [ -z "$CONTAINERS" ]; then
    echo "No sandbox containers found."
else
    COUNT=$(echo "$CONTAINERS" | wc -l)
    echo "Found $COUNT sandbox containers:"
    
    for CONTAINER_ID in $CONTAINERS; do
        NAME=$(docker inspect --format '{{.Name}}' "$CONTAINER_ID" 2>/dev/null | sed 's/^\///')
        echo "  - $NAME ($CONTAINER_ID)"
    done
    
    echo ""
    read -p "Are you sure you want to stop and remove all these containers? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        for CONTAINER_ID in $CONTAINERS; do
            echo "Stopping container: $CONTAINER_ID"
            docker stop -t 2 "$CONTAINER_ID" 2>/dev/null || true
            echo "Removing container: $CONTAINER_ID"
            docker rm -f "$CONTAINER_ID" 2>/dev/null || true
        done
        
        echo ""
        echo "Cleaning up temporary directories..."
        rm -rf /tmp/sandbox-* 2>/dev/null || true
        
        echo ""
        echo "=== Done ==="
        echo "All sandbox containers have been cleared."
    else
        echo "Operation cancelled."
        exit 0
    fi
fi

echo ""
echo "=== Done ==="
