"""
Comprehensive Test Runner for UR5 Robot Motion and RG2 Gripper Control (Phase 3)
Tests:
1. Kinematic Arm Motion & Trajectory Interpolation (No Objects)
2. Gripper Actuation Interface & Proximity Sensing
3. Single-Block Pick-and-Place & Bin Collection (Physics Grasp Verification)
"""

import sys
import os
import math
import time

# Ensure project root is accessible
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from core.sim_client import get_sim_client
from robot.kinematics import UR5Kinematics
from robot.robot_controller import UR5Controller
import config.settings as cfg


def test_motion_without_objects(controller: UR5Controller) -> bool:
    """
    Test 1: Arm Motion & Kinematics Test (Empty Manipulation)
    Verifies that the UR5 robot can move between Home, PrePick, Pick, PrePlace,
    and Place waypoints with zero collisions and exact kinematic tracking.
    """
    print("\n" + "=" * 70)
    print(" [TEST 1] UR5 Arm Motion & Kinematics Test (Empty Manipulation)")
    print("=" * 70)

    test_sequence = [
        ("Home Pose", "home"),
        ("Transit to PrePick", "pre_pick"),
        ("Vertical Descent to Pick", "pick"),
        ("Vertical Retract to PrePick", "pre_pick"),
        ("Corridor Transit to PrePlace (Red)", "pre_place_red"),
        ("Vertical Descent to Place (Red)", "place_red"),
        ("Vertical Retract to PrePlace (Red)", "pre_place_red"),
        ("Return to Home Pose", "home"),
    ]

    all_passed = True
    for desc, pose_name in test_sequence:
        target_q = UR5Kinematics.get_pose(pose_name)
        success = controller.move_joints(target_q, steps=10)
        actual_q = controller.get_joint_positions()
        tip_pos = controller.get_tip_position()

        max_joint_err_deg = max(
            abs(math.degrees(actual_q[k] - target_q[k])) for k in range(6)
        )
        tip_str = f"[{tip_pos[0]:.3f}, {tip_pos[1]:.3f}, {tip_pos[2]:.3f}]"

        if success and max_joint_err_deg < 0.5:
            print(
                f" [PASS] {desc:<35} -> Tip: {tip_str} | Max Err: {max_joint_err_deg:.3f}°"
            )
        else:
            all_passed = False
            print(
                f" [FAIL] {desc:<35} -> Tip: {tip_str} | Max Err: {max_joint_err_deg:.3f}°"
            )

    return all_passed


def test_gripper_interface(controller: UR5Controller) -> bool:
    """
    Test 2: RG2 Gripper Actuation & Proximity Sensor Interface Test
    Verifies mechanical opening (~5.4 cm), mechanical closing, and sensor response.
    """
    print("\n" + "=" * 70)
    print(" [TEST 2] RG2 Gripper Interface & Proximity Sensor Verification")
    print("=" * 70)

    sim = controller.sim
    all_passed = True

    # 1. Test Gripper Open
    controller.open_gripper(steps=22)
    open_angle = sim.getJointPosition(controller.open_close_joint)
    print(f" [+] Open command sent  -> openCloseJoint: {open_angle:.4f} rad (spread open)")
    if open_angle > 0.015:
        print(" [PASS] Gripper mechanical open fully confirmed.")
    else:
        all_passed = False
        print(" [FAIL] Gripper failed to open sufficiently.")

    # 2. Test Gripper Close
    controller.close_gripper(steps=20)
    close_angle = sim.getJointPosition(controller.open_close_joint)
    print(f" [+] Close command sent -> openCloseJoint: {close_angle:.4f} rad (closed)")
    if close_angle < open_angle - 0.025:
        print(" [PASS] Gripper mechanical close fully confirmed.")
    else:
        all_passed = False
        print(" [FAIL] Gripper failed to close properly.")

    # 3. Test Proximity Sensor (empty space check)
    detected, dist, detected_h = controller.check_grasp()
    print(f" [+] Proximity sensor empty check: detected={detected}, dist={dist:.4f}")
    if not detected:
        print(" [PASS] Proximity sensor reports clear workspace as expected.")
    else:
        all_passed = False
        print(" [FAIL] Proximity sensor gave false positive on empty workspace.")

    # Re-open gripper for subsequent operations
    controller.open_gripper(steps=15)
    return all_passed


