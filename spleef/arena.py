"""
SpleefArena Module
Manages multiple stacked floor layers for the Spleef game
"""

from typing import List, Tuple, Optional
import config
from spleef.floor_grid import FloorGrid
from spleef.block import Block


class SpleefArena:
    """
    Manages 2-3 stacked floor layers with vertical spacing
    Players fall through layers when blocks break beneath them
    """

    def __init__(self, center_x: float = 270, top_y: float = 200):
        """
        Initialize arena with stacked floor layers

        Args:
            center_x: Horizontal center of arena (default 270 for 540px screen)
            top_y: Y position of top layer (default 200)
        """
        self.center_x = center_x
        self.top_y = top_y

        # Get config values
        self.layer_count = getattr(config, 'SPLEEF_LAYER_COUNT', 3)
        self.layer_spacing = getattr(config, 'SPLEEF_LAYER_SPACING', 200)
        self.grid_width = getattr(config, 'SPLEEF_GRID_WIDTH', 20)
        self.grid_height = getattr(config, 'SPLEEF_GRID_HEIGHT', 15)
        self.block_size = getattr(config, 'SPLEEF_BLOCK_SIZE', 32)

        # Calculate arena dimensions
        arena_pixel_width = self.grid_width * self.block_size
        arena_pixel_height = self.grid_height * self.block_size

        # Position arena centered horizontally
        self.world_x = center_x - (arena_pixel_width / 2)

        # Create floor layers from top to bottom
        # Each layer has different Y in world space (for physics)
        # Renderer will normalize Y positions for visual stacking
        self.layers: List[FloorGrid] = []
        self.base_layer_y = top_y  # Store base Y (top layer)
        for i in range(self.layer_count):
            # Each layer gets its own Y position for physics
            layer_y = top_y + (i * self.layer_spacing)
            layer = FloorGrid(
                layer_index=i,
                world_x=self.world_x,
                world_y=layer_y  # Each layer at different Y
            )
            self.layers.append(layer)
            print(f"  Layer {i}: {len(layer.blocks)} blocks created at world_y={layer_y}")

    def get_layer(self, layer_index: int) -> Optional[FloorGrid]:
        """
        Get floor grid at specific layer

        Args:
            layer_index: Layer index (0=top, 1=middle, 2=bottom)

        Returns:
            FloorGrid instance or None if index out of range
        """
        if 0 <= layer_index < len(self.layers):
            return self.layers[layer_index]
        return None

    def get_layer_y_position(self, layer_index: int) -> float:
        """
        Get Y coordinate of layer origin

        Args:
            layer_index: Layer index

        Returns:
            World Y position of layer top-left corner
        """
        return self.top_y + (layer_index * self.layer_spacing)

    def get_block_at_position(self, world_x: float, world_y: float, layer_index: int) -> Optional[Block]:
        """
        Get block at world position on specific layer

        Args:
            world_x: World X position
            world_y: World Y position
            layer_index: Which layer to check

        Returns:
            Block instance or None
        """
        layer = self.get_layer(layer_index)
        if layer:
            return layer.get_block_at_world_pos(world_x, world_y)
        return None

    def determine_player_layer(self, player_y: float) -> int:
        """
        Determine which layer a player is currently on based on Y position

        Args:
            player_y: Player's world Y position

        Returns:
            Layer index (0=top, 1=middle, 2=bottom, etc.)
            Returns last layer if below all layers
        """
        for i in range(len(self.layers) - 1):
            layer_y = self.get_layer_y_position(i)
            next_layer_y = self.get_layer_y_position(i + 1)

            # Player is on this layer if between this layer and next
            if layer_y <= player_y < next_layer_y:
                return i

        # Player is on bottom layer (or has fallen below)
        return len(self.layers) - 1

    def get_spawn_positions(self, num_players: int) -> List[Tuple[float, float, int]]:
        """
        Generate spawn positions distributed across top layer

        Args:
            num_players: Number of players to spawn

        Returns:
            List of (world_x, world_y, layer_index) tuples
        """
        spawn_positions = []
        top_layer = self.layers[0]
        layer_y = self.get_layer_y_position(0)

        # Calculate grid spacing for even distribution
        # Leave 1-block border on all sides
        usable_width = self.grid_width - 2
        usable_height = self.grid_height - 2

        # Distribute players in a grid pattern
        import math
        cols = math.ceil(math.sqrt(num_players * usable_width / usable_height))
        rows = math.ceil(num_players / cols)

        x_spacing = usable_width / (cols + 1) if cols > 1 else usable_width / 2
        y_spacing = usable_height / (rows + 1) if rows > 1 else usable_height / 2

        player_idx = 0
        for row in range(rows):
            for col in range(cols):
                if player_idx >= num_players:
                    break

                # Calculate grid position (with 1-block border offset)
                grid_x = int(1 + (col + 1) * x_spacing)
                grid_y = int(1 + (row + 1) * y_spacing)

                # Convert to world position (center of block)
                world_x, world_y = top_layer.grid_to_world(grid_x, grid_y)

                spawn_positions.append((world_x, world_y, 0))  # layer_index=0
                player_idx += 1

            if player_idx >= num_players:
                break

        return spawn_positions

    def update(self, players: List, dt: float):
        """
        Update all floor layers and handle layer collapse

        If a layer has less than 5% of alive players, random blocks start disappearing
        to force remaining players down to lower layers.

        Args:
            players: List of SpleefPlayer instances
            dt: Delta time in seconds
        """
        # Update all layers
        for layer in self.layers:
            layer.update(players, dt)

        # Check for layer collapse (< 5% of players on a layer that still has players)
        alive_players = [p for p in players if p.alive]
        total_alive = len(alive_players)

        if total_alive == 0:
            return

        # Count players on each layer
        players_per_layer = {}
        for layer_index in range(len(self.layers)):
            players_per_layer[layer_index] = sum(1 for p in alive_players if p.current_layer == layer_index)

        # Find highest layer (smallest index) that has players
        highest_occupied_layer = None
        for layer_index in range(len(self.layers)):
            if players_per_layer[layer_index] > 0:
                highest_occupied_layer = layer_index
                break

        # If highest occupied layer has < 5% of alive players, start collapsing it
        if highest_occupied_layer is not None:
            players_on_top = players_per_layer[highest_occupied_layer]
            percentage = (players_on_top / total_alive) * 100

            if percentage < 5.0 and percentage > 0:  # Less than 5% but not empty
                # Start removing random blocks from this layer
                self._collapse_layer(highest_occupied_layer, dt, percentage)

    def _collapse_layer(self, layer_index: int, dt: float, percentage: float):
        """
        Remove random blocks from a layer to force players down

        Speed varies based on player percentage:
        - < 1%: Very rapid (0.05 seconds between blocks)
        - 1-5%: Normal speed (0.5 seconds between blocks)

        Args:
            layer_index: Layer to collapse
            dt: Delta time
            percentage: Percentage of alive players on this layer
        """
        import random
        import time

        layer = self.get_layer(layer_index)
        if not layer:
            return

        # Track last collapse time per layer
        if not hasattr(self, '_last_collapse_time'):
            self._last_collapse_time = {}

        current_time = time.time()
        last_collapse = self._last_collapse_time.get(layer_index, 0)

        # Adjust collapse speed based on player percentage
        if percentage < 1.0:
            # Very rapid collapse when < 1% of players remain
            collapse_interval = 0.05  # 20 blocks per second (very very rapid)
        else:
            # Normal collapse speed for 1-5% range
            collapse_interval = 0.5  # 2 blocks per second

        if current_time - last_collapse >= collapse_interval:
            # Get all solid blocks
            solid_blocks = [block for block in layer.blocks.values() if block.is_solid()]

            if solid_blocks:
                # Pick random block and instantly break it
                random_block = random.choice(solid_blocks)
                random_block.state = 3  # BlockState.BROKEN
                self._last_collapse_time[layer_index] = current_time

    def get_total_solid_blocks(self) -> int:
        """
        Count total solid blocks across all layers

        Returns:
            Total number of solid blocks
        """
        return sum(layer.get_solid_block_count() for layer in self.layers)

    def get_total_blocks(self) -> int:
        """
        Count total blocks (all states) across all layers

        Returns:
            Total number of blocks
        """
        return sum(layer.get_total_block_count() for layer in self.layers)

    def is_within_bounds(self, world_x: float, world_y: float, layer_index: int) -> bool:
        """
        Check if position is within arena bounds on specific layer

        Args:
            world_x: World X position
            world_y: World Y position
            layer_index: Layer to check

        Returns:
            True if within bounds
        """
        layer = self.get_layer(layer_index)
        if layer:
            return layer.is_within_bounds(world_x, world_y)
        return False

    def __repr__(self):
        solid_blocks = self.get_total_solid_blocks()
        total_blocks = self.get_total_blocks()
        return f"SpleefArena(layers={len(self.layers)}, blocks={total_blocks}, solid={solid_blocks})"
