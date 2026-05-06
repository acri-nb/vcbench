#!/bin/bash

# VCBench Environment Setup Script
# This script sets up the complete development environment for VCBench

set -e  # Exit on any error

echo "🚀 Setting up VCBench development environment..."

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_DIR="$PROJECT_ROOT/.venv"

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

# Check if conda is installed
if ! command -v conda &> /dev/null; then
    print_error "Conda is not installed. Please install Miniconda or Anaconda first."
    exit 1
fi

# Create local conda environment
if [[ -x "$ENV_DIR/bin/python" ]]; then
    print_status "Local Python environment already exists at .venv"
else
    print_info "Creating local Python environment at .venv..."
    conda create -p "$ENV_DIR" python=3.11 pip -y
    print_status "Local Python environment created"
fi

# Activate environment
print_info "Activating conda environment..."
eval "$(conda shell.bash hook)"
conda activate "$ENV_DIR"
print_status "Environment activated"

# Install pip packages
print_info "Installing Python packages..."
python -m pip install --upgrade pip
python -m pip install -r "$PROJECT_ROOT/requirements.txt"
print_status "Python packages installed"

# Install bcftools via homebrew (if on macOS)
if [[ "$OSTYPE" == "darwin"* ]]; then
    print_info "Installing bcftools via Homebrew..."
    if command -v brew &> /dev/null; then
        brew install bcftools
        print_status "bcftools installed"
    else
        print_warning "Homebrew not found. Please install bcftools manually."
    fi
else
    print_warning "Please install bcftools manually for your system."
fi

# Setup Docker services
print_info "Setting up Docker services..."
if command -v docker &> /dev/null && docker compose version &> /dev/null; then
    docker compose -f "$PROJECT_ROOT/docker/compose.yaml" up -d db
    print_status "PostgreSQL service started"
else
    print_warning "Docker Compose not found. Please start services manually."
fi

# Create necessary directories
print_info "Creating project directories..."
mkdir -p "$PROJECT_ROOT/data/lab_runs"
mkdir -p "$PROJECT_ROOT/data/processed"
mkdir -p "$PROJECT_ROOT/data/reference"
print_status "Directories created"

# Initialize database (optional)
print_info "Database initialization..."
read -p "Do you want to initialize the database? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    cd "$PROJECT_ROOT/qc-dashboard"
    python create_db_tables.py
    print_status "Database initialized"
else
    print_warning "Database initialization skipped. Run manually when ready."
fi

# Final instructions
print_status "Environment setup completed!"
echo ""
print_info "To activate the environment in future sessions:"
echo "  conda activate \"$ENV_DIR\""
echo ""
print_info "To start the application:"
echo "  cd qc-dashboard && ./start_app.sh"
echo ""
print_info "The web interface will be available at: http://localhost:8000"
print_info "API documentation will be available at: http://localhost:8000/docs"
echo ""
print_warning "Note: mamba-ssm requires special installation. Install with:"
echo "  pip install mamba-ssm --no-cache-dir"
echo ""
print_info "Happy coding with VCBench! 🎉"
