"""
UR5 Robot Kinematics and Named Waypoint Definitions
Provides exact kinematic solutions for UR5 + RG2 Gripper using CoppeliaSim simIK engine.
"""

import math
from typing import Dict, List, Optional, Tuple, Any


class UR5Kinematics:
    """
    Kinematics helper and pose repository for UR5 + RG2 gripper setup.
    Angles are stored in radians.
    """

    # Verified Reachable Joint Configurations (radians)
    # Calibrated for high-elbow overhead transit (Z=0.88m) and straight-down vertical action (Z=0.76m)
    # High-elbow geometry keeps upper arm tucked tightly near pedestal (Elbow Z=0.89m, radial < 0.10m),
    # guaranteeing complete clearance over conveyors, bumpers, cameras, and blocks during corridor transit.
    POSES: Dict[str, List[float]] = {
        "home": [
            math.radians(a) for a in [0.0, -18.55, -37.00, 145.55, -90.0, 0.0]
        ],
        "pre_pick": [
            math.radians(a) for a in [-72.72, -16.61, -39.74, 146.34, -90.0, -72.72]
        ],
        "pick": [
            math.radians(a) for a in [-72.70, -8.80, -68.72, 167.53, -90.0, -72.70]
        ],
        "pre_place_red": [
            math.radians(a) for a in [-163.16, -18.50, -37.08, 145.58, -90.0, 106.84]
        ],
        "place_red": [
            math.radians(a) for a in [-163.17, -10.28, -66.97, 167.25, -90.0, 106.83]
        ],
        "pre_place_green": [
            math.radians(a) for a in [106.82, -18.55, -36.97, 145.53, -90.0, -73.18]
        ],
        "place_green": [
            math.radians(a) for a in [106.83, -10.28, -66.97, 167.25, -90.0, -73.17]
        ],
        "pre_place_blue": [
            math.radians(a) for a in [16.82, -18.56, -36.95, 145.52, -90.0, 106.82]
        ],
        "place_blue": [
            math.radians(a) for a in [16.83, -10.28, -66.97, 167.25, -90.0, 106.83]
        ],
    }


    # Station Cartesians (meters) for validation and dynamic IK
    STATION_TARGETS = {
        "pick": ([-0.370, 0.0, 0.760], [-math.pi, 0.0, -math.pi / 2]),
        "place_red": ([0.0, 0.380, 0.760], [-math.pi, 0.0, math.pi]),
        "place_green": ([0.380, 0.0, 0.760], [-math.pi, 0.0, math.pi / 2]),
        "place_blue": ([0.0, -0.380, 0.760], [-math.pi, 0.0, 0.0]),
    }

    @classmethod
    def get_pose(cls, name: str) -> List[float]:
        """Returns joint configuration in radians for a named pose."""
        if name not in cls.POSES:
            raise KeyError(
                f"Unknown pose '{name}'. Available: {list(cls.POSES.keys())}"
            )
        return list(cls.POSES[name])

    @classmethod
    def get_pose_deg(cls, name: str) -> List[float]:
        """Returns joint configuration in degrees for inspection/logging."""
        return [round(math.degrees(a), 2) for a in cls.get_pose(name)]

    @staticmethod
    def solve_ik(
        client: Any,
        sim: Any,
        target_pos: List[float],
        target_ori: List[float],
        initial_guess: Optional[List[float]] = None,
    ) -> Tuple[bool, List[float], List[float]]:
        """
        Solves 6-DOF inverse kinematics using CoppeliaSim's native simIK plugin.
        
        Args:
            client: RemoteAPIClient instance.
            sim: CoppeliaSim sim module.
            target_pos: [X, Y, Z] position in world frame.
            target_ori: [alpha, beta, gamma] Euler angles in world frame.
            initial_guess: Optional starting joint angles for seed configuration.
            
        Returns:
            tuple: (success, solved_joint_angles, precision_errors)
        """
        simIK = client.require("simIK")
        ur5 = sim.getObject("/UR5")
        rg2 = sim.getObject("/UR5/connection/RG2")
        tip = sim.getObject("./attachPoint", {"proxy": rg2})
        joints = [sim.getObject(f"/UR5/UR5_joint{i}") for i in range(1, 7)]

        # Save initial joint positions to restore after solve
        saved_q = [sim.getJointPosition(j) for j in joints]

        if initial_guess:
            for i, j in enumerate(joints):
                sim.setJointPosition(j, initial_guess[i])

        target = sim.createDummy(0.02)
        sim.setObjectPosition(target, target_pos, -1)
        sim.setObjectOrientation(target, target_ori, -1)

        ik_env = simIK.createEnvironment()
        ik_group = simIK.createGroup(ik_env)
        simIK.setGroupCalculation(
            ik_env, ik_group, simIK.method_damped_least_squares, 0.05, 50
        )
        simIK.addIkElementFromScene(
            ik_env, ik_group, ur5, tip, target, simIK.constraint_pose
        )

        res, iters, prec = simIK.handleGroup(ik_env, ik_group, {})
        simIK.applyIkEnvironmentToScene(ik_env, ik_group)
        solved_q = [sim.getJointPosition(j) for j in joints]

        # Clean up IK environment and temporary target dummy
        simIK.eraseEnvironment(ik_env)
        sim.removeObject(target)

        # Restore original joint positions
        for i, j in enumerate(joints):
            sim.setJointPosition(j, saved_q[i])

        success = res == 1 or (prec[0] < 0.005 and prec[1] < 0.05)
        return success, solved_q, prec
