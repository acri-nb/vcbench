# VCBench - WGS Quality Control Dashboard

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.68+-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/docker-required-blue.svg)](https://www.docker.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-blue.svg)](https://www.postgresql.org/)

Comprehensive quality control platform for Whole Genome Sequencing (WGS) analysis with automated benchmarking and interactive visualization.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [REST API](#rest-api)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)

## Overview

VCBench is an integrated solution for evaluating and quality controlling genomic sequencing data from DRAGEN platforms. The platform offers:

- **Automated benchmarking** with hap.py and Truvari
- **Interactive visualization** of quality metrics
- **Centralized management** of analyses and samples
- **Modern REST API** for system integration
- **Responsive web interface** based on Dash

## Features

### 🔬 Bioinformatics Benchmarking
- **hap.py**: Small variant evaluation (SNP, indel)
- **Truvari**: Structural variant benchmarking
- Precision, sensitivity and F1 score metrics
- Automated TP/FP/FN classification

### 📊 Interactive Visualization
- Customizable dashboards
- Multi-sample comparative charts
- Coverage and mapping metrics
- Advanced statistical analysis

### 🗄️ Data Management
- Secure DRAGEN file uploads
- Automatic sample organization
- Persistent result storage
- Data and report exports

### 🔧 Complete REST API
- Endpoints for metrics and analyses
- Run and sample management
- Automated pipeline integration
- Interactive OpenAPI documentation

## Architecture

```mermaid
graph TB
    A[Dash Web Interface] --> B[FastAPI Backend]
    B --> C[PostgreSQL Database]
    B --> D[Bioinformatics Pipeline]
    D --> E[hap.py Container]
    D --> F[Truvari Container]
    D --> G[bcftools Container]
    H[DRAGEN Files] --> B
    I[Reference Data] --> D
```

### Technology Stack

- **Backend**: FastAPI, SQLAlchemy, PostgreSQL
- **Frontend**: Dash, Plotly, Custom CSS
- **Bioinformatics**: hap.py, Truvari, bcftools, RTG Tools
- **Containerization**: Docker, Docker Compose
- **Language**: Python 3.8+

## Prerequisites

### Operating System
- Linux/macOS (recommended)
- Windows 10/11 with WSL2

### Required Software
- **Docker & Docker Compose**: Version 20.10+
- **Conda**: Miniconda or Anaconda
- **Git**: For repository cloning

### Hardware Requirements
- **RAM**: 16GB minimum (32GB recommended)
- **Storage**: 100GB+ for genomic data
- **CPU**: 4+ cores (8+ recommended)

## Installation

### 1. Clone Repository
```bash
git clone <repository-url>
cd vcbench
```

### 2. Configure Conda Environment
```bash
# Activate bioinformatics environment
lenv conda gthbioinfocris

# Install special dependencies
pip install mamba-ssm --no-cache-dir
```

### 3. Configure Docker
```bash
# Start services
cd vcbenchmark/docker
docker-compose up -d

# Verify containers
docker ps
```

### 4. Initialize Database
```bash
# Create tables
cd vcbenchmark/qc-dashboard/api/app/test
python create_tables.py
```

## Configuration

### Environment Variables
```bash
# Database configuration
export DATABASE_URL="postgresql://wgs_user:password@localhost:5432/wgs"

# Data directories
export LAB_RUNS_DIR="/path/to/vcbenchmark/data/lab_runs"
export PROCESSED_DIR="/path/to/vcbenchmark/data/processed"
export REFERENCE_DIR="/path/to/vcbenchmark/data/reference"
```

### Application Configuration
Configuration files are located in:
- `qc-dashboard/dash_app/config.py`: Frontend parameters
- `qc-dashboard/api/app/database.py`: Database configuration
- `docker/compose.yaml`: Docker services

## Usage

### Starting the Application
```bash
cd vcbenchmark/qc-dashboard
./start_app.sh
```

The application will be accessible at:
- **Web Interface**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

### Typical Workflow

1. **Data Upload**
   - Compressed GVCF VCF files (.gvcf.gz)
   - DRAGEN metrics CSV files
   - MD5 checksum files

2. **Benchmarking Configuration**
   - Sample selection
   - Tool selection (hap.py, Truvari)
   - Parameter configuration

3. **Automated Execution**
   - Containerized bioinformatics pipeline
   - Quality metrics calculation
   - Result storage

4. **Analysis and Visualization**
   - Interactive dashboards
   - Multi-sample comparisons
   - Report exports

## Project Structure

```
vcbenchmark/
├── data/                    # Data and results
│   ├── lab_runs/           # Raw uploaded data
│   ├── processed/          # Processed results
│   └── reference/          # Reference genomes and truth sets
├── docker/                 # Container configuration
│   ├── compose.yaml        # Service orchestration
│   ├── Dockerfile.rtg      # RTG Tools image
│   └── db_start.sh         # Database initialization
├── pipeline/               # Bioinformatics scripts
│   ├── happy.sh           # hap.py pipeline
│   ├── truvari.sh         # Truvari pipeline
│   ├── vcf_filter.py      # VCF filtering
│   └── *.py               # Processing scripts
├── qc-dashboard/          # Main application
│   ├── api/               # FastAPI backend
│   │   ├── app/
│   │   │   ├── main.py    # API entry point
│   │   │   ├── models.py  # Data models
│   │   │   └── api_v1/endpoints/  # API endpoints
│   │   └── tasks/         # Asynchronous tasks
│   ├── dash_app/          # Dash frontend
│   │   ├── app.py         # Main application
│   │   ├── pages/         # Interface pages
│   │   ├── callbacks.py   # Interactive logic
│   │   └── assets/        # Static resources
│   └── start_app.sh       # Launch script
└── emedgene_report/       # Report generation module
```

## REST API

### Main Endpoints

#### Sample Management
- `GET /api/v1/runs` - List of runs
- `POST /api/v1/uploads` - File uploads
- `GET /api/v1/runs/{id}` - Run details

#### Quality Metrics
- `GET /api/v1/qc-metrics` - General metrics
- `GET /api/v1/happy-metrics` - hap.py results
- `GET /api/v1/metrics/{sample}` - Metrics by sample

#### User Management
- `POST /api/v1/users` - User creation
- `GET /api/v1/users/me` - User profile

### DRAGEN Data Formats

#### Files Required for hap.py
- `*.gvcf.gz`: Compressed genomic VCF files
- `*.gvcf.gz.md5sum`: MD5 checksums

#### Files Required for Truvari
- `*.sv.vcf.gz`: Structural variant files

#### Quality Metrics
- `*sv_metrics.csv`: Structural variant metrics
- `*roh_metrics.csv`: Runs of homozygosity
- `*ploidy_estimation_metrics.csv`: Ploidy estimation
- `*cnv_metrics.csv`: Copy number variations
- `*bed_coverage_metrics.csv`: Coverage metrics
- `*wgs_contig_mean_cov.csv`: Contig-level coverage
- `*vc_metrics.csv`: Variant calling metrics
- `*vc_hethome_ratio_metrics.csv`: Heterozygote/homozygote ratio
- `*mapping_metrics.csv`: Mapping metrics

## Development

### Development Environment Setup
```bash
# Development mode installation
pip install -e .

# Install development dependencies
pip install pytest black flake8 mypy
```

### Testing
```bash
# Unit tests
pytest qc-dashboard/api/tests/

# Integration tests
pytest qc-dashboard/api/tests/integration/
```

### Code Quality
```bash
# Formatting
black qc-dashboard/

# Style checking
flake8 qc-dashboard/

# Type checking
mypy qc-dashboard/
```

### Development Contribution
1. Create a feature branch: `git checkout -b feature/new-functionality`
2. Write tests for new features
3. Follow rules defined in `.cursor/rules/`
4. Submit a pull request with detailed description

## Contributing

We welcome community contributions! To contribute:

1. **Fork** the repository
2. Create a **feature branch** (`git checkout -b feature/AmazingFeature`)
3. **Commit** your changes (`git commit -m 'Add some AmazingFeature'`)
4. **Push** to the branch (`git push origin feature/AmazingFeature`)
5. Open a **Pull Request**

### Types of Contributions
- 🐛 **Bug fixes**
- ✨ **New features**
- 📚 **Documentation**
- 🧪 **Tests**
- 🎨 **UI/UX improvements**

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support and Contact

### Documentation
- [Detailed Installation Guide](docs/installation.md)
- [User Guide](docs/user-guide.md)
- [API Documentation](http://localhost:8000/docs)

### Support
- 🐛 **Issues**: [GitHub Issues](issues)
- 💬 **Discussions**: [GitHub Discussions](discussions)
- 📧 **Email**: support@vcbench.org

### Community
- ⭐ **GitHub Stars** appreciated!
- 🔄 **Share** with your colleagues
- 📖 **Cite** in your publications

---

**VCBench** - Quality control platform for genomics. Developed with ❤️ for the bioinformatics community.