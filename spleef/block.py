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
    INTACT (0) → CRACKED (1) → BREAKING (2) → BROKEN (3)
      1 damage     2 damages     3 damages

    Players can deal 1 damage per second by stepping on block
    """

    def __init__(self, grid_x: int, grid_y: int):
        """
        Initialize a block

        Args:
            grid_x: Grid X coordinate
            grid_y: Grid Y coordinate
        """
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.state = BlockState.INTACT
        self.last_stepped_time = 0.0

    def step_on(self):
        """
        Deal 1 damage to this block
        Each call advances the block to the next damage state

        INTACT → CRACKED → BREAKING → BROKEN
        """
        if self.state == BlockState.INTACT:
            self.state = BlockState.CRACKED
            self.last_stepped_time = time.time()
        elif self.state == BlockState.CRACKED:
            self.state = BlockState.BREAKING
            self.last_stepped_time = time.time()
        elif self.state == BlockState.BREAKING:
            self.state = BlockState.BROKEN
            self.last_stepped_time = time.time()

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
