# AWS Import Feature - Testing Guide

## Overview
The AWS import feature allows users to download sequencing runs from AWS S3 directly through the Run Management interface, using the existing `aws_download_gvcf.sh` script.

## Components Implemented

### 1. Backend API Endpoint
**File**: `qc-dashboard/api/app/api_v1/endpoints/uploads.py`

- **New Endpoint**: `POST /api/v1/upload/aws`
- **Request Body**:
  ```json
  {
    "sample_id": "NA24143_Lib3_Rep1",
    "benchmarking": "csv,truvari",
    "auto_process": true
  }
  ```
- **Response**:
  ```json
  {
    "ok": true,
    "sample_id": "NA24143_Lib3_Rep1",
    "run_name": "NA24143_Lib3_Rep1_R001",
    "auto_process": true,
    "benchmarking": "csv,truvari",
    "message": "AWS download initiated"
  }
  ```

### 2. Frontend UI
**File**: `qc-dashboard/dash_app/pages/runs.py`

New "Import from AWS S3" section in the Upload Run tab with:
- Sample ID input field
- Benchmarking options checkboxes (happy, stratified, truvari, csv)
- Auto-process toggle
- Import button (disabled until sample ID is entered)
- Status message area

### 3. Dash Callbacks
Three callbacks handle the UI logic:
- `update_aws_benchmarking_options`: Disables "stratified" unless "happy" is selected
- `update_aws_import_button`: Enables import button only when sample_id is provided
- `launch_aws_import`: Calls the API endpoint and displays results

## Manual Testing Steps

### Test 1: Basic AWS Import (UI)
1. Start the application: `bash qc-dashboard/start_app.sh`
2. Navigate to Run Management page
3. Go to "Upload Run" tab
4. In the "Import from AWS S3" section:
   - Enter a sample ID (e.g., `NA24143_Lib3_Rep1`)
   - Verify the "Import from AWS" button becomes enabled
   - Select benchmarking options (default: csv, truvari)
   - Click "Import from AWS"
   - Verify success message appears

### Test 2: Stratified Dependency
1. In the AWS import form, uncheck "hap.py"
2. Verify that "stratified" becomes disabled
3. Check "hap.py" again
4. Verify that "stratified" becomes enabled

### Test 3: API Endpoint (Direct)
Test the endpoint directly using curl:

```bash
curl -X POST "http://localhost:8002/api/v1/upload/aws" \
  -H "Content-Type: application/json" \
  -d '{
    "sample_id": "NA24143_Lib3_Rep1",
    "benchmarking": "csv,truvari",
    "auto_process": true
  }'
```

Expected response (200 OK):
```json
{
  "ok": true,
  "sample_id": "NA24143_Lib3_Rep1",
  "run_name": "NA24143_Lib3_Rep1_R001",
  "auto_process": true,
  "benchmarking": "csv,truvari",
  "message": "AWS download initiated"
}
```

### Test 4: Error Handling
1. Test with empty sample_id:
   ```bash
   curl -X POST "http://localhost:8002/api/v1/upload/aws" \
     -H "Content-Type: application/json" \
     -d '{"sample_id": "", "auto_process": true}'
   ```
   Expected: 400 Bad Request with "sample_id cannot be empty"

2. Test with invalid sample_id (one that doesn't exist in S3):
   - Should fail during background processing
   - Check logs for error messages

### Test 5: Background Processing
1. Import a valid sample with auto_process=true
2. Check that files appear in `data/lab_runs/{sample_id}_R001/`
3. Verify that selected benchmarking processes run
4. Check that results appear in `data/processed/`

### Test 6: Integration with Existing Flow
1. After AWS import completes, go to "Manage Runs" tab
2. Verify the new run appears in the dropdown
3. Test launching additional benchmarking if needed

## Expected File Structure

After successful AWS import, you should see:

```
data/
  lab_runs/
    NA24143_Lib3_Rep1_R001/
      NA24143_Lib3_Rep1_R001.gvcf.gz
      NA24143_Lib3_Rep1_R001.*.csv (metrics files)
  processed/
    YYYYMMDD_NA24143_Lib3_Rep1_R001/  (if auto_process=true)
      # Processed benchmark results
```

## Troubleshooting

### Script Not Found Error
If you get "AWS download script not found", verify:
```bash
ls -l /mnt/acri4_2/gth/project/vcbench/script/aws_download_gvcf.sh
```

### AWS Credentials Error
Ensure AWS CLI is configured with the `vitalite` profile:
```bash
aws --profile vitalite s3 ls
```

### Background Task Not Running
Check FastAPI logs for error messages. The background task runs asynchronously, so check:
- Terminal output where the app is running
- Any error messages in `aws-status-message` div

## Notes

- The AWS script is called with a single argument: the sample_id
- The script automatically appends `_R001` to the directory name
- Default benchmarking options match the FastAPI upload form: csv + truvari
- The import runs in the background, so the UI responds immediately
- Processing can be monitored in the application logs

