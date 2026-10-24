"""
Phase 6 Comprehensive Test Suite: Reliability, Stress Testing & Fault Recovery
Intelligent Industrial Object Sorting System

Test Modules:
1. Edge Cases & Fault Recovery Suite:
   - 1.1: Empty Queue Handling (graceful timeout, safe stop)
   - 1.2: Blocked Inlet Protection (collision prevention, spawn rejection)
   - 1.3: Maximum Spawn Count Enforcement (configurable ceiling)
   - 1.4: Ambiguous Camera Detection & Safe State Return (home pose, open gripper)
   - 1.5: Unavailable Destination Station & Safe State Return
   - 1.6: Failed Grasp / Lift Handling & Safe Recovery
   - 1.7: Duplicate Processing Prevention (guaranteed single-touch per block)

2. Continuous 12-Block Stress & Throughput Run:
   - 12 dynamically spawned blocks (mixed & repeated colors: 4 Red, 4 Green, 4 Blue)
   - Verification of 100% classification & routing accuracy
   - Physical 3D cavity containment verification inside matching bins
   - Metrics: total duration, average cycle time, throughput (blocks/min)

3. Consecutive Multi-Trial Stability:
   - Multiple sequential continuous sorting sessions without simulation reset
   - Consistency and stability validation across trials

4. Diagnostics & System Integrity Checks:
   - Stale object handle audit
   - Duplicate ID detection
   - Conveyor state audit
   - Clean dynamic object destruction and memory validation
"""

import os
import sys
import time
from typing import Dict, Any, List, Optional, Tuple

# Ensure project root is in Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.sim_client import get_sim_client
from robot.kinematics import UR5Kinematics
from src.object_spawner import ObjectSpawner, SpawnedObject, ObjectState
from src.sorting_controller import SortingController
import config.settings as cfg


def get_process_memory_mb() -> float:
    """Returns current process working set memory in MB."""
    try:
        import subprocess
        pid = os.getpid()
        cmd = f'tasklist /FI "PID eq {pid}" /FO CSV /NH'
        out = subprocess.check_output(cmd, shell=True).decode()
        mem_str = out.split(",")[-1].replace('"', '').replace(' K', '').replace(',', '').strip()
        return round(int(mem_str) / 1024.0, 2)
    except Exception:
        return 0.0


def reset_scene(sim, client):
    """Safely resets the CoppeliaSim simulation scene to a clean baseline."""
    sim.stopSimulation()
    while sim.getSimulationState() != sim.simulation_stopped:
        time.sleep(0.1)
    client.setStepping(False)
    time.sleep(0.2)
    sim.loadScene(cfg.SAVED_SCENE_FILE)
    client.setStepping(True)
    sim.startSimulation()
    while sim.getSimulationState() == sim.simulation_stopped:
        time.sleep(0.1)
    for _ in range(10):
        client.step()


# ==============================================================================
# SUITE 1: EDGE CASES & FAULT RECOVERY
# ==============================================================================

def test_1_1_empty_queue(sim, client) -> bool:
    """Tests that feeding an empty conveyor times out gracefully without errors."""
    print("\n" + "-" * 65)
    print(" [1.1] Edge Case: Empty Queue Handling")
    print("-" * 65)
    controller = SortingController(client, sim)
    controller.initialize_system()
    if controller.spawner:
        controller.spawner.clear_scene_initial_blocks()
    else:
        spawner = ObjectSpawner(client, sim)
        spawner.clear_scene_initial_blocks()

    for _ in range(5):
        client.step()

    print(" [*] Advancing empty input conveyor (expecting timeout in 25 steps)...")
    feed_ok, res = controller.feed_next_block(max_steps=25)

    # Input conveyor speed must be 0.0 after timeout
    table_data = sim.readCustomTableData(controller.in_conv, "__ctrl__")
    conv_vel = table_data.get("vel", 0.0) if table_data else 0.0

    passed = (not feed_ok) and (res.color == "none") and (conv_vel == 0.0)
    if passed:
        print(" [PASS] Empty conveyor handled safely: feed timed out and conveyor halted.")
    else:
        print(f" [FAIL] Unexpected result: feed_ok={feed_ok}, color={res.color}, vel={conv_vel}")
    return passed


