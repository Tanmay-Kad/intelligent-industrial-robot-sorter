"""
Industrial Sorting Factory - Automated Scene Builder
Builds the complete physical simulation environment in CoppeliaSim:
- UR5 Robot on mounting pedestal (Python-controlled joints, demo script removed)
- RG2 Gripper attached to UR5 connection flange
- 1 Input Conveyor with mechanical end-bumper
- 3 Color-Coded Output Conveyors (Red, Green, Blue)
- Overhead Inspection Camera with industrial mounting stand
- Dynamic Red, Green, and Blue sorting objects
- 3 Realistic Open-Top Collection Bins at conveyor discharge ends
- Saves scene to scenes/sorting_factory.ttt
"""

import sys
import os
import time
import math

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from core.sim_client import get_sim_client
import config.settings as cfg


def clean_scene_artifacts(sim):
    """Safely removes all previous custom components and any numbered duplicates."""
    clean_targets = [
        "RobotPedestal", "UR5", "RG2",
        "InputConveyor", "InputEndBumper",
        "OutputConveyorRed", "OutputConveyorGreen", "OutputConveyorBlue",
        "InspectionCamera", "CameraStand_Pole", "CameraStand_Arm",
        "RedBlock", "GreenBlock", "BlueBlock",
        "RedCollectionBin", "GreenCollectionBin", "BlueCollectionBin",
    ]
    try:
        handles = sim.getObjectsInTree(sim.handle_scene)
    except Exception:
        return

    for h in handles:
        try:
            alias = sim.getObjectAlias(h)
            for target in clean_targets:
                if alias == target or alias.startswith(target + "__"):
                    try:
                        sim.removeModel(h)
                    except Exception:
                        try:
                            sim.removeObject(h)
                        except Exception:
                            pass
                    break
        except Exception:
            pass


