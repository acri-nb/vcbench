# Transfer Observability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a persistent monitoring system for ZIP uploads, AWS imports, and pipeline processing in VCBench.

**Architecture:** Add persistent `TransferJob` and `TransferEvent` records, expose job APIs, integrate the existing upload/AWS/pipeline flows with a `job_service`, and add a Dash Monitoring page plus active-job summaries. The AWS shell downloader remains the execution path for compatibility, but it now emits structured job events through the service.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, PostgreSQL, Dash, existing WebSocket/polling support, pytest-compatible backend tests.

---

## File Structure

- Modify `qc-dashboard/api/app/models.py`: add enums and ORM models for transfer jobs/events.
- Modify `qc-dashboard/api/app/schemas.py`: add response schemas for jobs/events and summary payloads.
- Modify `qc-dashboard/api/app/crud.py`: add CRUD helpers for transfer jobs/events.
- Create `qc-dashboard/api/app/job_service.py`: single service API for creating jobs, progress updates, events, completion, failure, and summary formatting.
- Create `qc-dashboard/api/app/api_v1/endpoints/jobs.py`: job list/detail/events/summary/cancel/retry endpoints.
- Modify `qc-dashboard/api/app/main.py`: include jobs router and add `/ws/jobs/{job_id}` route.
- Create `qc-dashboard/migrations/versions/20260527_0003_add_transfer_jobs.py`: idempotent migration.
- Modify `qc-dashboard/api/app/api_v1/endpoints/uploads.py`: create jobs for ZIP/AWS flows and publish events.
- Modify `qc-dashboard/api/app/api_v1/endpoints/runs.py`: create jobs for manual benchmarking and publish pipeline events.
- Create `qc-dashboard/dash_app/pages/monitoring.py`: new Monitoring page with summary, filters, job table, and selected job detail.
- Modify `qc-dashboard/dash_app/pages/runs.py`: show active job summaries for AWS and iframe upload responses.
- Modify `qc-dashboard/dash_app/app.py`: add `/monitoring` route.
- Modify `qc-dashboard/dash_app/assets/style.css`: add high-contrast monitoring styles.
- Modify `qc-dashboard/api/app/api_v1/endpoints/uploads.py` upload form HTML/JS: use `XMLHttpRequest` progress and render returned job ID.
- Add backend tests under `qc-dashboard/api/app/test/test_transfer_jobs.py`.

## Tasks

### Task 1: Persistent Job Model

- [ ] Write tests in `qc-dashboard/api/app/test/test_transfer_jobs.py` for creating a job, appending events, progress updates, and summary aggregation.
- [ ] Run the test and verify it fails because job models/service do not exist.
- [ ] Add `TransferJobType`, `TransferJobStatus`, `TransferJobPhase`, `TransferEventLevel`, `TransferJob`, and `TransferEvent`.
- [ ] Add schemas and CRUD helpers.
- [ ] Add `job_service.py` with `create_job`, `append_event`, `update_progress`, `mark_phase`, `complete_job`, `fail_job`, `request_cancel`, `get_job_summary`.
- [ ] Run backend tests and verify they pass.
- [ ] Commit with `feat: add transfer job model`.

### Task 2: Job API

- [ ] Write tests for `GET /api/v1/jobs`, `GET /api/v1/jobs/summary`, `GET /api/v1/jobs/{job_id}`, `GET /api/v1/jobs/{job_id}/events`, and `POST /api/v1/jobs/{job_id}/cancel`.
- [ ] Run the tests and verify they fail because endpoints do not exist.
- [ ] Add `jobs.py` router and include it from `main.py`.
- [ ] Add WebSocket route `/ws/jobs/{job_id}` using the existing WebSocket manager where practical, with polling endpoints as the stable path.
- [ ] Run tests and verify they pass.
- [ ] Commit with `feat: expose transfer job api`.

### Task 3: Upload, AWS, and Pipeline Integration

- [ ] Write tests that local upload returns `job_id`, creates progress events, and records failure state on invalid processing.
- [ ] Run the tests and verify they fail because command endpoints do not create jobs.
- [ ] Update `/api/v1/upload/runs` to create a job, stream bytes to disk, emit upload progress snapshots, then emit validation/processing events.
- [ ] Update `/api/v1/upload/aws` and `process_aws_run_background` to create/use a job and publish structured events while preserving current shell-script execution.
- [ ] Update manual benchmarking endpoint to create a pipeline job and publish phase events.
- [ ] Run tests and verify they pass.
- [ ] Commit with `feat: publish transfer job events`.

### Task 4: Monitoring UI

- [ ] Add a Dash Monitoring page that fetches `/jobs/summary`, `/jobs`, and selected job events.
- [ ] Add navigation link to Monitoring.
- [ ] Add high-contrast monitoring styles.
- [ ] Add active-job summary on Pipeline page for newly launched AWS jobs and upload responses.
- [ ] Run app locally and verify `/monitoring` renders.
- [ ] Commit with `feat: add transfer monitoring dashboard`.

### Task 5: Browser Upload Progress

- [ ] Replace the upload form `fetch` call with `XMLHttpRequest`.
- [ ] Render upload percentage, bytes uploaded, and returned job ID.
- [ ] Keep API key header behavior unchanged.
- [ ] Smoke test a small ZIP upload with auth enabled.
- [ ] Commit with `feat: show browser upload progress`.

### Task 6: Verification

- [ ] Run backend tests.
- [ ] Run Alembic upgrade against the local database.
- [ ] Start VCBench on an available local port.
- [ ] Verify `/api/v1/jobs/summary`, `/api/v1/jobs`, `/monitoring`, and `/api/v1/upload/form`.
- [ ] Perform an authenticated small ZIP upload with `auto_process=false`.
- [ ] Verify the job appears in `/api/v1/jobs` and Monitoring.
- [ ] Clean up smoke-test artifacts.
- [ ] Commit any remaining verification fixes.
