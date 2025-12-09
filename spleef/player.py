"""
SpleefPlayer Module
Represents a player in the Spleef game with layer tracking
"""

import time
from typing import Optional


class SpleefPlayer:
    """
    Represents a single player in Spleef game

    Attributes:
        username: Instagram username
        display_name: Display name for rendering
        avatar: Profile picture (PIL Image or None)
        x, y: World position
        vx, vy: Velocity (vx=horizontal, vy=vertical/falling)
        current_layer: Which floor layer player is on (0=top, 1=middle, 2=bottom)
        alive: Whether player is still in the game
        elimination_time: When player was eliminated
        placement: Final placement (1=winner, 2=second, etc.)
        blocks_broken: Number of blocks this player has broken
    """

    def __init__(self, username: str, display_name: str, avatar=None):
        """
        Initialize a Spleef player

        Args:
            username: Instagram username
            display_name: Display name
            avatar: Profile picture (PIL Image) or None
        """
        self.username = username
        self.display_name = display_name
        self.avatar = avatar

        # Position and velocity
        self.x = 0.0
        self.y = 0.0
        self.vx = 0.0  # Horizontal velocity (X-axis movement on platform)
        self.vy_move = 0.0  # Horizontal velocity (Y-axis movement on platform)
        self.vy = 0.0  # Vertical velocity (falling/gravity)

        # Layer tracking
        self.current_layer = 0  # Start on top layer

        # Status
        self.alive = True
        self.elimination_time: Optional[float] = None
        self.placement: Optional[int] = None

        # Statistics
        self.blocks_broken = 0  # Track for scoring bonuses

        # AI state (will be set by SpleefAI)
        self.ai_target_x = 0.0
        self.ai_target_y = 0.0
        self.ai_state = "exploring"  # exploring, fleeing, attacking

        # Falling state (for smooth layer transitions)
        self.is_falling = False

        # Store grid position when falling starts (for proper layer transition)
        # This preserves the player's X/Y platform position when they drop to a lower layer
        self.fall_start_grid_x: int = 0
        self.fall_start_grid_y: int = 0

        # Random break speed modifier (±0.1 seconds variation)
        import random
        self.break_speed_modifier = random.uniform(-0.1, 0.1)

    def set_spawn_position(self, x: float, y: float, layer: int = 0):
        """
        Set initial spawn position

        Args:
            x: World X position
            y: World Y position
            layer: Initial layer index
        """
        self.x = x
        self.y = y
        self.current_layer = layer

    def eliminate(self):
        """
        Mark player as eliminated (fell through bottom layer)
        """
        if self.alive:
            self.alive = False
            self.elimination_time = time.time()

    def calculate_score(self) -> int:
        """
        Calculate player's score based on placement and blocks broken

        Returns:
            Total score (placement points + block bonus)
        """
        if self.placement is None:
            return 0

        # Placement points (decreasing by rank)
        placement_points = max(0, 1000 - (self.placement - 1) * 50)

        # Bonus points for breaking blocks
        block_bonus = self.blocks_broken * 5

        return placement_points + block_bonus

    def get_depth_sort_key(self, total_layers: int = 3) -> float:
        """
        Calculate depth sorting key for rendering (back to front)

        Returns:
            Depth value (higher = drawn later = closer to camera)
        """
        # Invert layer depth to match block rendering:
        # Top layer (0) gets highest depth (drawn last/in front)
        # Bottom layer (2) gets lowest depth (drawn first/in back)
        inverted_layer = (total_layers - 1 - self.current_layer)

        # Add slight offset to render players ABOVE blocks on same layer
        # Players should be ~100 units higher than blocks to appear on top
        return (inverted_layer * 10000) + self.x + self.y + 100

    def __repr__(self):
        status = "alive" if self.alive else f"eliminated@{self.placement}"
        return f"SpleefPlayer({self.display_name}, layer={self.current_layer}, {status})"
