# Intelligent Industrial Object Sorting System

An autonomous industrial pick-and-place sorting cell simulation built with CoppeliaSim Edu and Python via the ZeroMQ Remote API.

> 📖 **Looking to fork and run this project on your system?**  
> Check out the complete step-by-step [**Contributor & Setup Guide (CONTRIBUTING.md)**](CONTRIBUTING.md) for installation, virtual environments, CoppeliaSim ZeroMQ setup, and test execution!

---

## Project Status: Phase 5 Completed ✅

- [x] **Phase 1: Verification & ZeroMQ Remote API Setup** (Python 3.13.5 <-> CoppeliaSim 4.10.0 communication)
- [x] **Phase 2: Industrial Factory Scene Setup** (Pedestal, UR5, RG2, 4 Conveyors, 3 Bins, Camera, RGB Blocks)
- [x] **Phase 3: UR5 Motion & Gripper Control** (Kinematics poses, S-curve trajectory interpolation, physics grasping)
- [x] **Phase 4: Camera-Based RGB Detection & Automated Object Sorting** (OpenCV HSV classification, automated orchestration, sequential multi-block sorting)
- [x] **Phase 5: Dynamic Object Feeding & Continuous Factory Automation** (Dynamic spawner, queue flow control, lifecycle tracking, continuous multi-object pipeline)
- [ ] **Phase 6 (Planned): Real-Time Dashboard & Telemetry Analytics** (Throughput monitoring, Web/GUI telemetry)

---

## Project Structure

```text
d:/industrial-robot-sorter/
├── config/
│   ├── __init__.py
│   └── settings.py                     # Centralized geometry, coordinates, and model configurations
├── core/
│   ├── __init__.py
│   └── sim_client.py                   # Resilient ZMQ Remote API connection factory
├── robot/
│   ├── __init__.py
│   ├── kinematics.py                   # simIK solver & high-elbow collision-free waypoint repository
│   ├── robot_controller.py             # Modular UR5 controller (S-curve interpolation, RG2 grasp management)
│   └── test_robot_motion.py            # Phase 3 verification test suite
├── scene/
│   ├── __init__.py
│   ├── inspect_scene.py                # Inspects and prints all scene objects & types
│   ├── build_scene.py                  # Programmatic scene constructor (idempotent)
│   └── validate_scene.py               # Multi-point validation (handles, vision, signals, physics)
├── scenes/
│   └── sorting_factory.ttt             # Persisted CoppeliaSim binary scene (1.6 MB)
├── src/
│   ├── __init__.py
│   ├── object_spawner.py               # Phase 5 dynamic object spawner & lifecycle tracking
│   └── sorting_controller.py           # Automated sorting orchestrator & continuous automation pipeline
├── tests/
│   ├── __init__.py
│   ├── test_phase4_sorting.py          # Phase 4 comprehensive test suite (6 incremental tests)
│   └── test_phase5_continuous_sorting.py # Phase 5 continuous factory automation test suite
├── vision/
│   ├── __init__.py
│   ├── color_detector.py               # OpenCV HSV color detector with confidence scoring & annotations
│   └── test_color_detector.py          # Vision sensor capture & RGB classification unit tests
├── .gitignore                          # Comprehensive Git ignore rules
├── CONTRIBUTING.md                     # Step-by-step fork, installation, and setup guide
├── requirements.txt                    # Project dependencies (ZMQ client, NumPy, OpenCV)
├── test_connection.py                  # Basic connectivity verification
└── README.md
```

---

## Architecture & Subsystems

### 1. Vision & Color Detection (`vision/color_detector.py`)
- **Optics & Calibration**: Uses the overhead `/InspectionCamera` vision sensor looking directly down at the pickup station (`Z=1.15m`, 45° FOV).
- **Buffer Inversion**: Inverts the raw bottom-to-top byte buffer returned by `sim.getVisionSensorImg` (`np.flipud`) and converts from RGB to OpenCV BGR.
- **Pixel-Based HSV Classification**:
  - **Red**: $H \in [0, 10] \cup [170, 180], S \in [110, 255], V \in [70, 255]$
  - **Green**: $H \in [45, 85], S \in [110, 255], V \in [70, 255]$
  - **Blue**: $H \in [100, 135], S \in [110, 255], V \in [70, 255]$