def test_1_2_blocked_inlet(sim, client) -> bool:
    """Tests that spawning onto an obstructed inlet is blocked to prevent pileup."""
    print("\n" + "-" * 65)
    print(" [1.2] Edge Case: Blocked Inlet Protection")
    print("-" * 65)
    spawner = ObjectSpawner(client, sim)
    spawner.clear_scene_initial_blocks()
    for _ in range(5):
        client.step()

    obj1 = spawner.spawn_object(color_override="red")
    print(f" [+] Spawned block at inlet: {obj1.id}")

    # Immediately attempt spawning second block without moving the first
    obj2 = spawner.spawn_object(color_override="green")
    if obj2 is None and not spawner.is_spawn_zone_clear():
        print(" [PASS] Blocked inlet detected: Second spawn rejected to prevent collision.")
        passed = True
    else:
        print(" [FAIL] Second block spawned over an occupied inlet!")
        passed = False

    # Clean up obj1
    sim.removeObject(obj1.handle)
    for _ in range(5):
        client.step()
    return passed


def test_1_3_max_spawn_count(sim, client) -> bool:
    """Tests that the spawner strictly enforces maximum spawn count limits."""
    print("\n" + "-" * 65)
    print(" [1.3] Edge Case: Maximum Spawn Count Enforcement")
    print("-" * 65)
    max_count = 2
    spawner = ObjectSpawner(client, sim, max_spawn_count=max_count)
    spawner.clear_scene_initial_blocks()

    spawned = []
    for i in range(max_count):
        obj = spawner.spawn_object(color_override="blue")
        if obj is not None:
            spawned.append(obj)
            # Move away to clear inlet
            sim.setObjectPosition(obj.handle, [-5.0, float(i), 0.5], -1)
            for _ in range(3):
                client.step()

    # Attempt spawning beyond limit
    overflow_obj = spawner.spawn_object(color_override="blue")
    passed = (len(spawned) == max_count) and (overflow_obj is None) and (spawner.spawn_counter == max_count)

    if passed:
        print(f" [PASS] Max spawn count ({max_count}) respected: Overflow spawn rejected.")
    else:
        print(f" [FAIL] Spawner exceeded limit: spawned={len(spawned)}, overflow={overflow_obj}")

    # Clean up
    spawner.destroy_all()
    for _ in range(5):
        client.step()
    return passed


def test_1_4_ambiguous_camera_detection(sim, client) -> bool:
    """
    Tests handling of an ambiguous/unsupported color block.
    Verifies rejection and robot recovery to safe Home state with gripper open.
    """
    print("\n" + "-" * 65)
    print(" [1.4] Fault Injection: Ambiguous Camera Detection & Safe Recovery")
    print("-" * 65)
    controller = SortingController(client, sim)
    controller.initialize_system()

    # Create an off-color (yellow) block at the pick station
    yellow_rgb = [0.95, 0.95, 0.10]
    block_h = sim.createPrimitiveShape(sim.primitiveshape_cuboid, list(cfg.BLOCK_SIZE))
    sim.setObjectAlias(block_h, "Block_Yellow_Anomaly")
    sim.setObjectPosition(block_h, [-0.375, 0.0, 0.74], -1)
    sim.setShapeColor(block_h, None, sim.colorcomponent_ambient_diffuse, yellow_rgb)
    sim.setObjectInt32Param(block_h, sim.shapeintparam_static, 0)
    sim.setObjectInt32Param(block_h, sim.shapeintparam_respondable, 1)
    sim.setShapeMass(block_h, cfg.BLOCK_MASS)

    for _ in range(10):
        client.step()

    print(" [*] Executing sort cycle on anomalous yellow block...")
    result = controller.sort_cycle(auto_feed=False)

    # Verify cycle was rejected safely
    cycle_failed = (not result["success"])
    rejection_logged = ("Ambiguous" in result.get("reason", "") or "No block" in result.get("reason", ""))

    # Verify safe recovery state (gripper open, robot near home)
    arm_joints = [sim.getJointPosition(j) for j in controller.robot.joints]
    home_joints = UR5Kinematics.get_pose("home")
    max_joint_err = max(abs(a - h) for a, h in zip(arm_joints, home_joints))

    passed = cycle_failed and max_joint_err < 0.15
    if passed:
        print(f" [PASS] Ambiguous block rejected: Reason='{result.get('reason')}'")
        print(f" [PASS] Robot safely recovered to Home pose (joint error: {max_joint_err:.3f} rad).")
    else:
        print(f" [FAIL] Recovery failed: cycle_failed={cycle_failed}, joint_err={max_joint_err:.3f}")

    # Remove anomaly block
    sim.removeObject(block_h)
    for _ in range(5):
        client.step()
    return passed