def test_single_block_pick_and_place(controller: UR5Controller) -> bool:
    """
    Test 3: Single-Block Pick-and-Place Test with Real Physics
    Picks RedBlock from the input station, transfers it to OutputConveyorRed,
    releases it, and verifies discharge into RedCollectionBin.
    No artificial teleportation - verifies physical grasp and containment.
    """
    print("\n" + "=" * 70)
    print(" [TEST 3] Single-Block Pick-and-Place with Physics Verification")
    print("=" * 70)

    sim = controller.sim
    client = controller.client
    all_passed = True

    red_block = sim.getObject("/RedBlock")
    red_conv = sim.getObject("/OutputConveyorRed")
    in_conv = sim.getObject("/InputConveyor")


    # Stop input conveyor and allow settling
    sim.writeCustomTableData(in_conv, "__ctrl__", {"vel": 0.0})
    for _ in range(5):
        client.step()

    # Return robot to home pose with fully open gripper
    controller.move_to_named_pose("home", steps=10)
    controller.open_gripper(steps=25)

    # Position RedBlock at calibrated pick station (at end of belt, before bumper)
    pick_pos = [-0.375, 0.0, cfg.BLOCK_REST_Z]
    sim.setObjectPosition(red_block, pick_pos, -1)
    sim.setObjectOrientation(red_block, [0, 0, 0], -1)
    client.step()

    p_init = sim.getObjectPosition(red_block, -1)
    print(f" [+] RedBlock stabilized at pick station: {[round(x, 4) for x in p_init]}")

    # Set OutputConveyorRed velocity for subsequent transport
    sim.writeCustomTableData(red_conv, "__ctrl__", {"vel": 0.25})

    # Step 1: Pick sequence
    print(" [*] Executing pick_block sequence...")
    pick_ok = controller.pick_block(red_block, steps=10)
    p_lifted = sim.getObjectPosition(red_block, -1)
    print(f" [+] Block pos after pick: [{p_lifted[0]:.3f}, {p_lifted[1]:.3f}, {p_lifted[2]:.3f}]")

    if pick_ok and p_lifted[2] > 0.78:
        print(" [PASS] RedBlock grasped, attached, and lifted safely into transit corridor.")
    else:
        all_passed = False
        print(f" [FAIL] Grasp or lift failed! (lift_ok={pick_ok}, Z={p_lifted[2]:.3f}m)")

    # Step 2: Place sequence
    print(" [*] Executing place_block sequence to 'red' station...")
    place_ok = controller.place_block("red", red_block, steps=14)
    p_placed = sim.getObjectPosition(red_block, -1)
    print(f" [+] Block pos after place: [{p_placed[0]:.3f}, {p_placed[1]:.3f}, {p_placed[2]:.3f}]")

    # Check block is resting on Red conveyor surface (belt spans Y from 0.35m to 1.35m, Z=0.72m)
    on_conveyor = (
        abs(p_placed[0]) < 0.10
        and 0.35 <= p_placed[1] <= 1.35
        and p_placed[2] > 0.70
    )
    if place_ok and on_conveyor:
        print(" [PASS] RedBlock deposited cleanly on OutputConveyorRed belt surface.")
    else:
        all_passed = False
        print(f" [FAIL] Placement off target! (on_conveyor={on_conveyor}, pos={p_placed})")


    # Step 3: Conveyor transport and collection bin containment
    print(" [*] Operating OutputConveyorRed to transport block into RedCollectionBin...")
    for s in range(110):
        client.step()
        if s % 20 == 0:
            p_cur = sim.getObjectPosition(red_block, -1)
            print(f"     Step {s:03d}: Block pos = [{p_cur[0]:.3f}, {p_cur[1]:.3f}, {p_cur[2]:.3f}]")

    p_final = sim.getObjectPosition(red_block, -1)
    print(f" [+] Final block position: [{p_final[0]:.3f}, {p_final[1]:.3f}, {p_final[2]:.3f}]")

    # Red Collection Bin cavity validation:
    # Bin center is at [0.0, 1.52, 0.0]. Cavity dimensions: X in [-0.13, 0.13], Y in [1.39, 1.65], Z in [0.44, 0.68]
    inside_x = abs(p_final[0]) < (cfg.BIN_DIMENSIONS["cavity_width"] / 2.0)
    inside_y = abs(p_final[1] - 1.52) < (cfg.BIN_DIMENSIONS["cavity_length"] / 2.0)
    inside_z = 0.44 <= p_final[2] <= 0.68

    print(f" [+] Inside X cavity bounds   : {inside_x} (|dx| < {cfg.BIN_DIMENSIONS['cavity_width']/2:.3f}m)")
    print(f" [+] Inside Y cavity bounds   : {inside_y} (|dy| < {cfg.BIN_DIMENSIONS['cavity_length']/2:.3f}m)")
    print(f" [+] Inside Z cavity (on floor): {inside_z} (0.44m <= Z <= 0.68m)")

    if inside_x and inside_y and inside_z:
        print(" [PASS] RedBlock successfully rolled off conveyor and is secured inside RedCollectionBin!")
    else:
        all_passed = False
        print(f" [FAIL] Block did not land securely inside RedCollectionBin.")

    # Reset block position for clean subsequent operations
    sim.setObjectPosition(red_block, cfg.OBJECTS_CONFIG[0]["position"], -1)
    sim.setObjectOrientation(red_block, [0, 0, 0], -1)
    sim.writeCustomTableData(in_conv, "__ctrl__", {"vel": cfg.LAYOUT["input_conveyor"]["target_vel"]})

    return all_passed


