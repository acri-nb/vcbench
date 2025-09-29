# VCBench Environment Setup Guide

This guide explains how to set up the development environment for VCBench.

## Quick Setup (Recommended)

### Option 1: Automated Setup Script
```bash
# Make sure you're in the vcbench directory
cd vcbench

# Run the automated setup script
./setup_environment.sh
```

This script will:
- ✅ Create the conda environment `bioinfo`
- ✅ Install all required packages
- ✅ Install bcftools (on macOS via Homebrew)
- ✅ Start Docker services
- ✅ Create necessary directories
- ✅ Optionally initialize the database

### Option 2: Manual Setup
```bash
# 1. Create conda environment
conda env create -f environment.yml

# 2. Activate environment
conda activate bioinfo

# 3. Install additional pip packages
pip install -r requirements.txt

# 4. Install bcftools (macOS)
brew install bcftools

# 5. Start Docker services
cd docker
docker-compose up -d

# 6. Initialize database
cd ../qc-dashboard
python create_db_tables.py
```

## Environment Files

### `environment.yml`
Conda environment specification file containing all dependencies.
- Use with: `conda env create -f environment.yml`

### `requirements.txt`
Pip packages that complement the conda environment.
- Install with: `pip install -r requirements.txt`

### `setup_environment.sh`
Automated bash script for complete environment setup.
- Run with: `./setup_environment.sh`

## Required Software

### Conda/Mamba
- **Miniconda** or **Anaconda** required
- Mamba recommended for faster package resolution

### Docker & Docker Compose
- Required for bioinformatics tools (hap.py, Truvari)
- PostgreSQL database runs in container

### System Dependencies (macOS)
- **Homebrew** for bcftools installation
- **Xcode Command Line Tools** may be required

## Environment Activation

After setup, always activate the environment:
```bash
conda activate bioinfo
```

## Troubleshooting

### bcftools Installation Issues
If bcftools fails to install via conda:
```bash
# macOS with Homebrew
brew install bcftools

# Ubuntu/Debian
sudo apt-get install bcftools

# Conda (alternative)
conda install -c bioconda bcftools
```

### Docker Issues
If Docker services fail to start:
```bash
# Check Docker is running
docker info

# Start services manually
cd docker
docker-compose up -d

# Check service logs
docker-compose logs
```

### Database Issues
If database initialization fails:
```bash
# Check PostgreSQL container
docker ps | grep wgs_db

# Check database logs
docker-compose logs db

# Manual database setup
cd qc-dashboard/api/app/test
python create_tables.py
```

### Import Errors
If you get import errors after setup:
```bash
# Reinstall problematic packages
pip uninstall package_name
pip install package_name

# Or reinstall entire environment
conda env remove -n bioinfo
./setup_environment.sh
```

## Environment Variables

Set these for proper configuration:
```bash
# Database
export DATABASE_URL="postgresql://wgs_user:password@localhost:5432/wgs"

# Data directories
export LAB_RUNS_DIR="/path/to/vcbench/data/lab_runs"
export PROCESSED_DIR="/path/to/vcbench/data/processed"
export REFERENCE_DIR="/path/to/vcbench/data/reference"
```

## Development Workflow

1. **Activate environment**: `conda activate bioinfo`
2. **Start Docker services**: `cd docker && docker-compose up -d`
3. **Create database tables** (first time only): `cd qc-dashboard && python create_db_tables.py`
4. **Run application**: `cd qc-dashboard && ./start_app.sh`
5. **Access web interface**: http://localhost:8000
6. **View API docs**: http://localhost:8000/docs

## Recent Fixes (September 2025)

### Database Connection Issues
- **Problem**: `ModuleNotFoundError: No module named 'api'` when running `create_tables.py`
- **Solution**: Created `create_db_tables.py` script in qc-dashboard directory
- **Usage**: `cd qc-dashboard && python create_db_tables.py`

### PostgreSQL Configuration
- **Problem**: Wrong port (5432) and driver (`psycopg` instead of `psycopg2`)
- **Solution**: Updated `database.py` to use port 5433 and `psycopg2` driver
- **Note**: Port 5433 avoids conflicts with other PostgreSQL instances

### Docker Services
- **Problem**: Multiple image pull failures and architecture issues on M1/M2 Macs
- **Solution**: Updated `compose.yaml` with working images and platform specifications
- **Status**: Core services (PostgreSQL, bcftools, MultiQC) now working

### Import Path Issues
- **Problem**: Python couldn't find `api` module from test directory
- **Solution**: Modified scripts to change working directory to qc-dashboard before imports
- **Result**: All imports now work correctly from appropriate directories

## Package Versions

Key package versions in the environment:
- **Python**: 3.9.x
- **FastAPI**: 0.116.x
- **Dash**: 3.2.x
- **Plotly**: 6.3.x
- **Pandas**: 2.3.x
- **bcftools**: 1.22.x

## Updating Environment

To update packages:
```bash
# Update conda packages
conda update --all

# Update pip packages
pip install --upgrade -r requirements.txt

# Rebuild Docker images if needed
cd docker
docker-compose build --no-cache
```

## Support

For environment setup issues:
1. Check this guide first
2. Verify system requirements
3. Check GitHub Issues for similar problems
4. Create an issue with your system information and error messages
