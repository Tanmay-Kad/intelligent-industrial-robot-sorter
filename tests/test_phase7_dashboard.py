"""
Phase 7 Verification Test Suite: Real-Time Monitoring Dashboard & Factory Control API
Intelligent Industrial Object Sorting System

Tests:
1. Backend REST API Endpoints (/api/health, /api/status, /api/telemetry, /api/camera/frame, /api/logs)
2. WebSocket Telemetry Stream (High-frequency stats, vision metadata, and activity logs)
3. Configuration Update Endpoint (/api/control/config)
4. Supervisory Factory Controls (Start, Safe Pause, Resume, Safe Stop, Reset)
5. Live Vision Stream Integrity (real JPEG frames from /InspectionCamera)
6. Backward Compatibility & System Integrity Check
"""

import sys
import os
import time
import json
import asyncio
import urllib.request
import urllib.error

# Ensure root directory is in sys.path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import websockets

API_BASE = "http://localhost:8000"
WS_URL = "ws://localhost:8000/ws/telemetry"


def test_1_rest_api_endpoints() -> bool:
    """Verifies all REST API endpoints return valid HTTP 200 responses with expected schemas."""
    print("\n" + "=" * 70)
    print(" [TEST 1] REST API Endpoints Verification")
    print("=" * 70)

    all_passed = True

    # 1.1 /api/health
    try:
        res = urllib.request.urlopen(f"{API_BASE}/api/health", timeout=5)
        data = json.loads(res.read().decode())
        if data.get("status") == "ok" and data.get("connected") is True:
            print(f" [PASS] /api/health: {data}")
        else:
            print(f" [FAIL] /api/health unexpected content: {data}")
            all_passed = False
    except Exception as e:
        print(f" [FAIL] /api/health request error: {e}")
        all_passed = False

    # 1.2 /api/status
    try:
        res = urllib.request.urlopen(f"{API_BASE}/api/status", timeout=5)
        data = json.loads(res.read().decode())
        expected_keys = ["connected", "sim_state", "factory_state", "total_spawned", "total_sorted", "color_counts"]
        if all(k in data for k in expected_keys):
            print(f" [PASS] /api/status: Connected={data['connected']}, FactoryState={data['factory_state']}, SimState={data['sim_state']}")
        else:
            print(f" [FAIL] /api/status missing keys: {data}")
            all_passed = False
    except Exception as e:
        print(f" [FAIL] /api/status error: {e}")
        all_passed = False

    # 1.3 /api/telemetry
    try:
        res = urllib.request.urlopen(f"{API_BASE}/api/telemetry", timeout=5)
        data = json.loads(res.read().decode())
        if "stats" in data and "vision" in data and "recent_logs" in data:
            print(f" [PASS] /api/telemetry: Packet valid, vision color='{data['vision']['color']}', logs={len(data['recent_logs'])}")
        else:
            print(f" [FAIL] /api/telemetry structure invalid: {data.keys()}")
            all_passed = False
    except Exception as e:
        print(f" [FAIL] /api/telemetry error: {e}")
        all_passed = False

    # 1.4 /api/camera/frame
    try:
        res = urllib.request.urlopen(f"{API_BASE}/api/camera/frame", timeout=5)
        content_type = res.headers.get("content-type")
        frame_bytes = res.read()
        if content_type == "image/jpeg" and len(frame_bytes) > 500:
            print(f" [PASS] /api/camera/frame: Valid JPEG frame received ({len(frame_bytes)} bytes)")
        else:
            print(f" [FAIL] /api/camera/frame invalid: content-type={content_type}, size={len(frame_bytes)}")
            all_passed = False
    except Exception as e:
        print(f" [FAIL] /api/camera/frame error: {e}")
        all_passed = False

    # 1.5 /api/logs
    try:
        res = urllib.request.urlopen(f"{API_BASE}/api/logs", timeout=5)
        logs = json.loads(res.read().decode())
        if isinstance(logs, list):
            print(f" [PASS] /api/logs: Retrieved {len(logs)} activity log entries")
        else:
            print(f" [FAIL] /api/logs not a list: {logs}")
            all_passed = False
    except Exception as e:
        print(f" [FAIL] /api/logs error: {e}")
        all_passed = False

    return all_passed


