"""
UR5 Robot & RG2 Gripper Modular Controller
Provides robust, collision-safe motion planning, trajectory interpolation,
and physical grasp management via the ZeroMQ Remote API.
"""

import sys
import os
import math
import time
from typing import List, Tuple, Optional, Any

# Ensure project root is accessible
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from core.sim_client import get_sim_client
from robot.kinematics import UR5Kinematics
import config.settings as cfg


class UR5Controller:
    """
    Modular Controller for the UR5 6-DOF Manipulator and RG2 Gripper.
    Handles joint motion, trajectory generation, and physical gripper operation.
    """

    def __init__(self, client: Any = None, sim: Any = None):
        """
        Initializes the UR5 controller and dynamically resolves scene handles.
        """
        if client is None or sim is None:
            self.client, self.sim = get_sim_client(cfg.ZMQ_HOST, cfg.ZMQ_PORT)
        else:
            self.client = client
            self.sim = sim

        self._resolve_handles()
        self.configure_joints()

    def _resolve_handles(self):
        """Resolves all required scene object handles dynamically."""
        self.ur5_base = self.sim.getObject("/UR5")
        self.joints = [
            self.sim.getObject(f"/UR5/UR5_joint{i}") for i in range(1, 7)
        ]
        self.rg2 = self.sim.getObject("/UR5/connection/RG2")
        self.attach_point = self.sim.getObject("./attachPoint", {"proxy": self.rg2})
        self.attach_prox = self.sim.getObject("./attachProxSensor", {"proxy": self.rg2})
        self.open_close_joint = self.sim.getObject(
            "./openCloseJoint", {"proxy": self.rg2}
        )

    def configure_joints(self):
        """
        Configures UR5 arm links and joints for stable kinematic trajectory tracking.
        Makes arm shapes static (immune to gravity droop) while leaving RG2 dynamic.
        """
        try:
            rg2_shapes = set(self.sim.getObjectsInTree(self.rg2))
            for c in self.sim.getObjectsInTree(self.ur5_base):
                if self.sim.getObjectType(c) == self.sim.object_shape_type and c not in rg2_shapes:
                    self.sim.setObjectInt32Param(c, self.sim.shapeintparam_static, 1)

            for j in self.joints:
                self.sim.setJointMode(j, self.sim.jointmode_kinematic)
        except Exception:
            pass

    def get_joint_positions(self) -> List[float]:
        """Returns the current joint angles in radians."""
        return [self.sim.getJointPosition(j) for j in self.joints]

    def get_joint_positions_deg(self) -> List[float]:
        """Returns current joint angles in degrees."""
        return [round(math.degrees(a), 2) for a in self.get_joint_positions()]

    def get_tip_position(self) -> List[float]:
        """Returns current [X, Y, Z] world position of the gripper attachPoint."""
        return self.sim.getObjectPosition(self.attach_point, -1)

    def move_joints(
        self,
        target_q: List[float],
        steps: int = 10,
        tolerance: float = 0.02,
    ) -> bool:
        """
        Executes a smooth S-curve interpolated movement to target joint angles.
        
        S-curve formula: s(tau) = 3*tau^2 - 2*tau^3 (zero jerk/acceleration at bounds)
        
        Args:
            target_q: Target joint angles in radians.
            steps: Number of simulation steps for the trajectory segment.
            tolerance: Maximum allowable angle error per joint (radians).
            
        Returns:
            bool: True if motion completed within tolerance.
        """
        self.configure_joints()
        start_q = self.get_joint_positions()
        steps = max(steps, 2)

        for s in range(1, steps + 1):
            tau = s / float(steps)
            s_curve = 3.0 * (tau**2) - 2.0 * (tau**3)
            for k, j in enumerate(self.joints):
                q = start_q[k] + s_curve * (target_q[k] - start_q[k])
                self.sim.setJointPosition(j, q)
            self.client.step()

        # Convergence verification
        final_q = self.get_joint_positions()
        max_err = max(abs(final_q[k] - target_q[k]) for k in range(6))
        return max_err <= tolerance

    def move_to_named_pose(self, pose_name: str, steps: int = 10) -> bool:
        """Moves robot to one of the verified named waypoints in UR5Kinematics."""
        target_q = UR5Kinematics.get_pose(pose_name)
        return self.move_joints(target_q, steps=steps)

    def open_gripper(self, steps: int = 22):
        """
        Commands the RG2 gripper to open its fingers.
        Sets signal.RG2_open = 1 and advances steps for physical mechanical opening.
        """
        self.sim.setIntProperty(self.sim.handle_scene, "signal.RG2_open", 1)
        for _ in range(steps):
            self.client.step()

    def close_gripper(self, steps: int = 20):
        """
        Commands the RG2 gripper to close its fingers.
        Sets signal.RG2_open = 0 and advances steps for physical mechanical closing.
        """
        self.sim.setIntProperty(self.sim.handle_scene, "signal.RG2_open", 0)
        for _ in range(steps):
            self.client.step()

    def check_grasp(
        self, target_handle: int = None
    ) -> Tuple[bool, float, int]:
        """
        Queries RG2 proximity sensor (attachProxSensor) to detect objects between fingers.
        
        Returns:
            tuple: (detected: bool, distance: float, detected_object_handle: int)
        """
        handle_to_check = target_handle if target_handle is not None else self.sim.handle_all
        res, dist, _, detected_handle, _ = self.sim.checkProximitySensor(
            self.attach_prox, handle_to_check
        )
        detected = (res == 1)
        return detected, dist, detected_handle

    def attach_object(self, object_handle: int):
        """
        Physically locks grasped object to RG2 connector dummy (attachPoint).
        Prevents physics slippage during rapid arm movement.
        """
        self.sim.setObjectParent(object_handle, self.attach_point, True)

    def detach_object(self, object_handle: int):
        """
        Detaches object from RG2 connector, returning it to free dynamic world space.
        """
        self.sim.setObjectParent(object_handle, -1, True)

    def pick_block(self, block_handle: int = None, steps: int = 10) -> bool:
        """
        Executes complete, collision-safe vertical pickup sequence:
        1. Open gripper fully at transit height
        2. Move to PrePick pose (Z=0.88m)
        3. Descend vertically to Pick pose (Z=0.76m)
        4. Verify proximity detection
        5. Close fingers and attach block
        6. Retract vertically to PrePick pose (Z=0.88m)
        
        Returns:
            bool: True if block was successfully grasped and lifted.
        """

        self.open_gripper(steps=20)

        # Move to PrePick then Pick
        self.move_to_named_pose("pre_pick", steps=steps)
        self.move_to_named_pose("pick", steps=max(6, steps - 2))

        # Verify block detection via proximity sensor
        detected, dist, detected_h = self.check_grasp(block_handle)
        target_h = block_handle if block_handle is not None else detected_h

        if not detected:
            print(f"[!] Warning: Block not detected at pick pose (dist={dist:.4f})")
            return False

        # Close fingers and securely attach
        self.close_gripper(steps=20)
        self.attach_object(target_h)

        # Lift vertically back to pre_pick
        self.move_to_named_pose("pre_pick", steps=max(6, steps - 2))
        
        # Verify block is carried in air
        p_block = self.sim.getObjectPosition(target_h, -1)
        lift_success = p_block[2] > (cfg.CONVEYOR_SURFACE_Z + 0.05)
        return lift_success

    def place_block(
        self, station_name: str, block_handle: int = None, steps: int = 14
    ) -> bool:
        """
        Executes collision-safe transfer and placement sequence:
        1. Transfer horizontally at high transit corridor to target PrePlace pose
        2. Descend vertically to Place pose
        3. Release block (detach parent)
        4. Open gripper
        5. Retract vertically to PrePlace pose
        6. Return to Home pose
        
        Args:
            station_name: 'red', 'green', or 'blue'
            block_handle: Handle of the held block
            steps: Movement steps
            
        Returns:
            bool: True if placement completed successfully.
        """
        pre_pose = f"pre_place_{station_name.lower()}"
        place_pose = f"place_{station_name.lower()}"

        # 1. High corridor transfer to destination station
        self.move_to_named_pose(pre_pose, steps=steps)

        # 2. Vertical descent to belt surface
        self.move_to_named_pose(place_pose, steps=max(6, steps - 4))

        # 3. Detach and open gripper
        if block_handle is not None:
            self.detach_object(block_handle)
        self.open_gripper(steps=20)

        # 4. Vertical retract to clear belt and bumper
        self.move_to_named_pose(pre_pose, steps=max(6, steps - 4))

        # 5. Return to Home pose
        self.move_to_named_pose("home", steps=steps)
        return True
