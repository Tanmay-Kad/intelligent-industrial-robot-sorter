# Intelligent Industrial Object Sorting System

An autonomous industrial pick-and-place sorting cell simulation built with CoppeliaSim Edu and Python via the ZeroMQ Remote API.

> 📖 **Looking to fork and run this project on your system?**  
> Check out the complete step-by-step [**Contributor & Setup Guide (CONTRIBUTING.md)**](file:///d:/industrial-robot-sorter/CONTRIBUTING.md) for installation, virtual environments, CoppeliaSim ZeroMQ setup, and test execution!

---


## Project Structure

```text
d:/industrial-robot-sorter/
├── config/
│   ├── __init__.py
│   └── settings.py          # Centralized geometry, coordinates, and model configurations
├── core/
│   ├── __init__.py
│   └── sim_client.py        # Resilient ZMQ Remote API connection factory
├── robot/
│   ├── __init__.py
│   ├── kinematics.py        # simIK solver & high-elbow collision-free waypoint repository
│   ├── robot_controller.py  # Modular UR5 controller (S-curve interpolation, RG2 grasp management)
│   └── test_robot_motion.py # Phase 3 comprehensive verification test suite
├── scene/
│   ├── __init__.py
│   ├── inspect_scene.py     # Inspects and prints all scene objects & types
│   ├── build_scene.py       # Programmatic scene constructor (idempotent)
│   └── validate_scene.py    # Multi-point validation (handles, vision, signals, physics)
├── scenes/
│   └── sorting_factory.ttt  # Persisted CoppeliaSim binary scene (1.6 MB)
├── .gitignore               # Comprehensive Git ignore rules
├── CONTRIBUTING.md          # Step-by-step fork, installation, and setup guide
├── requirements.txt         # Project dependencies
├── test_connection.py       # Basic connectivity test from Phase 1
└── README.md
```


---

## Factory Layout Architecture

The scene is designed around a central 6-DOF industrial manipulator surrounded orthogonally by 4 conveyors:

| Component | CoppeliaSim Alias | Position `[X, Y, Z]` (m) | Orientation / Details |
| :--- | :--- | :--- | :--- |
| **Robot Pedestal** | `/RobotPedestal` | `[0.0, 0.0, 0.20]` | Static base, `[0.35, 0.35, 0.40]m` |
| **UR5 Robotic Arm** | `/UR5` | `[0.0, 0.0, 0.40]` | 6-DOF arm mounted on pedestal |
| **UR5 Joints** | `/UR5/UR5_joint1..6` | Varied | Renamed for direct Python control |
| **RG2 Gripper** | `/UR5/connection/RG2` | Relative to flange | Parallel servo gripper (controlled via `signal.RG2_open`) |
| **Input Conveyor** | `/InputConveyor` | `[-0.85, 0.0, 0.70]` | Moves West to East towards pickup zone (`Z=0.70m`) |
| **End Bumper** | `/InputEndBumper` | `[-0.34, 0.0, 0.73]` | Safety stop at pick station |
| **Output Red** | `/OutputConveyorRed` | `[0.0, 0.85, 0.70]` | Points North (+Y) with Red rails |
| **Output Green** | `/OutputConveyorGreen` | `[0.85, 0.0, 0.70]` | Points East (+X) with Green rails |
| **Output Blue** | `/OutputConveyorBlue` | `[0.0, -0.85, 0.70]` | Points South (-Y) with Blue rails |
| **Inspection Camera**| `/InspectionCamera` | `[-0.40, 0.0, 1.15]` | Overhead camera pointing directly down at pick zone |
| **Red Collection Bin**| `/RedCollectionBin` | `[0.0, 1.52, 0.0]` | Open-top container at Red conveyor discharge end (+Y) |
| **Green Collection Bin**| `/GreenCollectionBin` | `[1.52, 0.0, 0.0]` | Open-top container at Green conveyor discharge end (+X) |
| **Blue Collection Bin**| `/BlueCollectionBin` | `[0.0, -1.52, 0.0]` | Open-top container at Blue conveyor discharge end (-Y) |
| **Red Object** | `/RedBlock` | `[-0.55, 0.0, 0.725]`| Dynamic respondable cuboid (mass 0.05kg) |
| **Green Object** | `/GreenBlock` | `[-0.75, 0.0, 0.725]`| Dynamic respondable cuboid (mass 0.05kg) |
| **Blue Object** | `/BlueBlock` | `[-0.95, 0.0, 0.725]`| Dynamic respondable cuboid (mass 0.05kg) |

---

## Quickstart Commands

```powershell
# 1. Install dependencies
pip install -r requirements.txt

# 2. Verify ZeroMQ Remote API connection to CoppeliaSim
python test_connection.py

# 3. Inspect active scene hierarchy
python scene/inspect_scene.py

# 4. Build or rebuild the complete factory layout
python scene/build_scene.py

# 5. Run automated scene validation checks
python scene/validate_scene.py

# 6. Run UR5 motion, gripper control, and pick-and-place tests
python robot/test_robot_motion.py
```

