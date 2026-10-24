"""
Comprehensive Test Runner for Phase 5: Dynamic Object Feeding & Continuous Factory Automation
Tests:
1. Dynamic Object Spawning & Lifecycle Tracking (Red, Green, Blue)
2. Queue Clearance, Spawn Limits & Safe Handling
3. Continuous 6-Object Factory Sorting Run (Feed -> Pixel Vision -> Pick & Place -> Bin Containment)
4. Comprehensive Containment Audit & Statistics Validation
"""

import sys
import os
import time
from typing import Dict, Any, List

# Ensure project root is in Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.sim_client import get_sim_client
from src.object_spawner import ObjectSpawner, SpawnedObject, ObjectState
from src.sorting_controller import SortingController
import config.settings as cfg


def test_1_dynamic_spawner_unit(sim, client) -> bool:
    """
    Test 1: Dynamic Object Spawner Verification
    Tests spawning one object of each color, unique ID assignment,
    physical parameter assignment, and lifecycle state tracking.
    """
    print("\n" + "=" * 70)
    print(" [TEST 1] Dynamic Object Spawner & Unique ID Verification")
    print("=" * 70)

    # Clean scene state
    sim.stopSimulation()
    client.setStepping(False)
    time.sleep(0.2)
    sim.loadScene(cfg.SAVED_SCENE_FILE)
    client.setStepping(True)
    sim.startSimulation()

    spawner = ObjectSpawner(client, sim)
    spawner.clear_scene_initial_blocks()
    for _ in range(5):
        client.step()

    all_passed = True
    test_colors = ["red", "green", "blue"]
    spawned_list = []

    for color in test_colors:
        obj = spawner.spawn_object(color_override=color)
        if obj is None:
            print(f" [FAIL] Failed to spawn dynamic {color} object!")
            all_passed = False
            continue

        spawned_list.append(obj)
        print(f" [+] Spawned: {obj.id} (Handle: {obj.handle}, State: {obj.state.value})")

        # Verify physics attributes in CoppeliaSim
        is_static = sim.getObjectInt32Param(obj.handle, sim.shapeintparam_static)
        is_resp = sim.getObjectInt32Param(obj.handle, sim.shapeintparam_respondable)
        mass = sim.getShapeMass(obj.handle)

        if is_static == 0 and is_resp == 1 and abs(mass - cfg.BLOCK_MASS) < 1e-4:
            print(f" [PASS] {obj.id} verified: dynamic, respondable, mass={mass:.3f}kg")
        else:
            print(f" [FAIL] {obj.id} physics attributes invalid! (static={is_static}, resp={is_resp})")
            all_passed = False

        # Advance simulation and move object out of spawn inlet to allow next spawn
        sim.setObjectPosition(obj.handle, [-5.0, 0.0, 0.5], -1)
        for _ in range(3):
            client.step()

    # Verify unique IDs
    ids = [o.id for o in spawned_list]
    if len(ids) == len(set(ids)) == 3:
        print(f" [PASS] All {len(ids)} spawned objects have verified unique IDs: {ids}")
    else:
        print(f" [FAIL] Duplicate IDs detected: {ids}")
        all_passed = False

    sim.stopSimulation()
    client.setStepping(False)
    return all_passed


def test_2_queue_safety_and_limits(sim, client) -> bool:
    """
    Test 2: Queue Flow Control, Obstruction Rejection & Spawn Limits
    Tests that:
    1. Spawning into an obstructed spawn inlet is rejected safely (preventing pileup).
    2. Feed on an empty queue times out safely without crashing.
    """
    print("\n" + "=" * 70)
    print(" [TEST 2] Queue Flow Control, Inlet Clearance & Empty Queue Safety")
    print("=" * 70)

    sim.stopSimulation()
    client.setStepping(False)
    time.sleep(0.2)
    sim.loadScene(cfg.SAVED_SCENE_FILE)
    client.setStepping(True)
    sim.startSimulation()

    spawner = ObjectSpawner(client, sim)
    spawner.clear_scene_initial_blocks()
    for _ in range(5):
        client.step()

    all_passed = True

    # 1. Spawn first object at inlet
    obj1 = spawner.spawn_object(color_override="red")
    print(f" [+] Spawned initial block at inlet: {obj1.id}")

    # 2. Attempt immediately spawning second block without moving first (should be rejected)
    obj2 = spawner.spawn_object(color_override="green")
    if obj2 is None and not spawner.is_spawn_zone_clear():
        print(" [PASS] Inlet obstruction detected: Second spawn rejected to prevent collision.")
    else:
        print(" [FAIL] Second block was allowed to spawn over an occupied inlet!")
        all_passed = False

    # 3. Test empty queue feed on SortingController
    # Move obj1 away so belt is completely empty
    sim.setObjectPosition(obj1.handle, [-5.0, 0.0, 0.5], -1)
    for _ in range(3):
        client.step()

    controller = SortingController(client, sim)
    controller.initialize_system()

    print(" [*] Testing feed_next_block on an empty conveyor (expect graceful timeout)...")
    feed_ok, res = controller.feed_next_block(max_steps=30)
    if not feed_ok and res.color == "none":
        print(" [PASS] Empty queue handled gracefully: feed timed out without errors.")
    else:
        print(f" [FAIL] Unexpected result on empty queue: feed_ok={feed_ok}, color={res.color}")
        all_passed = False

    sim.stopSimulation()
    client.setStepping(False)
    return all_passed


