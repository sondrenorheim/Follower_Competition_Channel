"""
SpleefAI Module
Handles AI decision making for player movement and block breaking
"""

import random
import math
from typing import List, Tuple, Optional, Dict
from spleef.arena import SpleefArena
from spleef.player import SpleefPlayer
from spleef.block import BlockState


class SpleefAI:
    """
    AI controller for Spleef players

    Behavior:
    - Movement decisions every 0.3 seconds (move frequently)
    - 20% chance for random movement, 80% prefer safe (solid) blocks
    - Actively tries to damage nearby blocks (within 1 block radius)
    - Can deal 1 damage per second to blocks
    - Blocks require 3 hits to break: INTACT → CRACKED → BREAKING → BROKEN
    """

    def __init__(self):
        """Initialize AI system"""
        self.movement_decision_interval = 0.3  # Make movement decisions more frequently (every 0.3s)
        self.random_movement_chance = 0.20  # 20% chance for random movement
        self.block_break_interval = 1.0  # Can damage blocks every 1 second

        # Tracking per-player state
        self.last_movement_decision = {}  # Last time player made movement decision
        self.last_block_break = {}  # Last time player broke a block
        self.current_movement_direction = {}  # Current movement direction

    def get_adjacent_blocks(self, player: SpleefPlayer, arena: SpleefArena) -> List[Tuple[int, int, object]]:
        """
        Get all blocks within 1 block radius of player

        Args:
            player: Current player
            arena: Arena instance

        Returns:
            List of (grid_x, grid_y, block) tuples
        """
        layer = arena.get_layer(player.current_layer)
        if not layer:
            return []

        # Get the block the player is currently on
        player_block = layer.get_block_at_world_pos(player.x, player.y)
        if not player_block:
            return []

        player_grid_x, player_grid_y = player_block.grid_x, player_block.grid_y

        adjacent_blocks = []

        # Check all blocks within 1 block radius (3x3 grid)
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                if dx == 0 and dy == 0:
                    continue  # Skip center (player's own block)

                grid_x = player_grid_x + dx
                grid_y = player_grid_y + dy

                block = layer.get_block(grid_x, grid_y)
                if block:
                    adjacent_blocks.append((grid_x, grid_y, block))

        return adjacent_blocks

    def try_break_nearby_block(self, player: SpleefPlayer, arena: SpleefArena, current_time: float) -> bool:
        """
        Try to break a nearby block (within 1 block radius)

        Args:
            player: Current player
            arena: Arena instance
            current_time: Current game time

        Returns:
            True if block was broken/damaged, False otherwise
        """
        # Check if enough time has passed since last break
        # Apply player's random speed modifier for variation
        last_break = self.last_block_break.get(player.username, 0)
        player_break_interval = self.block_break_interval + player.break_speed_modifier
        if current_time - last_break < player_break_interval:
            return False

        # Get adjacent blocks
        adjacent_blocks = self.get_adjacent_blocks(player, arena)

        if not adjacent_blocks:
            return False

        # Filter to blocks that can still be damaged (not broken yet)
        breakable_blocks = [
            (gx, gy, block) for gx, gy, block in adjacent_blocks
            if block.state in [BlockState.INTACT, BlockState.CRACKED, BlockState.BREAKING]
        ]

        if not breakable_blocks:
            return False

        # Pick a random breakable block
        grid_x, grid_y, block = random.choice(breakable_blocks)

        # Track if this will break the block completely
        was_breaking = (block.state == BlockState.BREAKING)

        # Deal 1 damage to the block
        block.step_on()

        # Track stats: only count as "broken" when block becomes BROKEN state
        if was_breaking and block.state == BlockState.BROKEN:
            player.blocks_broken += 1

        self.last_block_break[player.username] = current_time
        return True

    def is_block_safe(self, grid_x: int, grid_y: int, layer) -> bool:
        """
        Check if a block is safe to move to (solid)

        Args:
            grid_x: Grid X coordinate
            grid_y: Grid Y coordinate
            layer: FloorGrid layer

        Returns:
            True if block is solid, False otherwise
        """
        block = layer.get_block(grid_x, grid_y)
        return block is not None and block.is_solid()

    def find_safe_direction(self, player: SpleefPlayer, arena: SpleefArena) -> Optional[Tuple[float, float]]:
        """
        Find a safe direction to move (toward solid blocks)

        Args:
            player: Current player
            arena: Arena instance

        Returns:
            (dx, dy) normalized direction or None
        """
        layer = arena.get_layer(player.current_layer)
        if not layer:
            return None

        # Get the block the player is currently on
        player_block = layer.get_block_at_world_pos(player.x, player.y)
        if not player_block:
            return None

        # Get player's current grid position
        current_grid_x, current_grid_y = player_block.grid_x, player_block.grid_y

        # Check 4 cardinal directions
        directions = [
            (1, 0, "right"),
            (-1, 0, "left"),
            (0, 1, "down"),
            (0, -1, "up")
        ]

        safe_directions = []

        for dx, dy, name in directions:
            target_grid_x = current_grid_x + dx
            target_grid_y = current_grid_y + dy

            # Check if target block is safe
            if self.is_block_safe(target_grid_x, target_grid_y, layer):
                safe_directions.append((float(dx), float(dy)))

        # Pick random safe direction
        if safe_directions:
            return random.choice(safe_directions)

        return None

    def get_random_direction(self) -> Tuple[float, float]:
        """
        Get a completely random direction (cardinal only for grid movement)

        Returns:
            (dx, dy) normalized direction
        """
        directions = [
            (1.0, 0.0),   # right
            (-1.0, 0.0),  # left
            (0.0, 1.0),   # down
            (0.0, -1.0)   # up
        ]
        return random.choice(directions)

    def update_player_ai(self, player: SpleefPlayer, arena: SpleefArena,
                        current_time: float) -> Tuple[float, float]:
        """
        Update AI decision for a single player

        Args:
            player: Current player
            arena: Arena instance
            current_time: Current game time

        Returns:
            (direction_x, direction_y) movement direction
        """
        if not player.alive:
            return (0, 0)

        # Try to break nearby blocks every second
        self.try_break_nearby_block(player, arena, current_time)

        # Check if it's time to make a new movement decision
        last_decision = self.last_movement_decision.get(player.username, 0)
        time_since_decision = current_time - last_decision

        if time_since_decision >= self.movement_decision_interval:
            # Time to make new decision
            self.last_movement_decision[player.username] = current_time

            # 20% chance for completely random movement
            if random.random() < self.random_movement_chance:
                direction = self.get_random_direction()
            else:
                # Try to find safe direction
                direction = self.find_safe_direction(player, arena)
                if direction is None:
                    # No safe direction, move randomly
                    direction = self.get_random_direction()

            # Store current direction
            self.current_movement_direction[player.username] = direction
            return direction
        else:
            # Continue with current direction
            return self.current_movement_direction.get(player.username, (0, 0))

    def update_all_players_ai(self, players: List[SpleefPlayer], arena: SpleefArena,
                             current_time: float) -> Dict[str, Tuple[float, float]]:
        """
        Update AI for all players

        Args:
            players: List of all players
            arena: Arena instance
            current_time: Current game time

        Returns:
            Dictionary mapping player username to (direction_x, direction_y)
        """
        decisions = {}

        for player in players:
            direction = self.update_player_ai(player, arena, current_time)
            decisions[player.username] = direction

        return decisions

    def __repr__(self):
        return f"SpleefAI(move_interval={self.movement_decision_interval}s, break_interval={self.block_break_interval}s)"