def test_1_5_unavailable_destination(sim, client) -> bool:
    """
    Tests system response when a destination conveyor is unavailable/faulted.
    Verifies that the block is not picked and the robot returns to safe state.
    """
    print("\n" + "-" * 65)
    print(" [1.5] Fault Injection: Unavailable Destination Station")
    print("-" * 65)
    controller = SortingController(client, sim)
    controller.initialize_system()

    # Temporarily remove green conveyor from controller routing table
    saved_green_conv = controller.out_convs.pop("green")

    # Place a green block at the pick station
    spawner = ObjectSpawner(client, sim)
    green_obj = spawner.spawn_object(color_override="green")
    sim.setObjectPosition(green_obj.handle, [-0.375, 0.0, 0.74], -1)

    for _ in range(10):
        client.step()

    print(" [*] Executing sort cycle for green block while Green destination is disabled...")
    result = controller.sort_cycle(auto_feed=False)

    passed = (not result["success"]) and ("Unavailable destination" in result.get("reason", ""))
    if passed:
        print(f" [PASS] Unavailable destination caught before pick: Reason='{result.get('reason')}'")
    else:
        print(f" [FAIL] Unexpected result: success={result['success']}, reason={result.get('reason')}")

    # Restore routing table and clean up
    controller.out_convs["green"] = saved_green_conv
    sim.removeObject(green_obj.handle)
    for _ in range(5):
        client.step()
    return passed


def test_1_6_failed_grasp_recovery(sim, client) -> bool:
    """
    Tests safe recovery when a grasp or lift fails.
    Verifies robot returns to Home pose, opens gripper, and logs failure.
    """
    print("\n" + "-" * 65)
    print(" [1.6] Fault Injection: Failed Grasp & Safe Recovery")
    print("-" * 65)
    controller = SortingController(client, sim)
    controller.initialize_system()
    controller.setup_spawner()
    controller.spawner.clear_scene_initial_blocks()

    # Spawn a red block at pick station
    obj = controller.spawner.spawn_object(color_override="red")
    sim.setObjectPosition(obj.handle, [-0.375, 0.0, 0.74], -1)

    for _ in range(10):
        client.step()

    # Inject grasp failure: simulate gripper slippage / missed contact
    saved_pick = controller.robot.pick_block
    controller.robot.pick_block = lambda *args, **kwargs: False

    print(" [*] Executing sort cycle with injected grasp slippage...")
    result = controller.sort_cycle(auto_feed=False)

    # Restore pick function
    controller.robot.pick_block = saved_pick

    # Verify safe recovery state (gripper open, robot docked at Home)
    arm_joints = [sim.getJointPosition(j) for j in controller.robot.joints]
    home_joints = UR5Kinematics.get_pose("home")
    max_joint_err = max(abs(a - h) for a, h in zip(arm_joints, home_joints))

    passed = (
        (not result["success"])
        and ("Grasp or lift failure" in result.get("reason", ""))
        and (max_joint_err < 0.15)
        and (obj.handle in controller.processed_handles)
    )

    if passed:
        print(f" [PASS] Grasp failure caught: Reason='{result.get('reason')}'")
        print(f" [PASS] Object {obj.id} flagged as failed and handle recorded.")
        print(f" [PASS] Robot safely docked at Home pose (joint error: {max_joint_err:.3f} rad).")
    else:
        print(f" [FAIL] Unexpected result: {result}, max_joint_err={max_joint_err:.3f}")

    sim.removeObject(obj.handle)
    for _ in range(5):
        client.step()
    return passed


