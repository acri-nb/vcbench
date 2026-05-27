# Transfer Observability Design

Date: 2026-05-27

## Summary

VCBench needs a unified monitoring surface for long-running transfers and processing. The current app has separate behavior for ZIP uploads and AWS imports: local upload shows only a basic "upload in progress" message, while AWS import streams logs through an in-memory polling store. The target design is a complete observability center for uploads, AWS downloads, validation, extraction, and pipeline execution.

The chosen direction is approach C: a dedicated monitoring system with persistent jobs, live progress, event history, diagnostic detail, and room for retry, cancel, alerts, and system metrics.

## Goals

- Represent every long-running operation as a persistent observable job.
- Show reliable progress for ZIP uploads, AWS imports, and pipeline phases.
- Provide a Monitoring page with global status, recent jobs, throughput, failures, and disk capacity.
- Keep the Pipeline page focused on launching work while still showing the active job summary.
- Persist logs and progress so users can diagnose failures after refreshing the browser.
- Use clear, accessible status colors with strong contrast.

## Non-Goals

- Full external observability integration such as Prometheus or Grafana in the first release.
- Distributed worker orchestration in the first release.
- Perfect byte-level progress for every pipeline tool. Pipeline phases may report phase-level progress when byte counts are not meaningful.
- Automatic repair of failed biological pipeline outputs.

## Current Context

Relevant current files:

- `qc-dashboard/api/app/api_v1/endpoints/uploads.py`: local ZIP upload and AWS import endpoints.
- `qc-dashboard/api/app/websocket.py`: in-memory log storage and WebSocket/polling support for AWS downloads.
- `qc-dashboard/api/app/api_v1/endpoints/download_status.py`: polling endpoints for AWS log/status retrieval.
- `qc-dashboard/dash_app/pages/runs.py`: Pipeline UI, AWS import callbacks, upload iframe, and log polling.
- `script/aws_download_gvcf.sh`: shell-based S3 listing and copy flow.

The current AWS flow already has a useful shape: background work emits logs and the UI polls them. The limitation is that logs are process-local and mostly text-based. ZIP upload has no real browser progress bar and no persisted job identity.

## UX Design

### Pipeline Page

The existing `/runs` page remains the main action page. When a user starts a ZIP upload, AWS import, or manual benchmarking run, the page should create or receive a `job_id` and show a compact active-job panel:

- job name and type;
- current status and phase;
- progress bar;
- bytes transferred when available;
- transfer rate and ETA when available;
- last few events;
- link to the full job detail.

This avoids turning the launch form into a full operations dashboard.

### Monitoring Page

Add a new Monitoring page to the navigation. It should provide:

- summary counters: active jobs, queued jobs, total throughput, failures in the last 24 hours, disk free;
- a job table with type, subject, status, phase, progress, ETA, updated time, and action;
- filters for `upload_zip`, `aws_import`, and `pipeline`;
- filters for status, including active, completed, failed, and canceled;
- access to job detail.

### Job Detail

The detail view should support diagnosis without opening terminal logs:

- source and destination;
- phase timeline;
- bytes done/total, transfer rate, ETA;
- disk free at relevant checkpoints;
- recent warnings and final error message;
- complete event log with level and timestamp;
- actions such as `Cancel`, `Retry`, and `Open run` when supported.

### Color and Contrast

Use a high-contrast operational palette:

- primary text: dark neutral, e.g. `#111827`;
- secondary text: medium neutral, e.g. `#374151` or `#4b5563`;
- surfaces: white or very light gray;
- queued: blue;
- running/progress: teal;
- completed: green;
- warning: orange;
- failed: red.

Avoid pale text on pale cards. Status colors should be used for badges, progress bars, and alerts rather than broad page backgrounds. Terminal-style logs may use a dark surface, but text contrast must remain high.

## Technical Design

### Core Abstraction

Introduce a job service that all long-running operations use:

- `create_job()`
- `update_progress()`
- `append_event()`
- `mark_phase()`
- `fail_job()`
- `complete_job()`
- `request_cancel()`

The service writes to Postgres and broadcasts updates over the existing real-time mechanism. Existing in-memory AWS log storage should be treated as a transition path, not the long-term source of truth.

### Data Model

Add `transfer_jobs`:

- `id`: UUID primary key.
- `type`: `upload_zip`, `aws_import`, `pipeline`.
- `subject_id`: sample ID, run name, or pipeline label.
- `status`: `queued`, `running`, `completed`, `failed`, `canceled`.
- `phase`: `upload`, `download`, `validate`, `extract`, `reference_setup`, `process`, `complete`.
- `source_uri`: optional source such as browser filename or S3 URI.
- `destination_path`: optional local destination.
- `bytes_total`: nullable integer.
- `bytes_done`: integer default `0`.
- `rate_bps`: nullable integer.
- `eta_seconds`: nullable integer.
- `started_at`, `updated_at`, `completed_at`.
- `error_code`, `error_message`.
- `cancel_requested`: boolean default `false`.
- `metadata`: JSON for tool-specific context.

Add `transfer_events`:

- `id`: monotonically increasing integer primary key.
- `job_id`: foreign key to `transfer_jobs`.
- `sequence`: per-job integer sequence.
- `timestamp`.
- `level`: `info`, `progress`, `success`, `warning`, `error`.
- `phase`.
- `message`.
- `bytes_done`, `bytes_total`, `rate_bps`: optional snapshot fields.
- `metadata`: JSON for details such as S3 key, filename, exit code, or validation result.

