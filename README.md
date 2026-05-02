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

## Routes

| Path                    | What it serves                                                   |
|-------------------------|------------------------------------------------------------------|
| `/`                     | Overview — recent runs panel and workspace navigation.           |
| `/home`                 | QC dashboard — multi-sample metric comparison.                   |
| `/runs`                 | Pipeline — AWS S3 import, ZIP upload, and benchmarking control. |
| `/truvari`              | Truvari structural-variant dashboard.                            |
| `/api/v1/*`             | REST API (runs, qc-metrics, happy-metrics, truvari-metrics, uploads, dash). |
| `/api/v1/upload/form`   | Embeddable upload form (used as an `<iframe>` in `/runs`).       |
| `/api/docs`             | Interactive OpenAPI documentation.                               |

## Usage

### 1. Upload Data

**Option A: AWS S3 import (recommended for GIAB samples)**
- Open the **Pipeline** page (`/runs`) → "Import from AWS S3" section
- Provide a sample ID (e.g. `NA24143_Lib3_Rep1`)
- The system auto-downloads files, fetches matching reference truth sets, and runs benchmarking

**Option B: Manual ZIP upload**
- Use the "Upload run archive" section on `/runs`
- Required files inside the ZIP: `*.gvcf.gz`, `*.sv.vcf.gz`, `*_metrics.csv`, `*.md5sum`

### 2. Run Benchmarking

1. Select a run from the dropdown on the **Manage runs** tab
2. Choose benchmarking tools:
   - **hap.py**: small variants (requires reference truth set)
   - **stratified**: stratified hap.py results (requires hap.py)
   - **Truvari**: structural variants
   - **csv**: reformat DRAGEN metrics for the dashboard
3. Click "Launch selected benchmarking"

### 3. View Results

- Interactive dashboards on `/home` (QC) and `/truvari` (structural variants)
- Download reports and export data
- Programmatic access: `/api/v1/runs/{run_name}/happy_metrics`, `/api/v1/runs/{run_name}/truvari_metrics`

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
│   ├── lab_runs/           # Uploaded DRAGEN files
│   ├── processed/          # Benchmarking results
│   └── reference/          # Reference genomes & truth sets
├── pipeline/               # Bioinformatics scripts (happy.sh, truvari.sh)
├── qc-dashboard/           # Main application
│   ├── api/                # FastAPI backend
│   │   ├── app/            # Routers, models, DB, websocket
│   │   └── tasks/          # Background tasks (upload, process, AWS, references)
│   ├── dash_app/           # Dash frontend
│   │   ├── pages/          # index, home, runs, truvari
│   │   ├── assets/         # Tokens (style.css, bar.css), fonts, logo
│   │   ├── config.py       # API_BASE_URL + FILE_TYPES
│   │   ├── data_loader.py  # API client helpers
│   │   ├── callbacks.py    # Cross-page interactive logic
│   │   └── visualization.py
│   ├── migrations/         # SQL migrations + apply_migration.py
│   └── init_db.py          # Database bootstrap
├── script/                 # Utility scripts
│   ├── aws_download_gvcf.sh        # AWS S3 download
│   └── setup_reference.sh          # Reference setup
└── docs/                   # Detailed documentation
```

## API Endpoints

### Run Management
- `GET /api/v1/runs` — list all runs
- `POST /api/v1/upload/aws` — import from AWS S3
- `POST /api/v1/runs/{run_name}/benchmarking` — launch benchmarking
- `GET /api/v1/runs/{run_name}/benchmarking` — completed benchmarking status

### Metrics
- `GET /api/v1/runs/{run_name}/happy_metrics` — hap.py results
- `GET /api/v1/runs/{run_name}/truvari_metrics` — Truvari results
- `GET /api/v1/qc-metrics` — general QC metrics
- `GET /api/v1/dash/samples/{file_type}` — samples available for a metric category
- `GET /api/v1/dash/data/{file_type}` — metric values across samples

### Real-time Logs
- `GET /api/v1/download/logs/{sample_id}` — polled log stream for AWS imports

Full API documentation: http://localhost:8002/docs

## Configuration

### Environment Variables

All variables are optional; the defaults match `docker/compose.yaml` and `start_app.sh`. Override only when the defaults don't fit your environment.

| Variable          | Default                                                            | Purpose                                                              |
|-------------------|--------------------------------------------------------------------|----------------------------------------------------------------------|
| `DATABASE_URL`    | `postgresql+psycopg2://wgs_user:password@localhost:5433/wgs`       | SQLAlchemy URL used by the API and `init_db.py`.                     |
| `API_HOST`        | `127.0.0.1`                                                        | Host used to compose `API_BASE_URL` for Dash → FastAPI calls.        |
| `API_PORT`        | `8002`                                                             | Port used to compose `API_BASE_URL` for Dash → FastAPI calls.        |
| `LAB_RUNS_DIR`    | `<project>/data/lab_runs`                                          | Raw uploaded run archives.                                           |
| `PROCESSED_DIR`   | `<project>/data/processed`                                         | Pipeline outputs.                                                    |
| `REFERENCE_DIR`   | `<project>/data/reference`                                         | Reference genome and truth sets used by hap.py / Truvari.            |
| `AWS_PROFILE`     | `vitalite`                                                         | AWS CLI profile for the S3 download script.                          |

