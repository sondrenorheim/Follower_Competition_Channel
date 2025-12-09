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

        # Get layer color for the outer border
        layer_color = self.layer_colors.get(player.current_layer, (200, 200, 200))

        # Draw outer border circle (layer color)
        border_size = 10  # Outer border size
        border_half = border_size // 2
        border_bbox = [
            screen_x - border_half,
            screen_y - border_half,
            screen_x + border_half,
            screen_y + border_half
        ]
        draw.ellipse(border_bbox, fill=layer_color, outline=layer_color)

        # Draw inner circle (player color - red)
        avatar_size = 6  # Inner circle
        avatar_half = avatar_size // 2
        bbox = [
            screen_x - avatar_half,
            screen_y - avatar_half,
            screen_x + avatar_half,
            screen_y + avatar_half
        ]
        draw.ellipse(bbox, fill=(255, 100, 100), outline=(200, 50, 50), width=1)

    def calculate_layer_opacity(self, layer_index: int, players: List[SpleefPlayer],
                                 highest_player_layer: int, total_layers: int) -> int:
        """
        Calculate opacity for a layer based on player distribution.

        Layers with many players: fully opaque (255)
        Layers with few/no players above action: more transparent

        Args:
            layer_index: Which layer (0=top)
            players: All players
            highest_player_layer: Topmost layer with players
            total_layers: Total number of layers

        Returns:
            Alpha value 0-255
        """
        # Check if transparency is enabled
        if not getattr(config, 'SPLEEF_USE_LAYER_TRANSPARENCY', True):
            return 255

        alive_players = [p for p in players if p.alive]
        total_alive = len(alive_players)

        if total_alive == 0:
            return 255  # Fully opaque if no players

        # Count players on this specific layer
        players_on_layer = sum(1 for p in alive_players if p.current_layer == layer_index)

        # Calculate what percentage of alive players are on this layer
        layer_percentage = players_on_layer / total_alive if total_alive > 0 else 0

        # Layers below the main action layer are always fully opaque
        if layer_index > highest_player_layer:
            return 255

        # Layer at the main action - mostly opaque
        if layer_index == highest_player_layer:
            return 255

        # Layers ABOVE the action (should be somewhat transparent)
        # These are layers with smaller indices than highest_player_layer
        min_opacity = getattr(config, 'SPLEEF_LAYER_MIN_OPACITY', 80)
        max_opacity = getattr(config, 'SPLEEF_LAYER_MAX_OPACITY', 255)

        # If this layer has players, make it more opaque based on player percentage
        if players_on_layer > 0:
            # Scale opacity: more players = more opaque
            opacity = min_opacity + int((max_opacity - min_opacity) * min(layer_percentage * 3, 1.0))
        else:
            # Empty layer above action - very transparent
            opacity = min_opacity

        return opacity

    def draw_isometric_block_rgba(self, draw: ImageDraw.ImageDraw, block: Block,
                                   layer_index: int, arena: SpleefArena, alpha: int):
        """
        Draw a single block in isometric perspective with transparency support.

        Args:
            draw: PIL ImageDraw instance (on RGBA surface)
            block: Block to draw
            layer_index: Which layer this block is on
            arena: Arena instance for grid calculations
            alpha: Alpha value 0-255
        """
        if block.state == BlockState.BROKEN:
            return

        layer = arena.get_layer(layer_index)
        if not layer:
            return

        # Get block center in world coordinates
        world_x, world_y = layer.grid_to_world(block.grid_x, block.grid_y)

        # Calculate block corners in world space
        half_size = layer.block_size / 2
        corners_world = [
            (world_x - half_size, world_y - half_size),
            (world_x + half_size, world_y - half_size),
            (world_x + half_size, world_y + half_size),
            (world_x - half_size, world_y + half_size),
        ]

        # Convert to isometric screen coordinates
        corners_screen = [
            self.world_to_isometric(wx, wy, layer_index, arena=arena)
            for wx, wy in corners_world
        ]

        # Get base color for this layer
        base_color = self.layer_colors.get(layer_index, (200, 200, 200))
        block_color = self.get_block_color(block, base_color)

        # Convert colors to RGBA
        block_color_rgba = (*block_color, alpha)
        darker_color = tuple(int(c * 0.6) for c in block_color)
        darker_color_rgba = (*darker_color, alpha)
        outline_rgba = (100, 100, 100, alpha)
        dark_outline_rgba = (80, 80, 80, alpha)

        # Draw vertical depth (3D effect)
        depth_height = 8
        right_depth = [
            corners_screen[1],
            corners_screen[2],
            (corners_screen[2][0], corners_screen[2][1] + depth_height),
            (corners_screen[1][0], corners_screen[1][1] + depth_height),
        ]
        draw.polygon(right_depth, fill=darker_color_rgba, outline=dark_outline_rgba)

        bottom_depth = [
            corners_screen[2],
            corners_screen[3],
            (corners_screen[3][0], corners_screen[3][1] + depth_height),
            (corners_screen[2][0], corners_screen[2][1] + depth_height),
        ]
        draw.polygon(bottom_depth, fill=darker_color_rgba, outline=dark_outline_rgba)

        # Draw top face
        draw.polygon(corners_screen, fill=block_color_rgba, outline=outline_rgba)

        # Draw cracks based on degradation
        crack_color = (0, 0, 0, alpha)
        if block.state == BlockState.CRACKED:
            cx = (corners_screen[0][0] + corners_screen[2][0]) / 2
            cy = (corners_screen[0][1] + corners_screen[2][1]) / 2
            draw.line([(cx - 5, cy - 5), (cx + 5, cy + 5)], fill=crack_color, width=1)
        elif block.state == BlockState.BREAKING:
            draw.line([corners_screen[0], corners_screen[2]], fill=crack_color, width=2)
            draw.line([corners_screen[1], corners_screen[3]], fill=crack_color, width=2)

    def draw_layer_to_surface(self, layer_index: int, arena: SpleefArena, alpha: int) -> Image.Image:
        """
        Draw a single layer to an RGBA surface with specified alpha.

        Args:
            layer_index: Which layer to draw
            arena: Arena instance
            alpha: Alpha value 0-255

        Returns:
            RGBA Image with the layer rendered
        """
        # Create transparent surface
        layer_img = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer_img)

        layer = arena.get_layer(layer_index)
        if not layer:
            return layer_img

        # Collect blocks and sort by depth within layer
        blocks_to_draw = []
        for block in layer.blocks.values():
            if block.state != BlockState.BROKEN:
                depth = block.grid_x + block.grid_y
                blocks_to_draw.append((depth, block))

        # Sort by depth (back to front within layer)
        blocks_to_draw.sort(key=lambda x: x[0])

        # Draw all blocks on this layer
        for depth, block in blocks_to_draw:
            self.draw_isometric_block_rgba(draw, block, layer_index, arena, alpha)

        return layer_img

    def render_frame(self, arena: SpleefArena, players: List[SpleefPlayer],
                    game_time: float, phase: str) -> Image.Image:
        """
        Render a complete game frame with progressive layer transparency.

        Uses RGBA compositing to render layers with varying opacity based on
        player distribution, allowing visibility of players on lower layers.

        Args:
            arena: SpleefArena instance
            players: List of all players
            game_time: Current game time
            phase: Game phase ("intro", "countdown", "playing", "finished")

        Returns:
            PIL Image of rendered frame
        """
        # Check if transparency is enabled - use fast path if not
        use_transparency = getattr(config, 'SPLEEF_USE_LAYER_TRANSPARENCY', True)

        # Create RGBA canvas for compositing
        img = Image.new('RGBA', (self.width, self.height), (30, 30, 50, 255))

        # Determine the highest layer (smallest index) with players
        highest_player_layer = len(arena.layers)
        for player in players:
            if player.alive and player.current_layer < highest_player_layer:
                highest_player_layer = player.current_layer

        # If no players alive, show all layers
        if highest_player_layer >= len(arena.layers):
            highest_player_layer = 0

        # Render layers from bottom to top (highest index first, then lower indices)
        # This ensures proper back-to-front compositing
        for layer_index in range(len(arena.layers) - 1, -1, -1):
            # Skip layers above the highest player layer (existing hide logic)
            if layer_index < highest_player_layer:
                continue

            # Calculate opacity for this layer
            if use_transparency:
                alpha = self.calculate_layer_opacity(
                    layer_index, players, highest_player_layer, len(arena.layers)
                )
            else:
                alpha = 255

            # Draw layer to separate surface and composite
            layer_surface = self.draw_layer_to_surface(layer_index, arena, alpha)
            img = Image.alpha_composite(img, layer_surface)

        # Draw players on a separate surface (always fully opaque)
        player_surface = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
        player_draw = ImageDraw.Draw(player_surface)

        # Collect and sort players by depth
        player_render_list = []
        for player in players:
            if player.alive:
                screen_x, screen_y = self.world_to_isometric(
                    player.x, player.y, player.current_layer, arena=arena
                )
                if -100 < screen_x < self.width + 100 and -100 < screen_y < self.height + 100:
                    depth = player.get_depth_sort_key(total_layers=len(arena.layers))
                    player_render_list.append((depth, player))

        # Sort players by depth (back to front)
        player_render_list.sort(key=lambda x: x[0])

        # Draw all players
        for depth, player in player_render_list:
            self.draw_player(player_draw, player, arena)

        # Composite players on top
        img = Image.alpha_composite(img, player_surface)

        # Convert to RGB for final output
        img_rgb = img.convert('RGB')
        draw = ImageDraw.Draw(img_rgb)

        # Draw UI overlay
        self.draw_ui(draw, players, game_time, phase, arena)

        return img_rgb

    def draw_layer_indicator_panel(self, draw: ImageDraw.ImageDraw,
                                    arena: SpleefArena,
                                    players: List[SpleefPlayer]):
        """
        Draw side panel showing player distribution across layers.

        Args:
            draw: PIL ImageDraw instance
            arena: Arena instance
            players: List of all players
        """
        # Check if panel is enabled
        if not getattr(config, 'SPLEEF_SHOW_LAYER_PANEL', True):
            return

        # Get config values
        panel_x = getattr(config, 'SPLEEF_LAYER_PANEL_X', 480)
        panel_y = getattr(config, 'SPLEEF_LAYER_PANEL_Y', 120)
        panel_width = getattr(config, 'SPLEEF_LAYER_PANEL_WIDTH', 55)
        bar_height = getattr(config, 'SPLEEF_LAYER_PANEL_BAR_HEIGHT', 8)
        spacing = getattr(config, 'SPLEEF_LAYER_PANEL_SPACING', 3)

        # Count players per layer
        alive_players = [p for p in players if p.alive]
        total_alive = len(alive_players)

        players_per_layer = {}
        max_players_on_layer = 0
        for i in range(len(arena.layers)):
            count = sum(1 for p in alive_players if p.current_layer == i)
            players_per_layer[i] = count
            max_players_on_layer = max(max_players_on_layer, count)

        # Calculate panel dimensions
        panel_height = (bar_height + spacing) * len(arena.layers) + 25

        # Draw semi-transparent background
        draw.rectangle(
            [panel_x - 5, panel_y - 5, panel_x + panel_width + 5, panel_y + panel_height],
            fill=(20, 20, 30)
        )

        # Draw header
        draw.text((panel_x, panel_y), "LAYERS", fill=(200, 200, 200), font=self.font_small)

        # Draw each layer indicator
        bar_start_y = panel_y + 18
        max_bar_width = panel_width - 25  # Leave room for count text

        for layer_index in range(len(arena.layers)):
            count = players_per_layer[layer_index]
            layer_color = self.layer_colors.get(layer_index, (200, 200, 200))

            # Calculate bar width proportional to player count
            if max_players_on_layer > 0:
                bar_width = max(1, int((count / max_players_on_layer) * max_bar_width)) if count > 0 else 0
            else:
                bar_width = 0

            y = bar_start_y + layer_index * (bar_height + spacing)

            # Draw layer number
            draw.text((panel_x, y - 1), f"{layer_index}", fill=(150, 150, 150), font=self.font_small)

            # Draw background bar (empty)
            bar_x = panel_x + 12
            draw.rectangle(
                [bar_x, y, bar_x + max_bar_width, y + bar_height],
                fill=(40, 40, 50),
                outline=(60, 60, 70)
            )

            # Draw filled portion
            if bar_width > 0:
                draw.rectangle(
                    [bar_x, y, bar_x + bar_width, y + bar_height],
                    fill=layer_color
                )

            # Draw player count
            count_x = bar_x + max_bar_width + 3
            count_color = (255, 255, 255) if count > 0 else (100, 100, 100)
            draw.text((count_x, y - 1), str(count), fill=count_color, font=self.font_small)

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
        # Draw layer indicator panel
        self.draw_layer_indicator_panel(draw, arena, players)

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