Optional later table: `job_metric_snapshots` for aggregate throughput, disk capacity, and queue metrics over time.

### API

Command endpoints should return a `job_id`:

- `POST /api/v1/upload/runs`
- `POST /api/v1/upload/aws`
- `POST /api/v1/runs/{run_name}/benchmarking`

Monitoring endpoints:

- `GET /api/v1/jobs`
- `GET /api/v1/jobs/summary`
- `GET /api/v1/jobs/{job_id}`
- `GET /api/v1/jobs/{job_id}/events?since=...`
- `POST /api/v1/jobs/{job_id}/cancel`
- `POST /api/v1/jobs/{job_id}/retry`
- `WS /ws/jobs/{job_id}`

The existing `/api/v1/download/logs/{sample_id}` endpoints can remain during migration, but new UI should prefer job-based endpoints.

### ZIP Upload Progress

For browser uploads, the most accurate transfer progress is available before the request reaches FastAPI. Replace the fetch-based upload form with `XMLHttpRequest` or another browser API that exposes upload progress events. The client should:

- create or receive a job ID at upload start;
- update the visible progress from `xhr.upload.onprogress`;
- submit the multipart upload with the API key header;
- switch to backend-reported phases after upload completion.

The backend should stream the incoming file to disk as it does now, then publish server-side events for validation, extraction, and optional pipeline execution.

### AWS Download Progress

For AWS imports, the preferred implementation is Python-based S3 downloading through `boto3`, not shell output parsing. The backend should:

- list required S3 objects before download;
- compute `bytes_total`;
- download files with callbacks that increment `bytes_done`;
- publish events per file and progress snapshots;
- record warnings for missing optional files and errors for missing required files.

The existing `script/aws_download_gvcf.sh` can remain as a fallback while the new path is built. If the shell script remains in use temporarily, parseable progress lines should be emitted so the job service can update the job without relying only on human-readable text.

### Pipeline Progress

Pipeline phases should publish events for:

- reference check/setup;
- ZIP extraction;
- CSV formatting;
- hap.py;
- Truvari;
- completion or failure.

Byte-level progress is not always meaningful here. Phase-level progress is acceptable, as long as the UI is explicit that the job is in processing rather than transferring bytes.

### Cancel and Retry

First release should support cancel requests in the model and UI, even if only some job types can honor cancellation immediately.

- ZIP upload cancellation is primarily client-side before the request completes.
- AWS Python downloads can check `cancel_requested` between files and during callbacks.
- Pipeline cancellation may need process tracking and should be limited until subprocess management is robust.

Retry should create a new job linked to the failed job in metadata. It should not mutate history in place.

### Alerts and Retention

Initial alerting can be in-app only:

- failed job badge in Monitoring;
- recent failures count;
- warning rows in job detail.

Later alerting can add email, Slack, or Telegram if needed.

Retain job history long enough for operational diagnosis. A reasonable default is 30 days for jobs and events, with a cleanup endpoint or scheduled cleanup task.

## Rollout Plan

### Phase 1: Job Foundation

- Add database models, schemas, CRUD, and migrations for `transfer_jobs` and `transfer_events`.
- Add a job service module.
- Add job listing, summary, detail, event, and WebSocket/polling endpoints.
- Keep existing AWS and upload behavior functional.

### Phase 2: UI Monitoring

- Add Monitoring page and navigation link.
- Add active-job panel to Pipeline page.
- Replace low-contrast mock styling with the approved high-contrast palette.

### Phase 3: Local Upload Integration

- Change upload form to use real browser upload progress.
- Return `job_id` from upload endpoints.
- Publish backend validation and processing events.

### Phase 4: AWS Integration

- Add Python S3 importer with object pre-listing, total bytes, callbacks, and job events.
- Keep shell script fallback until parity is verified.

### Phase 5: Operational Controls

- Add retry and cancel where technically supported.
- Add retention cleanup and in-app alert summaries.
- Add optional disk/throughput snapshots.

## Testing

Backend tests:

- job creation and status transitions;
- event sequencing and retrieval with `since`;
- summary aggregation;
- auth requirements for command/control endpoints;
- failure paths preserve error details.

Upload tests:

- missing API key returns 401 when auth is configured;
- valid ZIP creates a job and upload artifact;
- oversized uploads fail cleanly;
- invalid ZIP reports validation failure.

AWS tests:

- mocked S3 listing computes total bytes;
- download callbacks update progress;
- missing required objects fail with useful error;
- cancellation stops at a defined boundary.

UI tests:

- Monitoring page renders jobs and filters status/type;
- active job panel updates progress;
- failed job detail shows error and logs;
- color contrast remains readable across status states.

## Design Decisions

- Monitoring should be a top-level route `/monitoring`, with a navigation link next to Pipeline. The Pipeline page should keep only compact active-job summaries.
- The first implementation should support both WebSockets and polling. WebSockets give the best live experience; polling remains the fallback and matches the current AWS implementation style.
- The shell AWS downloader should remain only as a migration fallback. The target implementation is the Python S3 importer because it can report object sizes, byte progress, cancellation boundaries, and structured errors.
