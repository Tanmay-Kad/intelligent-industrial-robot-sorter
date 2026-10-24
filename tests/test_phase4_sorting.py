"""
Comprehensive Test Runner for Phase 4: Camera-Based RGB Detection & Automated Object Sorting
Tests:
1. Camera Image Capture & Resolution Validation
2. Multi-Color Detection Quality & Threshold Verification (Empty, Red, Green, Blue)
3. Single Red-Block Automated Sorting Cycle (Vision -> Pick -> Place -> Red Bin)
4. Single Green-Block Automated Sorting Cycle (Vision -> Pick -> Place -> Green Bin)
5. Single Blue-Block Automated Sorting Cycle (Vision -> Pick -> Place -> Blue Bin)
6. Continuous Multi-Block Sequential Sorting Run (3 Blocks Feed & Sort)
"""

import sys
import os
import time
from typing import Dict, Any

# Ensure project root is in Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.sim_client import get_sim_client
from vision.color_detector import ColorDetector
from src.sorting_controller import SortingController
import config.settings as cfg


def test_1_camera_capture(sim, client, output_dir: str) -> bool:
    print("\n" + "=" * 70)
    print(" [TEST 1] Camera Image Capture and Quality Check")
    print("=" * 70)

    detector = ColorDetector(client, sim)
    ok, frame = detector.capture_frame()

    if not ok or frame is None:
        print(" [FAIL] Failed to capture frame from /InspectionCamera")
        return False

    h, w, c = frame.shape
    print(f" [+] Frame acquired successfully: {w}x{h} px, {c} channels, dtype={frame.dtype}")
    
    save_path = os.path.join(output_dir, "test1_camera_capture.png")
    detector.save_image(frame, save_path)
    print(f" [+] Raw frame saved to: {save_path}")

    if w == 128 and h == 128 and c == 3:
        print(" [PASS] Test 1: Camera capture verified.")
        return True
    else:
        print(f" [FAIL] Unexpected frame dimensions: {frame.shape}")
        return False


def test_2_color_detection_static(sim, client, output_dir: str) -> bool:
    print("\n" + "=" * 70)
    print(" [TEST 2] Color Detection & Classification Quality (Real Camera Frames)")
    print("=" * 70)

    detector = ColorDetector(client, sim)
    red_block = sim.getObject("/RedBlock")
    green_block = sim.getObject("/GreenBlock")
    blue_block = sim.getObject("/BlueBlock")
    in_conv = sim.getObject("/InputConveyor")

    # Halt input conveyor
    sim.writeCustomTableData(in_conv, "__ctrl__", {"vel": 0.0})

    # Park all blocks outside FOV initially
    sim.setObjectPosition(red_block, [-5.0, 0.0, 0.5], -1)
    sim.setObjectPosition(green_block, [-5.0, 0.5, 0.5], -1)
    sim.setObjectPosition(blue_block, [-5.0, -0.5, 0.5], -1)
    for _ in range(5):
        client.step()

    test_colors = [
        ("Empty", None, "none", True),
        ("Red", red_block, "red", False),
        ("Green", green_block, "green", False),
        ("Blue", blue_block, "blue", False),
    ]

    all_passed = True
    pick_pos = [-0.375, 0.0, cfg.BLOCK_REST_Z]

    for label, block_handle, expected_color, expect_empty in test_colors:
        if block_handle is not None:
            sim.setObjectPosition(block_handle, pick_pos, -1)
            sim.setObjectOrientation(block_handle, [0, 0, 0], -1)
            for _ in range(5):
                client.step()

        res = detector.detect_color(annotate=True)
        img_path = os.path.join(output_dir, f"test2_detect_{label.lower()}.png")
        if res.annotated_frame is not None:
            detector.save_image(res.annotated_frame, img_path)

        # Remove tested block
        if block_handle is not None:
            sim.setObjectPosition(block_handle, [-5.0, 0.0, 0.5], -1)
            for _ in range(3):
                client.step()

        if expect_empty:
            if not res.detected and res.color == "none":
                print(f" [PASS] Empty Station: Correctly classified as '{res.color}' (0 false positives)")
            else:
                print(f" [FAIL] Empty Station: False positive detected as '{res.color}'")
                all_passed = False
        else:
            correct = (res.color == expected_color and res.confidence >= 0.75)
            if correct:
                print(
                    f" [PASS] {label:<6} Block: Classified as '{res.color}' "
                    f"(Conf: {res.confidence*100:.1f}%, Area: {res.contour_area}px, Center: {res.center})"
                )
            else:
                print(f" [FAIL] {label:<6} Block: Expected '{expected_color}', got '{res.color}' (conf={res.confidence})")
                all_passed = False

    return all_passed


