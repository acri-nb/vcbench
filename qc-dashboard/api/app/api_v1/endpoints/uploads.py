import asyncio
import os
import subprocess
from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks, HTTPException, Depends
from fastapi.responses import HTMLResponse
from pathlib import Path
from typing import Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.app import crud, job_service, models, schemas, settings
from api.app import websocket as ws_manager
from api.app.database import SessionLocal, get_db
from api.app.security import Role, require_role
from api.tasks.upload_run import upload_run, unique_upload_path, sanitize_upload_filename
from api.tasks.process_run import run_pipeline
from api.tasks.setup_reference import ensure_references
from api.tasks.utils import split_run_name

router = APIRouter()

LAB_RUNS_DIR = settings.LAB_RUNS_DIR
UPLOAD_DIR = settings.UPLOAD_DIR
AWS_DOWNLOAD_SCRIPT = settings.AWS_DOWNLOAD_SCRIPT


class AWSUploadRequest(BaseModel):
    sample_id: str
    benchmarking: Optional[str] = ""
    auto_process: bool = True

# FILES -------------------------------------------------------------------------------------------

def process_run_background(
    zip_path: Path,
    sample: str,
    lab_run_id: int,
    benchmarking_options: str = "",
    job_id: str | None = None,
):
    """Background task to process the uploaded run"""
    db = SessionLocal()
    try:
        if job_id:
            job_service.mark_phase(db, job_id, models.TransferJobPhase.EXTRACT, "Extracting uploaded archive")
        crud.update_lab_run_status(db, lab_run_id, models.RunStatus.PROCESSING)
        # Extract the run using existing upload_run function
        parsed_sample, run = upload_run(zip_path)
        run_name = f"{parsed_sample}_{run}"
        crud.update_lab_run_name(db, lab_run_id, run_name)

        # Parse benchmarking options
        happy = "happy" in benchmarking_options
        stratified = "stratified" in benchmarking_options
        truvari = "truvari" in benchmarking_options
        csv_reformat = "csv" in benchmarking_options

        # Run the pipeline
        if job_id:
            job_service.mark_phase(db, job_id, models.TransferJobPhase.PROCESS, "Starting benchmarking pipeline")
        run_pipeline(
            parsed_sample,
            run,
            happy=happy,
            stratified=stratified,
            truvari=truvari,
            csv_reformat=csv_reformat
        )
        crud.update_lab_run_status(db, lab_run_id, models.RunStatus.AWAITING_APPROVAL)
        if job_id:
            job_service.complete_job(db, job_id, "Upload processing completed")

    except Exception as e:
        db.rollback()
        crud.update_lab_run_status(db, lab_run_id, models.RunStatus.FAILED, error_message=str(e))
        if job_id:
            try:
                job_service.fail_job(db, job_id, str(e), error_code="upload_processing_failed")
            except Exception:
                db.rollback()
    finally:
        db.close()


def _get_or_create_lab_run(db: Session, run_name: str, status: models.RunStatus) -> models.LabRun:
    lab_run = crud.get_lab_run_by_name(db, run_name)
    if lab_run:
        updated = crud.update_lab_run_status(db, lab_run.id, status)
        return updated or lab_run
    return crud.create_lab_run(
        db,
        schemas.LabRunCreate(run_name=run_name, status=status),
    )


