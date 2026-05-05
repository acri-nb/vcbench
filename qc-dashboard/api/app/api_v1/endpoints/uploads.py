from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse
from pathlib import Path
import shutil
import subprocess
import asyncio
from typing import Optional
from pydantic import BaseModel

from api.tasks.upload_run import upload_run
from api.tasks.process_run import run_pipeline
from api.tasks.setup_reference import ensure_references, get_reference_status
from api.app import websocket as ws_manager

router = APIRouter()

# Get absolute path to project root
APP_DIR = Path(__file__).parent.parent.parent
PROJECT_ROOT = APP_DIR.parent.parent.parent
LAB_RUNS_DIR = PROJECT_ROOT / "data" / "lab_runs"
UPLOAD_DIR = PROJECT_ROOT / "qc-dashboard" / "api" / "app" / "tmp" / "uploads"
AWS_DOWNLOAD_SCRIPT = PROJECT_ROOT / "script" / "aws_download_gvcf.sh"

# Schema for AWS upload request
class AWSUploadRequest(BaseModel):
    sample_id: str
    benchmarking: Optional[str] = ""
    auto_process: bool = True

# FILES -------------------------------------------------------------------------------------------

def process_run_background(zip_path: Path, sample: str, benchmarking_options: str = ""):
    """Background task to process the uploaded run"""
    print(benchmarking_options)
    try:
        # Extract the run using existing upload_run function
        sample, run = upload_run()
        print(sample)
        print(run)
        
        # Parse benchmarking options
        happy = "happy" in benchmarking_options
        stratified = "stratified" in benchmarking_options
        truvari = "truvari" in benchmarking_options
        csv_reformat = "csv" in benchmarking_options
        
        print(f"happy: {happy}, stratified: {stratified}, csv_reformat: {csv_reformat}")
        
        # Run the pipeline
        run_pipeline(
            sample,
            run,
            happy=happy,
            stratified=stratified,
            truvari=truvari,
            csv_reformat=csv_reformat
        )
        print(f"[uploads.py] Processing completed for {sample}")
        
    except Exception as e:
        print(f"[uploads.py] Error processing {sample}: {str(e)}")

