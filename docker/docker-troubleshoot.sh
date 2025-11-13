#!/bin/bash

# VCBench Docker Troubleshooting Script
# This script helps diagnose and fix common Docker issues

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

echo "🔍 Diagnosing Docker issues for VCBench..."
echo "=========================================="

# Check if Docker is running
print_info "Checking Docker status..."
if ! docker info &> /dev/null; then
    print_error "Docker is not running. Please start Docker Desktop."
    echo "  On macOS: Open Docker Desktop application"
    echo "  On Linux: sudo systemctl start docker"
    exit 1
fi
print_status "Docker is running"

# Check Docker Compose version
print_info "Checking Docker Compose version..."
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE_VERSION=$(docker-compose --version)
    print_warning "Using legacy docker-compose: $DOCKER_COMPOSE_VERSION"
    print_info "Consider upgrading to Docker Compose V2 (docker compose)"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE_VERSION=$(docker compose version)
    print_status "Docker Compose V2 found: $DOCKER_COMPOSE_VERSION"
else
    print_error "Docker Compose not found"
    exit 1
fi

# Check architecture
print_info "Checking system architecture..."
ARCH=$(uname -m)
if [[ "$ARCH" == "arm64" ]]; then
    print_info "Running on ARM64 (Apple Silicon M1/M2/M3)"
    USE_ARM64=true
else
    print_info "Running on $ARCH architecture"
    USE_ARM64=false
fi

# Check available disk space
print_info "Checking available disk space..."
DISK_SPACE=$(df -h . | tail -1 | awk '{print $4}')
print_info "Available disk space: $DISK_SPACE"

# Test Docker pull
print_info "Testing Docker image pull..."
if docker pull hello-world &> /dev/null; then
    print_status "Docker pull works correctly"
    docker rmi hello-world &> /dev/null
else
    print_error "Docker pull failed. Check internet connection and Docker Desktop."
fi

# Check if we're in the right directory
print_info "Checking current directory..."
if [[ ! -f "compose.yaml" ]]; then
    print_error "compose.yaml not found. Please run this script from the docker directory."
    exit 1
fi
print_status "In correct directory"

# Clean up previous containers and images
print_info "Cleaning up previous containers..."
docker compose down -v 2>/dev/null || true
docker compose rm -f 2>/dev/null || true

# Try to start services with appropriate compose file
print_info "Attempting to start Docker services..."

if [[ "$USE_ARM64" == true ]]; then
    print_info "Using ARM64 configuration..."
    COMPOSE_FILE="docker-compose.arm64.yaml"
else
    print_info "Using AMD64 configuration..."
    COMPOSE_FILE="compose.yaml"
fi

# Check if ARM64 compose file exists
if [[ "$USE_ARM64" == true ]] && [[ ! -f "$COMPOSE_FILE" ]]; then
    print_warning "ARM64 compose file not found, falling back to standard compose.yaml"
    COMPOSE_FILE="compose.yaml"
fi

echo "Using compose file: $COMPOSE_FILE"

# Try to start services
if docker compose -f "$COMPOSE_FILE" up -d --pull always; then
    print_status "Docker services started successfully!"
    echo ""
    print_info "Service status:"
    docker compose -f "$COMPOSE_FILE" ps

    echo ""
    print_info "To view logs: docker compose -f $COMPOSE_FILE logs -f"
    print_info "To stop services: docker compose -f $COMPOSE_FILE down"

else
    print_error "Failed to start Docker services"
    echo ""
    print_info "Common solutions:"
    echo "1. For M1/M2 Macs: Enable Rosetta in Docker Desktop > Settings > General"
    echo "2. Increase Docker memory limit to at least 8GB"
    echo "3. Check Docker Desktop is up to date"
    echo "4. Try: docker system prune -a (removes all unused images)"
    echo "5. Restart Docker Desktop"
    echo ""
    print_info "Manual commands to try:"
    echo "  docker pull quay.io/biocontainers/bcftools:1.18--h8b37899_0"
    echo "  docker pull postgres:16-alpine"
    echo "  docker pull multiqc/multiqc:v1.19"
    echo ""
    print_info "If using ARM64 Mac, you can try:"
    echo "  docker compose -f docker-compose.arm64.yaml up -d"
fi

echo ""
print_info "Troubleshooting complete."
