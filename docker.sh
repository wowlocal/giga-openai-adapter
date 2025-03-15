#!/bin/bash

# Helper script for Docker operations

# Function to display usage information
show_usage() {
    echo "Usage: $0 [command]"
    echo "Commands:"
    echo "  build       - Build the Docker image"
    echo "  start       - Start the container (builds if not already built)"
    echo "  stop        - Stop the container"
    echo "  restart     - Restart the container"
    echo "  logs        - View container logs"
    echo "  shell       - Open a shell in the running container"
    echo "  clean       - Remove container and image"
    echo "  help        - Show this help message"
}

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed or not in PATH"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Error: Docker Compose is not installed or not in PATH"
    exit 1
fi

# Process commands
case "$1" in
    build)
        echo "Building Docker image..."
        docker-compose build
        ;;
    start)
        echo "Starting container..."
        docker-compose up -d
        ;;
    stop)
        echo "Stopping container..."
        docker-compose down
        ;;
    restart)
        echo "Restarting container..."
        docker-compose restart
        ;;
    logs)
        echo "Showing logs..."
        docker-compose logs -f
        ;;
    shell)
        echo "Opening shell in container..."
        docker-compose exec gigachat-proxy /bin/bash
        ;;
    clean)
        echo "Removing container and image..."
        docker-compose down --rmi all
        ;;
    help|*)
        show_usage
        ;;
esac