async def process_aws_run_background(sample_id: str, benchmarking_options: str = ""):
    """Background task to download run from AWS and process it with real-time logging"""
    
    # Initialize log store
    ws_manager.init_log_store(sample_id)
    ws_manager.set_status(sample_id, ws_manager.DownloadStatus.RUNNING)
    
    await ws_manager.broadcast_log(sample_id, f"Starting AWS download for sample: {sample_id}", ws_manager.LogLevel.INFO)
    
    try:
        # Execute the AWS download script with streaming output
        await ws_manager.broadcast_log(sample_id, f"Executing download script: {AWS_DOWNLOAD_SCRIPT}", ws_manager.LogLevel.INFO)
        
        process = await asyncio.create_subprocess_exec(
            str(AWS_DOWNLOAD_SCRIPT),
            sample_id,
            cwd=PROJECT_ROOT,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env={**subprocess.os.environ, "AWS_PROFILE": "vitalite"}
        )
        
        # Stream output line by line
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            
            decoded_line = line.decode('utf-8').strip()
            if decoded_line:
                # Determine log level based on content
                level = ws_manager.LogLevel.INFO
                if any(marker in decoded_line for marker in ["✅", "[SUCCESS]", "téléchargé avec succès"]):
                    level = ws_manager.LogLevel.SUCCESS
                elif any(marker in decoded_line for marker in ["⚠️", "[WARNING]", "ignoré"]):
                    level = ws_manager.LogLevel.WARNING
                elif any(marker in decoded_line for marker in ["❌", "[ERROR]", "Erreur"]):
                    level = ws_manager.LogLevel.ERROR
                elif any(marker in decoded_line for marker in ["⬇️", "[PROGRESS]", "Téléchargement"]):
                    level = ws_manager.LogLevel.PROGRESS
                
                await ws_manager.broadcast_log(sample_id, decoded_line, level)
        
        # Wait for process to complete
        await process.wait()
        
        if process.returncode != 0:
            await ws_manager.broadcast_log(
                sample_id, 
                f"AWS download script failed with exit code: {process.returncode}", 
                ws_manager.LogLevel.ERROR
            )
            ws_manager.set_status(sample_id, ws_manager.DownloadStatus.ERROR)
            raise subprocess.CalledProcessError(process.returncode, str(AWS_DOWNLOAD_SCRIPT))
        
        await ws_manager.broadcast_log(sample_id, "AWS download completed successfully", ws_manager.LogLevel.SUCCESS)
        
        # Verify run directory exists
        run_dir = LAB_RUNS_DIR / f"{sample_id}_R001"
        if not run_dir.exists():
            error_msg = f"Expected run directory not found: {run_dir}"
            await ws_manager.broadcast_log(sample_id, error_msg, ws_manager.LogLevel.ERROR)
            ws_manager.set_status(sample_id, ws_manager.DownloadStatus.ERROR)
            raise FileNotFoundError(error_msg)
        
        # Extract sample and run name
        parts = run_dir.name.split('_')
        if len(parts) < 2:
            error_msg = f"Unexpected directory name format: {run_dir.name}"
            await ws_manager.broadcast_log(sample_id, error_msg, ws_manager.LogLevel.ERROR)
            ws_manager.set_status(sample_id, ws_manager.DownloadStatus.ERROR)
            raise ValueError(error_msg)
        
        sample = parts[0]
        run = '_'.join(parts[1:])
        
        await ws_manager.broadcast_log(sample_id, f"Extracted sample: {sample}, run: {run}", ws_manager.LogLevel.INFO)
        
        # Verify and download references if needed
        await ws_manager.broadcast_log(sample_id, "Verifying reference files...", ws_manager.LogLevel.INFO)
        ready, message = ensure_references(sample, auto_download=True)
        
        if ready:
            await ws_manager.broadcast_log(sample_id, "Reference files verified successfully", ws_manager.LogLevel.SUCCESS)
        else:
            await ws_manager.broadcast_log(sample_id, f"Reference setup: {message}", ws_manager.LogLevel.WARNING)
        
        # Parse benchmarking options
        happy = "happy" in benchmarking_options
        stratified = "stratified" in benchmarking_options
        truvari = "truvari" in benchmarking_options
        csv_reformat = "csv" in benchmarking_options
        
        await ws_manager.broadcast_log(
            sample_id,
            f"Starting benchmarking pipeline (happy={happy}, stratified={stratified}, truvari={truvari}, csv={csv_reformat})",
            ws_manager.LogLevel.INFO
        )
        
        # Run the pipeline (synchronous call)
        try:
            run_pipeline(
                sample,
                run,
                happy=happy,
                stratified=stratified,
                truvari=truvari,
                csv_reformat=csv_reformat
            )
            await ws_manager.broadcast_log(sample_id, "Benchmarking pipeline completed successfully", ws_manager.LogLevel.SUCCESS)
            ws_manager.set_status(sample_id, ws_manager.DownloadStatus.COMPLETED)
        except Exception as pipeline_error:
            error_msg = f"Pipeline error: {str(pipeline_error)}"
            await ws_manager.broadcast_log(sample_id, error_msg, ws_manager.LogLevel.ERROR)
            ws_manager.set_status(sample_id, ws_manager.DownloadStatus.ERROR)
            raise
        
    except subprocess.CalledProcessError as e:
        error_msg = f"AWS download script failed: {str(e)}"
        await ws_manager.broadcast_log(sample_id, error_msg, ws_manager.LogLevel.ERROR)
        ws_manager.set_status(sample_id, ws_manager.DownloadStatus.ERROR)
        raise
    except Exception as e:
        error_msg = f"Error processing AWS run: {str(e)}"
        await ws_manager.broadcast_log(sample_id, error_msg, ws_manager.LogLevel.ERROR)
        ws_manager.set_status(sample_id, ws_manager.DownloadStatus.ERROR)
        raise