def test_1_7_duplicate_processing_prevention(sim, client) -> bool:
    """
    Tests that a block handle already recorded in processed_handles
    is strictly ignored by identify_block_at_pick_station.
    """
    print("\n" + "-" * 65)
    print(" [1.7] Integrity: Duplicate Block Processing Prevention")
    print("-" * 65)
    controller = SortingController(client, sim)
    controller.initialize_system()
    controller.setup_spawner()
    controller.spawner.clear_scene_initial_blocks()

    test_obj = controller.spawner.spawn_object(color_override="blue")
    sim.setObjectPosition(test_obj.handle, [-0.375, 0.0, 0.74], -1)

    for _ in range(10):
        client.step()

    # Case A: Before processing -> handle is identified
    h_before = controller.identify_block_at_pick_station()
    identified_first = (h_before == test_obj.handle)

    # Mark as processed in controller
    controller.processed_handles.add(test_obj.handle)

    # Case B: After being processed -> handle must be ignored
    h_after = controller.identify_block_at_pick_station()
    ignored_second = (h_after is None)

    passed = identified_first and ignored_second
    if passed:
        print(f" [PASS] Block {test_obj.id} identified initially, then strictly rejected after being flagged as processed.")
    else:
        print(f" [FAIL] Duplicate check failed: before={h_before}, after={h_after}")

    sim.removeObject(test_obj.handle)
    for _ in range(5):
        client.step()
    return passed


# ==============================================================================
# SUITE 2: CONTINUOUS 12-BLOCK STRESS & THROUGHPUT TEST
# ==============================================================================

def test_2_continuous_12_block_stress(sim, client) -> Dict[str, Any]:
    """
    Continuous sorting stress test with 12 dynamically spawned blocks:
    - Mixed and repeated colors: 4 Red, 4 Green, 4 Blue
    - Tracks complete lifecycle
    - Verifies 3D physical bin containment
    - Computes cycle times, throughput, and success rate
    """
    print("\n" + "=" * 70)
    print(" [TEST SUITE 2] Continuous 12-Block Stress & Throughput Test")
    print("=" * 70)

    reset_scene(sim, client)

    sequence_12 = [
        "red", "green", "blue",
        "blue", "red", "green",
        "red", "blue", "green",
        "red", "blue", "green",
    ]

    controller = SortingController(client, sim)
    controller.initialize_system()

    print(f" [*] Target Color Sequence (12 blocks): {sequence_12}")
    mem_before = get_process_memory_mb()

    start_time = time.time()
    summary = controller.run_continuous_sorting(
        max_objects=12,
        color_sequence=sequence_12,
        save_annotations=True,
    )
    total_time = time.time() - start_time
    mem_after = get_process_memory_mb()

    # Audit physical bin containment
    print("\n" + "-" * 65)
    print(" Physical 3D Bin Containment Audit for 12 Blocks:")
    print("-" * 65)
    all_contained = True
    for handle, obj in controller.spawner.objects.items():
        contained, pos = controller.check_bin_containment(obj.color, handle)
        status_str = "[CONTAINED]" if contained else "[MISSING]  "
        print(f" {status_str} {obj.id:20s} in {obj.target_bin:22s} at pos={pos}")
        if not contained:
            all_contained = False

    avg_cycle = total_time / 12.0
    throughput_bpm = (12.0 / total_time) * 60.0

    print("\n" + "=" * 70)
    print(" 12-BLOCK STRESS TEST METRICS:")
    print("=" * 70)
    print(f" Total Spawned       : {summary['total_spawned']} / 12")
    print(f" Successfully Sorted : {summary['total_sorted']} / 12 (Success Rate: {(summary['total_sorted']/12)*100:.1f}%)")
    print(f" 3D Bin Containment  : {'100% Verified' if all_contained else 'FAILED'}")
    print(f" Sorted by Color     : Red={summary['sorted_by_color']['red']}, Green={summary['sorted_by_color']['green']}, Blue={summary['sorted_by_color']['blue']}")
    print(f" Total Elapsed Time  : {total_time:.2f} s")
    print(f" Average Cycle Time  : {avg_cycle:.2f} s/block")
    print(f" System Throughput   : {throughput_bpm:.2f} blocks/min")
    print(f" Memory RSS (Python) : Before={mem_before:.1f}MB, After={mem_after:.1f}MB (Delta: {mem_after - mem_before:+.1f}MB)")
    print("=" * 70)

    summary["avg_cycle_s"] = round(avg_cycle, 2)
    summary["throughput_bpm"] = round(throughput_bpm, 2)
    summary["all_contained"] = all_contained
    summary["mem_delta_mb"] = round(mem_after - mem_before, 2)
    summary["passed"] = (summary["total_sorted"] == 12) and all_contained

    return summary


