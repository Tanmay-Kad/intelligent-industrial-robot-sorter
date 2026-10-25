"""
FastAPI Server & WebSocket Telemetry Gateway (Phase 7)
Intelligent Industrial Object Sorting System
"""

import os
import sys
import asyncio
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Ensure root directory is in sys.path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from dashboard.backend.models import (
    ConfigPayload,
    ControlCommand,
)
from dashboard.backend.factory_manager import FactoryManager

app = FastAPI(
    title="Intelligent Industrial Sorting Factory API",
    description="Real-Time Factory Monitoring & Supervisory Control Gateway",
    version="1.0.0",
)

# Enable CORS for local Vite development server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Central Factory Manager
manager = FactoryManager.get_instance()


# ------------------------------------------------------------------------------
# REST API Endpoints
# ------------------------------------------------------------------------------

@app.get("/api/health")
def get_health():
    """Health check endpoint."""
    return {"status": "ok", "connected": manager.sim is not None}


@app.get("/api/status")
def get_status():
    """Returns the current factory overview and statistics."""
    return manager.get_system_stats()


@app.get("/api/telemetry")
def get_telemetry():
    """Returns a full telemetry snapshot (stats, vision metadata, and recent logs)."""
    return manager.get_telemetry_packet()


@app.get("/api/camera/frame")
def get_camera_frame():
    """Returns the latest annotated JPEG frame from /InspectionCamera."""
    if manager.latest_frame_jpeg:
        return Response(content=manager.latest_frame_jpeg, media_type="image/jpeg")
    
    # Try capturing immediately
    manager.capture_live_vision()
    if manager.latest_frame_jpeg:
        return Response(content=manager.latest_frame_jpeg, media_type="image/jpeg")

    raise HTTPException(status_code=503, detail="Camera frame not currently available")


@app.get("/api/logs")
def get_logs():
    """Returns the full chronological activity log buffer."""
    return [log.model_dump() for log in manager.activity_logs]


@app.post("/api/control/start")
def start_sorting(config: Optional[ConfigPayload] = None):
    """Starts the continuous automated sorting cycle."""
    res = manager.start_sorting(config)
    if not res["success"]:
        raise HTTPException(status_code=400, detail=res["message"])
    return res


@app.post("/api/control/pause")
def pause_sorting():
    """Requests safe pause at the next operation boundary."""
    res = manager.pause_sorting()
    if not res["success"]:
        raise HTTPException(status_code=400, detail=res["message"])
    return res


@app.post("/api/control/resume")
def resume_sorting():
    """Resumes sorting after a safe pause."""
    res = manager.resume_sorting()
    if not res["success"]:
        raise HTTPException(status_code=400, detail=res["message"])
    return res


@app.post("/api/control/stop")
def stop_sorting():
    """Initiates a safe stop, returning robot arm to Home and halting infeed."""
    return manager.stop_sorting()


@app.post("/api/control/reset")
def reset_factory():
    """Resets simulation scene and counters to clean baseline."""
    res = manager.reset_factory()
    if not res["success"]:
        raise HTTPException(status_code=500, detail=res["message"])
    return res


@app.post("/api/control/config")
def update_config(payload: ConfigPayload):
    """Updates sorting parameters (e.g. max_objects, color_distribution, conveyor speeds)."""
    return manager.update_config(payload)


# ------------------------------------------------------------------------------
# WebSocket Real-Time Telemetry Streaming
# ------------------------------------------------------------------------------

@app.websocket("/ws/telemetry")
async def websocket_telemetry_stream(websocket: WebSocket):
    """
    Streams high-frequency real-time factory telemetry, camera frame base64,
    and timestamped activity logs to connected dashboard clients at ~10Hz.
    """
    await websocket.accept()
    try:
        while True:
            # Generate consolidated packet
            # Run in thread pool to avoid blocking the asyncio event loop
            packet = await asyncio.to_thread(manager.get_telemetry_packet)
            await websocket.send_json(packet)
            await asyncio.sleep(0.1)  # 10 Hz refresh rate
    except WebSocketDisconnect:
        pass
    except Exception as e:
        pass


# ------------------------------------------------------------------------------
# Static Frontend Serving (Production build)
# ------------------------------------------------------------------------------

frontend_dist = os.path.join(ROOT_DIR, "dashboard", "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = os.path.join(frontend_dist, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(frontend_dist, "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