async def process_aws_run_background(sample_id: str, benchmarking_options: str = "", job_id: str | None = None):
    """Download an AWS run, then process it while publishing polling/WebSocket logs."""
    run_name = f"{sample_id}_R001"
    lab_run_id: int | None = None
    db = SessionLocal()

    ws_manager.init_log_store(sample_id)
    ws_manager.set_status(sample_id, ws_manager.DownloadStatus.RUNNING)
    await ws_manager.broadcast_log(sample_id, f"Starting AWS download for sample: {sample_id}", ws_manager.LogLevel.INFO)

    try:
        if job_id is None:
            job = job_service.create_job(
                db,
                job_type=models.TransferJobType.AWS_IMPORT,
                subject_id=sample_id,
                phase=models.TransferJobPhase.DOWNLOAD,
                source_uri=f"s3://{sample_id}",
                destination_path=str(LAB_RUNS_DIR / run_name),
            )
            job_id = job.id
        else:
            job_service.mark_phase(db, job_id, models.TransferJobPhase.DOWNLOAD, "Starting AWS download")

        lab_run = _get_or_create_lab_run(db, run_name, models.RunStatus.PROCESSING)
        lab_run_id = lab_run.id

        await ws_manager.broadcast_log(sample_id, f"Executing download script: {AWS_DOWNLOAD_SCRIPT}", ws_manager.LogLevel.INFO)
        job_service.append_event(
            db,
            job_id,
            f"Executing download script: {AWS_DOWNLOAD_SCRIPT}",
            level=models.TransferEventLevel.INFO,
            phase=models.TransferJobPhase.DOWNLOAD,
        )
        process = await asyncio.create_subprocess_exec(
            str(AWS_DOWNLOAD_SCRIPT),
            sample_id,
            cwd=settings.PROJECT_ROOT,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env={**os.environ, "AWS_PROFILE": settings.AWS_PROFILE},
        )

        assert process.stdout is not None
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            decoded_line = line.decode("utf-8", errors="replace").strip()
            if decoded_line:
                level = ws_manager.LogLevel.INFO
                if any(marker in decoded_line for marker in ["[SUCCESS]", "téléchargé avec succès"]):
                    level = ws_manager.LogLevel.SUCCESS
                elif any(marker in decoded_line for marker in ["[WARNING]", "ignoré"]):
                    level = ws_manager.LogLevel.WARNING
                elif any(marker in decoded_line for marker in ["[ERROR]", "Erreur"]):
                    level = ws_manager.LogLevel.ERROR
                elif any(marker in decoded_line for marker in ["[PROGRESS]", "Téléchargement"]):
                    level = ws_manager.LogLevel.PROGRESS
                await ws_manager.broadcast_log(sample_id, decoded_line, level)
                event_level = {
                    ws_manager.LogLevel.SUCCESS: models.TransferEventLevel.SUCCESS,
                    ws_manager.LogLevel.WARNING: models.TransferEventLevel.WARNING,
                    ws_manager.LogLevel.ERROR: models.TransferEventLevel.ERROR,
                    ws_manager.LogLevel.PROGRESS: models.TransferEventLevel.PROGRESS,
                }.get(level, models.TransferEventLevel.INFO)
                job_service.append_event(
                    db,
                    job_id,
                    decoded_line,
                    level=event_level,
                    phase=models.TransferJobPhase.DOWNLOAD,
                )

        await process.wait()
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, str(AWS_DOWNLOAD_SCRIPT))

        await ws_manager.broadcast_log(sample_id, "AWS download completed successfully", ws_manager.LogLevel.SUCCESS)
        job_service.append_event(
            db,
            job_id,
            "AWS download completed successfully",
            level=models.TransferEventLevel.SUCCESS,
            phase=models.TransferJobPhase.DOWNLOAD,
        )
        run_dir = LAB_RUNS_DIR / run_name
        if not run_dir.exists():
            raise FileNotFoundError(f"Expected run directory not found: {run_dir}")

        parsed_sample, run = split_run_name(run_dir.name)
        if lab_run_id is not None and run_dir.name != run_name:
            crud.update_lab_run_name(db, lab_run_id, run_dir.name)

        await ws_manager.broadcast_log(sample_id, "Verifying reference files", ws_manager.LogLevel.INFO)
        job_service.mark_phase(db, job_id, models.TransferJobPhase.REFERENCE_SETUP, "Verifying reference files")
        ready, message = ensure_references(parsed_sample, auto_download=True)
        if not ready:
            raise FileNotFoundError(message)

        happy = "happy" in benchmarking_options
        stratified = "stratified" in benchmarking_options
        truvari = "truvari" in benchmarking_options
        csv_reformat = "csv" in benchmarking_options

        await ws_manager.broadcast_log(sample_id, "Starting benchmarking pipeline", ws_manager.LogLevel.INFO)
        job_service.mark_phase(db, job_id, models.TransferJobPhase.PROCESS, "Starting benchmarking pipeline")
        run_pipeline(
            parsed_sample,
            run,
            happy=happy,
            stratified=stratified,
            truvari=truvari,
            csv_reformat=csv_reformat,
        )
        if lab_run_id is not None:
            crud.update_lab_run_status(db, lab_run_id, models.RunStatus.AWAITING_APPROVAL)
        await ws_manager.broadcast_log(sample_id, "Benchmarking pipeline completed successfully", ws_manager.LogLevel.SUCCESS)
        job_service.complete_job(db, job_id, "Benchmarking pipeline completed successfully")
        ws_manager.set_status(sample_id, ws_manager.DownloadStatus.COMPLETED)

    except Exception as e:
        db.rollback()
        if lab_run_id is not None:
            try:
                crud.update_lab_run_status(db, lab_run_id, models.RunStatus.FAILED, error_message=str(e))
            except Exception:
                db.rollback()
        await ws_manager.broadcast_log(sample_id, f"Error processing AWS run: {e}", ws_manager.LogLevel.ERROR)
        if job_id:
            try:
                job_service.fail_job(db, job_id, str(e), error_code="aws_import_failed")
            except Exception:
                db.rollback()
        ws_manager.set_status(sample_id, ws_manager.DownloadStatus.ERROR)
        raise
    finally:
        db.close()