Example overrides:

```bash
export DATABASE_URL="postgresql+psycopg2://wgs_user:password@localhost:5433/wgs"
export API_HOST="127.0.0.1"
export API_PORT="8002"
```

### Configuration Files

| File                                       | Purpose                                                  |
|--------------------------------------------|----------------------------------------------------------|
| `qc-dashboard/dash_app/config.py`          | Builds `API_BASE_URL` from `API_HOST` / `API_PORT`, plus the file-type mapping. |
| `qc-dashboard/api/app/database.py`         | Reads `DATABASE_URL`; creates the SQLAlchemy engine.     |
| `qc-dashboard/dash_app/assets/style.css`   | Design tokens (`:root` block) and base primitives.       |
| `qc-dashboard/dash_app/assets/bar.css`     | Sidebars and dashboard chrome.                           |
| `docker/compose.yaml`                      | PostgreSQL, bcftools, MultiQC services.                  |
| `environment.yml` / `requirements.txt`     | Conda and pip dependency lists.                          |

## Design System

VCBench ships a small, tokenized design system. All colors, spacing, typography, and shadow values are CSS custom properties defined in `qc-dashboard/dash_app/assets/style.css` under a `:root` block. Override or extend by adding rules in the same file rather than introducing inline styles.

### Tokens

| Group        | Variables                                                                 |
|--------------|---------------------------------------------------------------------------|
| Brand        | `--vc-brand-{900,700,500,100}`, `--vc-accent-{500,400}`                   |
| Ink/neutral  | `--vc-ink-{900,700,500,300,100}`, `--vc-bg`, `--vc-surface`, `--vc-border`|
| Status       | `--vc-success-{700,500,100}`, `--vc-warn-{700,500,100}`, `--vc-danger-{700,500,100}` |
| Type         | `--vc-font-sans`, `--vc-font-mono`, `--vc-fs-{xs,sm,md,lg,xl,2xl,3xl}`    |
| Spacing      | `--vc-s-{1,2,3,4,5,6,8}` on a 4 px scale                                  |
| Radius       | `--vc-r-{sm,md,lg}`                                                       |
| Shadow       | `--vc-shadow-{sm,md,lg}`                                                  |
| Layout       | `--vc-header-h`, `--vc-sidebar-w-collapsed`, `--vc-sidebar-w-expanded`, `--vc-content-max` |

### Primitives

| Class            | Purpose                                                          |
|------------------|------------------------------------------------------------------|
| `.btn`           | Base button. Combine with `.btn-primary` / `.btn-secondary` / `.btn-success` / `.btn-ghost`. |
| `.action-card`   | Workspace navigation card (used on `/`).                         |
| `.runs-panel`    | Bordered surface for the recent-runs table.                      |
| `.section-card`  | Generic content card with `--vc-shadow-sm` and a subtle border.  |
| `.pill`          | Status pill: `.is-success`, `.is-warn`, `.is-danger`.            |
| `.alert`         | Inline alert: `.alert-success`, `.alert-warning`, `.alert-error`.|
| `.empty-state`   | Calm empty placeholder (no error styling).                       |
| `.error-state`   | Soft danger-colored placeholder for callback failures.           |

### Accessibility

- Inter system stack with `text-wrap: balance` on headings.
- All interactive elements expose a `:focus-visible` ring using `--vc-brand-500`.
- `prefers-reduced-motion: reduce` collapses every transition to ~0 ms.
- Touch targets follow the 44 px minimum in the responsive breakpoint.
- Status colors avoid red/green-only encoding; an amber warning tier is provided.

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

## Changelog

### May 2026 — UI overhaul

- **Design system**: introduced `:root` design tokens (color, spacing on a 4 px scale, type scale, radius, shadow). See the **Design System** section.
- **Typography**: replaced the Arial/Times default chain with an Inter system stack.
- **Primitives**: replaced ad-hoc inline styles with reusable primitives — `.btn`, `.action-card`, `.runs-panel`, `.section-card`, `.pill`, `.alert`, `.empty-state`, `.error-state`.
- **Landing page (`/`)**: replaced the stock-photo hero and translucent card with a tokenized hero band, a recent-runs panel, and three workspace action cards. Empty / error states render as designed alert blocks instead of raw traceback text.
- **Dashboard (`/home`)**: shipped with the shared site header so users can navigate back to Overview / Pipeline. Sidebar navigation icons replaced with letter marks (Sum / SV / VC / CNV / ROH / HT / Plo / Bed / Cov / Map). The right rail collapsed state shows a vertical "MANUAL STATUS" marker; the full controls appear on hover.
- **Pipeline (`/runs`)**: unified header, cleaner tabs, embedded upload form rebuilt with a custom file drop zone and a 2×2 benchmarking option grid. AWS S3 import section restyled with the same tokens.
- **Resilience**: dash callbacks now timeout after 4 s on reads and 10 s on POST so a stalled API no longer freezes the page.
- **Responsive**: 900 px breakpoint and `prefers-reduced-motion` support.

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

**VCBench** — Quality control platform for genomics. Developed for the bioinformatics community at the IARC.
