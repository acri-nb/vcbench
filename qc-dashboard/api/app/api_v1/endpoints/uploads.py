from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse
from pathlib import Path
import shutil
from typing import Optional

from api.tasks.upload_run import upload_run
from api.tasks.process_run import run_pipeline

router = APIRouter()

# Get absolute path to project root
APP_DIR = Path(__file__).parent.parent.parent
PROJECT_ROOT = APP_DIR.parent.parent.parent
LAB_RUNS_DIR = PROJECT_ROOT / "data" / "lab_runs"
UPLOAD_DIR = PROJECT_ROOT / "qc-dashboard" / "api" / "app" / "tmp" / "uploads"

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
            body { 
                font-family: Arial, sans-serif; 
                margin: 0; 
                padding: 20px; 
                background-color: #ffffff;
            }
            .upload-form {
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
                border: 1px solid #ddd;
                border-radius: 8px;
                background-color: #f8f9fa;
            }
            .form-group {
                margin-bottom: 20px;
            }
            label {
                display: block;
                margin-bottom: 8px;
                font-weight: bold;
            }
            input[type="text"], input[type="file"] {
                width: 100%;
                padding: 8px;
                border: 1px solid #ccc;
                border-radius: 4px;
                box-sizing: border-box;
            }
            .checkbox-group {
                margin-bottom: 15px;
            }
            .checkbox-group label {
                display: inline;
                font-weight: normal;
                margin-left: 8px;
            }
            .checkbox-group input {
                width: auto;
            }
            .upload-button {
                background-color: #28a745;
                color: white;
                padding: 12px 24px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-size: 16px;
            }
            .upload-button:hover {
                background-color: #218838;
            }
            .upload-button:disabled {
                background-color: #6c757d;
                cursor: not-allowed;
            }
            .progress {
                display: none;
                margin-top: 15px;
                padding: 15px;
                background-color: #e9f2fb;
                border-radius: 4px;
                color: #0c2d48;
            }
            .success {
                margin-top: 15px;
                padding: 15px;
                background-color: #d4edda;
                border-radius: 4px;
                color: #155724;
            }
            .error {
                margin-top: 15px;
                padding: 15px;
                background-color: #f8d7da;
                border-radius: 4px;
                color: #721c24;
            }
        </style>
    </head>
    <body>
        <div class="upload-form">
            <h3>Upload Run Data</h3>
            <form id="uploadForm" action="/api/v1/upload/runs" method="post" enctype="multipart/form-data">
                <div class="form-group">
                    <label for="sample">Sample/Run Name:</label>
                    <input type="text" id="sample" name="sample" required placeholder="Enter sample name">
                </div>
                
                <div class="form-group">
                    <label for="file">Select ZIP file containing run data:</label>
                    <input type="file" id="file" name="file" accept=".zip" required>
                </div>
                
                <div class="form-group">
                    <label>Select benchmarking options:</label>
                    <div class="checkbox-group">
                        <input type="checkbox" id="happy" name="benchmarking" value="happy">
                        <label for="happy">hap.py (Happy benchmarking)</label>
                    </div>
                    <div class="checkbox-group">
                        <input type="checkbox" id="stratified" name="benchmarking" value="stratified" disabled>
                        <label for="stratified">stratified (requires hap.py)</label>
                    </div>
                    <div class="checkbox-group">
                        <input type="checkbox" id="csv" name="benchmarking" value="csv" checked>
                        <label for="csv">csv (CSV output)</label>
                    </div>
                    <div class="checkbox-group">
                        <input type="checkbox" id="truvari" name="benchmarking" value="truvari" checked>
                        <label for="truvari">truvari (Truvari)</label>
                    </div>
                </div>
                
                <div class="checkbox-group">
                    <input type="checkbox" id="auto_process" name="auto_process" value="1" checked>
                    <label for="auto_process">Process automatically after upload</label>
                </div>
                
                <button type="submit" class="upload-button">Upload and Process Run</button>
            </form>
            
            <div id="progress" class="progress">
                <h4>📤 Upload in progress...</h4>
                <p>Please wait while your file is being uploaded...</p>
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
                        body: formData
                    });
                    
                    const data = await response.json();
                    
                    if (response.ok) {
                        result.innerHTML = `
                            <div class="success">
                                <h4>Upload Successful!</h4>
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
                            <h4>❌ Upload Failed</h4>
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
