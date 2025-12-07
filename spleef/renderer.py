"""
SpleefRenderer Module
Handles isometric 2.5D rendering with depth sorting
"""

import math
from typing import List, Tuple
from PIL import Image, ImageDraw, ImageFont
import config
from spleef.arena import SpleefArena
from spleef.player import SpleefPlayer
from spleef.block import Block, BlockState


class SpleefRenderer:
    """
    Renders Spleef game in isometric 2.5D perspective

    Coordinate system:
    - World space: (x, y) in pixels
    - Isometric space: Rotated 45° with depth
    - Screen space: Final pixel positions for rendering
    """

    def __init__(self, width: int = 540, height: int = 960):
        """
        Initialize renderer

        Args:
            width: Screen width in pixels
            height: Screen height in pixels
        """
        self.width = width
        self.height = height

        # Isometric projection parameters
        self.iso_angle = math.radians(getattr(config, 'SPLEEF_ISO_ANGLE', 30))
        self.iso_scale = 0.8  # Scale factor (increased from 0.6 to make blocks more visible)
        self.layer_visual_offset = getattr(config, 'SPLEEF_LAYER_VISUAL_OFFSET', 150)

        # Screen center for projection
        # Position to center platforms on screen vertically and horizontally
        self.screen_center_x = width // 2 + 70  # Shifted right by 70 pixels to center better
        self.screen_center_y = height // 2 - 450  # Move platforms higher up (increased from -400 to -450)

        # Layer colors (brightest=top, darkest=bottom)
        self.layer_colors = getattr(config, 'SPLEEF_LAYER_COLORS', {
            0: (220, 220, 255),  # Top - bright blue-white
            1: (180, 180, 220),  # Middle - medium blue-grey
            2: (140, 140, 180),  # Bottom - dark blue-grey
        })

        # Font for text rendering
        try:
            self.font = ImageFont.truetype("arial.ttf", 16)
            self.font_small = ImageFont.truetype("arial.ttf", 12)
        except:
            self.font = ImageFont.load_default()
            self.font_small = ImageFont.load_default()

    def world_to_isometric(self, world_x: float, world_y: float, layer_index: int,
                          layer_base_y: float = None, arena = None) -> Tuple[float, float]:
        """
        Convert world coordinates to isometric screen coordinates

        Note: world_y varies by layer in physics space (200, 325, 450),
        but we normalize it to a common base for rendering so layers stack vertically only.

        Args:
            world_x: World X position
            world_y: World Y position (physics space)
            layer_index: Layer index (for vertical stacking)
            layer_base_y: Base Y position for normalization (optional)
            arena: Arena instance for getting layer positions (optional)

        Returns:
            (screen_x, screen_y) tuple
        """
        # Normalize Y coordinate: all layers should render as if at same Y position
        # This prevents diagonal offset while maintaining physics accuracy
        if arena is not None:
            # Get the actual layer Y position in physics space
            layer_actual_y = arena.get_layer_y_position(layer_index)
            # Calculate offset within layer
            y_offset = world_y - layer_actual_y
            # Normalize to base layer Y (top layer at 200)
            normalized_y = arena.base_layer_y + y_offset
        else:
            # Fallback if no arena provided
            normalized_y = world_y

        # Apply isometric projection using normalized Y
        iso_x = (world_x - normalized_y) * math.cos(self.iso_angle)
        iso_y = (world_x + normalized_y) * math.sin(self.iso_angle)

        # Apply layer depth offset (lower layers appear BELOW on screen)
        # This is the ONLY vertical stacking - layers are at same X,Y in world
        iso_y += layer_index * self.layer_visual_offset

        # Scale and translate to screen space
        screen_x = self.screen_center_x + (iso_x * self.iso_scale)
        screen_y = self.screen_center_y + (iso_y * self.iso_scale)

        return (screen_x, screen_y)

    def get_block_color(self, block: Block, base_color: Tuple[int, int, int]) -> Tuple[int, int, int]:
        """
        Get block color based on degradation state

        Args:
            block: Block instance
            base_color: Base color for this layer

        Returns:
            RGB color tuple
        """
        if block.state == BlockState.INTACT:
            # Full brightness
            return base_color
        elif block.state == BlockState.CRACKED:
            # 80% brightness, slight darkening
            return tuple(int(c * 0.8) for c in base_color)
        elif block.state == BlockState.BREAKING:
            # 60% brightness, significant darkening
            return tuple(int(c * 0.6) for c in base_color)
        else:  # BROKEN
            # Should not be rendered
            return (0, 0, 0)

    def draw_isometric_block(self, draw: ImageDraw.ImageDraw, block: Block, layer_index: int,
                            arena: SpleefArena):
        """
        Draw a single block in isometric perspective

        Args:
            draw: PIL ImageDraw instance
            block: Block to draw
            layer_index: Which layer this block is on
            arena: Arena instance for grid calculations
        """
        if block.state == BlockState.BROKEN:
            return  # Don't draw broken blocks

        layer = arena.get_layer(layer_index)
        if not layer:
            return

        # Get block center in world coordinates
        world_x, world_y = layer.grid_to_world(block.grid_x, block.grid_y)

        # Calculate block corners in world space
        half_size = layer.block_size / 2
        corners_world = [
            (world_x - half_size, world_y - half_size),  # Top-left
            (world_x + half_size, world_y - half_size),  # Top-right
            (world_x + half_size, world_y + half_size),  # Bottom-right
            (world_x - half_size, world_y + half_size),  # Bottom-left
        ]

        # Convert to isometric screen coordinates
        corners_screen = [
            self.world_to_isometric(wx, wy, layer_index, arena=arena)
            for wx, wy in corners_world
        ]

        # Get base color for this layer
        base_color = self.layer_colors.get(layer_index, (200, 200, 200))
        block_color = self.get_block_color(block, base_color)

        # Draw vertical depth to show stacking (all layers get 3D effect)
        depth_height = 8  # Pixels of depth to show
        if True:  # Always draw depth for 3D effect
            darker_color = tuple(int(c * 0.6) for c in block_color)

            # Right edge vertical face
            right_depth = [
                corners_screen[1],  # Top-right corner
                corners_screen[2],  # Bottom-right corner
                (corners_screen[2][0], corners_screen[2][1] + depth_height),
                (corners_screen[1][0], corners_screen[1][1] + depth_height),
            ]
            draw.polygon(right_depth, fill=darker_color, outline=(80, 80, 80))

            # Bottom edge vertical face
            bottom_depth = [
                corners_screen[2],  # Bottom-right corner
                corners_screen[3],  # Bottom-left corner
                (corners_screen[3][0], corners_screen[3][1] + depth_height),
                (corners_screen[2][0], corners_screen[2][1] + depth_height),
            ]
            draw.polygon(bottom_depth, fill=darker_color, outline=(80, 80, 80))

        # Draw top face
        draw.polygon(corners_screen, fill=block_color, outline=(100, 100, 100))

        # Draw cracks based on degradation
        if block.state == BlockState.CRACKED:
            # Small crack - single line
            cx, cy = (corners_screen[0][0] + corners_screen[2][0]) / 2, (corners_screen[0][1] + corners_screen[2][1]) / 2
            draw.line([(cx - 5, cy - 5), (cx + 5, cy + 5)], fill=(0, 0, 0), width=1)
        elif block.state == BlockState.BREAKING:
            # Large crack - X pattern
            draw.line([corners_screen[0], corners_screen[2]], fill=(0, 0, 0), width=2)
            draw.line([corners_screen[1], corners_screen[3]], fill=(0, 0, 0), width=2)

    def draw_player(self, draw: ImageDraw.ImageDraw, player: SpleefPlayer, arena):
        """
        Draw a player avatar in isometric perspective

        Args:
            draw: PIL ImageDraw instance
            player: SpleefPlayer instance
            arena: Arena instance (to get layer base Y)
        """
        if not player.alive:
            return

        # Convert player position to screen coordinates
        # world_to_isometric() handles Y normalization for us
        screen_x, screen_y = self.world_to_isometric(player.x, player.y, player.current_layer, arena=arena)

        # Draw simple circle for all players
        avatar_size = 8  # Reduced by 50% from 16
        avatar_half = avatar_size // 2

        # Draw colored circle
        bbox = [
            screen_x - avatar_half,
            screen_y - avatar_half,
            screen_x + avatar_half,
            screen_y + avatar_half
        ]
        draw.ellipse(bbox, fill=(255, 100, 100), outline=(200, 50, 50), width=1)

    def render_frame(self, arena: SpleefArena, players: List[SpleefPlayer],
                    game_time: float, phase: str) -> Image.Image:
        """
        Render a complete game frame (OPTIMIZED for performance)

        Args:
            arena: SpleefArena instance
            players: List of all players
            game_time: Current game time
            phase: Game phase ("intro", "countdown", "playing", "finished")

        Returns:
            PIL Image of rendered frame
        """
        # Create blank canvas
        img = Image.new('RGB', (self.width, self.height), (30, 30, 50))
        draw = ImageDraw.Draw(img)

        # Determine the highest layer (smallest index) with players
        # Hide layers above (with smaller indices) if they're empty
        highest_player_layer = len(arena.layers)  # Start with no layer
        for player in players:
            if player.alive and player.current_layer < highest_player_layer:
                highest_player_layer = player.current_layer

        # If no players alive, show all layers
        if highest_player_layer >= len(arena.layers):
            highest_player_layer = 0

        # Collect renderable objects with depth sorting
        render_queue = []

        # Add blocks only from layers that have players or are below them
        # This hides empty layers above to see the action below
        # Depth sorting: Higher layers (layer 0) should be drawn LAST (in front)
        # Lower layers (layer 2) should be drawn FIRST (in back)
        for layer_index, layer in enumerate(arena.layers):
            # Only render this layer if it's at or below the highest player layer
            if layer_index >= highest_player_layer:
                for block in layer.blocks.values():
                    if block.state != BlockState.BROKEN:
                        # Invert layer depth: top layer (0) gets highest depth (drawn last/in front)
                        inverted_layer = (len(arena.layers) - 1 - layer_index)
                        depth = (inverted_layer * 10000) + block.grid_x + block.grid_y
                        render_queue.append(('block', depth, block, layer_index))

        # OPTIMIZATION: Only draw nearby players (within screen bounds + margin)
        alive_count = 0
        for player in players:
            if player.alive:
                alive_count += 1
                # Simple frustum culling - only render players in reasonable range
                screen_x, screen_y = self.world_to_isometric(player.x, player.y, player.current_layer, arena=arena)
                if -100 < screen_x < self.width + 100 and -100 < screen_y < self.height + 100:
                    depth = player.get_depth_sort_key(total_layers=len(arena.layers))
                    render_queue.append(('player', depth, player, None))

        # Sort by depth (lower depth = drawn first = further back)
        render_queue.sort(key=lambda x: x[1])

        # Render all objects in sorted order
        avatars_to_paste = []
        for obj_type, depth, obj, layer_index in render_queue:
            if obj_type == 'block':
                self.draw_isometric_block(draw, obj, layer_index, arena)
            elif obj_type == 'player':
                self.draw_player(draw, obj, arena)
                # Collect avatar for pasting after drawing
                if hasattr(obj, '_render_avatar'):
                    avatars_to_paste.append(obj._render_avatar)
                    delattr(obj, '_render_avatar')

        # Paste avatars on top (SKIP for performance if too many)
        if len(avatars_to_paste) < 200:
            for avatar, pos in avatars_to_paste:
                img.paste(avatar, pos, avatar if avatar.mode == 'RGBA' else None)

        # Draw UI overlay
        self.draw_ui(draw, players, game_time, phase, arena)

        return img

    def draw_ui(self, draw: ImageDraw.ImageDraw, players: List[SpleefPlayer],
               game_time: float, phase: str, arena: SpleefArena):
        """
        Draw UI elements (timer, player count, etc.)

        Args:
            draw: PIL ImageDraw instance
            players: List of all players
            game_time: Current game time
            phase: Game phase
            arena: Arena instance
        """
        # Draw title at top
        title = "SPLEEF"
        title_width = len(title) * 20
        draw.text(
            (self.width // 2 - title_width // 2, 20),
            title,
            fill=(255, 255, 100),
            font=self.font
        )

        # Draw player count
        alive_count = sum(1 for p in players if p.alive)
        player_text = f"Players: {alive_count}/{len(players)}"
        draw.text((20, 60), player_text, fill=(255, 255, 255), font=self.font)

        # Draw block count
        solid_blocks = arena.get_total_solid_blocks()
        total_blocks = arena.get_total_blocks()
        block_percentage = (solid_blocks / total_blocks * 100) if total_blocks > 0 else 0
        block_text = f"Blocks: {solid_blocks}/{total_blocks} ({block_percentage:.1f}%)"
        draw.text((20, 90), block_text, fill=(255, 255, 255), font=self.font)

        # Draw phase-specific UI
        if phase == "countdown":
            countdown_text = f"Starting in {int(4 - game_time)}..."
            text_width = len(countdown_text) * 15
            draw.text(
                (self.width // 2 - text_width // 2, self.height // 2),
                countdown_text,
                fill=(255, 255, 0),
                font=self.font
            )
        elif phase == "finished":
            # Find winner
            winner = None
            for p in players:
                if p.placement == 1:
                    winner = p
                    break

            if winner:
                winner_text = f"Winner: {winner.display_name}!"
                text_width = len(winner_text) * 12
                draw.text(
                    (self.width // 2 - text_width // 2, self.height // 2),
                    winner_text,
                    fill=(255, 215, 0),
                    font=self.font
                )

    def __repr__(self):
        return f"SpleefRenderer({self.width}x{self.height}, iso_angle={math.degrees(self.iso_angle)}°)"
