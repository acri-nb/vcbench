# VCBench - WGS Quality Control Dashboard

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.68+-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/docker-required-blue.svg)](https://www.docker.com/)

Quality control platform for Whole Genome Sequencing (WGS) analysis with automated benchmarking (hap.py, Truvari) and interactive visualization.

## Quick Start

### Prerequisites

- **Docker & Docker Compose** 20.10+
- **Conda** (Miniconda/Anaconda)
- **Hardware**: 16GB+ RAM, 100GB+ storage, 4+ CPU cores

### Installation

```bash
# 1. Clone repository
git clone https://github.com/acri-nb/vcbench
cd vcbench

# 2. Setup environment
conda env create -f environment.yml
conda activate bioinfo
# OR use automated script: ./setup_environment.sh

# 3. Start Docker services
cd docker && docker compose up -d

# 4. Initialize database
cd ../qc-dashboard
python init_db.py

# 5. Start application
uvicorn api.app.main:app --reload --host 0.0.0.0 --port 8002
```

**Access:**
- Web Interface: http://localhost:8002
- API Docs: http://localhost:8002/docs

## Features

### Benchmarking Tools

- **hap.py**: Small variant evaluation (SNP, indel) with precision, sensitivity, F1-score
- **Truvari**: Structural variant benchmarking with detailed metrics
- **Automated reference management**: Auto-downloads GIAB truth sets for known samples

### Data Management

- **AWS S3 integration**: Direct import from S3 buckets
- **DRAGEN file support**: Automatic processing of GVCF, metrics CSV, and checksums
- **Reference auto-setup**: Downloads and configures reference files for GIAB samples (NA12878, NA24143, etc.)

### Visualization & API

- Interactive Dash dashboards with multi-sample comparisons
- RESTful API with OpenAPI documentation
- PostgreSQL database for persistent storage

## Usage

### 1. Upload Data

**Option A: Manual Upload**
- Upload ZIP file containing DRAGEN output via web interface
- Required files: `*.gvcf.gz`, `*.sv.vcf.gz`, `*_metrics.csv`, `*.md5sum`

**Option B: AWS S3 Import**
- Use "Import from AWS S3" in Run Management
- Provide sample ID (e.g., `NA24143_Lib3_Rep1`)
- System automatically downloads files and sets up references

### 2. Run Benchmarking

1. Select run from dropdown
2. Choose benchmarking tools:
   - **hap.py**: Small variants (requires reference truth set)
   - **Truvari**: Structural variants
   - **CSV reformat**: Process DRAGEN metrics
3. Click "Launch Selected Benchmarking"

### 3. View Results

- Interactive dashboards show metrics and comparisons
- Download reports and export data
- Access via REST API: `/api/v1/runs/{run_name}/happy_metrics` or `/truvari_metrics`

## Reference Files

### Automatic Setup (GIAB Samples)

For known GIAB samples (NA12878, NA24143, NA24385, etc.), reference files are downloaded automatically:

```bash
# Manual setup if needed
./script/setup_reference.sh NA24143
```

### Manual Setup (Other Samples)

Place reference files in `data/reference/{sample}/`:

```
data/reference/
├── GCA_000001405.15_GRCh38_no_alt_analysis_set.fasta  # Genome reference
├── GCA_000001405.15_GRCh38_no_alt_analysis_set.fasta.fai
├── GRCh38.sdf/                                         # RTG Tools format
└── {sample}/
    ├── {sample}_truth.vcf.gz                          # Truth set
    ├── {sample}_confident_regions.bed                  # Confident regions
    └── stvar/                                          # Structural variants (optional)
        ├── {sample}_sv_truth.vcf.gz
        └── {sample}_sv_confident_regions.bed
```

See [data/struct.md](data/struct.md) for complete file structure documentation.

## Project Structure

```
vcbench/
├── data/
│   ├── lab_runs/          # Uploaded DRAGEN files
│   ├── processed/          # Benchmarking results
│   └── reference/          # Reference genomes & truth sets
├── pipeline/               # Bioinformatics scripts (happy.sh, truvari.sh)
├── qc-dashboard/          # Main application
│   ├── api/               # FastAPI backend
│   └── dash_app/          # Dash frontend
├── script/                # Utility scripts
│   ├── aws_download_gvcf.sh      # AWS S3 download
│   └── setup_reference.sh        # Reference setup
└── docs/                  # Detailed documentation
```

## API Endpoints

### Run Management
- `GET /api/v1/runs` - List all runs
- `POST /api/v1/upload/aws` - Import from AWS S3
- `POST /api/v1/runs/{run_name}/benchmarking` - Launch benchmarking

### Metrics
- `GET /api/v1/runs/{run_name}/happy_metrics` - hap.py results
- `GET /api/v1/runs/{run_name}/truvari_metrics` - Truvari results
- `GET /api/v1/qc-metrics` - General QC metrics

Full API documentation: http://localhost:8002/docs

## Configuration

### Environment Variables

```bash
export DATABASE_URL="postgresql://wgs_user:password@localhost:5433/wgs"
export LAB_RUNS_DIR="/path/to/vcbench/data/lab_runs"
export PROCESSED_DIR="/path/to/vcbench/data/processed"
export REFERENCE_DIR="/path/to/vcbench/data/reference"
```

### Configuration Files

- `qc-dashboard/dash_app/config.py` - Frontend configuration
- `qc-dashboard/api/app/database.py` - Database settings
- `docker/compose.yaml` - Docker services

## Development

```bash
# Install development dependencies
pip install pytest black flake8 mypy

# Run tests
cd qc-dashboard/api/app/test
python test_database.py

# Code formatting
black qc-dashboard/
flake8 qc-dashboard/
```

## Documentation

- **[Quick Start Guide](docs/QUICKSTART.md)** - Getting started tutorial
- **[Truvari Guide](docs/QUICKSTART_TRUVARI.md)** - Structural variant benchmarking
- **[File Structure](data/struct.md)** - Complete file structure reference
- **[Environment Setup](ENVIRONMENT_README.md)** - Detailed environment configuration
- **[AWS Integration](docs/AWS_INTEGRATION_README.md)** - AWS S3 import guide

## Recent Updates

### hap.py Integration
- ✅ Fixed reference file path resolution (base sample extraction)
- ✅ Automatic reference download for GIAB samples
- ✅ Improved error handling and logging

### AWS S3 Integration
- ✅ Direct import from S3 buckets
- ✅ Automatic file organization and processing
- ✅ Background task execution with progress tracking

### Truvari Visualization
- ✅ Interactive dashboard for structural variants
- ✅ Automated metric parsing and storage
- ✅ Complete REST API endpoints

## Support

- **Issues**: [GitHub Issues](https://github.com/acri-nb/vcbench/issues)
- **API Docs**: http://localhost:8002/docs
- **Email**: support@vcbench.org

## License

MIT License - see [LICENSE](LICENSE) file for details.

---

**VCBench** - Quality control platform for genomics. Developed with ❤️ for the bioinformatics community.