@router.post("/upload/runs")
async def upload_run_endpoint(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    sample: str = Form(...),
    benchmarking: Optional[str] = Form(default=""),
    auto_process: bool = Form(default=True),
    db: Session = Depends(get_db),
    _role: Role = Depends(require_role(Role.OPERATOR)),
):
    """Upload a run file with streaming to avoid memory issues"""
    try:
        filename = sanitize_upload_filename(file.filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    if not filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Expected a .zip file")

    # Create upload directory
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    dest = unique_upload_path(filename)
    run_name = Path(filename).stem
    job = job_service.create_job(
        db,
        job_type=models.TransferJobType.UPLOAD_ZIP,
        subject_id=run_name,
        phase=models.TransferJobPhase.UPLOAD,
        source_uri=filename,
        destination_path=str(dest),
        bytes_total=getattr(file, "size", None),
    )
    job_service.append_event(
        db,
        job.id,
        f"Receiving upload archive: {filename}",
        level=models.TransferEventLevel.INFO,
        phase=models.TransferJobPhase.UPLOAD,
    )

    # Stream to disk in chunks (no full read into memory)
    try:
        bytes_written = 0
        with dest.open("wb") as out:
            while True:
                chunk = await file.read(8 * 1024 * 1024)  # 8 MB chunks
                if not chunk:
                    break
                bytes_written += len(chunk)
                if bytes_written > settings.MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail="Upload exceeds configured size limit")
                out.write(chunk)
                job_service.update_progress(
                    db,
                    job.id,
                    bytes_done=bytes_written,
                    bytes_total=getattr(file, "size", None) or bytes_written,
                )

        lab_run = crud.get_lab_run_by_name(db, run_name)
        if lab_run is None:
            lab_run = crud.create_lab_run(
                db,
                schemas.LabRunCreate(
                    run_name=run_name,
                    status=models.RunStatus.PENDING_PROCESSING,
                ),
            )
        else:
            crud.update_lab_run_status(db, lab_run.id, models.RunStatus.PENDING_PROCESSING)

        if auto_process and background_tasks:
            background_tasks.add_task(process_run_background, dest, sample, lab_run.id, benchmarking, job.id)
        else:
            job_service.complete_job(db, job.id, "Upload stored successfully")

        return {
            "ok": True,
            "run_name": run_name,
            "job_id": job.id,
            "bytes_received": bytes_written,
            "status": models.RunStatus.PENDING_PROCESSING,
            "auto_process": auto_process,
            "benchmarking": benchmarking
        }

    except HTTPException:
        if dest.exists():
            dest.unlink()
        job_service.fail_job(db, job.id, "Upload failed", error_code="upload_failed")
        raise
    except Exception as e:
        # Clean up on error
        if dest.exists():
            dest.unlink()
        job_service.fail_job(db, job.id, str(e), error_code="upload_failed")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.get("/upload/form")