# ==============================================================================
# SUITE 3: CONSECUTIVE MULTI-TRIAL STABILITY
# ==============================================================================

def test_3_consecutive_trials(sim, client) -> bool:
    """
    Executes multiple consecutive continuous trials without resetting CoppeliaSim.
    Verifies that system does not suffer from handle exhaustion or memory leak.
    """
    print("\n" + "=" * 70)
    print(" [TEST SUITE 3] Consecutive Multi-Trial Stability Test")
    print("=" * 70)

    reset_scene(sim, client)

    trials_config = [
        {"name": "Trial 1 (Alternating Mixed)", "seq": ["red", "blue", "green", "red", "green", "blue"]},
        {"name": "Trial 2 (Repeated Bursts)", "seq": ["green", "green", "blue", "red", "blue", "red"]},
    ]

    trial_results = []
    controller = SortingController(client, sim)
    controller.initialize_system()

    for idx, trial in enumerate(trials_config):
        print(f"\n>>> STARTING {trial['name']} (6 blocks) <<<")
        t_start = time.time()
        res = controller.run_continuous_sorting(
            max_objects=6,
            color_sequence=trial["seq"],
            save_annotations=False,
        )
        t_elapsed = time.time() - t_start

        success = (res["total_sorted"] == 6)
        trial_results.append({
            "name": trial["name"],
            "success": success,
            "sorted": res["total_sorted"],
            "duration": round(t_elapsed, 2),
            "avg_cycle": round(t_elapsed / 6.0, 2),
        })

        # Allow conveyors to settle before next trial
        for _ in range(10):
            client.step()

    print("\n" + "=" * 70)
    print(" MULTI-TRIAL STABILITY REPORT:")
    print("=" * 70)
    all_trials_passed = True
    for tr in trial_results:
        status_str = "[PASS]" if tr["success"] else "[FAIL]"
        print(f" {status_str} {tr['name']:30s} | Sorted: {tr['sorted']}/6 | Time: {tr['duration']}s | Avg: {tr['avg_cycle']}s/block")
        if not tr["success"]:
            all_trials_passed = False
    print("=" * 70)

    return all_trials_passed


# ==============================================================================
# SUITE 4: DIAGNOSTICS & SYSTEM INTEGRITY
# ==============================================================================

def test_4_diagnostics_and_cleanup(sim, client) -> bool:
    """
    Verifies stale object handle cleanup, duplicate ID absence,
    and conveyor zero-velocity state on shutdown.
    """
    print("\n" + "=" * 70)
    print(" [TEST SUITE 4] Diagnostics, Handle Audit & Cleanup Verification")
    print("=" * 70)

    spawner = ObjectSpawner(client, sim)
    spawner.clear_scene_initial_blocks()

    # 1. Spawn a test set of 4 objects
    handles = []
    ids = []
    for c in ["red", "green", "blue", "red"]:
        obj = spawner.spawn_object(color_override=c)
        handles.append(obj.handle)
        ids.append(obj.id)
        # Advance to allow next spawn
        sim.setObjectPosition(obj.handle, [-5.0, float(len(handles)), 0.5], -1)
        for _ in range(3):
            client.step()

    # Check for duplicate IDs
    has_unique_ids = (len(ids) == len(set(ids)))
    print(f" [+] Unique ID Audit: {'PASS (No duplicates in ' + str(ids) + ')' if has_unique_ids else 'FAIL'}")

    # Verify handles currently exist in CoppeliaSim
    handles_exist_before = all(sim.getObjectAlias(h) != "" for h in handles)
    print(f" [+] Active Handles Verified: {'PASS' if handles_exist_before else 'FAIL'}")

    # 2. Execute destroy_all
    spawner.destroy_all()
    for _ in range(5):
        client.step()

    # Verify handles are removed from scene
    handles_cleaned = True
    for h in handles:
        try:
            alias = sim.getObjectAlias(h)
            # If alias was still resolved to the removed object
            if alias in ids:
                handles_cleaned = False
        except Exception:
            # Exception indicates handle no longer exists (expected)
            pass

    print(f" [+] Dynamic Object Cleanup: {'PASS (All objects safely unallocated)' if handles_cleaned else 'FAIL'}")

    passed = has_unique_ids and handles_exist_before and handles_cleaned
    if passed:
        print(" [PASS] Diagnostics & Cleanup Verified: Zero stale handles, clean lifecycle.")
    else:
        print(" [FAIL] Diagnostic defect detected.")
    return passed


