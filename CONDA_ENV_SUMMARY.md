# VCBench Conda Environment Summary

## Environment Created: `bioinfo`

A complete conda environment has been created for VCBench development with all necessary dependencies.

## Files Created

### `environment.yml`
Conda environment specification file
- **Location**: `vcbench/environment.yml`
- **Usage**: `conda env create -f environment.yml`
- **Contents**: All conda-installable packages

### `requirements.txt`
Pip package requirements
- **Location**: `vcbench/requirements.txt`
- **Usage**: `pip install -r requirements.txt`
- **Contents**: Additional pip packages

### `setup_environment.sh`
Automated setup script
- **Location**: `vcbench/setup_environment.sh`
- **Usage**: `./setup_environment.sh`
- **Features**: Complete automated environment setup

### `ENVIRONMENT_README.md`
Detailed setup documentation
- **Location**: `vcbench/ENVIRONMENT_README.md`
- **Contents**: Troubleshooting and detailed instructions

## Environment Contents

### Python Version
- **Python**: 3.9.23

### Core Packages
| Package | Version | Purpose |
|---------|---------|---------|
| fastapi | 0.116.1 | Web API framework |
| uvicorn | 0.34.3 | ASGI server |
| dash | 3.2.0 | Web dashboard framework |
| plotly | 6.3.0 | Interactive visualizations |
| pandas | 2.3.2 | Data manipulation |
| sqlalchemy | 2.0.43 | Database ORM |
| pydantic | 1.10.19 | Data validation |
| numpy | 1.26.4 | Numerical computing |

### Additional Packages
- httpx: HTTP client
- aiofiles: Async file operations
- email-validator: Email validation
- psycopg2-binary: PostgreSQL driver
- python-multipart: File uploads

### System Tools
- **bcftools**: 1.22 (via Homebrew)
- **Docker**: Required for bioinformatics containers
- **PostgreSQL**: Via Docker container

## Setup Methods

### Method 1: Automated (Recommended)
```bash
cd vcbench
./setup_environment.sh
```

### Method 2: Manual Conda
```bash
conda env create -f environment.yml
conda activate bioinfo
pip install -r requirements.txt
```

### Method 3: Manual Pip
```bash
conda create -n bioinfo python=3.9
conda activate bioinfo
pip install -r requirements.txt
```

## Verification

After setup, verify the environment:
```bash
conda activate bioinfo
python --version  # Should show Python 3.9.x
bcftools --version  # Should show bcftools 1.22
```

## Key Features

✅ **Complete environment** with all VCBench dependencies
✅ **Automated setup** script for easy installation
✅ **Documentation** with troubleshooting guides
✅ **Cross-platform** compatibility
✅ **Bioinformatics tools** (bcftools) included
✅ **Database support** (PostgreSQL via Docker)
✅ **Web framework** (FastAPI + Dash) ready

## Usage

Once environment is set up:
```bash
# Activate
conda activate bioinfo

# Start Docker services
cd docker && docker-compose up -d

# Run application
cd ../qc-dashboard && ./start_app.sh
```

Access the application at:
- **Web Interface**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## Notes

- **mamba-ssm**: Not included due to compilation issues. Install separately with: `pip install mamba-ssm --no-cache-dir`
- **Docker**: Required for hap.py, Truvari, and PostgreSQL services
- **bcftools**: Installed via Homebrew on macOS. Use system package manager on Linux

## Maintenance

```bash
# Update environment
conda update --all
pip install --upgrade -r requirements.txt

# Clean environment
conda clean --all

# Remove environment (if needed)
conda env remove -n bioinfo
```

---

**Environment Status**: ✅ Ready for VCBench development
**Last Updated**: $(date)
**Python Version**: 3.9
**Platform**: macOS (compatible with Linux/Windows)
