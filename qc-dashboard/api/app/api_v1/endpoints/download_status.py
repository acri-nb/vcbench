"""
Endpoints for checking download status and retrieving logs.

Provides HTTP endpoints for polling download progress (fallback for WebSocket).
"""

from fastapi import APIRouter, Query
from typing import Optional
from api.app import websocket as ws_manager

router = APIRouter()


@router.get("/download/status/{sample_id}")
async def get_download_status(sample_id: str):
    """
    Get the current status of a download/processing job.
    
    Args:
        sample_id: Sample identifier
        
    Returns:
        Status information including sample_id, status, log count, timestamps
    """
    status = ws_manager.get_status(sample_id)
    return status


@router.get("/download/logs/{sample_id}")
async def get_download_logs(
    sample_id: str,
    since: int = Query(default=0, description="Get logs from this index onwards")
):
    """
    Get logs for a download/processing job.
    
    Args:
        sample_id: Sample identifier
        since: Index to get logs from (for incremental polling)
        
    Returns:
        List of log entries and current status
    """
    logs = ws_manager.get_logs(sample_id, since=since)
    status = ws_manager.get_status(sample_id)
    
    return {
        "sample_id": sample_id,
        "logs": logs,
        "total_logs": status["log_count"],
        "status": status["status"],
        "has_more": since < status["log_count"]
    }


@router.post("/download/cleanup")
async def cleanup_old_logs():
    """
    Manually trigger cleanup of old logs.
    
    Returns:
        Success message
    """
    ws_manager.cleanup_old_logs()
    return {"message": "Old logs cleaned up successfully"}

