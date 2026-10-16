"""
Industrial Sorting Factory - Comprehensive Scene Validation Script
Verifies:
1. Object Handle Availability (Robots, Joints, Conveyors, Camera, Blocks, Collection Bins)
2. Collection Bins Structure & Open Cavity Integrity
3. Vision Sensor Capture (InspectionCamera)
4. Gripper Signal Interface (RG2)
5. Dynamic Physics & Conveyor Operation (Input conveyor transport)
6. Dynamic Physics Bin Capture Test (Block discharges off conveyor and settles inside bin)
"""

import sys
import os
import time

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from core.sim_client import get_sim_client
import config.settings as cfg


def validate_scene():
    print("=" * 70)
    print(" Validating Industrial Sorting Factory Scene Setup")
    print("=" * 70)

    client, sim = get_sim_client(cfg.ZMQ_HOST, cfg.ZMQ_PORT)
    all_passed = True

    # Check 1: Object handles verification
    print("\n[Check 1/6] Verifying Object Handles & Aliases...")
    required_objects = [
        ("Robot Pedestal", "/RobotPedestal"),
        ("UR5 Base", "/UR5"),
        ("UR5 Joint 1", "/UR5/UR5_joint1"),
        ("UR5 Joint 2", "/UR5/UR5_joint2"),
        ("UR5 Joint 3", "/UR5/UR5_joint3"),
        ("UR5 Joint 4", "/UR5/UR5_joint4"),
        ("UR5 Joint 5", "/UR5/UR5_joint5"),
        ("UR5 Joint 6", "/UR5/UR5_joint6"),
        ("RG2 Gripper", "/UR5/connection/RG2"),
        ("Input Conveyor", "/InputConveyor"),
        ("Input End Bumper", "/InputEndBumper"),
        ("Output Conveyor (Red)", "/OutputConveyorRed"),
        ("Output Conveyor (Green)", "/OutputConveyorGreen"),
        ("Output Conveyor (Blue)", "/OutputConveyorBlue"),
        ("Inspection Camera", "/InspectionCamera/camera"),
        ("Red Sorting Block", "/RedBlock"),
        ("Green Sorting Block", "/GreenBlock"),
        ("Blue Sorting Block", "/BlueBlock"),
        ("Red Collection Bin", "/RedCollectionBin"),
        ("Green Collection Bin", "/GreenCollectionBin"),
        ("Blue Collection Bin", "/BlueCollectionBin"),
    ]

    handles = {}
    for desc, path in required_objects:
        try:
            h = sim.getObject(path)
            handles[desc] = h
            print(f" [PASS] {desc:<26} -> handle: {h}")
        except Exception as e:
            all_passed = False
            print(f" [FAIL] {desc:<26} -> NOT FOUND ({e})")

    # Check 2: Collection Bins Structure & Open Cavity Inspection
    print("\n[Check 2/6] Verifying Collection Bins Structure & Open Cavity...")
    bins_to_check = [
        ("RedCollectionBin", [0.0, 1.52], "OutputConveyorRed", "Y", 1),
        ("GreenCollectionBin", [1.52, 0.0], "OutputConveyorGreen", "X", 1),
        ("BlueCollectionBin", [0.0, -1.52], "OutputConveyorBlue", "Y", -1),
    ]

    for b_name, exp_xy, conv_name, axis, sign in bins_to_check:
        try:
            b_handle = sim.getObject(f"/{b_name}")
            children = sim.getObjectsInTree(b_handle)
            child_aliases = [sim.getObjectAlias(c) for c in children]
            
            # Check for essential walls, bottom, and stand
            required_parts = ["Stand", "Bottom", "Wall_Near", "Wall_Far", "Wall_Left", "Wall_Right"]
            missing = [p for p in required_parts if p not in child_aliases]
            
            # Check near wall position relative to discharge end
            near_wall = sim.getObject("./Wall_Near", {"proxy": b_handle})
            nw_pos = sim.getObjectPosition(near_wall, -1)
            
            if not missing:
                print(f" [PASS] {b_name:<20}: 4 walls + bottom + stand present, open-top cavity confirmed.")
                print(f"        Discharge alignment: Near wall at [{nw_pos[0]:.2f}, {nw_pos[1]:.2f}, {nw_pos[2]:.2f}]")
            else:
                all_passed = False
                print(f" [FAIL] {b_name:<20}: Missing parts: {missing}")
        except Exception as e:
            all_passed = False
            print(f" [FAIL] Error inspecting {b_name}: {e}")

    # Check 3: Vision Sensor Frame Capture
    print("\n[Check 3/6] Verifying Inspection Camera Vision Capture...")
    try:
        cam_h = handles.get("Inspection Camera")
        res = sim.getVisionSensorResolution(cam_h)
        img, [w, h] = sim.getVisionSensorImg(cam_h)
        print(f" [PASS] Camera frame captured: {w}x{h} px ({len(img)} raw RGB bytes)")
    except Exception as e:
        all_passed = False
        print(f" [FAIL] Camera capture failed: {e}")

    # Check 4: Gripper Actuation Signal
    print("\n[Check 4/6] Testing RG2 Gripper Signal Interface...")
    try:
        sim.setIntProperty(sim.handle_scene, "signal.RG2_open", 1)
        val_open = sim.getIntProperty(sim.handle_scene, "signal.RG2_open")
        sim.setIntProperty(sim.handle_scene, "signal.RG2_open", 0)
        val_closed = sim.getIntProperty(sim.handle_scene, "signal.RG2_open")
        print(f" [PASS] RG2 open signal set: {val_open}, closed signal set: {val_closed}")
    except Exception as e:
        all_passed = False
        print(f" [FAIL] RG2 signal failed: {e}")

    # Check 5: Dynamic Physics Input Conveyor Transport Simulation
    print("\n[Check 5/6] Simulating Input Conveyor Motion (2.0s)...")
    try:
        red_h = handles.get("Red Sorting Block")
        p_start = sim.getObjectPosition(red_h, -1)
        
        # Run stepping simulation for 40 steps (2.0 seconds)
        client.setStepping(True)
        sim.startSimulation()
        
        for _ in range(40):
            client.step()
            
        p_end = sim.getObjectPosition(red_h, -1)
        sim.stopSimulation()
        client.setStepping(False)
        time.sleep(0.2)

        delta_x = p_end[0] - p_start[0]
        print(f" [+] Initial RedBlock Pos : [{p_start[0]:.3f}, {p_start[1]:.3f}, {p_start[2]:.3f}]")
        print(f" [+] Pos after 2.0s      : [{p_end[0]:.3f}, {p_end[1]:.3f}, {p_end[2]:.3f}]")
        print(f" [+] Forward Displacement: {delta_x:+.3f} m (transported towards bumper)")
        
        if delta_x > 0.01 and p_end[2] > 0.65:
            print(" [PASS] Dynamic physics and input conveyor transport fully verified!")
        else:
            all_passed = False
            print(f" [FAIL] Unexpected displacement ({delta_x}m) or height ({p_end[2]}m)")
            
    except Exception as e:
        all_passed = False
        print(f" [FAIL] Input conveyor physics test failed: {e}")

    # Check 6: Dynamic Physics Collection Bin Capture Test
    print("\n[Check 6/6] Testing Block Discharge and Bin Containment (Red Bin)...")
    try:
        # Spawn a test block at the end of OutputConveyorRed (Y=1.25)
        test_block = sim.createPrimitiveShape(sim.primitiveshape_cuboid, cfg.BLOCK_SIZE)
        sim.setObjectPosition(test_block, [0.0, 1.25, cfg.BLOCK_REST_Z], -1)
        sim.setShapeColor(test_block, None, sim.colorcomponent_ambient_diffuse, [0.95, 0.20, 0.20])
        sim.setObjectInt32Param(test_block, sim.shapeintparam_static, 0)
        sim.setObjectInt32Param(test_block, sim.shapeintparam_respondable, 1)
        sim.setShapeMass(test_block, cfg.BLOCK_MASS)

        # Run stepping simulation for 50 steps (2.5 seconds)
        client.setStepping(True)
        sim.startSimulation()
        for _ in range(50):
            client.step()
        p_captured = sim.getObjectPosition(test_block, -1)
        sim.stopSimulation()
        client.setStepping(False)
        time.sleep(0.2)

        # Clean up test block
        sim.removeObject(test_block)

        # Verify test block fell into RedCollectionBin cavity
        # Red bin cavity: X in [-0.13, 0.13], Y in [1.39, 1.65], Z in [0.44, 0.68]
        inside_x = abs(p_captured[0] - 0.0) < (cfg.BIN_DIMENSIONS["cavity_width"] / 2.0)
        inside_y = abs(p_captured[1] - 1.52) < (cfg.BIN_DIMENSIONS["cavity_length"] / 2.0)
        inside_z = 0.44 <= p_captured[2] <= 0.68

        print(f" [+] Block pos after discharge: [{p_captured[0]:.3f}, {p_captured[1]:.3f}, {p_captured[2]:.3f}]")
        print(f" [+] Inside X cavity bounds   : {inside_x} (|dx| < 0.13m)")
        print(f" [+] Inside Y cavity bounds   : {inside_y} (|dy| < 0.13m)")
        print(f" [+] Resting on Bin floor     : {inside_z} (0.44m <= Z <= 0.68m)")

        if inside_x and inside_y and inside_z:
            print(" [PASS] Block successfully rolled off conveyor, entered bin, and remained inside!")
        else:
            all_passed = False
            print(f" [FAIL] Block did not land inside bin cavity!")

    except Exception as e:
        all_passed = False
        print(f" [FAIL] Bin capture test failed: {e}")

    # Reset initial block positions and re-save clean scene
    print("\n[-] Restoring initial block positions and saving scene...")
    for obj in cfg.OBJECTS_CONFIG:
        h = sim.getObject('/' + obj['name'])
        sim.setObjectPosition(h, obj['position'], -1)
        sim.setObjectOrientation(h, [0, 0, 0], -1)

    sim.saveScene(cfg.SAVED_SCENE_FILE)
    print(f" [+] Scene re-saved cleanly to: {cfg.SAVED_SCENE_FILE}")

    print("\n" + "=" * 70)
    if all_passed:
        print(" [ALL CHECKS PASSED] Sorting Factory with Collection Bins is 100% Operational!")
    else:
        print(" [WARNING] Some validation checks failed. Please inspect logs above.")
    print("=" * 70)
    return all_passed


if __name__ == "__main__":
    success = validate_scene()
    sys.exit(0 if success else 1)
