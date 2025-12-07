"""
FloorGrid Module for Spleef
Manages a 2D sparse grid of blocks
"""

from typing import Dict, Tuple, Optional, List
import config
from spleef.block import Block, BlockState


class FloorGrid:
    """
    Manages a 2D grid of blocks using sparse storage
    Only stores existing blocks; broken blocks are removed from the dictionary
    """

    def __init__(self, layer_index: int, world_x: float, world_y: float):
        """
        Initialize floor grid

        Args:
            layer_index: Index of this layer (0=top, 1=middle, 2=bottom)
            world_x: Top-left world X coordinate
            world_y: Top-left world Y coordinate
        """
        self.layer_index = layer_index
        self.world_x = world_x
        self.world_y = world_y

        # Get grid dimensions from config
        self.grid_width = getattr(config, 'SPLEEF_GRID_WIDTH', 20)
        self.grid_height = getattr(config, 'SPLEEF_GRID_HEIGHT', 15)
        self.block_size = getattr(config, 'SPLEEF_BLOCK_SIZE', 32)

        # Sparse grid storage: only store existing blocks
        self.blocks: Dict[Tuple[int, int], Block] = {}

        # Track initial block count for total count reporting
        self.initial_block_count = self.grid_width * self.grid_height

        # Initialize all blocks as intact
        self._create_all_blocks()

    def _create_all_blocks(self):
        """Create all blocks in intact state"""
        for grid_y in range(self.grid_height):
            for grid_x in range(self.grid_width):
                block = Block(grid_x, grid_y)
                self.blocks[(grid_x, grid_y)] = block

    def get_block(self, grid_x: int, grid_y: int) -> Optional[Block]:
        """
        Get block at grid coordinates

        Args:
            grid_x: Grid X coordinate
            grid_y: Grid Y coordinate

        Returns:
            Block instance or None if no block exists
        """
        return self.blocks.get((grid_x, grid_y))

    def remove_block(self, grid_x: int, grid_y: int):
        """
        Remove block from grid (called when block breaks)

        Args:
            grid_x: Grid X coordinate
            grid_y: Grid Y coordinate
        """
        key = (grid_x, grid_y)
        if key in self.blocks:
            del self.blocks[key]

    def world_to_grid(self, world_x: float, world_y: float) -> Tuple[int, int]:
        """
        Convert world coordinates to grid coordinates

        Args:
            world_x: World X position
            world_y: World Y position

        Returns:
            (grid_x, grid_y) tuple
        """
        grid_x = int((world_x - self.world_x) / self.block_size)
        grid_y = int((world_y - self.world_y) / self.block_size)
        return (grid_x, grid_y)

    def grid_to_world(self, grid_x: int, grid_y: int) -> Tuple[float, float]:
        """
        Convert grid coordinates to world coordinates (center of block)

        Args:
            grid_x: Grid X coordinate
            grid_y: Grid Y coordinate

        Returns:
            (world_x, world_y) tuple pointing to block center
        """
        world_x = self.world_x + (grid_x * self.block_size) + (self.block_size / 2)
        world_y = self.world_y + (grid_y * self.block_size) + (self.block_size / 2)
        return (world_x, world_y)

    def get_block_at_world_pos(self, world_x: float, world_y: float) -> Optional[Block]:
        """
        Get block at world position

        Args:
            world_x: World X position
            world_y: World Y position

        Returns:
            Block instance or None if out of bounds or no block exists
        """
        grid_x, grid_y = self.world_to_grid(world_x, world_y)

        # Check bounds
        if (grid_x < 0 or grid_x >= self.grid_width or
            grid_y < 0 or grid_y >= self.grid_height):
            return None

        return self.get_block(grid_x, grid_y)

    def get_solid_block_count(self) -> int:
        """
        Count remaining solid blocks

        Returns:
            Number of blocks that are not broken
        """
        return sum(1 for block in self.blocks.values() if block.is_solid())

    def get_total_block_count(self) -> int:
        """
        Get total number of blocks (initial grid size, not current count)

        Returns:
            Total blocks in grid (initial count)
        """
        return self.initial_block_count

    def update(self, players: List, dt: float):
        """
        Update all blocks in this grid

        Note: Block damage is now handled by AI system, not by standing on blocks

        Args:
            players: List of SpleefPlayer instances
            dt: Delta time in seconds
        """
        blocks_to_remove = []

        for block in list(self.blocks.values()):
            # Update block state (currently does nothing, blocks are damage-based)
            block.update(dt)

            # Mark broken blocks for removal
            if block.state == BlockState.BROKEN:
                blocks_to_remove.append((block.grid_x, block.grid_y))

        # Remove broken blocks from grid
        for grid_x, grid_y in blocks_to_remove:
            self.remove_block(grid_x, grid_y)

    def get_bounds(self) -> Tuple[float, float, float, float]:
        """
        Get world space bounds of this grid (center of edge blocks)

        Returns:
            (left, top, right, bottom) in world coordinates
        """
        # Get center of first and last blocks (not layer origin)
        half_block = self.block_size / 2

        # First block center
        left = self.world_x + half_block
        top = self.world_y + half_block

        # Last block center
        right = self.world_x + (self.grid_width - 1) * self.block_size + half_block
        bottom = self.world_y + (self.grid_height - 1) * self.block_size + half_block

        return (left, top, right, bottom)

    def is_within_bounds(self, world_x: float, world_y: float) -> bool:
        """
        Check if world position is within grid bounds

        Args:
            world_x: World X position
            world_y: World Y position

        Returns:
            True if position is within bounds
        """
        left, top, right, bottom = self.get_bounds()
        return left <= world_x <= right and top <= world_y <= bottom

    def __repr__(self):
        solid_count = self.get_solid_block_count()
        total_count = self.get_total_block_count()
        return f"FloorGrid(layer={self.layer_index}, blocks={total_count}, solid={solid_count})"
