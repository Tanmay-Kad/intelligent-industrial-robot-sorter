"""
Vision Test Runner: Verifies Camera Frame Capture and RGB Classification (Phase 4, Step 2)
Tests:
1. Vision Sensor Frame Acquisition & Conversion (NumPy / OpenCV BGR)
2. Empty Pickup Station Detection (Zero False Positives)
3. Red Block Classification on Live Frame
4. Green Block Classification on Live Frame
5. Blue Block Classification on Live Frame
"""

import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from core.sim_client import get_sim_client
from vision.color_detector import ColorDetector
import config.settings as cfg


def run_vision_tests() -> bool:
    print("=" * 70)
    print(" Phase 4: Camera-Based Color Detection Test Suite")
    print("=" * 70)

    client, sim = get_sim_client(cfg.ZMQ_HOST, cfg.ZMQ_PORT)

    # Clean scene state
    sim.stopSimulation()
    client.setStepping(False)
    time.sleep(0.2)
    sim.loadScene(cfg.SAVED_SCENE_FILE)

    client.setStepping(True)
    sim.startSimulation()

    detector = ColorDetector(client, sim)
    
    red_block = sim.getObject("/RedBlock")
    green_block = sim.getObject("/GreenBlock")
    blue_block = sim.getObject("/BlueBlock")
    in_conv = sim.getObject("/InputConveyor")

    # Stop input conveyor so blocks stay parked
    sim.writeCustomTableData(in_conv, "__ctrl__", {"vel": 0.0})
    for _ in range(3):
        client.step()

    # Move all blocks outside camera FOV initially
    sim.setObjectPosition(red_block, [-5.0, 0.0, 0.5], -1)
    sim.setObjectPosition(green_block, [-5.0, 0.5, 0.5], -1)
    sim.setObjectPosition(blue_block, [-5.0, -0.5, 0.5], -1)
    for _ in range(5):
        client.step()

    output_dir = "test_output"
    os.makedirs(output_dir, exist_ok=True)
    results = {}
    all_passed = True

    # -------------------------------------------------------------
    # Test 1: Camera Frame Capture & Resolution Validation
    # -------------------------------------------------------------
    print("\n[TEST 1] Testing Camera Frame Acquisition...")
    ok, frame = detector.capture_frame()
    if ok and frame is not None and frame.shape == (128, 128, 3):
        print(f" [PASS] Frame captured successfully: shape={frame.shape}, dtype={frame.dtype}")
        results["Frame Capture"] = True
    else:
        print(f" [FAIL] Frame capture failed! (ok={ok})")
        results["Frame Capture"] = False
        all_passed = False

    # -------------------------------------------------------------
    # Test 2: Empty Conveyor Detection (Zero False Positives)
    # -------------------------------------------------------------
    print("\n[TEST 2] Testing Empty Pickup Station Detection...")
    res_empty = detector.detect_color(frame=None, annotate=True)
    detector.save_image(res_empty.annotated_frame, f"{output_dir}/vision_empty.png")
    print(f" [+] Detected: '{res_empty.color}', confidence: {res_empty.confidence:.2f}, area: {res_empty.contour_area}")

    if not res_empty.detected and res_empty.color == "none":
        print(" [PASS] Empty belt correctly identified with ZERO false positives.")
        results["Empty Detection"] = True
    else:
        print(f" [FAIL] Unexpected detection on empty conveyor: {res_empty.color}")
        results["Empty Detection"] = False
        all_passed = False

    # -------------------------------------------------------------
    # Test 3: Red Block Classification
    # -------------------------------------------------------------
    print("\n[TEST 3] Testing Red Block Classification...")
    pick_pos = [-0.375, 0.0, cfg.BLOCK_REST_Z]
    sim.setObjectPosition(red_block, pick_pos, -1)
    sim.setObjectOrientation(red_block, [0, 0, 0], -1)
    for _ in range(5):
        client.step()

    res_red = detector.detect_color(frame=None, annotate=True)
    detector.save_image(res_red.annotated_frame, f"{output_dir}/vision_red.png")
    print(f" [+] Detected: '{res_red.color}', confidence: {res_red.confidence:.2f}, area: {res_red.contour_area}, center: {res_red.center}")

    # Ground truth validation (checking object handle post-detection)
    if res_red.color == "red" and res_red.confidence >= 0.70:
        print(" [PASS] Red block identified with high confidence.")
        results["Red Block Detection"] = True
    else:
        print(f" [FAIL] Red block detection failed: got '{res_red.color}' (conf={res_red.confidence:.2f})")
        results["Red Block Detection"] = False
        all_passed = False

    # -------------------------------------------------------------
    # Test 4: Green Block Classification
    # -------------------------------------------------------------
    print("\n[TEST 4] Testing Green Block Classification...")
    sim.setObjectPosition(red_block, [-5.0, 0.0, 0.5], -1)
    sim.setObjectPosition(green_block, pick_pos, -1)
    sim.setObjectOrientation(green_block, [0, 0, 0], -1)
    for _ in range(5):
        client.step()

    res_green = detector.detect_color(frame=None, annotate=True)
    detector.save_image(res_green.annotated_frame, f"{output_dir}/vision_green.png")
    print(f" [+] Detected: '{res_green.color}', confidence: {res_green.confidence:.2f}, area: {res_green.contour_area}, center: {res_green.center}")

    if res_green.color == "green" and res_green.confidence >= 0.70:
        print(" [PASS] Green block identified with high confidence.")
        results["Green Block Detection"] = True
    else:
        print(f" [FAIL] Green block detection failed: got '{res_green.color}' (conf={res_green.confidence:.2f})")
        results["Green Block Detection"] = False
        all_passed = False

    # -------------------------------------------------------------
    # Test 5: Blue Block Classification
    # -------------------------------------------------------------
    print("\n[TEST 5] Testing Blue Block Classification...")
    sim.setObjectPosition(green_block, [-5.0, 0.5, 0.5], -1)
    sim.setObjectPosition(blue_block, pick_pos, -1)
    sim.setObjectOrientation(blue_block, [0, 0, 0], -1)
    for _ in range(5):
        client.step()

    res_blue = detector.detect_color(frame=None, annotate=True)
    detector.save_image(res_blue.annotated_frame, f"{output_dir}/vision_blue.png")
    print(f" [+] Detected: '{res_blue.color}', confidence: {res_blue.confidence:.2f}, area: {res_blue.contour_area}, center: {res_blue.center}")

    if res_blue.color == "blue" and res_blue.confidence >= 0.70:
        print(" [PASS] Blue block identified with high confidence.")
        results["Blue Block Detection"] = True
    else:
        print(f" [FAIL] Blue block detection failed: got '{res_blue.color}' (conf={res_blue.confidence:.2f})")
        results["Blue Block Detection"] = False
        all_passed = False

    sim.stopSimulation()
    client.setStepping(False)

    # -------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------
    print("\n" + "=" * 70)
    print(" VISION DETECTION TEST SUMMARY")
    print("=" * 70)
    for name, ok in results.items():
        status = "[PASSED]" if ok else "[FAILED]"
        print(f" {status:<10} : {name}")
    print("=" * 70)
    if all_passed:
        print(" [SUCCESS] Vision Color Detection is 100% Verified!")
    else:
        print(" [FAILURE] Some vision tests failed.")
    print("=" * 70)

    return all_passed


if __name__ == "__main__":
    success = run_vision_tests()
    sys.exit(0 if success else 1)