def upload_form():
    """Serve a styled upload form that matches the Dash UI"""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            :root {
                --color-inkwell: #000000;
                --color-paper-white: #FFFFFF;
                --color-parchment: #FAF8F5;
                --color-graphite: #27251E;
                --color-faded-stone: #92918B;
                --color-dusk-gray: #72706B;
            }
            * {
                box-sizing: border-box;
            }
            body {
                font-family: Inter, "SF Pro Text", "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                margin: 0;
                padding: 0;
                color: var(--color-inkwell);
                background: var(--color-paper-white);
            }
            .upload-form {
                max-width: 760px;
                margin: 0 auto;
                padding: 4px;
                background: var(--color-paper-white);
            }
            h3 {
                margin: 0 0 18px;
                font-size: 16px;
                font-weight: 500;
                letter-spacing: 0;
            }
            .form-grid {
                display: grid;
                grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
                gap: 16px;
            }
            .form-group {
                margin-bottom: 18px;
            }
            .form-group--wide {
                grid-column: 1 / -1;
            }
            .option-panel {
                grid-column: 1 / -1;
                padding: 16px;
                border: 1px solid rgba(39, 37, 30, 0.12);
                border-radius: 8px;
                background: var(--color-parchment);
            }
            label {
                display: block;
                margin-bottom: 7px;
                color: var(--color-graphite);
                font-size: 14px;
                font-weight: 400;
            }
            input[type="text"], input[type="file"] {
                width: 100%;
                min-height: 40px;
                padding: 8px 10px;
                border: 1px solid rgba(39, 37, 30, 0.16);
                border-radius: 8px;
                box-sizing: border-box;
                color: var(--color-inkwell);
                background: var(--color-parchment);
                font: inherit;
            }
            input[type="file"] {
                padding: 7px 10px;
            }
            .checkbox-group {
                display: flex;
                align-items: center;
                gap: 8px;
                margin-bottom: 10px;
            }
            .checkbox-group label {
                display: inline;
                margin: 0;
                color: var(--color-graphite);
                font-size: 14px;
                font-weight: 400;
            }
            .checkbox-group input {
                width: auto;
            }
            .upload-button {
                min-height: 42px;
                background-color: var(--color-graphite);
                color: var(--color-paper-white);
                padding: 0 18px;
                border: none;
                border-radius: 9999px;
                cursor: pointer;
                font-size: 14px;
                font-weight: 400;
            }
            .upload-button:hover {
                background-color: var(--color-inkwell);
            }
            .upload-button:disabled {
                background-color: var(--color-parchment);
                color: var(--color-faded-stone);
                cursor: not-allowed;
            }
            .progress {
                display: none;
                margin-top: 15px;
                padding: 15px;
                background-color: var(--color-parchment);
                border: 1px solid rgba(39, 37, 30, 0.12);
                border-radius: 8px;
                color: var(--color-graphite);
            }
            .success {
                margin-top: 15px;
                padding: 15px;
                background-color: var(--color-parchment);
                border: 1px solid rgba(39, 37, 30, 0.12);
                border-radius: 8px;
                color: var(--color-graphite);
            }
            .error {
                margin-top: 15px;
                padding: 15px;
                background-color: var(--color-parchment);
                border: 1px solid rgba(39, 37, 30, 0.12);
                border-radius: 8px;
                color: var(--color-graphite);
            }
            @media (max-width: 640px) {
                .form-grid {
                    grid-template-columns: 1fr;
                }
            }
        </style>
    </head>
    <body>
        <div class="upload-form">
            <h3>Upload run data</h3>
            <form id="uploadForm" action="/api/v1/upload/runs" method="post" enctype="multipart/form-data">
                <div class="form-grid">
                    <div class="form-group">
                        <label for="sample">Sample or run name</label>
                        <input type="text" id="sample" name="sample" required placeholder="Example: 2026-05-run-01">
                    </div>

                    <div class="form-group">
                        <label for="file">Run archive</label>
                        <input type="file" id="file" name="file" accept=".zip" required>
                    </div>

                    <div class="form-group form-group--wide">
                        <label for="api_key">API key</label>
                        <input type="text" id="api_key" name="api_key" placeholder="Required when server auth is enabled">
                    </div>

                    <div class="option-panel">
                        <label>Benchmarking</label>
                        <div class="checkbox-group">
                            <input type="checkbox" id="happy" name="benchmarking" value="happy">
                            <label for="happy">hap.py small variant benchmarking</label>
                        </div>
                        <div class="checkbox-group">
                            <input type="checkbox" id="stratified" name="benchmarking" value="stratified" disabled>
                            <label for="stratified">Stratified hap.py results</label>
                        </div>
                        <div class="checkbox-group">
                            <input type="checkbox" id="csv" name="benchmarking" value="csv" checked>
                            <label for="csv">CSV output formatting</label>
                        </div>
                        <div class="checkbox-group">
                            <input type="checkbox" id="truvari" name="benchmarking" value="truvari" checked>
                            <label for="truvari">Truvari structural variant benchmarking</label>
                        </div>
                    </div>

                    <div class="checkbox-group form-group--wide">
                        <input type="checkbox" id="auto_process" name="auto_process" value="1" checked>
                        <label for="auto_process">Process automatically after upload</label>
                    </div>
                </div>
                <button type="submit" class="upload-button">Upload and process</button>
            </form>

            <div id="progress" class="progress">
                <h4>Upload in progress</h4>
                <p>Please wait while the archive is uploaded.</p>
            </div>

            <div id="result"></div>
        </div>

        <script>
            // Enable/disable stratified option based on happy selection
            document.getElementById('happy').addEventListener('change', function() {
                const stratified = document.getElementById('stratified');
                stratified.disabled = !this.checked;
                if (!this.checked) {
                    stratified.checked = false;
                }
            });

            // Handle form submission with progress indicator
            document.getElementById('uploadForm').addEventListener('submit', async function(e) {
                e.preventDefault();

                const form = e.target;
                const formData = new FormData();
                const submitButton = form.querySelector('button[type="submit"]');
                const progress = document.getElementById('progress');
                const result = document.getElementById('result');

                // Manually collect form data to handle multiple checkboxes properly
                formData.append('sample', form.querySelector('#sample').value);
                formData.append('file', form.querySelector('#file').files[0]);
                formData.append('auto_process', form.querySelector('#auto_process').checked ? '1' : '0');

                // Collect all checked benchmarking options
                const benchmarkingOptions = [];
                const checkboxes = form.querySelectorAll('input[name="benchmarking"]:checked');
                checkboxes.forEach(checkbox => {
                    benchmarkingOptions.push(checkbox.value);
                });
                formData.append('benchmarking', benchmarkingOptions.join(','));

                // Show progress, disable button
                progress.style.display = 'block';
                submitButton.disabled = true;
                result.innerHTML = '';

                try {
                    const response = await fetch(form.action, {
                        method: 'POST',
                        headers: form.querySelector('#api_key').value
                            ? {'X-VCBench-API-Key': form.querySelector('#api_key').value}
                            : {},
                        body: formData
                    });

                    const data = await response.json();

                    if (response.ok) {
                        result.innerHTML = `
                            <div class="success">
                                <h4>Upload complete</h4>
                                <p><strong>Run Name:</strong> ${data.run_name}</p>
                                <p><strong>Auto Process:</strong> ${data.auto_process ? 'Yes' : 'No'}</p>
                                <p><strong>Benchmarking:</strong> ${data.benchmarking || 'None'}</p>
                            </div>
                        `;
                    } else {
                        throw new Error(data.detail || 'Upload failed');
                    }
                } catch (error) {
                    result.innerHTML = `
                        <div class="error">
                            <h4>Upload failed</h4>
                            <p><strong>Error:</strong> ${error.message}</p>
                        </div>
                    `;
                }

                // Hide progress, enable button
                progress.style.display = 'none';
                submitButton.disabled = false;
            });
        </script>
    </body>
    </html>
    """)


@router.post("/upload/aws")
async def upload_aws_run_endpoint(
    background_tasks: BackgroundTasks,
    request: AWSUploadRequest,
    db: Session = Depends(get_db),
    _role: Role = Depends(require_role(Role.OPERATOR)),
):
    """Import a run from AWS S3 using the configured download script."""
    if not AWS_DOWNLOAD_SCRIPT.exists():
        raise HTTPException(status_code=500, detail=f"AWS download script not found: {AWS_DOWNLOAD_SCRIPT}")

    sample_id = request.sample_id.strip() if request.sample_id else ""
    if not sample_id:
        raise HTTPException(status_code=400, detail="sample_id cannot be empty")

    job = job_service.create_job(
        db,
        job_type=models.TransferJobType.AWS_IMPORT,
        subject_id=sample_id,
        phase=models.TransferJobPhase.DOWNLOAD,
        status=models.TransferJobStatus.QUEUED,
        source_uri=f"s3://{sample_id}",
        destination_path=str(LAB_RUNS_DIR / f"{sample_id}_R001"),
        metadata_json={"benchmarking": request.benchmarking or ""},
    )

    if request.auto_process:
        background_tasks.add_task(process_aws_run_background, sample_id, request.benchmarking or "", job.id)

    return {
        "ok": True,
        "sample_id": sample_id,
        "run_name": f"{sample_id}_R001",
        "job_id": job.id,
        "auto_process": request.auto_process,
        "benchmarking": request.benchmarking,
        "message": "AWS download initiated" if request.auto_process else "AWS download will be triggered manually",
    }