@router.post("/upload/runs")
async def upload_run_endpoint(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    sample: str = Form(...),
    benchmarking: Optional[str] = Form(default=""),
    auto_process: bool = Form(default=True)
):
    """Upload a run file with streaming to avoid memory issues"""
    if not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Expected a .zip file")

    # Create upload directory
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    dest = UPLOAD_DIR / file.filename

    # Stream to disk in chunks (no full read into memory)
    try:
        with dest.open("wb") as out:
            while True:
                chunk = await file.read(8 * 1024 * 1024)  # 8 MB chunks
                if not chunk:
                    break
                out.write(chunk)
        
        print(f"[uploads.py] File uploaded: {file.filename} ({dest.stat().st_size} bytes)")
        
        if auto_process and background_tasks:
            background_tasks.add_task(process_run_background, dest, sample, benchmarking)
            
        return {
            "ok": True, 
            "run_name": file.filename[:-4],  # Remove .zip extension
            "path": str(dest), 
            "auto_process": auto_process,
            "benchmarking": benchmarking
        }
        
    except Exception as e:
        # Clean up on error
        if dest.exists():
            dest.unlink()
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
                --vc-brand-700: #004a8f;
                --vc-brand-900: #002a52;
                --vc-success-500: #2aa36a;
                --vc-success-700: #1f7a4d;
                --vc-success-100: #dff3e8;
                --vc-danger-500: #d23344;
                --vc-danger-700: #9a1c2a;
                --vc-danger-100: #fbe2e5;
                --vc-ink-100: #eef1f5;
                --vc-ink-500: #57667a;
                --vc-ink-700: #2c3a4b;
                --vc-ink-900: #0f1722;
                --vc-bg: #f6f8fb;
                --vc-border: #e1e6ee;
                --vc-r-sm: 4px;
                --vc-r-md: 8px;
            }
            * { box-sizing: border-box; }
            html, body {
                margin: 0;
                padding: 0;
                background: transparent;
            }
            body {
                font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI",
                             Roboto, "Helvetica Neue", Arial, sans-serif;
                color: var(--vc-ink-900);
                font-size: 0.9375rem;
                line-height: 1.5;
                padding: 0.25rem 0 1rem 0;
            }
            .upload-form { max-width: 640px; margin: 0; padding: 0; }
            .form-group { margin-bottom: 1.25rem; }
            .field-label {
                display: block;
                margin-bottom: 0.375rem;
                font-weight: 500;
                font-size: 0.8125rem;
                color: var(--vc-ink-500);
            }
            .field-help {
                margin: 0.375rem 0 0 0;
                font-size: 0.8125rem;
                color: var(--vc-ink-500);
            }
            input[type="text"] {
                width: 100%;
                padding: 0.5rem 0.75rem;
                border: 1px solid var(--vc-border);
                border-radius: var(--vc-r-sm);
                font-size: 0.9375rem;
                font-family: inherit;
                background: #ffffff;
                color: var(--vc-ink-900);
            }
            input[type="text"]::placeholder { color: var(--vc-ink-500); }
            input[type="text"]:focus {
                outline: none;
                border-color: var(--vc-brand-700);
                box-shadow: 0 0 0 3px rgba(15,108,184,0.15);
            }
            /* Custom file input */
            input[type="file"] {
                position: absolute;
                width: 1px;
                height: 1px;
                padding: 0;
                margin: -1px;
                overflow: hidden;
                clip: rect(0,0,0,0);
                border: 0;
            }
            .file-drop {
                display: flex;
                align-items: center;
                gap: 0.75rem;
                padding: 0.625rem 0.75rem;
                border: 1px dashed var(--vc-border);
                border-radius: var(--vc-r-sm);
                background: var(--vc-bg);
                cursor: pointer;
                transition: border-color 0.15s ease, background 0.15s ease;
            }
            .file-drop:hover {
                border-color: var(--vc-brand-500);
                background: #eef4fb;
            }
            .file-drop:focus-within {
                border-color: var(--vc-brand-700);
                box-shadow: 0 0 0 3px rgba(15,108,184,0.15);
            }
            .file-drop .pick {
                display: inline-block;
                padding: 0.375rem 0.75rem;
                background: var(--vc-surface, #ffffff);
                border: 1px solid var(--vc-border);
                border-radius: var(--vc-r-sm);
                font-size: 0.8125rem;
                font-weight: 600;
                color: var(--vc-ink-700);
                white-space: nowrap;
            }
            .file-drop .file-name {
                font-size: 0.875rem;
                color: var(--vc-ink-500);
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }
            .file-drop.has-file .file-name { color: var(--vc-ink-900); }
            /* Checkbox grid */
            .check-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 0.5rem 1rem;
            }
            .check-grid label {
                display: flex;
                align-items: center;
                gap: 0.5rem;
                padding: 0.5rem 0.75rem;
                border: 1px solid var(--vc-border);
                border-radius: var(--vc-r-sm);
                background: #ffffff;
                cursor: pointer;
                transition: border-color 0.15s ease, background 0.15s ease;
                font-size: 0.875rem;
            }
            .check-grid label:has(input:checked) {
                border-color: var(--vc-brand-500);
                background: #eef4fb;
            }
            .check-grid label:has(input:disabled) {
                opacity: 0.5;
                cursor: not-allowed;
            }
            .check-grid input { margin: 0; }
            .check-grid .opt-meta {
                display: block;
                font-size: 0.75rem;
                color: var(--vc-ink-500);
                margin-top: 0.125rem;
            }
            /* Auto-process toggle row */
            .toggle-row {
                display: flex;
                align-items: center;
                gap: 0.5rem;
                padding: 0.5rem 0;
                font-size: 0.875rem;
                color: var(--vc-ink-700);
            }
            .upload-button {
                background: var(--vc-success-500);
                color: #ffffff;
                padding: 0.625rem 1.125rem;
                border: none;
                border-radius: var(--vc-r-sm);
                cursor: pointer;
                font-size: 0.9375rem;
                font-weight: 600;
                font-family: inherit;
                transition: background-color 0.15s ease;
            }
            .upload-button:hover { background: var(--vc-success-700); }
            .upload-button:disabled {
                background: var(--vc-ink-100);
                color: var(--vc-ink-500);
                cursor: not-allowed;
            }
            .progress, .success, .error {
                margin-top: 1rem;
                padding: 0.75rem 1rem;
                border-radius: var(--vc-r-sm);
                font-size: 0.875rem;
                border: 1px solid transparent;
            }
            .progress { display: none; background: #e6eef7; color: var(--vc-brand-900); border-color: var(--vc-brand-700); }
            .success  { background: var(--vc-success-100); color: var(--vc-success-700); border-color: var(--vc-success-500); }
            .error    { background: var(--vc-danger-100);  color: var(--vc-danger-700);  border-color: var(--vc-danger-500); }
            .progress h4, .success h4, .error h4 {
                margin: 0 0 0.25rem 0;
                font-size: 0.875rem;
                font-weight: 600;
            }
            .progress p, .success p, .error p { margin: 0.125rem 0; }
            @media (max-width: 600px) {
                .check-grid { grid-template-columns: 1fr; }
            }
        </style>
    </head>
    <body>
        <div class="upload-form">
            <form id="uploadForm" action="/api/v1/upload/runs" method="post" enctype="multipart/form-data">
                <div class="form-group">
                    <label for="sample" class="field-label">Sample / run name</label>
                    <input type="text" id="sample" name="sample" required placeholder="e.g. NA12878-2024-01-15">
                </div>

                <div class="form-group">
                    <label for="file" class="field-label">Run archive (ZIP)</label>
                    <label class="file-drop" id="fileDrop">
                        <span class="pick">Choose file</span>
                        <span class="file-name" id="fileName">No file selected</span>
                        <input type="file" id="file" name="file" accept=".zip" required>
                    </label>
                    <p class="field-help">DRAGEN outputs packaged as a single .zip.</p>
                </div>

                <div class="form-group">
                    <span class="field-label">Benchmarking options</span>
                    <div class="check-grid">
                        <label><input type="checkbox" id="happy" name="benchmarking" value="happy">
                            <span>hap.py<span class="opt-meta">Small variants</span></span></label>
                        <label><input type="checkbox" id="stratified" name="benchmarking" value="stratified" disabled>
                            <span>Stratified<span class="opt-meta">Requires hap.py</span></span></label>
                        <label><input type="checkbox" id="csv" name="benchmarking" value="csv" checked>
                            <span>CSV export<span class="opt-meta">Reformat outputs</span></span></label>
                        <label><input type="checkbox" id="truvari" name="benchmarking" value="truvari" checked>
                            <span>Truvari<span class="opt-meta">Structural variants</span></span></label>
                    </div>
                </div>

                <label class="toggle-row">
                    <input type="checkbox" id="auto_process" name="auto_process" value="1" checked>
                    <span>Run benchmarking automatically once the upload finishes</span>
                </label>

                <button type="submit" class="upload-button" style="margin-top: 0.75rem;">Upload and process run</button>
            </form>

            <div id="progress" class="progress">
                <h4>Uploading…</h4>
                <p>Hold tight while the archive transfers.</p>
            </div>

            <div id="result"></div>
        </div>
        
        <script>
            // File-drop label keeps the chosen file name visible.
            document.getElementById('file').addEventListener('change', function() {
                const drop = document.getElementById('fileDrop');
                const nameEl = document.getElementById('fileName');
                const f = this.files && this.files[0];
                if (f) {
                    nameEl.textContent = f.name;
                    drop.classList.add('has-file');
                } else {
                    nameEl.textContent = 'No file selected';
                    drop.classList.remove('has-file');
                }
            });

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
                        body: formData
                    });
                    
                    const data = await response.json();
                    
                    if (response.ok) {
                        result.innerHTML = `
                            <div class="success">
                                <h4>Upload complete.</h4>
                                <p>Run: <strong>${data.run_name}</strong></p>
                                <p>Auto-process: ${data.auto_process ? 'enabled' : 'disabled'}</p>
                                <p>Benchmarking: ${data.benchmarking || 'none'}</p>
                            </div>
                        `;
                    } else {
                        throw new Error(data.detail || 'Upload failed');
                    }
                } catch (error) {
                    result.innerHTML = `
                        <div class="error">
                            <h4>Upload failed.</h4>
                            <p>${error.message}</p>
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

def run_async_task(coro):
    """Wrapper to run async coroutine in background task"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(coro)
    finally:
        loop.close()

@router.post("/upload/aws")
async def upload_aws_run_endpoint(
    background_tasks: BackgroundTasks,
    request: AWSUploadRequest
):
    """Import a run from AWS S3 using the aws_download_gvcf.sh script"""
    
    # Validate that the AWS download script exists
    if not AWS_DOWNLOAD_SCRIPT.exists():
        raise HTTPException(
            status_code=500, 
            detail=f"AWS download script not found: {AWS_DOWNLOAD_SCRIPT}"
        )
    
    # Validate sample_id is not empty
    if not request.sample_id or not request.sample_id.strip():
        raise HTTPException(status_code=400, detail="sample_id cannot be empty")
    
    sample_id = request.sample_id.strip()
    
    try:
        # Enqueue background task if auto_process is enabled
        if request.auto_process:
            # Wrap async function for background tasks
            background_tasks.add_task(
                run_async_task,
                process_aws_run_background(sample_id, request.benchmarking)
            )
            
        return {
            "ok": True,
            "sample_id": sample_id,
            "run_name": f"{sample_id}_R001",
            "auto_process": request.auto_process,
            "benchmarking": request.benchmarking,
            "message": "AWS download initiated" if request.auto_process else "AWS download will be triggered manually"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to initiate AWS download: {str(e)}"
        )