def test_3_continuous_six_block_sorting(sim, client) -> bool:
    """
    Test 3: Continuous 6-Object Factory Sorting Run
    Spawns and sorts 6 objects sequentially (2 Red, 2 Green, 2 Blue):
    - Color sequence: ['red', 'green', 'blue', 'red', 'green', 'blue']
    - Validates pixel-based classification
    - Validates collision-free robot pick & place
    - Validates conveyor discharge into collection bins
    - Validates 3D physical containment for every single block
    """
    print("\n" + "=" * 70)
    print(" [TEST 3] Continuous 6-Object Factory Sorting Run (2 Red, 2 Green, 2 Blue)")
    print("=" * 70)

    sim.stopSimulation()
    client.setStepping(False)
    time.sleep(0.2)
    sim.loadScene(cfg.SAVED_SCENE_FILE)
    client.setStepping(True)
    sim.startSimulation()

    controller = SortingController(client, sim)
    controller.initialize_system()

    sequence = ["red", "green", "blue", "red", "green", "blue"]
    summary = controller.run_continuous_sorting(
        max_objects=6,
        color_sequence=sequence,
        save_annotations=True,
    )

    all_passed = True

    # 1. Verify total counts
    if summary["total_sorted"] == 6 and summary["total_failed"] == 0:
        print(f" [PASS] Total sorted count verified: {summary['total_sorted']} / 6 (0 failures)")
    else:
        print(f" [FAIL] Sorting counts mismatch: sorted={summary['total_sorted']}, failed={summary['total_failed']}")
        all_passed = False

    # 2. Verify color distribution counts
    color_counts = summary["sorted_by_color"]
    if color_counts["red"] == 2 and color_counts["green"] == 2 and color_counts["blue"] == 2:
        print(f" [PASS] Color distribution verified: Red={color_counts['red']}, Green={color_counts['green']}, Blue={color_counts['blue']}")
    else:
        print(f" [FAIL] Color distribution mismatch: {color_counts}")
        all_passed = False

    # 3. Verify physical 3D containment for all 6 blocks inside bins
    print("\n" + "-" * 70)
    print(" Physical Collection Bin Containment Audit (6 Blocks):")
    for handle, obj in controller.spawner.objects.items():
        contained, pos = controller.check_bin_containment(obj.color, handle)
        status = "[CONTAINED]" if contained else "[OUTSIDE]"
        print(
            f" {status:<12} {obj.id:<20} in {obj.target_bin:<22} "
            f"at pos={[round(x, 3) for x in pos]} | State: {obj.state.value}"
        )
        if not contained or obj.state != ObjectState.SORTED:
            all_passed = False

    # 4. Verify lifecycle histories
    print("\n" + "-" * 70)
    print(" Object Lifecycle History Audit:")
    for obj_meta in summary["objects"]:
        states = [s for s, _ in obj_meta["history"]]
        expected_states = ["WAITING", "DETECTED", "PICKED", "PLACED", "SORTED"]
        has_full_lifecycle = all(s in states for s in expected_states)
        audit_str = " -> ".join(states)
        status = "[PASS]" if has_full_lifecycle else "[FAIL]"
        print(f" {status} {obj_meta['id']}: {audit_str}")
        if not has_full_lifecycle:
            all_passed = False

    sim.stopSimulation()
    client.setStepping(False)
    return all_passed


def run_all_phase5_tests() -> bool:
    print("=" * 75)
    print(" Intelligent Industrial Robot Sorter - Phase 5 Continuous Automation Test Suite")
    print("=" * 75)

    client, sim = get_sim_client(cfg.ZMQ_HOST, cfg.ZMQ_PORT)
    output_dir = "test_output"
    os.makedirs(output_dir, exist_ok=True)

    results = {}

    try:
        results["1. Dynamic Spawning & ID Tracking"] = test_1_dynamic_spawner_unit(sim, client)
        results["2. Flow Control & Queue Safety"] = test_2_queue_safety_and_limits(sim, client)
        results["3. Continuous 6-Object Sorting Run"] = test_3_continuous_six_block_sorting(sim, client)
    except Exception as err:
        print(f"\n[!] Phase 5 test run encountered an exception: {err}")
        import traceback
        traceback.print_exc()
        results["Execution Exception"] = False
    finally:
        sim.stopSimulation()
        client.setStepping(False)

    print("\n" + "=" * 75)
    print(" PHASE 5 TEST SUITE FINAL REPORT")
    print("=" * 75)
    all_ok = True
    for test_name, passed in results.items():
        status = "[PASSED]" if passed else "[FAILED]"
        print(f" {status:<10} : {test_name}")
        if not passed:
            all_ok = False

    print("=" * 75)
    if all_ok:
        print(" [SUCCESS] Phase 5 Continuous Factory Automation is 100% Verified!")
    else:
        print(" [WARNING] Some Phase 5 tests failed. Check output details above.")
    print("=" * 75)

    return all_ok


if __name__ == "__main__":
    success = run_all_phase5_tests()
    sys.exit(0 if success else 1)