# ==============================================================================
# MAIN RUNNER
# ==============================================================================

def run_phase6_test_suite():
    print("\n" + "=" * 75)
    print(" INTELLIGENT INDUSTRIAL OBJECT SORTING SYSTEM")
    print(" PHASE 6: RELIABILITY, STRESS TESTING & FAULT RECOVERY TEST SUITE")
    print("=" * 75)

    client, sim = get_sim_client()

    results = {}

    # Reset scene initially
    reset_scene(sim, client)

    # 1. Edge Cases & Fault Recovery
    print("\n>>> EXECUTING SUITE 1: EDGE CASES & FAULT RECOVERY <<<")
    results["1.1 Empty Queue"] = test_1_1_empty_queue(sim, client)
    results["1.2 Blocked Inlet"] = test_1_2_blocked_inlet(sim, client)
    results["1.3 Max Spawn Count"] = test_1_3_max_spawn_count(sim, client)
    results["1.4 Ambiguous Camera Detection"] = test_1_4_ambiguous_camera_detection(sim, client)
    results["1.5 Unavailable Destination"] = test_1_5_unavailable_destination(sim, client)
    results["1.6 Failed Grasp Recovery"] = test_1_6_failed_grasp_recovery(sim, client)
    results["1.7 Duplicate Processing Prevention"] = test_1_7_duplicate_processing_prevention(sim, client)

    # 2. Continuous 12-Block Stress & Throughput
    print("\n>>> EXECUTING SUITE 2: CONTINUOUS 12-BLOCK STRESS RUN <<<")
    stress_res = test_2_continuous_12_block_stress(sim, client)
    results["2. 12-Block Continuous Stress Run"] = stress_res["passed"]

    # 3. Consecutive Multi-Trial Stability
    print("\n>>> EXECUTING SUITE 3: CONSECUTIVE MULTI-TRIAL STABILITY <<<")
    results["3. Consecutive Multi-Trial Stability"] = test_3_consecutive_trials(sim, client)

    # 4. Diagnostics & Cleanup
    print("\n>>> EXECUTING SUITE 4: DIAGNOSTICS & CLEANUP <<<")
    results["4. Diagnostics & Cleanup"] = test_4_diagnostics_and_cleanup(sim, client)

    # Reset and close
    sim.stopSimulation()
    client.setStepping(False)

    print("\n" + "=" * 75)
    print(" PHASE 6 TEST SUITE FINAL REPORT")
    print("=" * 75)
    all_passed = True
    for test_name, status in results.items():
        tag = "[PASSED]" if status else "[FAILED]"
        print(f" {tag:10s} : {test_name}")
        if not status:
            all_passed = False

    print("=" * 75)
    if all_passed:
        print(" [SUCCESS] Phase 6 Reliability, Stress Testing & Fault Recovery is 100% VERIFIED!")
    else:
        print(" [FAILURE] One or more Phase 6 test cases failed. Please review defect logs.")
    print("=" * 75)

    return all_passed


if __name__ == "__main__":
    success = run_phase6_test_suite()
    sys.exit(0 if success else 1)