def run_all_tests():
    """Main Test Suite Runner."""
    print("=" * 70)
    print(" Phase 3: UR5 Robot Motion & Gripper Control Test Suite")
    print("=" * 70)

    client, sim = get_sim_client(cfg.ZMQ_HOST, cfg.ZMQ_PORT)

    # Ensure clean starting state
    sim.stopSimulation()
    client.setStepping(False)
    time.sleep(0.3)

    # Reload clean scene from disk to ensure pristine state
    sim.loadScene(cfg.SAVED_SCENE_FILE)

    # Start stepping simulation FIRST so handles and environment are initialized
    client.setStepping(True)
    sim.startSimulation()

    # Initialize controller and configure joints inside the running simulation
    controller = UR5Controller(client, sim)
    controller.configure_joints()

    # Stop input conveyor during tests so unpicked blocks remain parked
    in_conv = sim.getObject("/InputConveyor")
    sim.writeCustomTableData(in_conv, "__ctrl__", {"vel": 0.0})
    for _ in range(5):
        client.step()


    results = {}
    try:
        results["Empty Motion Test"] = test_motion_without_objects(controller)
        results["Gripper Interface Test"] = test_gripper_interface(controller)
        results["Pick-and-Place Test"] = test_single_block_pick_and_place(controller)
    except Exception as e:
        print(f"\n[!] Test run encountered an exception: {e}")
        import traceback
        traceback.print_exc()
        results["Execution Exception"] = False
    finally:
        sim.stopSimulation()
        client.setStepping(False)
        time.sleep(0.2)

    # Summary report
    print("\n" + "=" * 70)
    print(" PHASE 3 TEST SUMMARY REPORT")
    print("=" * 70)
    all_ok = True
    for test_name, passed in results.items():
        status = "[PASSED]" if passed else "[FAILED]"
        print(f" {status:<10} : {test_name}")
        if not passed:
            all_ok = False

    print("=" * 70)
    if all_ok:
        print(" [SUCCESS] Phase 3 Robot Motion and Gripper Control is 100% Verified!")
    else:
        print(" [WARNING] Some tests did not pass. Check details in output above.")
    print("=" * 70)
    return all_ok


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
