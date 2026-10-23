# Contributor & Setup Guide

Welcome to the **Intelligent Industrial Object Sorting System** project! This guide walks you through everything you need to fork this repository, configure your local environment, install prerequisites (CoppeliaSim Edu, Python, and dependencies), connect your code to the simulation, run tests, and contribute your own improvements.

---

## Table of Contents

1. [Prerequisites & System Requirements](#1-prerequisites--system-requirements)
2. [Step 1: Fork and Clone the Repository](#2-step-1-fork-and-clone-the-repository)
3. [Step 2: Python Virtual Environment Setup](#3-step-2-python-virtual-environment-setup)
4. [Step 3: CoppeliaSim Edu Installation & Scene Setup](#4-step-3-coppeliasim-edu-installation--scene-setup)
5. [Step 4: Verify Python-to-Simulator Connection](#5-step-4-verify-python-to-simulator-connection)
6. [Step 5: Run Verification Tests & Motion Control](#6-step-5-run-verification-tests--motion-control)
7. [Step 6: Project Architecture & Module Overview](#7-step-6-project-architecture--module-overview)
8. [Step 7: Development & Pull Request Workflow](#8-step-7-development--pull-request-workflow)
9. [Troubleshooting & Common Issues](#9-troubleshooting--common-issues)

---

## 1. Prerequisites & System Requirements

Before starting, ensure your machine meets the following requirements:

| Component | Minimum / Recommended | Notes |
| :--- | :--- | :--- |
| **Operating System** | Windows 10/11, Ubuntu 20.04/22.04+, macOS | Tested primarily on Windows 11 and Linux x86_64 |
| **Python** | Python 3.10 to 3.13 | 64-bit Python installation |
| **Git** | 2.30+ | For version control and GitHub synchronization |
| **CoppeliaSim** | **CoppeliaSim Edu 4.6.0 to 4.10.0+** | Free for educational & research use |
| **RAM** | 8 GB RAM (16 GB recommended) | For smooth physics simulation and 3D rendering |
| **GPU / Graphics** | Dedicated GPU or modern integrated graphics | OpenGL 3.2+ support required |

---

## 2. Step 1: Fork and Clone the Repository

### 1. Fork the Repository on GitHub
1. Navigate to the upstream repository:  
   👉 **[https://github.com/Tanmay-Kad/intelligent-industrial-robot-sorter](https://github.com/Tanmay-Kad/intelligent-industrial-robot-sorter)**
2. In the top-right corner of the page, click the **Fork** button.
3. Choose your personal GitHub account as the destination and click **Create fork**.

### 2. Clone Your Fork Locally
Open your terminal (PowerShell, Command Prompt, or Bash) and clone your fork:

```bash
# Replace <your-username> with your actual GitHub username
git clone https://github.com/<your-username>/intelligent-industrial-robot-sorter.git
cd intelligent-industrial-robot-sorter
```

### 3. Add the Upstream Remote
To easily sync updates from the main repository in the future, add `upstream`:

```bash
git remote add upstream https://github.com/Tanmay-Kad/intelligent-industrial-robot-sorter.git

# Verify your remotes
git remote -v
# origin   https://github.com/<your-username>/intelligent-industrial-robot-sorter.git (fetch)
# origin   https://github.com/<your-username>/intelligent-industrial-robot-sorter.git (push)
# upstream https://github.com/Tanmay-Kad/intelligent-industrial-robot-sorter.git (fetch)
# upstream https://github.com/Tanmay-Kad/intelligent-industrial-robot-sorter.git (push)
```

---

## 3. Step 2: Python Virtual Environment Setup

Always use an isolated virtual environment to prevent package conflicts with your system Python.

### Windows (PowerShell)
```powershell
# Create virtual environment named .venv
python -m venv .venv

# If script execution is restricted, enable it for current user:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Activate virtual environment
.venv\Scripts\Activate.ps1
```

### Linux / macOS (Bash)
```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate
```

*(You should now see `(.venv)` at the beginning of your terminal prompt).*

### Install Dependencies
With your virtual environment active, install the required packages:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### What is in `requirements.txt`?
- **`coppeliasim-zmqremoteapi-client`**: Official ZeroMQ Remote API client for Python that communicates with the CoppeliaSim engine.
- **`cbor2`**: High-performance binary object serializer used by the ZeroMQ protocol for low-latency command transfer.

---

## 4. Step 3: CoppeliaSim Edu Installation & Scene Setup

### 1. Download & Install CoppeliaSim Edu
1. Visit the official download page:  
   👉 **[https://www.coppeliarobotics.com/downloads](https://www.coppeliarobotics.com/downloads)**
2. Download **CoppeliaSim Player / Edu** for your operating system.
3. Run the installer and complete the setup.
   - **Default Windows installation directory**:  
     `C:\Program Files\CoppeliaRobotics\CoppeliaSimEdu\`
   - **Default Linux directory**:  
     `~/CoppeliaSim_Edu_.../`

### 2. Verify the ZeroMQ Remote API Server
In CoppeliaSim version 4.3.0 and newer (including 4.10.0), the **ZeroMQ Remote API Server** is built-in and starts automatically when CoppeliaSim launches.
- Default listening host: `127.0.0.1` (localhost)
- Default listening port: `23004`
- You can confirm it is running in CoppeliaSim under the menu **Add-ons -> ZMQ remote API server** (it should show a checkmark or indicate running in the status bar console).

### 3. Open the Project Scene
1. Launch **CoppeliaSim Edu**.
2. Click **File -> Open scene...** (or press `Ctrl+O`).
3. Browse to your cloned repository folder:
   ```
   intelligent-industrial-robot-sorter/scenes/sorting_factory.ttt
   ```
4. Click **Open**.

> [!NOTE]
> The scene includes the UR5 robot, RG2 parallel gripper, an input conveyor belt with safety bumper, three color-coded output conveyors (Red, Green, Blue), three open-top collection bins, an overhead inspection camera, and sample RGB blocks.

---

## 5. Step 4: Verify Python-to-Simulator Connection

Keep **CoppeliaSim open** with the scene loaded, and run the connection test in your terminal:

```bash
python test_connection.py
```

### Expected Output:
```text
============================================================
 Testing CoppeliaSim ZeroMQ Remote API Connection
============================================================
[+] Successfully connected to CoppeliaSim Remote API Server!
[+] Simulation state      : Stopped
[+] Current simulation time: 0.000 s
[+] Successfully pinged simulator. Connection is HEALTHY!
============================================================
```

If you see this message, Python and CoppeliaSim are communicating properly.

---

## 6. Step 5: Run Verification Tests & Motion Control

### 1. Validate Scene Hierarchy & Physics
Verify that all 21 key scene objects, camera sensors, collection bins, and conveyor velocities are configured:

```bash
python scene/validate_scene.py
```
This script checks:
- Object handle resolution (`/UR5`, `/RobotPedestal`, `/OutputConveyorRed`, etc.)
- Collection bin open cavity dimensions and discharge alignment
- Inspection camera vision capture (128x128 RGB array)
- RG2 gripper signal communication
- Conveyor physics and block transport

### 2. Run the UR5 Robot Motion & Gripper Test Suite
Execute the full automated motion controller test runner:

```bash
python robot/test_robot_motion.py
```

This autonomous test validates 3 key operations:
1. **Empty Motion Test**: Arm moves through calibrated waypoints (`Home` -> `PrePick` -> `Pick` -> `PrePlaceRed` -> `PlaceRed` -> `Home`) using high-elbow kinematics with $0.000^\circ$ joint error and zero collisions.
2. **Gripper Interface Test**: Verifies mechanical stroke of the RG2 parallel jaw gripper (opening to ~5.4 cm and closing) and queries the internal infrared proximity sensor.
3. **Single-Block Pick-and-Place**: Grasping the red block at the pickup station, lifting it into the high transit corridor, depositing it on the Red output conveyor, and operating the belt until the block tumbles into the Red collection bin.

### 3. (Optional) Rebuild the Scene from Scratch
If an object was accidentally deleted or modified in CoppeliaSim, you can regenerate the entire factory layout programmatically:

```bash
python scene/build_scene.py
```
*(Make sure simulation is stopped in CoppeliaSim before running `build_scene.py`).*

---

## 7. Step 6: Project Architecture & Module Overview

```text
intelligent-industrial-robot-sorter/
├── config/
│   ├── __init__.py
│   └── settings.py          # Central coordinates, conveyor speeds, bin dimensions, ZMQ port
├── core/
│   ├── __init__.py
│   └── sim_client.py        # Resilient ZMQ Remote API connection factory singleton
├── robot/
│   ├── __init__.py          # Exports UR5Kinematics and UR5Controller
│   ├── kinematics.py        # simIK inverse kinematics solver & high-elbow waypoint definitions
│   ├── robot_controller.py  # Modular controller (S-curve trajectory interpolation, grasp management)
│   └── test_robot_motion.py # Phase 3 comprehensive verification test runner
├── scene/
│   ├── __init__.py
│   ├── build_scene.py       # Programmatic scene builder (loads UR5, conveyors, bins, camera)
│   ├── inspect_scene.py     # Diagnostic tool that enumerates all scene handles & aliases
│   └── validate_scene.py    # Multi-point validation suite
├── scenes/
│   └── sorting_factory.ttt  # Persisted CoppeliaSim binary scene (1.6 MB)
├── .gitignore               # Comprehensive Git ignore rules (protects scenes, ignores cache)
├── CONTRIBUTING.md          # This setup and contribution guide
├── README.md                # Project documentation overview
├── requirements.txt         # Python dependencies
└── test_connection.py       # Standalone connectivity test script
```

### Key Modules Explained

- **`robot/robot_controller.py` (`UR5Controller`)**:
  - Dynamically resolves all UR5 joint and RG2 gripper handles.
  - Generates smooth cubic Hermite S-curve velocity profiles ($s(\tau) = 3\tau^2 - 2\tau^3$) for zero-jerk joint trajectories.
  - Commands the RG2 gripper using `signal.RG2_open` (`1` = open, `0` = close).
  - Queries `attachProxSensor` before establishing parent attachment to `attachPoint`.
- **`robot/kinematics.py` (`UR5Kinematics`)**:
  - Contains calibrated joint angles for all transit and action stations.
  - Uses an **optimized high-elbow kinematic branch** (`Elbow Z ≈ 0.895m`, radial distance from base `< 0.10m`) ensuring the upper arm stays tucked near the pedestal to prevent collisions with conveyors and blocks.
  - Integrates CoppeliaSim's native `simIK` plugin (Damped Least Squares method).
- **`config/settings.py`**:
  - Single source of truth for all spatial coordinates, component sizes, conveyor belt velocities, and communication ports.

---

## 8. Step 7: Development & Pull Request Workflow

We follow standard GitHub flow. Here is how you can contribute:

### 1. Create a Topic Branch
Before making changes, sync your `main` branch with `upstream` and create a descriptive branch:

```bash
git checkout main
git pull upstream main
git checkout -b feature/your-feature-name
```

### 2. Make Your Changes
- Maintain documentation integrity and preserve docstrings.
- Ensure new features have accompanying tests or validation checks.
- Do not commit generated `__pycache__` files or temporary logs (verified by `.gitignore`).

### 3. Run Validation Scripts
Before committing, make sure all tests pass cleanly:

```bash
python test_connection.py
python scene/validate_scene.py
python robot/test_robot_motion.py
```

### 4. Commit and Push
```bash
git add .
git commit -m "feat(robot): add automatic vision-based color classification"
git push -u origin feature/your-feature-name
```

### 5. Submit a Pull Request
1. Go to your fork on GitHub: `https://github.com/<your-username>/intelligent-industrial-robot-sorter`
2. You will see a banner: **"Compare & pull request"**. Click it.
3. Provide a clear title and description of your changes, including test output.
4. Click **Create pull request**.

---

## 9. Troubleshooting & Common Issues

### Issue 1: `Connection refused` or `Timeout` in `test_connection.py`
- **Cause**: CoppeliaSim is not open, or the ZeroMQ Remote API server is not running on port `23004`.
- **Fix**:
  1. Make sure CoppeliaSim Edu is running.
  2. In CoppeliaSim, check **Add-ons -> ZMQ remote API server** to ensure it is active.
  3. Ensure no local firewall is blocking port `23004` on loopback `127.0.0.1`.
  4. If your CoppeliaSim uses a custom port, update `ZMQ_PORT` in `config/settings.py`.

### Issue 2: `Model file not found at: C:\Program Files\CoppeliaRobotics\...`
- **Cause**: `scene/build_scene.py` looks for default model files (UR5, RG2, Conveyor) in the standard CoppeliaSim installation path. If CoppeliaSim is installed in a non-standard location or on Linux/macOS, paths may differ.
- **Fix**:
  - You do **not** need to run `build_scene.py` if you simply open `scenes/sorting_factory.ttt`, which already includes all models embedded!
  - If you do wish to run `build_scene.py`, update `COPPELIASIM_DIR` or `MODEL_PATHS` in `config/settings.py` to point to your CoppeliaSim installation path.

### Issue 3: `Script execution is disabled on this system` (PowerShell)
- **Cause**: Windows PowerShell restricts virtualenv activation scripts by default.
- **Fix**:
  Run PowerShell as Administrator or for your user:
  ```powershell
  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
  ```

### Issue 4: Robot arm falls or droops due to gravity
- **Cause**: By default, UR5 joints in CoppeliaSim have dynamic motors with low torque.
- **Fix**:
  The `UR5Controller.configure_joints()` method automatically sets arm shapes to `shapeintparam_static = 1` and joints to `jointmode_kinematic` during initialization. Always use `UR5Controller` to ensure rigid kinematic stability.

---

## Questions or Need Help?

If you encounter any issues or have questions:
- Open an **[Issue](https://github.com/Tanmay-Kad/intelligent-industrial-robot-sorter/issues)** on GitHub.
- Submit a **[Discussion](https://github.com/Tanmay-Kad/intelligent-industrial-robot-sorter/discussions)** topic.

Happy robotics coding! 🚀