- **Noise & Edge Rejection**: Rejects empty belt pixels ($S < 30$), yellow bumper ($H \approx 22$), and conveyor rails using an inspection station Region of Interest (ROI) and morphological opening/closing kernels.
- **Confidence Scoring**: Evaluates contour area relative to expected block size ($~340\text{ px}$), shape aspect ratio $\frac{\min(w,h)}{\max(w,h)}$, and color pixel purity within the bounding box.
- **Ambiguity Detection**: Rejects overlapping or ambiguous multi-color frames.

### 2. Robot Manipulation & Trajectories (`robot/`)
- **High-Elbow Clearance Waypoints**: Operates along an overhead transit corridor ($Z=0.88\text{m}$, elbow $Z=0.89\text{m}$) tucked close to the pedestal, guaranteeing zero collisions with conveyors, cameras, or standing obstacles.
- **S-Curve Interpolation**: Smooth joint interpolation preventing dynamic vibrations.
- **Mechanical RG2 Gripper**: Actuates fingers and dynamically attaches the grasped block during transit.

### 3. Dynamic Object Spawning & Lifecycle Tracking (`src/object_spawner.py`)
- **Runtime Generation**: Safely creates dynamic, respondable cuboids in CoppeliaSim using `sim.createPrimitiveShape` with verified mass ($0.05\text{ kg}$) and calibrated RGB diffuse colors.
- **Unique Identification**: Assigns unique identifiers (e.g. `Block_Red_001`, `Block_Green_002`) and tracks metadata.
- **Collision & Overlap Prevention**: Inspects the conveyor inlet spawn zone ($X = -1.20\text{m}$) before spawning; enforces safe minimum spacing ($0.22\text{m}$) to eliminate physical pileups.
- **Lifecycle State Machine**:
  $$\text{SPAWNED} \longrightarrow \text{WAITING} \longrightarrow \text{DETECTED} \longrightarrow \text{PICKED} \longrightarrow \text{PLACED} \longrightarrow \text{SORTED} \ (\text{or } \text{FAILED})$$

### 4. Continuous Sorting Automation (`src/sorting_controller.py`)
- **Conveyor Flow Control**: Automatically halts the input conveyor when the pickup station is occupied and resumes it when the station is cleared by the robot.
- **Pure Pixel Decision Routing**: Directs the UR5 arm strictly using camera pixel classifications.
- **End-to-End Containment Verification**: Confirms each sorted object has physically discharged from the conveyor and is contained within the 3D cavity bounds of its matching collection bin.
- **Audit & Metrics**: Records per-object lifecycle history, duration, sorted counts by color, and waiting queue totals.

---

## Factory Layout Reference

| Component | CoppeliaSim Alias | Position `[X, Y, Z]` (m) | Orientation / Details |
| :--- | :--- | :--- | :--- |
| **Robot Pedestal** | `/RobotPedestal` | `[0.0, 0.0, 0.20]` | Static base, `[0.35, 0.35, 0.40]m` |
| **UR5 Robotic Arm** | `/UR5` | `[0.0, 0.0, 0.40]` | 6-DOF arm mounted on pedestal |
| **UR5 Joints** | `/UR5/UR5_joint1..6` | Varied | Renamed for direct Python control |
| **RG2 Gripper** | `/UR5/connection/RG2` | Relative to flange | Parallel jaw gripper (`signal.RG2_open`) |
| **Input Conveyor** | `/InputConveyor` | `[-0.85, 0.0, 0.70]` | Moves West to East towards pickup zone (`Z=0.70m`) |
| **End Bumper** | `/InputEndBumper` | `[-0.34, 0.0, 0.73]` | Mechanical stop at pick station |
| **Output Red** | `/OutputConveyorRed` | `[0.0, 0.85, 0.70]` | Points North (+Y) with Red rails |
| **Output Green** | `/OutputConveyorGreen` | `[0.85, 0.0, 0.70]` | Points East (+X) with Green rails |
| **Output Blue** | `/OutputConveyorBlue` | `[0.0, -0.85, 0.70]` | Points South (-Y) with Blue rails |
| **Inspection Camera**| `/InspectionCamera` | `[-0.40, 0.0, 1.15]` | Overhead camera pointing directly down at pick zone |
| **Red Collection Bin**| `/RedCollectionBin` | `[0.0, 1.52, 0.0]` | Open-top container at Red conveyor discharge end (+Y) |
| **Green Collection Bin**| `/GreenCollectionBin` | `[1.52, 0.0, 0.0]` | Open-top container at Green conveyor discharge end (+X) |
| **Blue Collection Bin**| `/BlueCollectionBin` | `[0.0, -1.52, 0.0]` | Open-top container at Blue conveyor discharge end (-Y) |