def build_collection_bin(sim, bin_cfg: dict, dims: dict) -> int:
    """
    Constructs a realistic open-top collection bin at the conveyor discharge end.
    Comprises a support stand, bottom floor plate, and four collision-enabled walls.
    """
    name = bin_cfg["name"]
    cx, cy, _ = bin_cfg["position"]
    color = bin_cfg["color"]
    axis = bin_cfg["axis"]
    sign = bin_cfg["sign"]

    w_int = dims["cavity_width"]
    l_int = dims["cavity_length"]
    h_w = dims["wall_height"]
    t = dims["wall_thickness"]
    z_stand = dims["stand_height"]
    stand_color = dims["stand_color"]

    # Create root model dummy for clean hierarchy management
    root = sim.createDummy(0.05)
    sim.setObjectAlias(root, name)
    sim.setModelProperty(root, 0)

    # 1. Base Stand (from floor Z=0 to bottom plate at Z=z_stand)
    stand = sim.createPrimitiveShape(sim.primitiveshape_cuboid, [0.26, 0.26, z_stand])
    sim.setObjectAlias(stand, "Stand")
    sim.setObjectParent(stand, root, True)
    sim.setObjectPosition(stand, [cx, cy, z_stand / 2.0], -1)
    sim.setShapeColor(stand, None, sim.colorcomponent_ambient_diffuse, stand_color)
    sim.setObjectInt32Param(stand, sim.shapeintparam_static, 1)
    sim.setObjectInt32Param(stand, sim.shapeintparam_respondable, 1)

    # 2. Bottom plate
    bot = sim.createPrimitiveShape(sim.primitiveshape_cuboid, [w_int + 2 * t, l_int + 2 * t, t])
    sim.setObjectAlias(bot, "Bottom")
    sim.setObjectParent(bot, root, True)
    sim.setObjectPosition(bot, [cx, cy, z_stand + t / 2.0], -1)
    sim.setShapeColor(bot, None, sim.colorcomponent_ambient_diffuse, color)
    sim.setObjectInt32Param(bot, sim.shapeintparam_static, 1)
    sim.setObjectInt32Param(bot, sim.shapeintparam_respondable, 1)

    # 3. Four walls with open interior cavity
    z_wall = z_stand + t + h_w / 2.0

    if axis == "Y":
        # Discharges along Y axis: near wall is facing conveyor at (cy - sign * (l_int + t)/2)
        # Near Wall
        w_near = sim.createPrimitiveShape(sim.primitiveshape_cuboid, [w_int + 2 * t, t, h_w])
        sim.setObjectAlias(w_near, "Wall_Near")
        sim.setObjectParent(w_near, root, True)
        sim.setObjectPosition(w_near, [cx, cy - sign * (l_int + t) / 2.0, z_wall], -1)
        sim.setShapeColor(w_near, None, sim.colorcomponent_ambient_diffuse, color)
        sim.setObjectInt32Param(w_near, sim.shapeintparam_static, 1)
        sim.setObjectInt32Param(w_near, sim.shapeintparam_respondable, 1)

        # Far Wall
        w_far = sim.createPrimitiveShape(sim.primitiveshape_cuboid, [w_int + 2 * t, t, h_w])
        sim.setObjectAlias(w_far, "Wall_Far")
        sim.setObjectParent(w_far, root, True)
        sim.setObjectPosition(w_far, [cx, cy + sign * (l_int + t) / 2.0, z_wall], -1)
        sim.setShapeColor(w_far, None, sim.colorcomponent_ambient_diffuse, color)
        sim.setObjectInt32Param(w_far, sim.shapeintparam_static, 1)
        sim.setObjectInt32Param(w_far, sim.shapeintparam_respondable, 1)

        # Left Wall (-X side)
        w_l = sim.createPrimitiveShape(sim.primitiveshape_cuboid, [t, l_int, h_w])
        sim.setObjectAlias(w_l, "Wall_Left")
        sim.setObjectParent(w_l, root, True)
        sim.setObjectPosition(w_l, [cx - (w_int + t) / 2.0, cy, z_wall], -1)
        sim.setShapeColor(w_l, None, sim.colorcomponent_ambient_diffuse, color)
        sim.setObjectInt32Param(w_l, sim.shapeintparam_static, 1)
        sim.setObjectInt32Param(w_l, sim.shapeintparam_respondable, 1)

        # Right Wall (+X side)
        w_r = sim.createPrimitiveShape(sim.primitiveshape_cuboid, [t, l_int, h_w])
        sim.setObjectAlias(w_r, "Wall_Right")
        sim.setObjectParent(w_r, root, True)
        sim.setObjectPosition(w_r, [cx + (w_int + t) / 2.0, cy, z_wall], -1)
        sim.setShapeColor(w_r, None, sim.colorcomponent_ambient_diffuse, color)
        sim.setObjectInt32Param(w_r, sim.shapeintparam_static, 1)
        sim.setObjectInt32Param(w_r, sim.shapeintparam_respondable, 1)

    else:
        # Discharges along X axis: near wall is facing conveyor at (cx - sign * (l_int + t)/2)
        # Near Wall
        w_near = sim.createPrimitiveShape(sim.primitiveshape_cuboid, [t, w_int + 2 * t, h_w])
        sim.setObjectAlias(w_near, "Wall_Near")
        sim.setObjectParent(w_near, root, True)
        sim.setObjectPosition(w_near, [cx - sign * (l_int + t) / 2.0, cy, z_wall], -1)
        sim.setShapeColor(w_near, None, sim.colorcomponent_ambient_diffuse, color)
        sim.setObjectInt32Param(w_near, sim.shapeintparam_static, 1)
        sim.setObjectInt32Param(w_near, sim.shapeintparam_respondable, 1)

        # Far Wall
        w_far = sim.createPrimitiveShape(sim.primitiveshape_cuboid, [t, w_int + 2 * t, h_w])
        sim.setObjectAlias(w_far, "Wall_Far")
        sim.setObjectParent(w_far, root, True)
        sim.setObjectPosition(w_far, [cx + sign * (l_int + t) / 2.0, cy, z_wall], -1)
        sim.setShapeColor(w_far, None, sim.colorcomponent_ambient_diffuse, color)
        sim.setObjectInt32Param(w_far, sim.shapeintparam_static, 1)
        sim.setObjectInt32Param(w_far, sim.shapeintparam_respondable, 1)

        # Left Wall (+Y side)
        w_l = sim.createPrimitiveShape(sim.primitiveshape_cuboid, [l_int, t, h_w])
        sim.setObjectAlias(w_l, "Wall_Left")
        sim.setObjectParent(w_l, root, True)
        sim.setObjectPosition(w_l, [cx, cy + (w_int + t) / 2.0, z_wall], -1)
        sim.setShapeColor(w_l, None, sim.colorcomponent_ambient_diffuse, color)
        sim.setObjectInt32Param(w_l, sim.shapeintparam_static, 1)
        sim.setObjectInt32Param(w_l, sim.shapeintparam_respondable, 1)

        # Right Wall (-Y side)
        w_r = sim.createPrimitiveShape(sim.primitiveshape_cuboid, [l_int, t, h_w])
        sim.setObjectAlias(w_r, "Wall_Right")
        sim.setObjectParent(w_r, root, True)
        sim.setObjectPosition(w_r, [cx, cy - (w_int + t) / 2.0, z_wall], -1)
        sim.setShapeColor(w_r, None, sim.colorcomponent_ambient_diffuse, color)
        sim.setObjectInt32Param(w_r, sim.shapeintparam_static, 1)
        sim.setObjectInt32Param(w_r, sim.shapeintparam_respondable, 1)

    return root


