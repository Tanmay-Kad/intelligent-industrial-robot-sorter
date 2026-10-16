"""
Centralized Configuration Settings for Industrial Sorting System
"""

import os
import math

# ZMQ Remote API Connection
ZMQ_HOST = "localhost"
ZMQ_PORT = 23000

# CoppeliaSim Installation and Model Paths
COPPELIASIM_APP_PATH = "C:/Program Files/CoppeliaRobotics/CoppeliaSimEdu"
MODELS_DIR = os.path.join(COPPELIASIM_APP_PATH, "models")

MODEL_PATHS = {
    "ur5": os.path.join(MODELS_DIR, "robots", "non-mobile", "UR5.ttm"),
    "rg2": os.path.join(MODELS_DIR, "components", "grippers", "RG2.ttm"),
    "conveyor": os.path.join(MODELS_DIR, "equipment", "conveyors", "generic conveyor (efficient).ttm"),
    "camera": os.path.join(MODELS_DIR, "components", "sensors", "Blob detection camera.ttm"),
}

# Elevation Constants
PEDESTAL_HEIGHT = 0.40
CONVEYOR_SURFACE_Z = 0.70  # Model position Z=0.70 puts belt surface at Z=0.70m
BLOCK_HEIGHT = 0.045
BLOCK_REST_Z = CONVEYOR_SURFACE_Z + (BLOCK_HEIGHT / 2.0)  # 0.7225m

# Scene Layout Geometry (Positions in meters [X, Y, Z], Orientations in radians [alpha, beta, gamma])
LAYOUT = {
    "pedestal": {
        "size": [0.35, 0.35, PEDESTAL_HEIGHT],
        "position": [0.0, 0.0, PEDESTAL_HEIGHT / 2.0],  # Centered at Z=0.20m, top at 0.40m
        "color": [0.20, 0.22, 0.25],  # Anthracite slate
    },
    "robot": {
        "position": [0.0, 0.0, PEDESTAL_HEIGHT],  # Mounted on top of pedestal at Z=0.40m
        "home_joint_angles": [0.0, -math.pi / 4, math.pi / 2, -math.pi / 4, -math.pi / 2, 0.0],
    },
    "input_conveyor": {
        "name": "InputConveyor",
        "position": [-0.85, 0.0, CONVEYOR_SURFACE_Z],
        "orientation": [0.0, 0.0, 0.0],
        "rail_color": [0.85, 0.65, 0.10],  # Safety amber/yellow
        "target_vel": 0.12,  # m/s
    },
    "input_bumper": {
        "name": "InputEndBumper",
        "size": [0.02, 0.20, 0.06],
        "position": [-0.34, 0.0, CONVEYOR_SURFACE_Z + 0.03],  # Centered at 0.73m
        "color": [0.90, 0.70, 0.10],  # Safety yellow
    },
    "output_red": {
        "name": "OutputConveyorRed",
        "position": [0.0, 0.85, CONVEYOR_SURFACE_Z],
        "orientation": [0.0, 0.0, math.pi / 2],  # Points North (+Y)
        "rail_color": [0.85, 0.15, 0.15],  # Signal red
        "target_vel": 0.12,
    },
    "output_green": {
        "name": "OutputConveyorGreen",
        "position": [0.85, 0.0, CONVEYOR_SURFACE_Z],
        "orientation": [0.0, 0.0, 0.0],  # Points East (+X)
        "rail_color": [0.15, 0.75, 0.25],  # Emerald green
        "target_vel": 0.12,
    },
    "output_blue": {
        "name": "OutputConveyorBlue",
        "position": [0.0, -0.85, CONVEYOR_SURFACE_Z],
        "orientation": [0.0, 0.0, -math.pi / 2],  # Points South (-Y)
        "rail_color": [0.15, 0.35, 0.85],  # Cobalt blue
        "target_vel": 0.12,
    },
    "camera": {
        "name": "InspectionCamera",
        "position": [-0.40, 0.0, 1.15],
        "orientation": [-math.pi / 2, 0.0, 0.0],  # Points down (-Z)
    },
    "camera_stand": {
        "pole_pos": [-0.40, 0.25, 0.575],
        "pole_size": [0.03, 0.03, 1.15],
        "arm_pos": [-0.40, 0.125, 1.15],
        "arm_size": [0.03, 0.25, 0.03],
        "color": [0.35, 0.37, 0.40],
    },
}

# Collection Bin Geometry & Configuration
BIN_DIMENSIONS = {
    "cavity_width": 0.26,     # Cross-width across conveyor (26 cm)
    "cavity_length": 0.26,    # Length along discharge direction (26 cm)
    "wall_height": 0.24,      # Wall height (24 cm, top rim at Z=0.68m)
    "wall_thickness": 0.02,   # Wall thickness (2 cm)
    "stand_height": 0.42,     # Floor stand height (42 cm)
    "stand_color": [0.22, 0.24, 0.26],  # Matte anthracite slate
}

BINS_CONFIG = [
    {
        "name": "RedCollectionBin",
        "conveyor_name": "OutputConveyorRed",
        "position": [0.0, 1.52, 0.0],
        "color": [0.85, 0.15, 0.15],  # Signal red
        "axis": "Y",
        "sign": 1,  # Discharges in +Y direction
    },
    {
        "name": "GreenCollectionBin",
        "conveyor_name": "OutputConveyorGreen",
        "position": [1.52, 0.0, 0.0],
        "color": [0.15, 0.75, 0.25],  # Emerald green
        "axis": "X",
        "sign": 1,  # Discharges in +X direction
    },
    {
        "name": "BlueCollectionBin",
        "conveyor_name": "OutputConveyorBlue",
        "position": [0.0, -1.52, 0.0],
        "color": [0.15, 0.35, 0.85],  # Cobalt blue
        "axis": "Y",
        "sign": -1,  # Discharges in -Y direction
    },
]

# Sorting Object Dimensions & Initial Poses
BLOCK_SIZE = [BLOCK_HEIGHT, BLOCK_HEIGHT, BLOCK_HEIGHT]
BLOCK_MASS = 0.05  # 50 grams

OBJECTS_CONFIG = [
    {
        "name": "RedBlock",
        "color": [0.90, 0.10, 0.10],
        "position": [-0.55, 0.0, BLOCK_REST_Z],
        "target_conveyor": "OutputConveyorRed",
    },
    {
        "name": "GreenBlock",
        "color": [0.10, 0.85, 0.20],
        "position": [-0.75, 0.0, BLOCK_REST_Z],
        "target_conveyor": "OutputConveyorGreen",
    },
    {
        "name": "BlueBlock",
        "color": [0.10, 0.30, 0.90],
        "position": [-0.95, 0.0, BLOCK_REST_Z],
        "target_conveyor": "OutputConveyorBlue",
    },
]

# Scene file output path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCENES_DIR = os.path.join(PROJECT_ROOT, "scenes")
SAVED_SCENE_FILE = os.path.join(SCENES_DIR, "sorting_factory.ttt")
