"""
Dynamic Object Spawner & Lifecycle Tracking Module (Phase 5)
Manages dynamic generation, unique identification, physical attributes,
and state lifecycle tracking of sorting cuboids on the Input Conveyor.
"""

import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any

import config.settings as cfg


class ObjectState(str, Enum):
    """Lifecycle states of an object in the automated sorting pipeline."""
    SPAWNED = "SPAWNED"      # Instantiated at conveyor inlet
    WAITING = "WAITING"      # Moving along input conveyor toward inspection
    DETECTED = "DETECTED"    # Arrived at bumper, classified by vision
    PICKED = "PICKED"        # Grasp verified and lifted into transit corridor
    PLACED = "PLACED"        # Deposited onto destination output conveyor
    SORTED = "SORTED"        # Discharged into matching collection bin
    FAILED = "FAILED"        # Dropped, missed pick, or misplaced


@dataclass
class SpawnedObject:
    """Represents a dynamically spawned physical block in CoppeliaSim."""
    id: str                                  # Unique identifier (e.g. Block_Red_001)
    handle: int                              # CoppeliaSim scene object handle
    color: str                               # 'red', 'green', or 'blue'
    color_rgb: List[float]                   # [R, G, B] normalized values
    spawn_time: float                        # Timestamp when spawned
    spawn_pos: List[float]                   # Initial [X, Y, Z] position
    size: List[float] = field(default_factory=lambda: list(cfg.BLOCK_SIZE))
    mass: float = cfg.BLOCK_MASS
    state: ObjectState = ObjectState.SPAWNED
    target_conveyor: str = ""
    target_bin: str = ""
    current_pos: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    final_pos: Optional[List[float]] = None
    state_history: List[Tuple[ObjectState, float]] = field(default_factory=list)

    def transition_to(self, new_state: ObjectState):
        """Updates object state and records timestamped transition."""
        self.state = new_state
        self.state_history.append((new_state, time.time()))