---

## Execution Commands

### Prerequisites
```powershell
pip install -r requirements.txt
```

### 1. Connection & Scene Validation
```powershell
python test_connection.py
python scene/validate_scene.py
```

### 2. Robot Kinematics & Manipulation Tests (Phase 3)
```powershell
python robot/test_robot_motion.py
```

### 3. Vision & Color Classification Unit Tests (Phase 4)
```powershell
python vision/test_color_detector.py
```

### 4. Phase 4 Automated Sorting Test Suite
```powershell
python tests/test_phase4_sorting.py
```

### 5. Phase 5 Dynamic Object Feeding & Continuous Automation Test Suite
Runs dynamic spawning verification, queue clearance & flow control, and continuous sequential sorting of 6 objects (2 Red, 2 Green, 2 Blue):
```powershell
python tests/test_phase5_continuous_sorting.py
```

---

## Configuration Options

When initializing `SortingController` or calling `run_continuous_sorting()`, the following parameters are configurable:

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `max_objects` | `int` | `6` | Maximum total objects to spawn and sort |
| `max_duration_s` | `float` | `None` | Optional maximum run time cutoff (seconds) |
| `color_sequence` | `List[str]` | `None` | Explicit ordered list of colors (e.g. `['red', 'green', 'blue', ...]`) |
| `color_distribution` | `Dict[str, float]` | `1:1:1` | Probabilistic color distribution weights |
| `min_spacing` | `float` | `0.22m` | Minimum distance required between blocks to prevent pileups |
| `output_conveyor_vel` | `float` | `0.25 m/s` | Discharge conveyor travel speed |
| `input_conveyor_vel` | `float` | `0.15 m/s` | Infeed conveyor travel speed |
| `save_annotations` | `bool` | `True` | Saves annotated vision frames to `test_output/` |

---

## Test Results Summary

| Test Phase | Scope / Objective | Status | Details |
| :--- | :--- | :---: | :--- |
| **Phase 1** | Remote API Connectivity | **PASSED** | ZMQ connection verified on `localhost:23000` |
| **Phase 2** | Factory Scene Construction | **PASSED** | 15 components validated, 3 collection bins created |
| **Phase 3** | UR5 Motion & Gripper Physics | **PASSED** | Joint error < 0.001°, physical grasp verified, red block sorted |
| **Phase 4 - Test 1** | Camera Image Acquisition | **PASSED** | 128x128 px RGB/BGR frame captured and verified |
| **Phase 4 - Test 2** | Color Classification Quality | **PASSED** | 0 false positives on empty belt; Red (98.5%), Green (98.5%), Blue (98.5%) |
| **Phase 4 - Test 3** | Single Red-Block Cycle | **PASSED** | Vision decision: 'red', deposited on Red conveyor, collected in Red Bin |
| **Phase 4 - Test 4** | Single Green-Block Cycle | **PASSED** | Vision decision: 'green', deposited on Green conveyor, collected in Green Bin |
| **Phase 4 - Test 5** | Single Blue-Block Cycle | **PASSED** | Vision decision: 'blue', deposited on Blue conveyor, collected in Blue Bin |
| **Phase 4 - Test 6** | Multi-Block Sequential Run | **PASSED** | 3/3 blocks fed, classified, and sorted into matching bins |
| **Phase 5 - Test 1** | Dynamic Spawning & ID Tracking | **PASSED** | Dynamic cuboid spawning, mass=0.05kg, unique IDs (`Block_<Color>_<ID>`) |
| **Phase 5 - Test 2** | Queue Flow Control & Safety | **PASSED** | Inlet obstruction detected (prevented overlap); empty queue safe timeout |
| **Phase 5 - Test 3** | Continuous 6-Object Sorting | **PASSED** | **6/6 sorted (2 Red, 2 Green, 2 Blue)**; 100% bin containment; full lifecycle verified |

---

## Git Workflow & Review
As per instructions, changes are staged locally and not automatically pushed to the remote repository. To inspect and commit:
```powershell
git status
git diff
git add .
git commit -m "Implement Phase 5: Dynamic object feeding and continuous factory automation"
```