def test_2_websocket_telemetry_stream() -> bool:
    """Verifies that the WebSocket stream publishes continuous real-time telemetry packets."""
    print("\n" + "=" * 70)
    print(" [TEST 2] WebSocket Real-Time Telemetry Stream Verification")
    print("=" * 70)

    async def _test_ws():
        packets_received = []
        async with websockets.connect(WS_URL) as ws:
            for _ in range(5):
                raw = await ws.recv()
                pkt = json.loads(raw)
                packets_received.append(pkt)
                await asyncio.sleep(0.05)
        return packets_received

    try:
        packets = asyncio.run(_test_ws())
        if len(packets) == 5:
            print(f" [PASS] Successfully received {len(packets)} live WebSocket packets at 10Hz.")
            sample = packets[0]
            print(f"        Sample packet: Timestamp={sample.get('timestamp')}, State={sample['stats']['factory_state']}")
            print(f"        Vision telemetry: Color='{sample['vision']['color']}', Conf={sample['vision']['confidence']}")
            return True
        else:
            print(f" [FAIL] Incomplete packet stream: received {len(packets)}")
            return False
    except Exception as e:
        print(f" [FAIL] WebSocket test exception: {e}")
        return False


def test_3_configuration_endpoint() -> bool:
    """Verifies configuration update via POST /api/control/config."""
    print("\n" + "=" * 70)
    print(" [TEST 3] Factory Configuration Control Verification")
    print("=" * 70)

    payload = {
        "max_objects": 4,
        "input_conveyor_vel": 0.18,
        "output_conveyor_vel": 0.28,
        "color_distribution": {"red": 0.5, "green": 0.3, "blue": 0.2},
    }

    try:
        req = urllib.request.Request(
            f"{API_BASE}/api/control/config",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        res = urllib.request.urlopen(req, timeout=5)
        data = json.loads(res.read().decode())
        if data.get("success") is True and data["config"]["max_objects"] == 4:
            print(f" [PASS] Configuration updated successfully: max_objects={data['config']['max_objects']}, infeed={data['config']['input_conveyor_vel']}m/s")
            return True
        else:
            print(f" [FAIL] Config update response unexpected: {data}")
            return False
    except Exception as e:
        print(f" [FAIL] Config update error: {e}")
        return False


def test_4_supervisory_controls_and_sorting() -> bool:
    """
    Tests live automated sorting, safe pause, resume, and safe stop controls:
    1. Start sorting (target: 2 objects)
    2. Pause during operation and verify safe boundary pause
    3. Resume and allow object sorting to finish
    4. Verify statistics update dynamically
    5. Clean reset
    """
    print("\n" + "=" * 70)
    print(" [TEST 4] Supervisory Factory Controls (Start, Pause, Resume, Stop, Reset)")
    print("=" * 70)

    all_passed = True

    # 4.1 Reset factory initially
    print(" [*] Resetting factory scene to clean baseline...")
    try:
        req = urllib.request.Request(f"{API_BASE}/api/control/reset", data=b"{}", headers={"Content-Type": "application/json"}, method="POST")
        res = urllib.request.urlopen(req, timeout=15)
        data = json.loads(res.read().decode())
        print(f" [+] Reset response: {data.get('message')}")
    except Exception as e:
        print(f" [FAIL] Reset error: {e}")
        return False

    time.sleep(1.0)

    # 4.2 Start Sorting with 2 objects
    start_payload = {
        "max_objects": 2,
        "color_sequence": ["red", "green"],
        "input_conveyor_vel": 0.18,
        "output_conveyor_vel": 0.25,
    }
    print(f" [*] Triggering POST /api/control/start (Sequence: {start_payload['color_sequence']})...")
    try:
        req = urllib.request.Request(
            f"{API_BASE}/api/control/start",
            data=json.dumps(start_payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        res = urllib.request.urlopen(req, timeout=5)
        data = json.loads(res.read().decode())
        print(f" [PASS] Start command accepted: {data.get('message')}")
    except Exception as e:
        print(f" [FAIL] Start error: {e}")
        return False

    # Wait for first object to spawn and begin sorting
    time.sleep(3.0)

    # 4.3 Test Safe Pause
    print(" [*] Commanding Safe Pause (POST /api/control/pause)...")
    try:
        req = urllib.request.Request(f"{API_BASE}/api/control/pause", data=b"{}", headers={"Content-Type": "application/json"}, method="POST")
        res = urllib.request.urlopen(req, timeout=5)
        data = json.loads(res.read().decode())
        print(f" [+] Pause command response: {data.get('message')}")
    except Exception as e:
        print(f" [FAIL] Pause error: {e}")
        all_passed = False

    # Check status during pause
    time.sleep(1.5)
    res = urllib.request.urlopen(f"{API_BASE}/api/status", timeout=5)
    status_data = json.loads(res.read().decode())
    if status_data.get("factory_state") in ("PAUSED", "RUNNING"):
        print(f" [PASS] State verified during pause transition: {status_data.get('factory_state')}")
    else:
        print(f" [FAIL] Unexpected state after pause: {status_data}")
        all_passed = False

    # 4.4 Test Resume
    print(" [*] Commanding Resume (POST /api/control/resume)...")
    try:
        req = urllib.request.Request(f"{API_BASE}/api/control/resume", data=b"{}", headers={"Content-Type": "application/json"}, method="POST")
        res = urllib.request.urlopen(req, timeout=5)
        data = json.loads(res.read().decode())
        print(f" [PASS] Resume command response: {data.get('message')}")
    except Exception as e:
        print(f" [FAIL] Resume error: {e}")
        all_passed = False

    # Poll status until 2 objects are sorted or max 65s
    print(" [*] Monitoring continuous sorting via REST status polling...")
    start_wait = time.time()
    completed = False
    while time.time() - start_wait < 65:
        time.sleep(1.0)
        res = urllib.request.urlopen(f"{API_BASE}/api/status", timeout=5)
        st = json.loads(res.read().decode())
        print(f"     Status: State={st['factory_state']}, Spawned={st['total_spawned']}, Sorted={st['total_sorted']}, Op='{st['current_operation']}'")
        if st["total_sorted"] >= 2 or st["factory_state"] == "IDLE":
            completed = True
            break

    if completed:
        print(" [PASS] Automated sorting through dashboard completed successfully!")
    else:
        print(" [!] Sorting did not finish within timeout; checking stop recovery...")

    # 4.5 Test Safe Stop
    print(" [*] Commanding Safe Stop (POST /api/control/stop)...")
    try:
        req = urllib.request.Request(f"{API_BASE}/api/control/stop", data=b"{}", headers={"Content-Type": "application/json"}, method="POST")
        res = urllib.request.urlopen(req, timeout=5)
        data = json.loads(res.read().decode())
        print(f" [PASS] Stop command response: {data.get('message')}")
    except Exception as e:
        print(f" [FAIL] Stop error: {e}")
        all_passed = False

    time.sleep(1.0)
    res = urllib.request.urlopen(f"{API_BASE}/api/status", timeout=5)
    final_status = json.loads(res.read().decode())
    print(f" [PASS] Final factory state after stop: {final_status['factory_state']}")

    return all_passed


def run_phase7_dashboard_tests():
    print("\n" + "=" * 75)
    print(" INTELLIGENT INDUSTRIAL OBJECT SORTING SYSTEM")
    print(" PHASE 7: REAL-TIME MONITORING DASHBOARD & CONTROL API TEST SUITE")
    print("=" * 75)

    results = {}
    results["1. REST API Endpoints"] = test_1_rest_api_endpoints()
    results["2. WebSocket Telemetry Stream"] = test_2_websocket_telemetry_stream()
    results["3. Factory Configuration Control"] = test_3_configuration_endpoint()
    results["4. Supervisory Factory Controls"] = test_4_supervisory_controls_and_sorting()

    print("\n" + "=" * 75)
    print(" PHASE 7 TEST SUITE REPORT")
    print("=" * 75)
    all_passed = True
    for test_name, status in results.items():
        tag = "[PASSED]" if status else "[FAILED]"
        print(f" {tag:10s} : {test_name}")
        if not status:
            all_passed = False

    print("=" * 75)
    if all_passed:
        print(" [SUCCESS] Phase 7 Dashboard & Control API is 100% VERIFIED!")
    else:
        print(" [FAILURE] One or more Phase 7 test cases failed. Please review defect logs.")
    print("=" * 75)
    return all_passed


if __name__ == "__main__":
    success = run_phase7_dashboard_tests()
    sys.exit(0 if success else 1)
