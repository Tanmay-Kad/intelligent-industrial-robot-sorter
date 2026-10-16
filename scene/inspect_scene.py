"""
Scene Inspector for CoppeliaSim
Queries and displays all scene objects, types, positions, and hierarchical relationships.
"""

import sys
import os

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from core.sim_client import get_sim_client


OBJECT_TYPE_NAMES = {
    0: "Shape",
    1: "Joint",
    2: "Graph",
    3: "Camera",
    4: "Dummy",
    5: "ProximitySensor",
    6: "Octree",
    7: "PointCloud",
    9: "VisionSensor",
    11: "ForceSensor",
    12: "Light",
    13: "Mirror",
    17: "Script",
}


def inspect_scene():
    client, sim = get_sim_client()
    print("=" * 70)
    print(" CoppeliaSim Scene Object Hierarchy & Inspection")
    print("=" * 70)

    try:
        handles = sim.getObjectsInTree(sim.handle_scene)
    except Exception as err:
        print(f"[!] Error retrieving scene objects: {err}")
        return []

    print(f"Total objects found in scene: {len(handles)}\n")
    print(f"{'Handle':<8} {'Type':<18} {'Position (X, Y, Z)':<25} {'Alias / Path'}")
    print("-" * 70)

    objects_summary = []
    for h in handles:
        try:
            alias = sim.getObjectAlias(h, 3)
            obj_type = sim.getObjectType(h)
            type_str = OBJECT_TYPE_NAMES.get(obj_type, f"Type_{obj_type}")
            pos = sim.getObjectPosition(h, -1)
            pos_str = f"[{pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f}]"
            print(f"{h:<8} {type_str:<18} {pos_str:<25} {alias}")
            objects_summary.append({
                "handle": h,
                "type": type_str,
                "type_id": obj_type,
                "position": pos,
                "alias": alias
            })
        except Exception:
            pass

    print("-" * 70)
    
    # Analyze if this is the default empty scene
    user_objects = [
        obj for obj in objects_summary 
        if not any(k in obj["alias"] for k in ["Camera", "Light", "Floor", "box"])
    ]
    
    print("\n[Scene Assessment]")
    if not user_objects:
        print(" -> Scene is DEFAULT / EMPTY (contains only default Floor, Lights, and Cameras).")
        print(" -> No robot arm, conveyors, or sorting objects exist yet.")
    else:
        print(f" -> Scene contains {len(user_objects)} custom objects/components:")
        for u in user_objects[:10]:
            print(f"    - {u['alias']} ({u['type']})")
        if len(user_objects) > 10:
            print(f"    ... and {len(user_objects) - 10} more.")
            
    print("=" * 70)
    return objects_summary


if __name__ == "__main__":
    inspect_scene()
