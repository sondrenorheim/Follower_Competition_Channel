"""
Block Module for Spleef
Manages individual block state and degradation
"""

import time
from enum import IntEnum


class BlockState(IntEnum):
    """Block degradation states"""
    INTACT = 0     # Solid, bright color, no cracks
    CRACKED = 1    # Solid, darker, small cracks visible
    BREAKING = 2   # Solid, very dark, large cracks
    BROKEN = 3     # Non-solid, removed from grid, invisible


class Block:
    """
    Represents a single floor block that can degrade over time

    State Machine (damage-based, not time-based):
    INTACT (0) -> CRACKED (1) -> BREAKING (2) -> BROKEN (3)
    Players deal 1 damage per step; total hits required to break is configurable.
    """

    def __init__(self, grid_x: int, grid_y: int, hits_to_break: int = 4):
        """
        Initialize a block

        Args:
            grid_x: Grid X coordinate
            grid_y: Grid Y coordinate
            hits_to_break: Total hits required to reach BROKEN
        """
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.state = BlockState.INTACT
        self.last_stepped_time = 0.0
        self.hits_to_break = max(1, hits_to_break)
        self.damage_taken = 0

    def step_on(self):
        """
        Deal 1 damage to this block
        Each call advances the block based on configured durability
        """
        if self.state == BlockState.BROKEN:
            return

        self.damage_taken += 1
        self.last_stepped_time = time.time()

        # Spread the three visible states evenly across the required hit count
        # progress_stage: 0=intact, 1=cracked, 2=breaking, 3=broken
        progress_stage = int((self.damage_taken * 3) // self.hits_to_break)
        progress_stage = min(progress_stage, BlockState.BROKEN)
        self.state = BlockState(progress_stage)

    def update(self, dt: float):
        """
        Update block state based on elapsed time

        Note: Blocks no longer auto-progress through states.
        State changes only happen when step_on() is called.

        Args:
            dt: Delta time in seconds
        """
        # Blocks are now damage-based, not time-based
        # No automatic state progression
        pass

    def is_solid(self) -> bool:
        """
        Check if block can support player weight

        Returns:
            True if block is solid (states 0-2), False if broken
        """
        return self.state < BlockState.BROKEN

    def __repr__(self):
        return f"Block({self.grid_x}, {self.grid_y}, state={self.state.name})"
