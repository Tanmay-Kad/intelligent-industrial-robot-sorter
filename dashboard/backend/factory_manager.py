"""
Factory Manager Module for Intelligent Industrial Robot Sorter Dashboard (Phase 7)
Coordinates thread-safe execution, real-time telemetry streaming, live camera feed encoding,
and safe factory operation controls (start, pause, resume, stop, reset).
"""

import os
import sys
import time
import base64
import uuid
import threading
from collections import deque
from typing import Dict, List, Optional, Any, Callable

import cv2
import numpy as np

# Ensure root directory is in sys.path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from core.sim_client import get_sim_client
import config.settings as cfg
from src.sorting_controller import SortingController
from src.object_spawner import ObjectSpawner, ObjectState
from vision.color_detector import ColorDetector, DetectionResult
from dashboard.backend.models import (
    FactoryState,
    RobotOperation,
    SystemStats,
    ColorCounts,
    VisionTelemetry,
    ActivityLogEntry,
    ConfigPayload,
    TelemetryPacket,
)


class FactoryManager:
    """
    Central, thread-safe orchestrator for the CoppeliaSim sorting factory.
    Safely serializes Remote API commands and streams real-time telemetry.
    """

    _instance: Optional["FactoryManager"] = None
    _lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> "FactoryManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __init__(self):
        self.sim = None
        self.client = None
        self.controller: Optional[SortingController] = None
        self.detector: Optional[ColorDetector] = None

        self.state: FactoryState = FactoryState.IDLE
        self.current_operation: str = "System Initialized"
        self.config: ConfigPayload = ConfigPayload()

        self._stop_requested = False
        self._pause_requested = False
        self._worker_thread: Optional[threading.Thread] = None

        # Logging & Telemetry History
        self.activity_logs: deque = deque(maxlen=200)
        self.start_time: Optional[float] = None
        self.total_uptime_s: float = 0.0

        # Latest vision cache
        self.latest_vision: VisionTelemetry = VisionTelemetry()
        self.latest_frame_jpeg: Optional[bytes] = None

        # WebSocket subscribers callback list
        self.ws_subscribers: List[Callable[[Dict[str, Any]], None]] = []

        # Connect simulation
        self._initialize_simulation()

    def _initialize_simulation(self) -> bool:
        """Connects to CoppeliaSim Remote API and initializes sorting subsystems."""
        try:
            print("[MANAGER] Connecting to CoppeliaSim ZeroMQ Remote API...")
            self.client, self.sim = get_sim_client()
            
            # Create controller and vision detector
            self.controller = SortingController(self.client, self.sim)
            self.detector = self.controller.detector

            # Wire event emission and vision callbacks
            self.controller.on_event = self._handle_controller_event
            self.detector.on_detection = self._handle_detection_result

            # Initial vision capture safely
            with self._lock:
                self.detector.detect_color()

            self._add_log("info", "Successfully connected to CoppeliaSim ZeroMQ Remote API on port 23000.")
            return True
        except Exception as e:
            print(f"[MANAGER] Connection failed: {e}")
            self.state = FactoryState.ERROR
            self._add_log("error", f"Failed to connect to CoppeliaSim: {e}")
            return False

    def _handle_detection_result(self, res: DetectionResult):
        """Callback invoked whenever ColorDetector processes a camera frame."""
        if res.annotated_frame is not None:
            try:
                success, buf = cv2.imencode(".jpg", res.annotated_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                if success:
                    jpeg_bytes = buf.tobytes()
                    self.latest_frame_jpeg = jpeg_bytes
                    b64_str = base64.b64encode(jpeg_bytes).decode("utf-8")

                    self.latest_vision = VisionTelemetry(
                        has_frame=True,
                        detected=res.detected,
                        color=res.color,
                        confidence=round(res.confidence, 3),
                        center=list(res.center) if res.center else None,
                        bbox=list(res.bbox) if res.bbox else None,
                        contour_area=round(res.contour_area, 1),
                        image_base64=b64_str,
                    )
            except Exception:
                pass

    def _add_log(self, log_type: str, message: str, details: Optional[Dict[str, Any]] = None):
        """Records a timestamped activity log entry and notifies subscribers."""
        timestamp_str = time.strftime("%H:%M:%S")
        entry = ActivityLogEntry(
            id=str(uuid.uuid4())[:8],
            timestamp=timestamp_str,
            type=log_type,
            message=message,
            details=details,
        )
        self.activity_logs.appendleft(entry)

    def _handle_controller_event(self, event_type: str, message: str, details: Optional[Dict[str, Any]] = None):
        """Callback invoked by SortingController during operations."""
        self.current_operation = message
        self._add_log(event_type, message, details)

    # --------------------------------------------------------------------------
    # Simulation Telemetry & Camera Capture
    # --------------------------------------------------------------------------

    def capture_live_vision(self) -> VisionTelemetry:
        """Captures frame from /InspectionCamera and generates annotated telemetry."""
        if not self.detector or not self.sim:
            return self.latest_vision

        # When running or resetting, the worker thread exclusively owns the ZeroMQ connection.
        # Return cached vision telemetry to avoid concurrent socket access.
        if self.state in (FactoryState.RUNNING, FactoryState.RESETTING):
            return self.latest_vision

        try:
            with self._lock:
                res = self.detector.detect_color()
                self._handle_detection_result(res)
        except Exception:
            pass

        return self.latest_vision

    def get_system_stats(self) -> SystemStats:
        """Computes current factory overview statistics."""
        connected = False
        sim_state_str = "STOPPED"
        if self.state == FactoryState.RUNNING:
            sim_state_str = "RUNNING"
            connected = (self.sim is not None)
        elif self.state == FactoryState.RESETTING:
            sim_state_str = "STOPPED"
            connected = (self.sim is not None)
        else:
            with self._lock:
                if self.sim:
                    try:
                        sim_state = self.sim.getSimulationState()
                        connected = True
                        if sim_state == self.sim.simulation_stopped:
                            sim_state_str = "STOPPED"
                        elif sim_state == self.sim.simulation_paused:
                            sim_state_str = "PAUSED"
                        else:
                            sim_state_str = "RUNNING"
                    except Exception:
                        connected = False

        # Read controller stats
        stats_dict = self.controller.stats if self.controller else {
            "red": 0, "green": 0, "blue": 0, "total_sorted": 0,
            "detection_failures": 0, "grasp_failures": 0, "bin_failures": 0
        }

        total_sorted = stats_dict.get("total_sorted", 0)
        total_failed = (
            stats_dict.get("detection_failures", 0)
            + stats_dict.get("grasp_failures", 0)
            + stats_dict.get("bin_failures", 0)
        )
        total_attempts = total_sorted + total_failed
        success_rate = (total_sorted / total_attempts * 100.0) if total_attempts > 0 else 100.0

        # Spawner tracking
        total_spawned = 0
        pending_objects = 0
        if self.controller and self.controller.spawner:
            total_spawned = self.controller.spawner.spawn_counter
            pending_objects = len(self.controller.spawner.get_objects_in_state(ObjectState.WAITING))

        # Uptime & Throughput
        uptime = 0.0
        if self.start_time and self.state in (FactoryState.RUNNING, FactoryState.PAUSED):
            uptime = time.time() - self.start_time
            self.total_uptime_s = uptime
        else:
            uptime = self.total_uptime_s

        avg_cycle_time = (uptime / total_sorted) if total_sorted > 0 else 0.0
        throughput = (total_sorted / (uptime / 60.0)) if uptime > 5.0 and total_sorted > 0 else 0.0

        return SystemStats(
            connected=connected,
            sim_state=sim_state_str,
            factory_state=self.state,
            current_operation=self.current_operation,
            total_spawned=total_spawned,
            total_sorted=total_sorted,
            total_failed=total_failed,
            pending_objects=pending_objects,
            color_counts=ColorCounts(
                red=stats_dict.get("red", 0),
                green=stats_dict.get("green", 0),
                blue=stats_dict.get("blue", 0),
            ),
            success_rate=round(success_rate, 1),
            avg_cycle_time_s=round(avg_cycle_time, 2),
            throughput_bpm=round(throughput, 2),
            uptime_seconds=round(uptime, 1),
        )

    def get_telemetry_packet(self) -> Dict[str, Any]:
        """Constructs a consolidated telemetry packet for REST or WebSocket clients."""
        stats = self.get_system_stats()
        vision = self.capture_live_vision()
        recent_logs = list(self.activity_logs)[:35]

        return {
            "timestamp": time.time(),
            "stats": stats.model_dump(),
            "vision": vision.model_dump(),
            "recent_logs": [log.model_dump() for log in recent_logs],
        }

    # --------------------------------------------------------------------------
    # Factory Control Logic (Start, Pause, Resume, Stop, Reset)
    # --------------------------------------------------------------------------

    def start_sorting(self, config_payload: Optional[ConfigPayload] = None) -> Dict[str, Any]:
        """Starts automated sorting execution in a background worker thread."""
        if self.state == FactoryState.RUNNING:
            return {"success": False, "message": "Automation is already actively running."}

        if self.state == FactoryState.PAUSED:
            return self.resume_sorting()

        if config_payload:
            self.config = config_payload

        # Ensure CoppeliaSim connection
        if not self.sim:
            if not self._initialize_simulation():
                return {"success": False, "message": "Failed to connect to CoppeliaSim."}

        self._stop_requested = False
        self._pause_requested = False
        self.start_time = time.time()
        self.state = FactoryState.RUNNING

        self._add_log(
            "info",
            f"Starting continuous sorting run (Target: {self.config.max_objects} objects)...",
            {"config": self.config.model_dump()}
        )

        # Launch dedicated worker thread
        self._worker_thread = threading.Thread(
            target=self._run_sorting_worker,
            daemon=True,
            name="SortingWorkerThread"
        )
        self._worker_thread.start()

        return {"success": True, "message": "Automated sorting pipeline started."}

    def _run_sorting_worker(self):
        """Worker thread executing the continuous sorting pipeline."""
        try:
            with self._lock:
                # Verify simulation is running
                if self.sim.getSimulationState() == self.sim.simulation_stopped:
                    self.client.setStepping(True)
                    self.sim.startSimulation()
                    for _ in range(5):
                        self.client.step()

                # Initialize controller hardware subsystems
                self.controller.initialize_system()
                self.controller.input_conveyor_vel = self.config.input_conveyor_vel
                self.controller.output_conveyor_vel = self.config.output_conveyor_vel

            self._add_log("info", "Subsystems initialized. Beginning dynamic block feeding...")

            # Run sorting loop with safe pause & stop checks
            summary = self.controller.run_continuous_sorting(
                max_objects=self.config.max_objects,
                color_sequence=self.config.color_sequence,
                color_distribution=self.config.color_distribution,
                save_annotations=True,
                pause_checker=lambda: self._pause_requested,
                stop_checker=lambda: self._stop_requested,
            )

            with self._lock:
                if self._stop_requested:
                    self.state = FactoryState.STOPPED
                    self.current_operation = "Automation Stopped Safely"
                    self._add_log("info", "Automated sorting safely stopped.")
                else:
                    self.state = FactoryState.IDLE
                    self.current_operation = "All Targets Processed"
                    self._add_log(
                        "sorted",
                        f"Continuous sorting run completed! Sorted: {summary['total_sorted']} / {summary['total_spawned']}",
                        {"summary": summary}
                    )

        except Exception as e:
            print(f"[MANAGER] Worker thread error: {e}")
            self.state = FactoryState.ERROR
            self.current_operation = f"Error: {e}"
            self._add_log("error", f"Pipeline encountered an exception: {e}")
            try:
                with self._lock:
                    self.controller.recover_to_safe_state()
            except Exception:
                pass

    def pause_sorting(self) -> Dict[str, Any]:
        """Requests safe pause at the next operation boundary."""
        if self.state != FactoryState.RUNNING:
            return {"success": False, "message": "Cannot pause: System is not actively running."}

        self._pause_requested = True
        self.state = FactoryState.PAUSED
        self._add_log("warning", "Safe Pause Requested. Finishing active action and pausing at boundary...")
        return {"success": True, "message": "Pause requested. Pipeline will pause at safe boundary."}

    def resume_sorting(self) -> Dict[str, Any]:
        """Resumes sorting after a safe pause."""
        if self.state != FactoryState.PAUSED:
            return {"success": False, "message": "Cannot resume: System is not currently paused."}

        self._pause_requested = False
        self.state = FactoryState.RUNNING
        self._add_log("info", "Factory Automation Resumed.")
        return {"success": True, "message": "Sorting automation resumed."}

    def stop_sorting(self) -> Dict[str, Any]:
        """Commands a safe stop, returning robot to Home and halting conveyors."""
        self._stop_requested = True
        self._pause_requested = False
        self.state = FactoryState.STOPPED
        self._add_log("warning", "Safe Stop Commanded. Halting conveyors and docking robot at Home...")

        if not self._worker_thread or not self._worker_thread.is_alive():
            with self._lock:
                if self.controller:
                    try:
                        self.controller.recover_to_safe_state()
                    except Exception:
                        pass
        return {"success": True, "message": "Safe stop initiated. Robot returning to Home."}

    def reset_factory(self) -> Dict[str, Any]:
        """Resets simulation scene and clears all statistics."""
        self._stop_requested = True
        self._pause_requested = False
        self.state = FactoryState.RESETTING

        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=3.0)

        with self._lock:
            try:
                if self.sim:
                    self.sim.stopSimulation()
                    while self.sim.getSimulationState() != self.sim.simulation_stopped:
                        time.sleep(0.1)

                    self.client.setStepping(False)
                    time.sleep(0.3)
                    self.sim.loadScene(cfg.SAVED_SCENE_FILE)
                    time.sleep(0.3)
                    self.client.setStepping(True)
                    self.sim.startSimulation()

                    while self.sim.getSimulationState() == self.sim.simulation_stopped:
                        time.sleep(0.1)

                    for _ in range(5):
                        self.client.step()

                # Re-initialize controller
                self.controller = SortingController(self.client, self.sim)
                self.controller.on_event = self._handle_controller_event
                self.detector = self.controller.detector
                self.detector.on_detection = self._handle_detection_result
                self.controller.initialize_system()

                self.state = FactoryState.IDLE
                self.current_operation = "Scene Reset Cleanly"
                self.start_time = None
                self.total_uptime_s = 0.0
                self.activity_logs.clear()

                self._add_log("info", "Factory scene reloaded and initialized to clean baseline.")
                return {"success": True, "message": "Factory reset successfully."}
            except Exception as e:
                self.state = FactoryState.ERROR
                self._add_log("error", f"Factory reset failed: {e}")
                return {"success": False, "message": f"Reset failed: {e}"}

    def update_config(self, config_payload: ConfigPayload) -> Dict[str, Any]:
        """Updates sorting automation configuration."""
        self.config = config_payload
        if self.controller:
            self.controller.input_conveyor_vel = config_payload.input_conveyor_vel
            self.controller.output_conveyor_vel = config_payload.output_conveyor_vel

        self._add_log("info", "Factory configuration updated.", {"config": config_payload.model_dump()})
        return {"success": True, "message": "Configuration saved.", "config": self.config.model_dump()}