def test_single_color_cycle(sim, client, target_color: str, output_dir: str) -> bool:
    print("\n" + "=" * 70)
    print(f" [TEST] Single {target_color.capitalize()}-Block Automated Sorting Cycle")
    print("=" * 70)

    # Reload clean scene
    sim.stopSimulation()
    client.setStepping(False)
    time.sleep(0.2)
    sim.loadScene(cfg.SAVED_SCENE_FILE)

    client.setStepping(True)
    sim.startSimulation()

    sorter = SortingController(client, sim)
    sorter.initialize_system()

    target_block = sorter.blocks[target_color]
    other_colors = [c for c in sorter.SUPPORTED_COLORS if c != target_color]

    # Park other blocks away so only target color is tested
    for c in other_colors:
        sim.setObjectPosition(sorter.blocks[c], [-5.0, 0.0, 0.5], -1)

    # Position target block at pickup station
    pick_pos = [-0.375, 0.0, cfg.BLOCK_REST_Z]
    sim.setObjectPosition(target_block, pick_pos, -1)
    sim.setObjectOrientation(target_block, [0, 0, 0], -1)
    for _ in range(5):
        client.step()

    annotation_path = os.path.join(output_dir, f"cycle_{target_color}.png")
    result = sorter.sort_cycle(auto_feed=False, save_annotation_path=annotation_path)

    # Audit ground truth vs vision
    correct_color = (result["color"] == target_color)
    contained = result["contained"]

    if result["success"] and correct_color and contained:
        print(f" [PASS] {target_color.capitalize()}-block cycle succeeded!")
        print(f"        Vision decision: '{result['color']}' | Final pos: {result['final_position']}")
        return True
    else:
        print(f" [FAIL] {target_color.capitalize()}-block cycle failed! (result: {result})")
        return False


def test_6_multi_block_sorting(sim, client, output_dir: str) -> bool:
    print("\n" + "=" * 70)
    print(" [TEST 6] Continuous Multi-Block Sequential Sorting Run (Feed -> Detect -> Sort)")
    print("=" * 70)

    # Reload clean scene with all 3 blocks in their initial positions on input conveyor
    sim.stopSimulation()
    client.setStepping(False)
    time.sleep(0.2)
    sim.loadScene(cfg.SAVED_SCENE_FILE)

    client.setStepping(True)
    sim.startSimulation()

    sorter = SortingController(client, sim)
    sorter.initialize_system()

    success = sorter.run_multi_block_sorting(target_count=3)

    print("\n" + "-" * 70)
    print(" Multi-Block Run Containment Audit:")
    for color, block_h in sorter.blocks.items():
        contained, p = sorter.check_bin_containment(color, block_h)
        status = "[CONTAINED]" if contained else "[OUTSIDE]"
        print(f" {status:<12} {color.capitalize()}Block in {color.capitalize()}CollectionBin: pos={[round(x, 3) for x in p]}")

    return success


def run_all_phase4_tests() -> bool:
    print("=" * 75)
    print(" Intelligent Industrial Robot Sorter - Phase 4 Comprehensive Test Suite")
    print("=" * 75)

    client, sim = get_sim_client(cfg.ZMQ_HOST, cfg.ZMQ_PORT)
    output_dir = "test_output"
    os.makedirs(output_dir, exist_ok=True)

    results = {}

    try:
        # Step 1: Camera capture
        sim.stopSimulation()
        client.setStepping(False)
        time.sleep(0.2)
        sim.loadScene(cfg.SAVED_SCENE_FILE)
        client.setStepping(True)
        sim.startSimulation()

        results["1. Camera Frame Capture"] = test_1_camera_capture(sim, client, output_dir)
        results["2. Multi-Color Detection"] = test_2_color_detection_static(sim, client, output_dir)

        # Steps 3-5: Single color cycles
        results["3. Red-Block Sorting Cycle"] = test_single_color_cycle(sim, client, "red", output_dir)
        results["4. Green-Block Sorting Cycle"] = test_single_color_cycle(sim, client, "green", output_dir)
        results["5. Blue-Block Sorting Cycle"] = test_single_color_cycle(sim, client, "blue", output_dir)

        # Step 6: Multi-block continuous run
        if all(results.values()):
            results["6. Multi-Block Sorting Run"] = test_6_multi_block_sorting(sim, client, output_dir)
        else:
            print("\n[!] Skipping multi-block test because a prior unit test failed.")
            results["6. Multi-Block Sorting Run"] = False

    except Exception as err:
        print(f"\n[!] Test suite encountered an exception: {err}")
        import traceback
        traceback.print_exc()
        results["Execution Error"] = False

    finally:
        sim.stopSimulation()
        client.setStepping(False)

    print("\n" + "=" * 75)
    print(" PHASE 4 TEST SUITE FINAL REPORT")
    print("=" * 75)
    all_ok = True
    for test_name, passed in results.items():
        status = "[PASSED]" if passed else "[FAILED]"
        print(f" {status:<10} : {test_name}")
        if not passed:
            all_ok = False

    print("=" * 75)
    if all_ok:
        print(" [SUCCESS] Phase 4 Camera-Based Detection & Automated Sorting is 100% Verified!")
    else:
        print(" [WARNING] Some Phase 4 tests failed. Review output above.")
    print("=" * 75)

    return all_ok


if __name__ == "__main__":
    success = run_all_phase4_tests()
    sys.exit(0 if success else 1)
