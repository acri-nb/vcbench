"""
WebSocket manager for real-time log streaming during AWS downloads and processing.

This module provides:
- WebSocket endpoints for real-time log streaming
- In-memory log storage for HTTP polling fallback
- Log management by sample_id
"""

from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Set
from datetime import datetime, timedelta
import asyncio
import logging

logger = logging.getLogger(__name__)

# Log storage structure
# {sample_id: {"logs": [{"timestamp": ..., "message": ..., "level": ...}], "status": "running|completed|error"}}
log_store: Dict[str, Dict] = {}

# Active WebSocket connections per sample_id
active_connections: Dict[str, Set[WebSocket]] = {}

# Cleanup threshold (logs older than 1 hour are removed)
LOG_RETENTION_HOURS = 1


class LogLevel:
    """Log level constants"""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    PROGRESS = "progress"


class DownloadStatus:
    """Download status constants"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"


def init_log_store(sample_id: str):
    """Initialize log storage for a sample"""
    if sample_id not in log_store:
        log_store[sample_id] = {
            "logs": [],
            "status": DownloadStatus.PENDING,
            "started_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        active_connections[sample_id] = set()


def add_log(sample_id: str, message: str, level: str = LogLevel.INFO):
    """
    Add a log entry for a sample.
    
    Args:
        sample_id: Sample identifier
        message: Log message
        level: Log level (info, success, warning, error, progress)
    """
    init_log_store(sample_id)
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "message": message,
        "level": level
    }
    
    log_store[sample_id]["logs"].append(log_entry)
    log_store[sample_id]["updated_at"] = datetime.now().isoformat()
    
    logger.info(f"[{sample_id}] {level.upper()}: {message}")


def set_status(sample_id: str, status: str):
    """
    Set the status for a sample download/processing.
    
    Args:
        sample_id: Sample identifier
        status: Status (pending, running, completed, error)
    """
    init_log_store(sample_id)
    log_store[sample_id]["status"] = status
    log_store[sample_id]["updated_at"] = datetime.now().isoformat()


def get_logs(sample_id: str, since: int = 0) -> List[Dict]:
    """
    Get logs for a sample.
    
    Args:
        sample_id: Sample identifier
        since: Index to get logs from (for incremental updates)
        
    Returns:
        List of log entries
    """
    if sample_id not in log_store:
        return []
    
    logs = log_store[sample_id]["logs"]
    if since > 0:
        return logs[since:]
    return logs


def get_status(sample_id: str) -> Dict:
    """
    Get status information for a sample.
    
    Args:
        sample_id: Sample identifier
        
    Returns:
        Dictionary with status, log count, timestamps
    """
    if sample_id not in log_store:
        return {
            "sample_id": sample_id,
            "status": DownloadStatus.PENDING,
            "log_count": 0,
            "started_at": None,
            "updated_at": None
        }
    
    data = log_store[sample_id]
    return {
        "sample_id": sample_id,
        "status": data["status"],
        "log_count": len(data["logs"]),
        "started_at": data.get("started_at"),
        "updated_at": data.get("updated_at")
    }


def cleanup_old_logs():
    """Remove logs older than LOG_RETENTION_HOURS"""
    cutoff_time = datetime.now() - timedelta(hours=LOG_RETENTION_HOURS)
    
    samples_to_remove = []
    for sample_id, data in log_store.items():
        # Only cleanup completed or errored downloads
        if data["status"] in [DownloadStatus.COMPLETED, DownloadStatus.ERROR]:
            updated_at = datetime.fromisoformat(data["updated_at"])
            if updated_at < cutoff_time:
                samples_to_remove.append(sample_id)
    
    for sample_id in samples_to_remove:
        logger.info(f"Cleaning up old logs for {sample_id}")
        del log_store[sample_id]
        if sample_id in active_connections:
            del active_connections[sample_id]


async def connect_websocket(websocket: WebSocket, sample_id: str):
    """
    Handle WebSocket connection for a sample.
    
    Args:
        websocket: WebSocket connection
        sample_id: Sample identifier
    """
    await websocket.accept()
    
    init_log_store(sample_id)
    active_connections[sample_id].add(websocket)
    
    logger.info(f"WebSocket connected for {sample_id}")
    
    # Send existing logs to the new connection
    existing_logs = get_logs(sample_id)
    for log_entry in existing_logs:
        try:
            await websocket.send_json(log_entry)
        except Exception as e:
            logger.error(f"Error sending existing logs: {e}")
            break


async def disconnect_websocket(websocket: WebSocket, sample_id: str):
    """
    Handle WebSocket disconnection.
    
    Args:
        websocket: WebSocket connection
        sample_id: Sample identifier
    """
    if sample_id in active_connections:
        active_connections[sample_id].discard(websocket)
    
    logger.info(f"WebSocket disconnected for {sample_id}")


async def broadcast_log(sample_id: str, message: str, level: str = LogLevel.INFO):
    """
    Broadcast a log message to all connected WebSocket clients for a sample.
    
    Args:
        sample_id: Sample identifier
        message: Log message
        level: Log level
    """
    # Store the log
    add_log(sample_id, message, level)
    
    # Broadcast to WebSocket connections
    if sample_id in active_connections:
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "message": message,
            "level": level
        }
        
        disconnected = set()
        for websocket in active_connections[sample_id]:
            try:
                await websocket.send_json(log_entry)
            except Exception as e:
                logger.error(f"Error broadcasting to WebSocket: {e}")
                disconnected.add(websocket)
        
        # Remove disconnected clients
        for websocket in disconnected:
            active_connections[sample_id].discard(websocket)


async def websocket_endpoint(websocket: WebSocket, sample_id: str):
    """
    WebSocket endpoint handler.
    
    Args:
        websocket: WebSocket connection
        sample_id: Sample identifier
    """
    await connect_websocket(websocket, sample_id)
    
    try:
        # Keep the connection alive
        while True:
            # Wait for any client messages (ping/pong)
            data = await websocket.receive_text()
            
            # Echo back for keep-alive
            if data == "ping":
                await websocket.send_text("pong")
                
    except WebSocketDisconnect:
        await disconnect_websocket(websocket, sample_id)
    except Exception as e:
        logger.error(f"WebSocket error for {sample_id}: {e}")
        await disconnect_websocket(websocket, sample_id)

