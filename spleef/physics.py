"""
SpleefPhysics Module
Handles gravity, falling, and layer transitions for Spleef players
"""

from typing import List, Optional
import config
from spleef.arena import SpleefArena
from spleef.block import Block


class SpleefPhysics:
    """
    Manages player physics including:
    - Gravity and falling through broken blocks
    - Layer transitions when falling
    - Player elimination when falling below bottom layer
    """

    def __init__(self):
        """Initialize physics system"""
        # Get physics constants from config
        self.gravity = getattr(config, 'SPLEEF_GRAVITY', 1200.0)
        self.max_fall_speed = getattr(config, 'SPLEEF_FALL_SPEED_MAX', 800.0)
        self.move_speed = getattr(config, 'SPLEEF_MOVE_SPEED', 150.0)
        self.layer_spacing = getattr(config, 'SPLEEF_LAYER_SPACING', 200)

    def get_block_beneath_player(self, player, arena: SpleefArena) -> Optional[Block]:
        """
        Find the block directly beneath a player on their current layer

        Args:
            player: SpleefPlayer instance
            arena: SpleefArena instance

        Returns:
            Block instance or None if no block exists or player out of bounds
        """
        layer = arena.get_layer(player.current_layer)
        if not layer:
            return None

        # Get block at player's position
        block = layer.get_block_at_world_pos(player.x, player.y)
        return block

    def is_player_supported(self, player, arena: SpleefArena) -> bool:
        """
        Check if player is standing on a solid block

        When falling between layers, players should continue falling even if there's
        a solid block on the layer below, until they actually land on it.

        Args:
            player: SpleefPlayer instance
            arena: SpleefArena instance

        Returns:
            True if standing on solid block, False otherwise
        """
        # If player is in falling state, they're not supported yet
        # They need to reach the layer surface before they can land
        if player.is_falling:
            layer_y = arena.get_layer_y_position(player.current_layer)
            # Only consider supported if player has reached or passed the layer surface
            if player.y < layer_y + 10:  # Small margin (10 pixels past layer surface)
                return False

        block = self.get_block_beneath_player(player, arena)
        if block and block.is_solid():
            # Player has landed - clear falling state
            player.is_falling = False
            return True
        else:
            # No solid block beneath - player is falling
            player.is_falling = True
            return False

    def apply_gravity(self, player, dt: float):
        """
        Apply gravity to falling player

        Args:
            player: SpleefPlayer instance
            dt: Delta time in seconds
        """
        # Increase downward velocity
        player.vy += self.gravity * dt

        # Clamp to max fall speed
        if player.vy > self.max_fall_speed:
            player.vy = self.max_fall_speed

    def update_player_position(self, player, arena: SpleefArena, dt: float):
        """
        Update player position based on velocity

        Note: Players have two types of Y velocity:
        - vy_move: Horizontal movement on the platform (controlled by AI)
        - vy: Vertical falling due to gravity (controlled by physics)

        When supported by a block, only vy_move is applied.
        When falling, vy (gravity) takes over.

        Args:
            player: SpleefPlayer instance
            arena: SpleefArena instance
            dt: Delta time in seconds
        """
        # Check if player is supported (on solid ground)
        is_supported = self.is_player_supported(player, arena)

        if is_supported:
            # Player is on solid ground - apply horizontal movement only
            new_x = player.x + player.vx * dt
            new_y = player.y + player.vy_move * dt
        else:
            # Player is falling - apply horizontal movement + gravity
            new_x = player.x + player.vx * dt
            new_y = player.y + player.vy * dt

        # Clamp position to arena bounds (prevent walking off platform)
        # Only apply clamping when player is on solid ground, not when falling
        layer = arena.get_layer(player.current_layer)
        if layer and is_supported:
            left, top, right, bottom = layer.get_bounds()

            # Clamp X within bounds
            if new_x < left:
                new_x = left
                player.vx = 0
            elif new_x > right:
                new_x = right
                player.vx = 0

            # Clamp Y within bounds
            if new_y < top:
                new_y = top
                player.vy_move = 0
            elif new_y > bottom:
                new_y = bottom
                player.vy_move = 0

        player.x = new_x
        player.y = new_y

    def check_layer_transition(self, player, arena: SpleefArena) -> bool:
        """
        Check if player has fallen to the next layer's Y position

        Players fall naturally with gravity, and when they reach the next layer's
        Y coordinate, we update their current_layer assignment.

        Args:
            player: SpleefPlayer instance
            arena: SpleefArena instance

        Returns:
            True if player transitioned or was eliminated, False otherwise
        """
        # Check if there's a next layer
        next_layer = player.current_layer + 1

        if next_layer < len(arena.layers):
            # Get next layer's Y position
            next_layer_y = arena.get_layer_y_position(next_layer)

            # If player has fallen past the next layer's Y position, transition them
            if player.y >= next_layer_y:
                # Update layer assignment (player continues falling naturally)
                player.current_layer = next_layer
                # Ensure player stays in falling state during transition
                player.is_falling = True
                return True
        else:
            # No more layers below - check if player has fallen beyond bottom layer
            bottom_layer_y = arena.get_layer_y_position(len(arena.layers) - 1)

            # If fallen 200 pixels below bottom layer, eliminate
            if player.y >= bottom_layer_y + self.layer_spacing:
                if player.alive:
                    player.eliminate()
                return True

        return False

    def snap_to_surface(self, player, arena: SpleefArena):
        """
        Stop vertical falling velocity when player is on solid ground

        Note: Don't override Y position - players need to move freely on the platform
        Only reset the falling velocity (vy) to stop gravity

        Args:
            player: SpleefPlayer instance
            arena: SpleefArena instance
        """
        # Just reset falling velocity - don't override position
        # Players can move freely in X and Y on the platform surface
        player.vy = 0

    def update_player_physics(self, player, arena: SpleefArena, dt: float):
        """
        Main physics update for a single player

        Args:
            player: SpleefPlayer instance
            arena: SpleefArena instance
            dt: Delta time in seconds
        """
        if not player.alive:
            return

        # Check if player is supported by a solid block
        is_supported = self.is_player_supported(player, arena)

        if is_supported:
            # Player is on solid ground
            self.snap_to_surface(player, arena)
        else:
            # Player is falling
            self.apply_gravity(player, dt)

        # Update position based on velocity
        self.update_player_position(player, arena, dt)

        # Check if player has fallen to next layer
        if not is_supported:
            self.check_layer_transition(player, arena)

    def update_all_players(self, players: List, arena: SpleefArena, dt: float):
        """
        Update physics for all players

        Args:
            players: List of SpleefPlayer instances
            arena: SpleefArena instance
            dt: Delta time in seconds
        """
        for player in players:
            self.update_player_physics(player, arena, dt)

    def apply_movement_input(self, player, direction_x: float, direction_y: float):
        """
        Apply horizontal movement input from AI

        Note: In Spleef's coordinate system:
        - X is horizontal (left/right)
        - Y is also horizontal in world space (up/down on the platform)
        - Falling is handled separately by gravity

        Args:
            player: SpleefPlayer instance
            direction_x: X direction (-1 to 1) - left/right on platform
            direction_y: Y direction (-1 to 1) - up/down on platform (NOT falling)
        """
        if not player.alive:
            return

        # Normalize diagonal movement
        import math
        magnitude = math.sqrt(direction_x**2 + direction_y**2)
        if magnitude > 0:
            direction_x /= magnitude
            direction_y /= magnitude

        # Set horizontal velocities
        player.vx = direction_x * self.move_speed
        player.vy_move = direction_y * self.move_speed

    def __repr__(self):
        return f"SpleefPhysics(gravity={self.gravity}, max_fall={self.max_fall_speed}, speed={self.move_speed})"
