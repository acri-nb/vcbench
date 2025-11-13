#!/bin/bash

# VCBench Environment Setup Script
# This script sets up the complete development environment for VCBench

set -e  # Exit on any error

echo "🚀 Setting up VCBench development environment..."

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

# Create conda environment
print_info "Creating conda environment 'bioinfo'..."
conda create -n bioinfo python=3.9 -y
print_status "Conda environment created"

# Activate environment
print_info "Activating conda environment..."
eval "$(conda shell.bash hook)"
conda activate bioinfo
print_status "Environment activated"

# Install conda packages
print_info "Installing conda packages..."
conda install -c conda-forge -c bioconda -c defaults -y \
    fastapi \
    uvicorn \
    sqlalchemy \
    psycopg2-binary \
    pandas \
    numpy \
    plotly \
    dash \
    python-multipart \
    aiofiles \
    pydantic
print_status "Conda packages installed"

# Install pip packages
print_info "Installing pip packages..."
pip install --upgrade pip
pip install -r requirements.txt
print_status "Pip packages installed"

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
if command -v docker &> /dev/null && command -v docker-compose &> /dev/null; then
    cd docker
    docker-compose up -d
    cd ..
    print_status "Docker services started"
else
    print_warning "Docker or docker-compose not found. Please start services manually."
fi

# Create necessary directories
print_info "Creating project directories..."
mkdir -p data/lab_runs
mkdir -p data/processed
mkdir -p data/reference
print_status "Directories created"

# Initialize database (optional)
print_info "Database initialization..."
read -p "Do you want to initialize the database? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    cd qc-dashboard/api/app/test
    python create_tables.py
    print_status "Database initialized"
else
    print_warning "Database initialization skipped. Run manually when ready."
fi

# Final instructions
print_status "Environment setup completed!"
echo ""
print_info "To activate the environment in future sessions:"
echo "  conda activate bioinfo"
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