class ObjectSpawner:
    """
    Configurable dynamic object generator and lifecycle manager.
    Safely creates dynamic respondable cuboids in CoppeliaSim during runtime.
    """

    COLOR_DEFINITIONS = {
        "red": {
            "rgb": [0.90, 0.10, 0.10],
            "conveyor": "OutputConveyorRed",
            "bin": "RedCollectionBin",
        },
        "green": {
            "rgb": [0.10, 0.85, 0.20],
            "conveyor": "OutputConveyorGreen",
            "bin": "GreenCollectionBin",
        },
        "blue": {
            "rgb": [0.10, 0.30, 0.90],
            "conveyor": "OutputConveyorBlue",
            "bin": "BlueCollectionBin",
        },
    }

    # Default spawn location at the inlet end of the input conveyor
    DEFAULT_SPAWN_POS = [-1.20, 0.0, cfg.BLOCK_REST_Z + 0.015]

    def __init__(
        self,
        client: Any,
        sim: Any,
        spawn_pos: Optional[List[float]] = None,
        block_size: Optional[List[float]] = None,
        block_mass: float = cfg.BLOCK_MASS,
        color_sequence: Optional[List[str]] = None,
        color_distribution: Optional[Dict[str, float]] = None,
        min_spacing: float = 0.22,
        max_spawn_count: Optional[int] = None,
    ):
        """
        Initializes the dynamic spawner.
        
        Args:
            client: RemoteAPIClient instance.
            sim: CoppeliaSim sim module.
            spawn_pos: [X, Y, Z] coordinates where blocks appear on conveyor.
            block_size: [dx, dy, dz] cuboid dimensions.
            block_mass: Mass in kg.
            color_sequence: Optional explicit list of colors to spawn sequentially.
            color_distribution: Optional probability weights for random color selection.
            min_spacing: Minimum distance in meters required before spawning next block.
            max_spawn_count: Optional ceiling on total spawned objects.
        """
        self.client = client
        self.sim = sim
        self.spawn_pos = spawn_pos if spawn_pos is not None else list(self.DEFAULT_SPAWN_POS)
        self.block_size = block_size if block_size is not None else list(cfg.BLOCK_SIZE)
        self.block_mass = block_mass
        self.color_sequence = color_sequence
        self.color_distribution = color_distribution or {"red": 1/3, "green": 1/3, "blue": 1/3}
        self.min_spacing = min_spacing
        self.max_spawn_count = max_spawn_count

        # Internal tracking
        self.spawn_counter = 0
        self.sequence_index = 0
        self.objects: Dict[int, SpawnedObject] = {}       # handle -> SpawnedObject
        self.objects_by_id: Dict[str, SpawnedObject] = {}  # id -> SpawnedObject

    def clear_scene_initial_blocks(self):
        """
        Moves the 3 initial static scene blocks out of the active conveyor space
        so only dynamically tracked blocks participate in Phase 5 tests.
        """
        for block_alias in ["/RedBlock", "/GreenBlock", "/BlueBlock"]:
            try:
                h = self.sim.getObject(block_alias)
                self.sim.setObjectPosition(h, [-5.0, 0.0, 0.5], -1)
            except Exception:
                pass

    def is_spawn_zone_clear(self) -> bool:
        """
        Checks whether the inlet spawn area is clear of existing objects
        to prevent overlapping or uncontrolled physical collision.
        """
        for handle, obj in self.objects.items():
            try:
                p = self.sim.getObjectPosition(handle, -1)
                # Distance in X along conveyor belt
                dx = abs(p[0] - self.spawn_pos[0])
                dy = abs(p[1] - self.spawn_pos[1])
                if dx < self.min_spacing and dy < 0.10 and p[2] > 0.65:
                    return False
            except Exception:
                continue
        return True

    def select_next_color(self) -> str:
        """Determines next color using configured sequence or distribution."""
        if self.color_sequence and len(self.color_sequence) > 0:
            color = self.color_sequence[self.sequence_index % len(self.color_sequence)]
            self.sequence_index += 1
            return color.lower()

        # Weighted selection or round-robin fallback
        colors = list(self.color_distribution.keys())
        weights = [self.color_distribution[c] for c in colors]
        import random
        return random.choices(colors, weights=weights, k=1)[0].lower()

    def spawn_object(self, color_override: Optional[str] = None) -> Optional[SpawnedObject]:
        """
        Dynamically instantiates a new physical cuboid on the input conveyor.
        
        Args:
            color_override: If specified, forces this color ('red', 'green', 'blue').
            
        Returns:
            SpawnedObject instance if successful, or None if spawn zone is obstructed or max reached.
        """
        if self.max_spawn_count is not None and self.spawn_counter >= self.max_spawn_count:
            print(f" [SPAWNER] Max spawn count ({self.max_spawn_count}) reached. No further blocks will be spawned.")
            return None

        if not self.is_spawn_zone_clear():
            print(f" [SPAWNER] Spawn zone at {self.spawn_pos[0]:.2f}m is not clear. Waiting...")
            return None

        color = (color_override.lower() if color_override else self.select_next_color())
        if color not in self.COLOR_DEFINITIONS:
            raise ValueError(f"Unsupported color '{color}'. Supported: {list(self.COLOR_DEFINITIONS.keys())}")

        self.spawn_counter += 1
        obj_id = f"Block_{color.capitalize()}_{self.spawn_counter:03d}"
        color_meta = self.COLOR_DEFINITIONS[color]

        # 1. Create primitive cuboid shape in CoppeliaSim
        handle = self.sim.createPrimitiveShape(self.sim.primitiveshape_cuboid, self.block_size)

        # 2. Configure object alias and world position
        self.sim.setObjectAlias(handle, obj_id)
        self.sim.setObjectPosition(handle, self.spawn_pos, -1)
        self.sim.setObjectOrientation(handle, [0.0, 0.0, 0.0], -1)

        # 3. Apply ambient/diffuse color
        self.sim.setShapeColor(handle, None, self.sim.colorcomponent_ambient_diffuse, color_meta["rgb"])

        # 4. Configure dynamic physics attributes
        self.sim.setObjectInt32Param(handle, self.sim.shapeintparam_static, 0)
        self.sim.setObjectInt32Param(handle, self.sim.shapeintparam_respondable, 1)
        self.sim.setShapeMass(handle, self.block_mass)

        # 5. Build tracked object record
        obj = SpawnedObject(
            id=obj_id,
            handle=handle,
            color=color,
            color_rgb=color_meta["rgb"],
            spawn_time=time.time(),
            spawn_pos=list(self.spawn_pos),
            size=list(self.block_size),
            mass=self.block_mass,
            state=ObjectState.SPAWNED,
            target_conveyor=color_meta["conveyor"],
            target_bin=color_meta["bin"],
            current_pos=list(self.spawn_pos),
        )
        obj.transition_to(ObjectState.WAITING)

        self.objects[handle] = obj
        self.objects_by_id[obj_id] = obj

        print(
            f" [+] Spawned {obj_id} (Handle: {handle}, Color: {color.upper()}) "
            f"at {[round(x, 3) for x in self.spawn_pos]}"
        )
        return obj

    def get_object(self, handle: int) -> Optional[SpawnedObject]:
        """Retrieves tracked object metadata by handle."""
        return self.objects.get(handle)

    def get_object_by_id(self, obj_id: str) -> Optional[SpawnedObject]:
        """Retrieves tracked object metadata by custom ID."""
        return self.objects_by_id.get(obj_id)

    def get_objects_in_state(self, state: ObjectState) -> List[SpawnedObject]:
        """Returns all tracked objects currently in the specified state."""
        return [o for o in self.objects.values() if o.state == state]

    def update_positions(self):
        """Refreshes current positions of all active objects from simulation."""
        for handle, obj in list(self.objects.items()):
            try:
                p = self.sim.getObjectPosition(handle, -1)
                obj.current_pos = [round(x, 4) for x in p]
            except Exception:
                pass

    def destroy_all(self):
        """Safely removes all dynamically created objects from the simulation."""
        for handle in list(self.objects.keys()):
            try:
                self.sim.removeObject(handle)
            except Exception:
                pass
        self.objects.clear()
        self.objects_by_id.clear()
        self.spawn_counter = 0
        self.sequence_index = 0
