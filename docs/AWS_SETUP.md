# AWS S3 import — setup & operation

How to make the **AWS S3 import** feature (`/runs` → *Import from AWS S3*, `POST /api/v1/upload/aws`) work on a machine, what it depends on, and the known limitations.

> The import pulls DRAGEN / Emedgene result files from a Vitalité production S3
> bucket. Emedgene (Illumina) is the source platform; its results land in the
> `cac1-emg-prd-s3-auto-results` bucket, and this feature downloads the GVCF /
> SV-VCF / metric CSVs from there into `data/lab_runs/<sample>_R001/`.

---

## 1. Prerequisites

### AWS CLI (required)

The download script (`script/aws_download_gvcf.sh`) shells out to the `aws` CLI
and exits immediately if it is not on `PATH`.

Install (macOS / Homebrew):

```bash
brew install awscli
aws --version        # expect aws-cli/2.x
```

Other platforms: see <https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html>.

### AWS credentials for the `vitalite` profile (required)

Every `aws` call in the script is hardcoded to `--profile vitalite` against:

| Setting     | Value                                                        |
|-------------|--------------------------------------------------------------|
| Bucket      | `cac1-emg-prd-s3-auto-results`                               |
| Base path   | `vitalite-genmol_6cb572b1-386c-3305-82ab-f05a82a5233a`       |
| Region      | `ca-central-1` (cac1)                                        |
| Profile     | `vitalite`                                                   |

So the host needs a configured `vitalite` profile with read access to that
bucket. Two ways to configure it:

**Option A — AWS IAM Identity Center / SSO (recommended; a `~/.aws/sso/` cache already exists on the ops machine):**

```bash
aws configure sso --profile vitalite
# answer the prompts: SSO start URL, region (ca-central-1), account, role
aws sso login --profile vitalite          # opens a browser to authenticate
```

**Option B — static access keys:**

```bash
aws configure --profile vitalite
# AWS Access Key ID:     <key>
# AWS Secret Access Key: <secret>
# Default region name:   ca-central-1
```

> ⚠️ Never commit credentials. They live in `~/.aws/credentials` /
> `~/.aws/config`, outside the repo.

### Verify connectivity (read-only)

```bash
aws --profile vitalite s3 ls "s3://cac1-emg-prd-s3-auto-results/vitalite-genmol_6cb572b1-386c-3305-82ab-f05a82a5233a/"
```

If this lists sample IDs, the import will work. Common failures:

| Error                                            | Cause / fix                                  |
|--------------------------------------------------|----------------------------------------------|
| `aws: command not found`                         | AWS CLI not installed (see above)            |
| `The config profile (vitalite) could not be found` | `vitalite` profile not configured          |
| `Error when retrieving token ... sso`            | Run `aws sso login --profile vitalite`       |
| `AccessDenied`                                   | Profile lacks IAM read access to the bucket  |

---

## 2. How the import works end-to-end

1. **`POST /api/v1/upload/aws`** (`uploads.py`) with `{ "sample_id": "NA24143", "auto_process": true, "benchmarking": "happy,truvari,csv" }`.
   Creates a `TransferJob` (type `aws_import`) and, if `auto_process`, schedules
   `process_aws_run_background`.
2. **`process_aws_run_background`** runs `script/aws_download_gvcf.sh <sample_id>`,
   streaming stdout line-by-line into both the live console (WebSocket
   `/ws/download/{sample_id}` + polling fallback `/api/v1/download/logs/...`) and
   `TransferEvent` rows.
3. The script downloads `*.gvcf.gz`, `*.sv.vcf.gz` and the metric CSVs into
   `data/lab_runs/<sample_id>_R001/`.
4. On success → `ensure_references` (download GIAB truth set) → `run_pipeline`
   (hap.py / Truvari / csv). The `LabRun` ends `AWAITING_APPROVAL`.
5. **On any failure** the script's non-zero exit raises `CalledProcessError`;
   the run is marked **`FAILED`** with the error message, surfaced in the run
   list and the live console. (Failures are explicit, not silent.)

---

## 3. Known limitations (tracked in `docs/audit/AUDIT-2026-06-18.md`)

- **Bucket / base-path / profile are hardcoded** in `script/aws_download_gvcf.sh`.
  The README documents an `AWS_PROFILE` env var, but the script overrides it on
  line 8 and every call uses a literal `--profile vitalite`, so `AWS_PROFILE` has
  **no effect**. A non-Vitalité deployment cannot use this feature without
  editing the script. *(Recommended fix: honor env vars —
  `AWS_PROFILE="${AWS_PROFILE:-vitalite}"`, `BUCKET="${VCBENCH_S3_BUCKET:-...}"`,
  and replace every literal `--profile vitalite` with `--profile "$AWS_PROFILE"`.)*
- **AWS jobs never populate byte progress** (`bytes_total`/`bytes_done`/`rate_bps`),
  so on `/monitoring` the progress bar, throughput and ETA stay empty for AWS
  imports (only text events stream).
- **`auto_process=false`** leaves the job in `QUEUED` with no worker to start it
  (no manual-trigger endpoint exists) — a permanent "queued" job.

---

## 4. Emedgene (Illumina) — relationship to this app

- The S3 bucket above holds **Emedgene-produced results** (`emg` = Emedgene); the
  AWS import is how VCBench ingests them. Authentication to that bucket is **AWS**
  (the `vitalite` profile), **not** an Emedgene API token.
- The **Emedgene REST API token is NOT used anywhere in this codebase.** The only
  Emedgene-related code is `emedgene_report/report_gen.py`, which reads a local
  `json_output_emedgene.json` file (an exported case JSON) and renders a PDF — it
  does no API calls and needs no token. (It also needs `reportlab`, which is not
  in the dependency files.)
- If a direct Emedgene-API integration (pull cases/results via token) is desired,
  it does not exist yet and would be new work; the token would belong in an env
  var / secrets manager, never in the repo.

---

## 5. Quick local check

```bash
# 1. CLI present?
aws --version
# 2. profile + access?
aws --profile vitalite s3 ls "s3://cac1-emg-prd-s3-auto-results/vitalite-genmol_6cb572b1-386c-3305-82ab-f05a82a5233a/" | head
# 3. then trigger from the UI (/runs → Import from AWS S3) or:
curl -s -X POST http://127.0.0.1:8002/api/v1/upload/aws \
  -H 'Content-Type: application/json' \
  -d '{"sample_id":"NA24143","auto_process":true,"benchmarking":"happy,csv"}'
```
