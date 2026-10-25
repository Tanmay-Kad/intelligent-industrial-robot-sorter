"""
Pydantic Data Models for Factory Monitoring Dashboard & Control API (Phase 7)
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class FactoryState(str, Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"
    RESETTING = "RESETTING"
    ERROR = "ERROR"


class RobotOperation(str, Enum):
    IDLE = "Idle / Docked"
    FEEDING = "Advancing Conveyor"
    INSPECTING = "Inspecting Station"
    DETECTED = "Object Detected"
    PICKING = "Picking Block"
    TRANSIT = "Corridor Transit"
    PLACING = "Placing on Conveyor"
    TRANSPORTING = "Discharging to Bin"
    SAFE_RECOVERY = "Safe State Recovery"


class ColorCounts(BaseModel):
    red: int = 0
    green: int = 0
    blue: int = 0


class SystemStats(BaseModel):
    connected: bool = False
    sim_state: str = "STOPPED"  # STOPPED, RUNNING, PAUSED
    factory_state: FactoryState = FactoryState.IDLE
    current_operation: str = "System Initialized"
    
    # Object counts
    total_spawned: int = 0
    total_sorted: int = 0
    total_failed: int = 0
    pending_objects: int = 0
    
    # Color breakdown
    color_counts: ColorCounts = Field(default_factory=ColorCounts)
    
    # Analytics
    success_rate: float = 0.0
    avg_cycle_time_s: float = 0.0
    throughput_bpm: float = 0.0
    uptime_seconds: float = 0.0


class VisionTelemetry(BaseModel):
    has_frame: bool = False
    detected: bool = False
    color: str = "none"
    confidence: float = 0.0
    center: Optional[List[int]] = None
    bbox: Optional[List[int]] = None  # [x, y, w, h]
    contour_area: float = 0.0
    image_base64: Optional[str] = None  # JPEG base64 string with annotations


class ActivityLogEntry(BaseModel):
    id: str
    timestamp: str  # e.g. "12:05:32"
    type: str       # "spawn", "detect", "pick", "place", "sorted", "recovery", "info", "warning", "error"
    message: str
    details: Optional[Dict[str, Any]] = None


class ConfigPayload(BaseModel):
    max_objects: int = Field(default=12, ge=1, le=50)
    color_distribution: Dict[str, float] = Field(
        default_factory=lambda: {"red": 1/3, "green": 1/3, "blue": 1/3}
    )
    color_sequence: Optional[List[str]] = None
    input_conveyor_vel: float = Field(default=0.15, ge=0.05, le=0.50)
    output_conveyor_vel: float = Field(default=0.25, ge=0.05, le=0.60)


class ControlCommand(BaseModel):
    command: str  # "start", "pause", "resume", "stop", "reset"
    params: Optional[Dict[str, Any]] = None


class TelemetryPacket(BaseModel):
    timestamp: float
    stats: SystemStats
    vision: VisionTelemetry
    recent_logs: List[ActivityLogEntry]
