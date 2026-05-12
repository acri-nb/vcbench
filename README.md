# VCBench

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.68+-009688.svg)](https://fastapi.tiangolo.com/)
[![Dash](https://img.shields.io/badge/Dash-2.x-119DFF.svg)](https://dash.plotly.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1.svg)](https://www.postgresql.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](#license)

Quality-control platform for whole-genome sequencing (WGS) runs. VCBench ingests DRAGEN outputs, runs hap.py and Truvari benchmarking against GIAB truth sets, and visualises the results in an interactive dashboard.

Built at the [Atlantic Cancer Research Institute (IARC)](https://canceratlantique.ca/en/).

---

## Screenshots

| Overview (`/`)                                    | QC dashboard (`/home`)                              |
|---------------------------------------------------|-----------------------------------------------------|
| ![Overview page](docs/images/overview.png)        | ![QC dashboard](docs/images/dashboard.png)          |

| Pipeline (`/runs`)                                | Truvari (`/truvari`)                                |
|---------------------------------------------------|-----------------------------------------------------|
| ![Pipeline page](docs/images/pipeline.png)        | ![Truvari results](docs/images/truvari.png)         |

---

## Table of contents

1. [Quick start](#quick-start)
2. [Routes](#routes)
3. [Usage](#usage)
4. [Reference files](#reference-files)
5. [Project structure](#project-structure)
6. [API endpoints](#api-endpoints)
7. [Configuration](#configuration)
8. [Design system](#design-system)
9. [Development](#development)
10. [Documentation](#documentation)
11. [Changelog](#changelog)
12. [License](#license)

---

## Quick start

### Prerequisites

- Docker and Docker Compose 20.10+
- Conda (Miniconda or Anaconda)
- 16 GB RAM, 100 GB free disk, 4+ CPU cores

### Install and run

```bash
# 1. Clone
git clone https://github.com/acri-nb/vcbench
cd vcbench

# 2. Conda environment
conda env create -f environment.yml
conda activate vcbench
# (alternative: ./setup_environment.sh — creates a local ./.venv instead)

# 3. Start PostgreSQL (the only service the app needs at runtime)
cd docker && docker compose up -d && cd ..
# Optional: ad-hoc bcftools/multiqc tool containers live under the `tools`
# profile — see docker/README.md.

# 4. Initialise the database (stays in qc-dashboard for the next step)
cd qc-dashboard && python init_db.py

# 5. Launch the API + dashboard
./start_app.sh
```

`start_app.sh` picks up the active conda env automatically (via `$CONDA_PREFIX`); if you used `setup_environment.sh` instead, it falls back to `./.venv/bin/python`. Override with `PYTHON_BIN=/path/to/python ./start_app.sh` if needed.

The application is then available at <http://localhost:8002> (OpenAPI docs at <http://localhost:8002/docs>).

---

## Routes

The Dash UI is mounted inside FastAPI via `WSGIMiddleware`, so a single uvicorn process serves both the dashboard and the REST API.

| Path                  | What it serves                                                       |
|-----------------------|----------------------------------------------------------------------|
| `/`                   | Overview — recent runs and workspace navigation                      |
| `/home`               | QC dashboard — multi-sample metric comparison                        |
| `/runs`               | Pipeline — AWS S3 import, ZIP upload, benchmarking control           |
| `/truvari`            | Structural-variant benchmarking results                              |
| `/api/v1/*`           | REST API (runs, hap.py / Truvari metrics, uploads, dash, downloads)  |
| `/api/v1/upload/form` | Embeddable upload form (used as an `<iframe>` inside `/runs`)        |
| `/docs`               | Interactive OpenAPI documentation (Swagger UI)                       |

---

## Usage

### Upload data

**Option A — AWS S3 import (recommended for GIAB samples).**
On `/runs`, fill the *Import from AWS S3* form with a sample ID (e.g. `NA24143_Lib3_Rep1`). VCBench downloads the run, fetches the matching reference truth set, and launches benchmarking.

**Option B — manual ZIP upload.**
Drop a ZIP archive of DRAGEN outputs (`*.gvcf.gz`, `*.sv.vcf.gz`, `*_metrics.csv`, `*.md5sum`) into the *Upload run archive* section. The FastAPI streaming endpoint avoids browser timeouts on large files.

### Benchmark a run

1. On the *Manage runs* tab of `/runs`, pick a run.
2. Tick the tools to launch:
   - `hap.py` — small-variant evaluation against a truth set
   - `stratified` — stratified hap.py results (requires `hap.py`)
   - `truvari` — structural-variant benchmarking
   - `csv` — reformat DRAGEN metrics for the dashboard
3. Click *Launch selected benchmarking*.

### Inspect results

- `/home` plots metric distributions across samples for the selected reference.
- `/truvari` shows precision, recall, F1 and genotype concordance for each Truvari run.
- All results are also reachable through the REST API (see [API endpoints](#api-endpoints)).

---

## Reference files

### Automatic setup (GIAB samples)

For known GIAB samples (NA12878, NA24143, NA24385, …), references are downloaded on demand:

```bash
./script/setup_reference.sh NA24143
```

### Manual setup (other samples)

Drop reference files in `data/reference/{sample}/`:

```text
data/reference/
├── GCA_000001405.15_GRCh38_no_alt_analysis_set.fasta       # genome
├── GCA_000001405.15_GRCh38_no_alt_analysis_set.fasta.fai
├── GRCh38.sdf/                                              # RTG Tools format
└── {sample}/
    ├── {sample}_truth.vcf.gz                                # truth set
    ├── {sample}_confident_regions.bed                       # confident regions
    └── stvar/                                               # SV truth (optional)
        ├── {sample}_sv_truth.vcf.gz
        └── {sample}_sv_confident_regions.bed
```

See [docs/AWS_INTEGRATION_README.md](docs/AWS_INTEGRATION_README.md) for the complete file-structure reference.

---

## Project structure

```text
vcbench/
├── data/
│   ├── lab_runs/                # uploaded DRAGEN runs
│   ├── processed/               # benchmarking results
│   └── reference/               # genomes and truth sets
├── docker/                      # PostgreSQL + bioinformatics images
├── docs/
│   ├── images/                  # README screenshots
│   └── *.md                     # AWS, Truvari, hap.py guides
├── pipeline/                    # bioinformatics scripts (happy.sh, truvari.sh, …)
├── qc-dashboard/
│   ├── api/
│   │   ├── app/                 # FastAPI routers, models, DB, websocket
│   │   └── tasks/               # background tasks (upload, process, AWS, references)
│   ├── dash_app/
│   │   ├── pages/               # index.py, home.py, runs.py, truvari.py
│   │   ├── assets/              # style.css, bar.css, fonts, logo
│   │   ├── config.py            # API_BASE_URL + FILE_TYPES
│   │   ├── data_loader.py       # API client helpers
│   │   ├── callbacks.py         # cross-page callbacks
│   │   └── visualization.py
│   ├── migrations/              # SQL migrations + apply_migration.py
│   └── init_db.py               # database bootstrap
└── script/                      # AWS download, reference setup
```

---

## API endpoints

Full schema and try-it-out forms live at `/api/docs` (powered by Swagger UI).

### Run management

| Method | Path                                               | Purpose                                  |
|--------|----------------------------------------------------|------------------------------------------|
| GET    | `/api/v1/runs`                                     | List all runs                            |
| POST   | `/api/v1/upload/runs`                              | Manual ZIP upload                        |
| POST   | `/api/v1/upload/aws`                               | AWS S3 import                            |
| GET    | `/api/v1/runs/{run_name}/benchmarking`             | Completed benchmarking status            |
| POST   | `/api/v1/runs/{run_name}/benchmarking`             | Launch benchmarking                      |

### Metrics

| Method | Path                                               | Purpose                                  |
|--------|----------------------------------------------------|------------------------------------------|
| GET    | `/api/v1/runs/{run_name}/happy_metrics`            | hap.py results                           |
| GET    | `/api/v1/runs/{run_name}/truvari_metrics`          | Truvari results                          |
| GET    | `/api/v1/qc-metrics`                               | General QC metrics                       |
| GET    | `/api/v1/dash/samples/{file_type}`                 | Samples available for a metric category  |
| GET    | `/api/v1/dash/data/{file_type}`                    | Metric values across samples             |

### Users and downloads

| Method | Path                                               | Purpose                                  |
|--------|----------------------------------------------------|------------------------------------------|
| POST   | `/api/v1/users`                                    | Create a user                            |
| GET    | `/api/v1/users/me`                                 | Current user profile                     |
| GET    | `/api/v1/download/logs/{sample_id}`                | Polled log stream for AWS imports        |

---

## Configuration

### Environment variables

All variables are optional and default to values that match `docker/compose.yaml` and `start_app.sh`. Override only when the defaults don't fit your setup.

| Variable          | Default                                                            | Purpose                                                          |
|-------------------|--------------------------------------------------------------------|------------------------------------------------------------------|
| `DATABASE_URL`    | `postgresql+psycopg2://wgs_user:password@localhost:55433/wgs`      | SQLAlchemy URL used by the API and `init_db.py` (host port matches `docker/compose.yaml`; override with `POSTGRES_HOST_PORT`) |
| `API_HOST`        | `127.0.0.1`                                                        | Host used by `dash_app/config.py` to compose `API_BASE_URL`      |
| `API_PORT`        | `8002`                                                             | Port used by `dash_app/config.py` to compose `API_BASE_URL`      |
| `LAB_RUNS_DIR`    | `<project>/data/lab_runs`                                          | Raw uploaded run archives                                        |
| `PROCESSED_DIR`   | `<project>/data/processed`                                         | Pipeline outputs                                                 |
| `REFERENCE_DIR`   | `<project>/data/reference`                                         | Reference genome and truth sets                                  |
| `AWS_PROFILE`     | `vitalite`                                                         | AWS CLI profile used by `script/aws_download_gvcf.sh`            |

Example overrides:

```bash
export DATABASE_URL="postgresql+psycopg2://wgs_user:password@localhost:55433/wgs"
export API_HOST="127.0.0.1"
export API_PORT="8002"
```

### Configuration files

| File                                       | Purpose                                                           |
|--------------------------------------------|-------------------------------------------------------------------|
| `qc-dashboard/dash_app/config.py`          | Builds `API_BASE_URL` from `API_HOST` / `API_PORT`; file-type map |
| `qc-dashboard/api/app/database.py`         | Reads `DATABASE_URL` and creates the SQLAlchemy engine            |
| `qc-dashboard/dash_app/assets/style.css`   | Design tokens (`:root`) and base primitives                       |
| `qc-dashboard/dash_app/assets/bar.css`     | Sidebars and dashboard chrome                                     |
| `docker/compose.yaml`                      | PostgreSQL, bcftools, MultiQC services                            |
| `environment.yml` / `requirements.txt`     | Conda and pip dependency lists                                    |

---

## Design system

VCBench ships a small tokenised design system. Colors, spacing, typography, radius, and shadow values are all CSS custom properties declared in `qc-dashboard/dash_app/assets/style.css` under a `:root` block. Override or extend by adding rules in the same file rather than introducing inline styles.

### Tokens

| Group        | Variables                                                                            |
|--------------|--------------------------------------------------------------------------------------|
| Brand        | `--vc-brand-{900,700,500,100}`, `--vc-accent-{500,400}`                              |
| Ink/neutral  | `--vc-ink-{900,700,500,300,100}`, `--vc-bg`, `--vc-surface`, `--vc-border`           |
| Status       | `--vc-success-{700,500,100}`, `--vc-warn-{700,500,100}`, `--vc-danger-{700,500,100}` |
| Type         | `--vc-font-sans`, `--vc-font-mono`, `--vc-fs-{xs,sm,md,lg,xl,2xl,3xl}`               |
| Spacing      | `--vc-s-{1,2,3,4,5,6,8}` on a 4 px scale                                             |
| Radius       | `--vc-r-{sm,md,lg}`                                                                  |
| Shadow       | `--vc-shadow-{sm,md,lg}`                                                             |
| Layout       | `--vc-header-h`, `--vc-sidebar-w-collapsed`, `--vc-sidebar-w-expanded`, `--vc-content-max` |

### Primitives

| Class                                              | Purpose                                                          |
|----------------------------------------------------|------------------------------------------------------------------|
| `.btn` + `.btn-primary` / `.btn-secondary` / `.btn-success` / `.btn-ghost` | Buttons with brand and status variants    |
| `.action-card`                                     | Workspace navigation card (used on `/`)                          |
| `.runs-panel`                                      | Bordered surface for the recent-runs table                       |
| `.section-card`                                    | Generic content card with `--vc-shadow-sm` and a subtle border   |
| `.pill` + `.is-success` / `.is-warn` / `.is-danger` | Inline status pill                                              |
| `.alert` + `.alert-success` / `.alert-warning` / `.alert-error` | Inline alert blocks                                  |
| `.empty-state`                                     | Calm empty placeholder                                           |
| `.error-state`                                     | Soft danger-coloured placeholder for callback failures           |

### Accessibility

- Inter system stack with `text-wrap: balance` on headings.
- All interactive elements expose a `:focus-visible` ring using `--vc-brand-500`.
- `prefers-reduced-motion: reduce` collapses every transition to ~0 ms.
- Touch targets meet the 44 px minimum on the responsive breakpoint.
- Status colors avoid red/green-only encoding; an amber warning tier is provided.

---

## Development

```bash
# Development dependencies
pip install pytest black flake8 mypy

# Database tests
cd qc-dashboard/api/app/test
python test_database.py

# Format and lint
black qc-dashboard/
flake8 qc-dashboard/
```

---

## Documentation

- [Quick-start guide](docs/QUICKSTART.md)
- [Truvari guide](docs/QUICKSTART_TRUVARI.md)
- [AWS S3 integration](docs/AWS_INTEGRATION_README.md)
- [Environment setup](docs/ENVIRONMENT_README.md)

---

## Changelog

### 2026-05 — UI overhaul

- Tokenised design system: `:root` block with brand, ink, status, typography, spacing, radius, and shadow scales.
- Inter system stack replaces the previous Arial/Times default chain.
- Reusable primitives: `.btn`, `.action-card`, `.runs-panel`, `.section-card`, `.pill`, `.alert`, `.empty-state`, `.error-state`.
- New landing page (`/`): tokenised hero band, recent-runs panel, three workspace action cards. Empty and error states render as designed alert blocks instead of raw traceback text.
- `/home`: ships the shared site header so users can navigate back to other pages. Sidebar nav icons replaced with letter marks (Sum, SV, VC, CNV, ROH, HT, Plo, Bed, Cov, Map). The right rail collapsed shows a vertical *MANUAL STATUS* marker; expanded reveals the controls.
- `/runs`: unified header, cleaner tabs, AWS S3 import section restyled with tokens, ZIP upload form rebuilt with a custom file drop zone and a 2 × 2 benchmarking option grid.
- `/truvari`: shared header and design tokens for visual consistency.
- Resilience: dash callbacks now timeout after 4 s on reads and 10 s on POST so a stalled API no longer freezes the page.
- Responsive: 900 px breakpoint and `prefers-reduced-motion` support.

### 2025-09 — Truvari and AWS integration

- Truvari structural-variant benchmarking: pipeline script, parser, REST endpoints, and dashboard page.
- AWS S3 import: download script, background task with real-time log streaming over polling, automatic reference setup for known GIAB samples.
- hap.py: reference-path resolution fix for non-trivial sample names, automatic GIAB truth-set download.

---

## License

MIT.

## Issues

Report bugs and feature requests on [GitHub Issues](https://github.com/acri-nb/vcbench/issues).