def build_scene():
    print("=" * 70)
    print(" Building Industrial Sorting Factory Scene in CoppeliaSim")
    print("=" * 70)

    client, sim = get_sim_client(cfg.ZMQ_HOST, cfg.ZMQ_PORT)
    
    # Ensure simulation is stopped before modifying scene
    state = sim.getSimulationState()
    if state != sim.simulation_stopped:
        print("[*] Stopping active simulation...")
        sim.stopSimulation()
        time.sleep(0.3)

    # Clean previous custom components to ensure clean, non-duplicate rebuild
    print("[*] Checking for previous setup artifacts to clean...")
    clean_scene_artifacts(sim)

    created_components = {}

    # 1. Build Robot Pedestal
    print("\n[1/8] Building Robot Pedestal...")
    ped_cfg = cfg.LAYOUT["pedestal"]
    ped_handle = sim.createPrimitiveShape(sim.primitiveshape_cuboid, ped_cfg["size"])
    sim.setObjectAlias(ped_handle, "RobotPedestal")
    sim.setObjectPosition(ped_handle, ped_cfg["position"], -1)
    sim.setShapeColor(ped_handle, None, sim.colorcomponent_ambient_diffuse, ped_cfg["color"])
    sim.setObjectInt32Param(ped_handle, sim.shapeintparam_static, 1)
    sim.setObjectInt32Param(ped_handle, sim.shapeintparam_respondable, 1)
    created_components["RobotPedestal"] = ped_handle
    print(f" [+] Created RobotPedestal at {ped_cfg['position']}")

    # 2. Load and Mount UR5 Robot
    print("\n[2/8] Loading and Mounting UR5 Manipulator...")
    ur5_path = cfg.MODEL_PATHS["ur5"]
    if not os.path.exists(ur5_path):
        raise FileNotFoundError(f"UR5 model not found at: {ur5_path}")
    
    ur5_handle = sim.loadModel(ur5_path)
    sim.setObjectAlias(ur5_handle, "UR5")
    sim.setObjectPosition(ur5_handle, cfg.LAYOUT["robot"]["position"], -1)
    
    # Remove hard-coded demo script on UR5 so Python has exclusive control
    for child in sim.getObjectsInTree(ur5_handle):
        if sim.getObjectType(child) == sim.object_script_type:
            sim.removeObject(child)
            print(" [+] Removed UR5 built-in demo script (Python has full control)")

    # Name individual joints UR5_joint1 .. UR5_joint6 and set home angles
    joints = [c for c in sim.getObjectsInTree(ur5_handle) if sim.getObjectType(c) == sim.object_joint_type]
    for i, j in enumerate(joints):
        sim.setObjectAlias(j, f"UR5_joint{i+1}")
        angle = cfg.LAYOUT["robot"]["home_joint_angles"][i]
        sim.setJointPosition(j, angle)
        sim.setJointTargetPosition(j, angle)
    
    created_components["UR5"] = ur5_handle
    print(f" [+] UR5 loaded, mounted on pedestal at {cfg.LAYOUT['robot']['position']}")
    print(f" [+] Configured {len(joints)} joints to home pose (/UR5/UR5_joint1 to UR5_joint6)")

    # 3. Mount RG2 Gripper
    print("\n[3/8] Mounting RG2 Parallel Jaw Gripper...")
    rg2_path = cfg.MODEL_PATHS["rg2"]
    if not os.path.exists(rg2_path):
        raise FileNotFoundError(f"RG2 model not found at: {rg2_path}")
    
    conn_handle = sim.getObject("./connection", {"proxy": ur5_handle})
    rg2_handle = sim.loadModel(rg2_path)
    sim.setObjectAlias(rg2_handle, "RG2")
    sim.setObjectParent(rg2_handle, conn_handle, True)
    sim.setObjectPosition(rg2_handle, [0, 0, 0], conn_handle)
    sim.setObjectOrientation(rg2_handle, [0, 0, 0], conn_handle)
    created_components["RG2"] = rg2_handle
    print(f" [+] RG2 Gripper mounted directly onto UR5 connection flange")

    # 4. Create Conveyor Belts (1 Input + 3 Color-Coded Outputs)
    print("\n[4/8] Loading and Positioning 4 Conveyor Belts...")
    conveyor_path = cfg.MODEL_PATHS["conveyor"]
    if not os.path.exists(conveyor_path):
        raise FileNotFoundError(f"Conveyor model not found at: {conveyor_path}")

    conveyor_configs = [
        cfg.LAYOUT["input_conveyor"],
        cfg.LAYOUT["output_red"],
        cfg.LAYOUT["output_green"],
        cfg.LAYOUT["output_blue"],
    ]

    for c_cfg in conveyor_configs:
        c_handle = sim.loadModel(conveyor_path)
        name = c_cfg["name"]
        sim.setObjectAlias(c_handle, name)
        sim.setObjectPosition(c_handle, c_cfg["position"], -1)
        sim.setObjectOrientation(c_handle, c_cfg["orientation"], -1)
        
        # Color the side rail frame (visible2 shape)
        try:
            rail = sim.getObject("./visible2", {"proxy": c_handle})
            sim.setShapeColor(rail, None, sim.colorcomponent_ambient_diffuse, c_cfg["rail_color"])
        except Exception:
            pass

        # Set target velocity in conveyor table data
        try:
            sim.writeCustomTableData(c_handle, '__ctrl__', {'vel': c_cfg.get('target_vel', 0.12)})
        except Exception:
            pass
            
        created_components[name] = c_handle
        print(f" [+] Configured {name:<18} at {c_cfg['position']} (ori: {c_cfg['orientation']})")

    # 5. Build Input Conveyor Mechanical Bumper
    print("\n[5/8] Creating Input Conveyor End Bumper...")
    bmp_cfg = cfg.LAYOUT["input_bumper"]
    bmp_handle = sim.createPrimitiveShape(sim.primitiveshape_cuboid, bmp_cfg["size"])
    sim.setObjectAlias(bmp_handle, bmp_cfg["name"])
    sim.setObjectPosition(bmp_handle, bmp_cfg["position"], -1)
    sim.setShapeColor(bmp_handle, None, sim.colorcomponent_ambient_diffuse, bmp_cfg["color"])
    sim.setObjectInt32Param(bmp_handle, sim.shapeintparam_static, 1)
    sim.setObjectInt32Param(bmp_handle, sim.shapeintparam_respondable, 1)
    created_components[bmp_cfg["name"]] = bmp_handle
    print(f" [+] Mechanical Bumper placed at {bmp_cfg['position']}")

    # 6. Overhead Inspection Camera & Stand
    print("\n[6/8] Mounting Inspection Camera & Structural Stand...")
    cam_cfg = cfg.LAYOUT["camera"]
    stand_cfg = cfg.LAYOUT["camera_stand"]
    
    # Stand Pole
    pole = sim.createPrimitiveShape(sim.primitiveshape_cuboid, stand_cfg["pole_size"])
    sim.setObjectAlias(pole, "CameraStand_Pole")
    sim.setObjectPosition(pole, stand_cfg["pole_pos"], -1)
    sim.setShapeColor(pole, None, sim.colorcomponent_ambient_diffuse, stand_cfg["color"])
    sim.setObjectInt32Param(pole, sim.shapeintparam_static, 1)
    sim.setObjectInt32Param(pole, sim.shapeintparam_respondable, 1)
    
    # Stand Arm
    arm = sim.createPrimitiveShape(sim.primitiveshape_cuboid, stand_cfg["arm_size"])
    sim.setObjectAlias(arm, "CameraStand_Arm")
    sim.setObjectPosition(arm, stand_cfg["arm_pos"], -1)
    sim.setShapeColor(arm, None, sim.colorcomponent_ambient_diffuse, stand_cfg["color"])
    sim.setObjectInt32Param(arm, sim.shapeintparam_static, 1)
    sim.setObjectInt32Param(arm, sim.shapeintparam_respondable, 1)

    # Blob detection camera
    cam_model_path = cfg.MODEL_PATHS["camera"]
    cam_handle = sim.loadModel(cam_model_path)
    sim.setObjectAlias(cam_handle, cam_cfg["name"])
    sim.setObjectPosition(cam_handle, cam_cfg["position"], -1)
    sim.setObjectOrientation(cam_handle, cam_cfg["orientation"], -1)
    created_components[cam_cfg["name"]] = cam_handle
    print(f" [+] Overhead Inspection Camera aligned at {cam_cfg['position']} pointing down")

    # 7. Create Red, Green, and Blue Sorting Blocks
    print("\n[7/8] Spawning 3D Sorting Objects (Red, Green, Blue)...")
    for obj_data in cfg.OBJECTS_CONFIG:
        block_h = sim.createPrimitiveShape(sim.primitiveshape_cuboid, cfg.BLOCK_SIZE)
        sim.setObjectAlias(block_h, obj_data["name"])
        sim.setObjectPosition(block_h, obj_data["position"], -1)
        sim.setShapeColor(block_h, None, sim.colorcomponent_ambient_diffuse, obj_data["color"])
        
        # Make dynamic & respondable
        sim.setObjectInt32Param(block_h, sim.shapeintparam_static, 0)
        sim.setObjectInt32Param(block_h, sim.shapeintparam_respondable, 1)
        sim.setShapeMass(block_h, cfg.BLOCK_MASS)
        created_components[obj_data["name"]] = block_h
        print(f" [+] Spawned {obj_data['name']:<12} at {obj_data['position']} (color: {obj_data['color']})")

    # 8. Build 3 Realistic Open-Top Collection Bins
    print("\n[8/8] Building 3 Realistic Open-Top Collection Bins (Red, Green, Blue)...")
    for b_cfg in cfg.BINS_CONFIG:
        bin_handle = build_collection_bin(sim, b_cfg, cfg.BIN_DIMENSIONS)
        created_components[b_cfg["name"]] = bin_handle
        print(f" [+] Constructed {b_cfg['name']:<20} at {b_cfg['position']} (discharge for {b_cfg['conveyor_name']})")

    # Save scene to scenes/sorting_factory.ttt
    print("\n" + "-" * 70)
    print(" Saving Scene File...")
    os.makedirs(cfg.SCENES_DIR, exist_ok=True)
    save_result = sim.saveScene(cfg.SAVED_SCENE_FILE)
    
    if save_result == 1 and os.path.exists(cfg.SAVED_SCENE_FILE):
        file_size_kb = os.path.getsize(cfg.SAVED_SCENE_FILE) / 1024.0
        print(f" [SUCCESS] Scene saved successfully to:")
        print(f"   -> {cfg.SAVED_SCENE_FILE} ({file_size_kb:.1f} KB)")
    else:
        print(f" [!] Notice: sim.saveScene returned {save_result}.")
        print("     If your CoppeliaSim requires GUI save, press Ctrl+S in the CoppeliaSim window.")

    print("=" * 70)
    print(f" Scene construction complete! Total primary components added: {len(created_components)}")
    print("=" * 70)
    return created_components


if __name__ == "__main__":
    build_scene()
