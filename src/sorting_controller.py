"""
Automated Sorting Orchestration Controller (Phase 4)
Integrates:
- /InspectionCamera Vision & OpenCV HSV Color Classification (Red, Green, Blue)
- UR5 6-DOF Robot Kinematics & High-Elbow Collision-Free Trajectories
- RG2 Gripper Parallel Jaw Mechanical Actuation & Physics Grasping
- Conveyor Belts (Input feed & 3 Color-Coded Discharge Conveyors)
- 3 Open-Top Collection Bins with Real Physics Containment Verification
"""

import sys
import os
import time
import math
from typing import Dict, Any, Optional, Tuple, List

# Ensure project root is in Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.sim_client import get_sim_client
from robot.robot_controller import UR5Controller
from vision.color_detector import ColorDetector, DetectionResult
import config.settings as cfg


class SortingController:
    """
    Automated Industrial Sorting Orchestrator.
    Manages camera-based inspection, color decision routing, robot pick-and-place,
    conveyor transport, and bin containment tracking.
    """

    SUPPORTED_COLORS = ["red", "green", "blue"]

    def __init__(
        self,
        client: Any,
        sim: Any,
        output_conveyor_vel: float = 0.25,
        input_conveyor_vel: float = 0.15,
    ):
        """
        Initializes the SortingController.
        
        Args:
            client: RemoteAPIClient instance.
            sim: CoppeliaSim sim module.
            output_conveyor_vel: Target speed for output conveyors (m/s).
            input_conveyor_vel: Target feed speed for input conveyor (m/s).
        """
        self.client = client
        self.sim = sim
        self.output_conveyor_vel = output_conveyor_vel
        self.input_conveyor_vel = input_conveyor_vel

        # Robot controller & Vision detector
        self.robot = UR5Controller(client, sim)
        self.detector = ColorDetector(client, sim)

        # Resolve scene conveyor handles
        self.in_conv = self.sim.getObject("/InputConveyor")
        self.out_convs = {
            "red": self.sim.getObject("/OutputConveyorRed"),
            "green": self.sim.getObject("/OutputConveyorGreen"),
            "blue": self.sim.getObject("/OutputConveyorBlue"),
        }

        # Resolve block handles (used only for post-classification physics & validation)
        self.blocks = {
            "red": self.sim.getObject("/RedBlock"),
            "green": self.sim.getObject("/GreenBlock"),
            "blue": self.sim.getObject("/BlueBlock"),
        }

        # Sorting statistics counters
        self.stats = {
            "red": 0,
            "green": 0,
            "blue": 0,
            "total_sorted": 0,
            "detection_failures": 0,
            "grasp_failures": 0,
            "bin_failures": 0,
        }
        self.history: List[Dict[str, Any]] = []

    def initialize_system(self):
        """Prepares robot, conveyors, and grippers for clean operational sorting."""
        print("[*] Initializing Sorting System...")
        self.robot.configure_joints()
        self.robot.move_to_named_pose("home", steps=10)
        self.robot.open_gripper(steps=20)

        # Initialize output conveyor velocities
        for color, handle in self.out_convs.items():
            self.sim.writeCustomTableData(handle, "__ctrl__", {"vel": self.output_conveyor_vel})

        # Ensure input conveyor is initially stopped
        self.sim.writeCustomTableData(self.in_conv, "__ctrl__", {"vel": 0.0})
        for _ in range(5):
            self.client.step()
        print(" [+] All subsystems initialized and verified ready.")

    def set_input_conveyor_speed(self, speed: float):
        """Sets the input conveyor velocity."""
        self.sim.writeCustomTableData(self.in_conv, "__ctrl__", {"vel": speed})

    def check_bin_containment(self, color: str, block_handle: int) -> Tuple[bool, List[float]]:
        """
        Verifies whether the block has entered and settled inside the specified collection bin.
        
        Bin geometries from config/settings.py:
        - Red:   Center [0.0,  1.52, 0.0]
        - Green: Center [1.52,  0.0, 0.0]
        - Blue:  Center [0.0, -1.52, 0.0]
        Cavity: half-width = 0.13m, floor Z in [0.44, 0.68]m.
        """
        p = self.sim.getObjectPosition(block_handle, -1)
        cavity_half = cfg.BIN_DIMENSIONS["cavity_width"] / 2.0  # 0.13m
        inside_z = 0.44 <= p[2] <= 0.68

        if color == "red":
            inside_x = abs(p[0]) < cavity_half
            inside_y = abs(p[1] - 1.52) < cavity_half
        elif color == "green":
            inside_x = abs(p[0] - 1.52) < cavity_half
            inside_y = abs(p[1]) < cavity_half
        elif color == "blue":
            inside_x = abs(p[0]) < cavity_half
            inside_y = abs(p[1] + 1.52) < cavity_half
        else:
            return False, p

        is_contained = inside_x and inside_y and inside_z
        return is_contained, p

    def identify_block_at_pick_station(self) -> Optional[int]:
        """
        Identifies which physical block is currently resting at the pick station.
        Used strictly for physical grasp attachment and ground-truth validation.
        """
        pick_station_x = -0.375
        for color, handle in self.blocks.items():
            try:
                p = self.sim.getObjectPosition(handle, -1)
                # Block must be within 0.08m of pick station and at conveyor elevation
                if abs(p[0] - pick_station_x) < 0.08 and abs(p[1]) < 0.08 and p[2] > 0.70:
                    return handle
            except Exception:
                continue
        return None

    def feed_next_block(self, max_steps: int = 120) -> Tuple[bool, DetectionResult]:
        """
        Advances the input conveyor until a block arrives at the bumper pickup station
        (image center X >= 70) and is classified by the camera with high confidence.
        
        Returns:
            (success, detection_result)
        """
        print(" [*] Feeding input conveyor to advance next block to inspection camera...")
        self.set_input_conveyor_speed(self.input_conveyor_vel)

        for step_idx in range(max_steps):
            self.client.step()

            res = self.detector.detect_color()
            # Block reaches pickup station when centroid X >= 70 (at bumper X=-0.375)
            if res.detected and res.color in self.SUPPORTED_COLORS and res.center[0] >= 70 and res.confidence >= 0.75:
                # Stop conveyor immediately so block settles at bumper
                self.set_input_conveyor_speed(0.0)
                for _ in range(5):
                    self.client.step()

                # Capture final settled frame
                res_settled = self.detector.detect_color()
                print(
                    f" [+] Block arrived & settled at bumper: Color='{res_settled.color.upper()}', "
                    f"Conf={res_settled.confidence*100:.1f}%, Center={res_settled.center}, Area={res_settled.contour_area}px (feed step {step_idx})"
                )
                return True, res_settled

        self.set_input_conveyor_speed(0.0)
        print(" [!] Feed timeout: No eligible block reached pickup station at bumper.")
        empty_res = self.detector.detect_color()
        return False, empty_res

    def sort_cycle(
        self,
        auto_feed: bool = True,
        save_annotation_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes one full automated sorting cycle:
        1. Identifies and inspects block using /InspectionCamera pixel data.
        2. Classifies color using OpenCV HSV thresholding.
        3. Routes to matching output conveyor ('red', 'green', or 'blue').
        4. Picks block using UR5 arm and RG2 gripper.
        5. Places block on corresponding output conveyor.
        6. Operates output conveyor until block rolls into matching collection bin.
        7. Verifies final containment and updates counters.
        
        Returns:
            Dict containing cycle metrics and success status.
        """
        cycle_start_time = time.time()
        print("\n" + "=" * 65)
        print(" STARTING AUTOMATED SORTING CYCLE")
        print("=" * 65)

        # 1. Vision Detection at Inspection Station
        res = self.detector.detect_color()
        # If no block or block has not arrived at bumper yet (center X < 70)
        if not res.detected or res.color == "none" or res.center[0] < 70:
            if auto_feed:
                feed_ok, res = self.feed_next_block()
                if not feed_ok:
                    self.stats["detection_failures"] += 1
                    return {"success": False, "reason": "No block reached inspection station"}
            else:
                self.stats["detection_failures"] += 1
                return {"success": False, "reason": "No block detected at pickup station"}

        detected_color = res.color
        confidence = res.confidence

        if detected_color not in self.SUPPORTED_COLORS or confidence < 0.70:
            print(f" [!] Classification rejected: color='{detected_color}', conf={confidence:.2f}")
            self.stats["detection_failures"] += 1
            return {"success": False, "reason": f"Ambiguous or unsupported color: {detected_color}"}

        print(
            f" [VISION] Decision: Target Route = '{detected_color.upper()}' "
            f"(Confidence: {confidence*100:.1f}%, Area: {res.contour_area}px)"
        )

        if save_annotation_path and res.annotated_frame is not None:
            self.detector.save_image(res.annotated_frame, save_annotation_path)

        # 2. Resolve Physical Block Handle
        block_h = self.identify_block_at_pick_station()
        if block_h is None:
            print(" [!] Error: Camera detected color, but physical block could not be resolved.")
            self.stats["grasp_failures"] += 1
            return {"success": False, "reason": "Object handle resolution failed"}

        # Ground truth check for auditing (does not influence sorting decision)
        ground_truth_alias = self.sim.getObjectAlias(block_h)
        print(f" [AUDIT] Ground Truth Scene Alias: '{ground_truth_alias}' -> Vision: '{detected_color}'")

        # 3. Pick Sequence
        print(f" [*] Picking '{detected_color}' block from input station...")
        pick_ok = self.robot.pick_block(block_h, steps=10)
        p_lifted = self.sim.getObjectPosition(block_h, -1)

        if not pick_ok or p_lifted[2] <= (cfg.CONVEYOR_SURFACE_Z + 0.05):
            print(f" [FAIL] Failed to grasp or lift block! (lift_z={p_lifted[2]:.3f}m)")
            self.stats["grasp_failures"] += 1
            return {"success": False, "reason": "Grasp or lift failure"}
        print(f" [+] Block lifted safely to corridor height: Z={p_lifted[2]:.3f}m")

        # 4. Place Sequence to Matching Output Conveyor
        print(f" [*] Transporting and depositing onto 'OutputConveyor{detected_color.capitalize()}'...")
        place_ok = self.robot.place_block(detected_color, block_h, steps=14)
        p_placed = self.sim.getObjectPosition(block_h, -1)
        print(f" [+] Deposited position: {[round(x, 3) for x in p_placed]}")

        # 5. Conveyor Transport to Collection Bin
        out_conv = self.out_convs[detected_color]
        self.sim.writeCustomTableData(out_conv, "__ctrl__", {"vel": self.output_conveyor_vel})
        print(f" [*] Operating OutputConveyor{detected_color.capitalize()} to transport block into bin...")

        for s in range(110):
            self.client.step()

        # 6. Verify Bin Containment
        contained, p_final = self.check_bin_containment(detected_color, block_h)
        print(f" [+] Final position: {[round(x, 3) for x in p_final]}")

        bin_name = f"{detected_color.capitalize()}CollectionBin"
        if contained:
            print(f" [PASS] Block successfully secured inside {bin_name}!")
            self.stats[detected_color] += 1
            self.stats["total_sorted"] += 1
            success = True
        else:
            print(f" [FAIL] Block did not land securely inside {bin_name}.")
            self.stats["bin_failures"] += 1
            success = False

        duration = time.time() - cycle_start_time
        cycle_result = {
            "success": success,
            "color": detected_color,
            "confidence": confidence,
            "ground_truth": ground_truth_alias,
            "final_position": [round(x, 3) for x in p_final],
            "contained": contained,
            "duration_s": round(duration, 2),
        }
        self.history.append(cycle_result)
        return cycle_result

    def run_multi_block_sorting(self, target_count: int = 3) -> bool:
        """
        Executes sequential sorting for multiple blocks arriving on the input conveyor.
        """
        print("\n" + "=" * 70)
        print(f" EXECUTING MULTI-BLOCK SORTING RUN (Target: {target_count} blocks)")
        print("=" * 70)

        for i in range(target_count):
            print(f"\n>>> CYCLE {i+1} OF {target_count} <<<")
            result = self.sort_cycle(auto_feed=True, save_annotation_path=f"test_output/multi_cycle_{i+1}.png")
            if not result["success"]:
                print(f"[!] Cycle {i+1} failed: {result.get('reason')}")
                return False

        print("\n" + "=" * 70)
        print(" MULTI-BLOCK SORTING RUN COMPLETED SUCCESSFULLY")
        print("=" * 70)
        print(f" Total Sorted: {self.stats['total_sorted']} / {target_count}")
        print(f" Red Blocks  : {self.stats['red']}")
        print(f" Green Blocks: {self.stats['green']}")
        print(f" Blue Blocks : {self.stats['blue']}")
        print("=" * 70)
        return True
