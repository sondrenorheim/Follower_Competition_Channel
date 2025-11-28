"""
Platformer Race Renderer

Handles all rendering for the platformer race game with top 5 UI.
"""

import pygame
import math
from PIL import Image
import config
from fighter_arena import FighterRenderer  # Reuse for racer avatars


class PlatformerRenderer:
    """Renders the platformer race"""

    def __init__(self, screen):
        """
        Initialize renderer

        Args:
            screen: Pygame screen surface
        """
        self.screen = screen
        self.font = pygame.font.Font(None, 32)
        self.font_small = pygame.font.Font(None, 24)
        self.font_medium = pygame.font.Font(None, 36)
        self.font_title = pygame.font.Font(None, 56)
        self.font_subtitle = pygame.font.Font(None, 32)
        self.font_day = pygame.font.Font(None, 36)
        self.font_large = pygame.font.Font(None, 72)

        # Reuse fighter renderer for high-res avatar rendering
        self.fighter_renderer = FighterRenderer(screen)

        # Cached surfaces for racers
        self.racer_surfaces = {}

        # Animation state for waving flags
        self.checkpoint_wave_offset = 0
        self.goal_wave_offset = 0

        # Game area position (extended viewport: 500x700 centered)
        self.game_area_x = (config.SCREEN_WIDTH - 500) // 2
        self.game_area_y = 180
        self.game_area_width = 500
        self.game_area_height = 700

    def render_frame(self, level, visible_racers, camera, game_state):
        """
        Render a complete frame

        Args:
            level: PlatformerLevel instance
            visible_racers: List of racers currently visible (dynamic culling)
            camera: PlatformerCamera instance
            game_state: Dictionary with game state info
        """
        # Clear screen
        self.screen.fill(config.COLOR_BACKGROUND)

        # Draw enhanced background
        self._draw_enhanced_background()

        # Draw title and subtitle (in screen space)
        self._draw_title_and_subtitle()

        # Draw game area border
        self._draw_game_area_border()

        # Render world (in camera/world space - static camera for vertical)
        self._draw_platforms(level.platforms, camera)
        self._draw_spikes(level.spikes, camera)
        self._draw_ladders(level.ladders, camera)
        self._draw_ropes(level.ropes, camera)
        self._draw_walls(level.walls, camera)
        self._draw_checkpoints(level.checkpoints, camera)
        self._draw_goal(level.goal, camera)
        self._draw_racers(visible_racers, camera)

        # Draw UI (in screen space)
        self._draw_day_counter(game_state.get('day', 1), game_state.get('racer_count', 0))

        # Draw finish counter during race phase
        if game_state.get('phase') == 'race':
            self._draw_finish_counter(game_state.get('finished_count', 0))

        # Draw countdown text if in countdown phase
        if game_state.get('phase') == 'countdown':
            self._draw_countdown_text()

        # Draw winner display or leaderboards if game finished
        if game_state.get('phase') == 'finished':
            if game_state.get('finished_sub_phase') == 'top_10':
                self._draw_winner_display(game_state.get('winner'), game_state.get('top_10'))
            else:
                self._draw_leaderboards(game_state)

        # Update animation offsets
        self.checkpoint_wave_offset += 0.1
        self.goal_wave_offset += 0.15

    def _draw_enhanced_background(self):
        """Draw enhanced background with gradient and grid overlay"""
        # Clip to game area
        game_rect = pygame.Rect(self.game_area_x, self.game_area_y,
                                self.game_area_width, self.game_area_height)

        # Draw vertical gradient (15 bands for smooth transition)
        SKY_TOP = (135, 206, 250)
        SKY_BOTTOM = (70, 130, 180)
        band_height = self.game_area_height // 15

        for i in range(15):
            t = i / 14.0  # Interpolation factor
            color = (
                int(SKY_TOP[0] + (SKY_BOTTOM[0] - SKY_TOP[0]) * t),
                int(SKY_TOP[1] + (SKY_BOTTOM[1] - SKY_TOP[1]) * t),
                int(SKY_TOP[2] + (SKY_BOTTOM[2] - SKY_TOP[2]) * t)
            )
            rect = pygame.Rect(self.game_area_x, self.game_area_y + i * band_height,
                              self.game_area_width, band_height + 1)
            pygame.draw.rect(self.screen, color, rect)

        # Grid overlay with transparency
        grid_surface = pygame.Surface((self.game_area_width, self.game_area_height), pygame.SRCALPHA)
        grid_color = (100, 149, 237, 30)  # Blue with alpha

        # Vertical lines every 50px
        for x in range(0, self.game_area_width, 50):
            pygame.draw.line(grid_surface, grid_color, (x, 0), (x, self.game_area_height), 1)

        # Horizontal lines every 50px
        for y in range(0, self.game_area_height, 50):
            pygame.draw.line(grid_surface, grid_color, (0, y), (self.game_area_width, y), 1)

        self.screen.blit(grid_surface, (self.game_area_x, self.game_area_y))

    def _draw_title_and_subtitle(self):
        """Draw title and subtitle with glow and shadow effects"""
        title_text = "PLATFORMER RACE"
        subtitle_text = "Making my followers battle every day"

        # Title with glow effect (multiple shadow layers for glow)
        title_center = (config.SCREEN_WIDTH // 2, 60)

        # Outer glow layers
        for i in range(3):
            glow_offset = 4 - i
            glow_alpha = 60 - i * 20
            glow_surface = self.font_title.render(title_text, True, config.COLOR_TEXT)
            glow_surface.set_alpha(glow_alpha)
            glow_rect = glow_surface.get_rect(center=(title_center[0] + glow_offset,
                                                       title_center[1] + glow_offset))
            self.screen.blit(glow_surface, glow_rect)

        # Main title with shadow
        self._draw_text_with_shadow(title_text, self.font_title, config.COLOR_TEXT, title_center, shadow_offset=3)

        # Subtitle with shadow
        subtitle_center = (config.SCREEN_WIDTH // 2, 100)
        self._draw_text_with_shadow(subtitle_text, self.font_subtitle, (0, 0, 0), subtitle_center, shadow_offset=2)

    def _draw_game_area_border(self):
        """Draw enhanced border with shadow and bevel effect"""
        border_rect = pygame.Rect(
            self.game_area_x - 2,
            self.game_area_y - 2,
            self.game_area_width + 4,
            self.game_area_height + 4
        )

        # Outer shadow (multiple layers for blur effect)
        shadow_surface = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), pygame.SRCALPHA)
        for i in range(5):
            shadow_alpha = 40 - (i * 8)
            shadow_offset = 6 + i * 2
            shadow_rect = pygame.Rect(
                border_rect.x - shadow_offset,
                border_rect.y - shadow_offset,
                border_rect.width + shadow_offset * 2,
                border_rect.height + shadow_offset * 2
            )
            pygame.draw.rect(shadow_surface, (0, 0, 0, shadow_alpha), shadow_rect, 3)
        self.screen.blit(shadow_surface, (0, 0))

        # Main border (dark base)
        pygame.draw.rect(self.screen, (80, 80, 80), border_rect, 4)

        # Beveled edges (3D effect)
        # Top edge (light)
        pygame.draw.line(self.screen, (200, 200, 200),
                        (border_rect.left, border_rect.top),
                        (border_rect.right, border_rect.top), 2)
        # Left edge (light)
        pygame.draw.line(self.screen, (200, 200, 200),
                        (border_rect.left, border_rect.top),
                        (border_rect.left, border_rect.bottom), 2)
        # Bottom edge (dark)
        pygame.draw.line(self.screen, (40, 40, 40),
                        (border_rect.left, border_rect.bottom - 2),
                        (border_rect.right, border_rect.bottom - 2), 2)
        # Right edge (dark)
        pygame.draw.line(self.screen, (40, 40, 40),
                        (border_rect.right - 2, border_rect.top),
                        (border_rect.right - 2, border_rect.bottom), 2)

        # Corner accents (small gold triangles)
        corner_size = 8
        accent_color = (255, 215, 0)

        # Top-left corner
        tl_points = [
            (border_rect.left - corner_size, border_rect.top - corner_size),
            (border_rect.left + corner_size, border_rect.top - corner_size),
            (border_rect.left - corner_size, border_rect.top + corner_size)
        ]
        pygame.draw.polygon(self.screen, accent_color, tl_points)

        # Top-right corner
        tr_points = [
            (border_rect.right - corner_size, border_rect.top - corner_size),
            (border_rect.right + corner_size, border_rect.top - corner_size),
            (border_rect.right + corner_size, border_rect.top + corner_size)
        ]
        pygame.draw.polygon(self.screen, accent_color, tr_points)

        # Bottom-left corner
        bl_points = [
            (border_rect.left - corner_size, border_rect.bottom - corner_size),
            (border_rect.left - corner_size, border_rect.bottom + corner_size),
            (border_rect.left + corner_size, border_rect.bottom + corner_size)
        ]
        pygame.draw.polygon(self.screen, accent_color, bl_points)

        # Bottom-right corner
        br_points = [
            (border_rect.right - corner_size, border_rect.bottom + corner_size),
            (border_rect.right + corner_size, border_rect.bottom + corner_size),
            (border_rect.right + corner_size, border_rect.bottom - corner_size)
        ]
        pygame.draw.polygon(self.screen, accent_color, br_points)

    def _draw_platforms(self, platforms, camera):
        """Draw enhanced platforms with shadows, gradients, and textures"""
        for platform in platforms:
            screen_pos = camera.world_to_screen((platform.x, platform.y))

            # Only draw if visible
            if -100 <= screen_pos[0] <= self.game_area_x + self.game_area_width + 100:
                self._draw_enhanced_platform(platform, screen_pos)

    def _draw_enhanced_platform(self, platform, screen_pos):
        """Draw a single platform with gradient, shadow, and texture"""
        platform_rect = pygame.Rect(
            int(screen_pos[0]), int(screen_pos[1]),
            int(platform.width), int(platform.height)
        )

        # Only draw if visible in game area
        if not (platform_rect.right >= self.game_area_x and
                platform_rect.left <= self.game_area_x + self.game_area_width):
            return

        # Step 1: Drop shadow
        shadow_rect = platform_rect.copy()
        shadow_rect.x += 4
        shadow_rect.y += 4
        shadow_surface = pygame.Surface((shadow_rect.width, shadow_rect.height), pygame.SRCALPHA)
        shadow_surface.fill((0, 0, 0, 80))
        self.screen.blit(shadow_surface, shadow_rect)

        # Step 2: Determine color scheme
        is_dark = platform.color[0] < 80  # Dark stone check
        if is_dark:
            top_color = (95, 95, 105)
            bottom_color = (55, 55, 65)
            highlight = (120, 120, 130)
        else:
            top_color = (130, 130, 140)
            bottom_color = (70, 70, 80)
            highlight = (160, 160, 170)

        # Step 3: Gradient fill (horizontal bands)
        num_bands = max(3, int(platform.height / 2))
        for i in range(num_bands):
            t = i / (num_bands - 1) if num_bands > 1 else 0
            band_color = (
                int(top_color[0] + (bottom_color[0] - top_color[0]) * t),
                int(top_color[1] + (bottom_color[1] - top_color[1]) * t),
                int(top_color[2] + (bottom_color[2] - top_color[2]) * t)
            )
            band_rect = pygame.Rect(
                platform_rect.x,
                platform_rect.y + int(i * platform.height / num_bands),
                platform_rect.width,
                int(platform.height / num_bands) + 1
            )
            pygame.draw.rect(self.screen, band_color, band_rect)

        # Step 4: Surface texture (random dots seeded by position)
        import random
        seed = int(platform.x * 1000 + platform.y)
        random.seed(seed)
        num_dots = int(platform.width * platform.height / 200)
        for _ in range(num_dots):
            dot_x = platform_rect.x + random.randint(2, max(3, platform_rect.width - 3))
            dot_y = platform_rect.y + random.randint(2, max(3, platform_rect.height - 3))
            dot_size = random.randint(2, 3)
            dot_brightness = random.randint(-15, 15)
            dot_color = (
                max(0, min(255, top_color[0] + dot_brightness)),
                max(0, min(255, top_color[1] + dot_brightness)),
                max(0, min(255, top_color[2] + dot_brightness))
            )
            pygame.draw.rect(self.screen, dot_color,
                            pygame.Rect(dot_x, dot_y, dot_size, dot_size))

        # Step 5: Beveled edges
        # Top highlight
        pygame.draw.line(self.screen, highlight,
                        (platform_rect.left, platform_rect.top),
                        (platform_rect.right, platform_rect.top), 2)
        # Left highlight
        pygame.draw.line(self.screen, highlight,
                        (platform_rect.left, platform_rect.top),
                        (platform_rect.left, platform_rect.bottom), 1)
        # Right shadow
        shadow_color = (40, 40, 50)
        pygame.draw.line(self.screen, shadow_color,
                        (platform_rect.right - 1, platform_rect.top),
                        (platform_rect.right - 1, platform_rect.bottom), 1)
        # Bottom shadow
        pygame.draw.line(self.screen, shadow_color,
                        (platform_rect.left, platform_rect.bottom - 1),
                        (platform_rect.right, platform_rect.bottom - 1), 2)

    def _draw_spikes(self, spikes, camera):
        """Draw enhanced spikes with gradients and metallic sheen"""
        for spike in spikes:
            screen_pos = camera.world_to_screen((spike.x, spike.y))

            # Only draw if visible
            if camera.is_visible(spike.x, spike.y):
                if spike.orientation == "up":
                    # Upward spikes - triangles pointing up
                    num_spikes = max(1, int(spike.width // 20))  # One spike every 20px
                    spike_width = spike.width / num_spikes
                    for i in range(num_spikes):
                        spike_x = screen_pos[0] + (i * spike_width)
                        points = [
                            (int(spike_x), int(screen_pos[1] + spike.height)),  # Bottom left
                            (int(spike_x + spike_width / 2), int(screen_pos[1])),  # Top point
                            (int(spike_x + spike_width), int(screen_pos[1] + spike.height))  # Bottom right
                        ]
                        self._draw_enhanced_spike(points, "up")
                elif spike.orientation == "down":
                    # Downward spikes - triangles pointing down
                    num_spikes = max(1, int(spike.width // 20))
                    spike_width = spike.width / num_spikes
                    for i in range(num_spikes):
                        spike_x = screen_pos[0] + (i * spike_width)
                        points = [
                            (int(spike_x), int(screen_pos[1])),  # Top left
                            (int(spike_x + spike_width / 2), int(screen_pos[1] + spike.height)),  # Bottom point
                            (int(spike_x + spike_width), int(screen_pos[1]))  # Top right
                        ]
                        self._draw_enhanced_spike(points, "down")

    def _draw_enhanced_spike(self, points, orientation):
        """Draw a single spike with gradient and metallic sheen"""
        if len(points) != 3:
            return

        # Identify base and tip
        if orientation == "up":
            base_points = [points[0], points[2]]  # Bottom two points
            tip_point = points[1]  # Top point
        else:  # down
            base_points = [points[0], points[2]]  # Top two points
            tip_point = points[1]  # Bottom point

        # Calculate midpoint of base
        base_mid = ((base_points[0][0] + base_points[1][0]) / 2,
                    (base_points[0][1] + base_points[1][1]) / 2)

        # Calculate intermediate points for gradient (thirds)
        mid1 = (
            base_mid[0] + (tip_point[0] - base_mid[0]) * 0.33,
            base_mid[1] + (tip_point[1] - base_mid[1]) * 0.33
        )
        mid2 = (
            base_mid[0] + (tip_point[0] - base_mid[0]) * 0.66,
            base_mid[1] + (tip_point[1] - base_mid[1]) * 0.66
        )

        # Edge midpoints for segments
        left_mid1 = (
            base_points[0][0] + (tip_point[0] - base_points[0][0]) * 0.33,
            base_points[0][1] + (tip_point[1] - base_points[0][1]) * 0.33
        )
        right_mid1 = (
            base_points[1][0] + (tip_point[0] - base_points[1][0]) * 0.33,
            base_points[1][1] + (tip_point[1] - base_points[1][1]) * 0.33
        )
        left_mid2 = (
            base_points[0][0] + (tip_point[0] - base_points[0][0]) * 0.66,
            base_points[0][1] + (tip_point[1] - base_points[0][1]) * 0.66
        )
        right_mid2 = (
            base_points[1][0] + (tip_point[0] - base_points[1][0]) * 0.66,
            base_points[1][1] + (tip_point[1] - base_points[1][1]) * 0.66
        )

        # Draw gradient segments (base to tip)
        # Base segment (dark red)
        base_poly = [base_points[0], base_points[1], right_mid1, left_mid1]
        pygame.draw.polygon(self.screen, (120, 40, 40), base_poly)

        # Middle segment (red)
        mid_poly = [left_mid1, right_mid1, right_mid2, left_mid2]
        pygame.draw.polygon(self.screen, (180, 50, 50), mid_poly)

        # Tip segment (bright red/orange)
        tip_poly = [left_mid2, right_mid2, tip_point]
        pygame.draw.polygon(self.screen, (255, 100, 80), tip_poly)

        # Metallic sheen on left edge (semi-transparent)
        sheen_surface = pygame.Surface((self.screen.get_width(), self.screen.get_height()), pygame.SRCALPHA)
        sheen_end = (
            base_points[0][0] + (tip_point[0] - base_points[0][0]) * 0.8,
            base_points[0][1] + (tip_point[1] - base_points[0][1]) * 0.8
        )
        pygame.draw.line(sheen_surface, (255, 200, 180, 120),
                        base_points[0], sheen_end, 2)
        self.screen.blit(sheen_surface, (0, 0))

        # Enhanced outline
        pygame.draw.polygon(self.screen, (150, 30, 30), points, 2)

    def _draw_checkpoints(self, checkpoints, camera):
        """Draw enhanced checkpoints with animated waving flags and glow"""
        for checkpoint in checkpoints:
            screen_pos = camera.world_to_screen((checkpoint.x, checkpoint.y))

            # Only draw if visible
            if camera.is_visible(checkpoint.x, checkpoint.y):
                self._draw_enhanced_checkpoint(checkpoint, screen_pos, self.checkpoint_wave_offset)

    def _draw_enhanced_checkpoint(self, checkpoint, screen_pos, wave_offset):
        """Draw a single checkpoint with animated flag, glow, and shadows"""
        import math

        pole_height = 40
        pole_x = int(screen_pos[0])
        pole_bottom_y = int(screen_pos[1])
        pole_top_y = pole_bottom_y - pole_height

        # Step 1: Glow effect (3 concentric circles with decreasing alpha)
        glow_surface = pygame.Surface((self.screen.get_width(), self.screen.get_height()), pygame.SRCALPHA)
        glow_color = (100, 200, 255)

        for i in range(3):
            radius = 20 + i * 8
            alpha = 40 - i * 12
            glow_circle_surface = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow_circle_surface, (*glow_color, alpha), (radius, radius), radius)
            self.screen.blit(glow_circle_surface, (pole_x - radius, pole_top_y - radius))

        # Step 2: Pole shadow (beneath pole)
        shadow_surface = pygame.Surface((6, pole_height + 2), pygame.SRCALPHA)
        shadow_surface.fill((0, 0, 0, 60))
        self.screen.blit(shadow_surface, (pole_x + 2, pole_top_y + 2))

        # Step 3: Gradient pole with highlights
        # Draw pole as gradient from light gray (top) to dark gray (bottom)
        num_bands = max(3, pole_height // 3)
        pole_top_color = (220, 220, 220)
        pole_bottom_color = (160, 160, 160)

        for i in range(num_bands):
            t = i / (num_bands - 1) if num_bands > 1 else 0
            color = (
                int(pole_top_color[0] + (pole_bottom_color[0] - pole_top_color[0]) * t),
                int(pole_top_color[1] + (pole_bottom_color[1] - pole_top_color[1]) * t),
                int(pole_top_color[2] + (pole_bottom_color[2] - pole_top_color[2]) * t)
            )
            band_y = pole_top_y + int(i * pole_height / num_bands)
            band_height = int(pole_height / num_bands) + 1
            pygame.draw.line(self.screen, color,
                           (pole_x, band_y),
                           (pole_x, band_y + band_height), 3)

        # Pole highlight (left edge)
        pygame.draw.line(self.screen, (255, 255, 255),
                        (pole_x - 1, pole_top_y),
                        (pole_x - 1, pole_bottom_y), 1)

        # Step 4: Animated waving flag (5 segments)
        flag_width = 25
        flag_height = 20
        flag_color = (100, 200, 255)
        num_segments = 5

        flag_points = []

        # Top edge of flag (waves)
        for i in range(num_segments + 1):
            t = i / num_segments
            x_offset = flag_width * t
            # Sine wave based on wave_offset
            wave = 3 * math.sin(wave_offset + t * math.pi * 2)
            flag_points.append((pole_x + x_offset, pole_top_y + wave))

        # Bottom edge of flag (waves, offset phase)
        for i in range(num_segments, -1, -1):
            t = i / num_segments
            x_offset = flag_width * t
            wave = 3 * math.sin(wave_offset + 0.5 + t * math.pi * 2)
            flag_points.append((pole_x + x_offset, pole_top_y + flag_height + wave))

        # Draw flag
        pygame.draw.polygon(self.screen, flag_color, flag_points)

        # Fabric texture lines (3 horizontal lines across flag)
        for i in range(1, 4):
            y_offset = (flag_height / 4) * i
            line_points = []
            for j in range(num_segments + 1):
                t = j / num_segments
                x_offset = flag_width * t
                wave = 3 * math.sin(wave_offset + t * math.pi * 2)
                line_points.append((pole_x + x_offset, pole_top_y + y_offset + wave))

            if len(line_points) >= 2:
                pygame.draw.lines(self.screen, (80, 160, 200), False, line_points, 1)

        # Flag outline for definition
        pygame.draw.polygon(self.screen, (70, 140, 180), flag_points, 2)

    def _draw_ladders(self, ladders, camera):
        """Draw enhanced ladders with wood texture"""
        for ladder in ladders:
            screen_pos = camera.world_to_screen((ladder.x, ladder.y))
            self._draw_enhanced_ladder(ladder, screen_pos)

    def _draw_enhanced_ladder(self, ladder, screen_pos):
        """Draw ladder with wood grain texture and depth"""
        rail_width = 4
        rung_height = 4

        # Helper function for wood rail
        def draw_wood_rail(x, y, width, height):
            # Gradient fill
            num_bands = max(3, height // 3)
            for i in range(num_bands):
                t = i / (num_bands - 1) if num_bands > 1 else 0
                color = (
                    int(101 + (139 - 101) * t),
                    int(67 + (90 - 67) * t),
                    int(33 + (43 - 33) * t)
                )
                band_rect = pygame.Rect(x, y + int(i * height / num_bands),
                                       width, int(height / num_bands) + 1)
                pygame.draw.rect(self.screen, color, band_rect)

            # Wood grain lines (seeded by position)
            import random
            seed = int(x * 1000 + y)
            random.seed(seed)
            num_lines = height // 30
            for _ in range(num_lines):
                line_y = y + random.randint(5, height - 5)
                line_color = (
                    max(0, 101 - random.randint(10, 20)),
                    max(0, 67 - random.randint(10, 20)),
                    max(0, 33 - random.randint(5, 15))
                )
                pygame.draw.line(self.screen, line_color,
                               (x, line_y), (x + width, line_y), 1)

            # Highlight and shadow
            pygame.draw.line(self.screen, (165, 115, 70),
                            (x, y), (x, y + height), 1)
            pygame.draw.line(self.screen, (80, 53, 25),
                            (x + width - 1, y), (x + width - 1, y + height), 1)

        # Draw left rail
        draw_wood_rail(int(screen_pos[0]), int(screen_pos[1]),
                       rail_width, int(ladder.height))

        # Draw right rail
        draw_wood_rail(int(screen_pos[0] + ladder.width - rail_width),
                       int(screen_pos[1]), rail_width, int(ladder.height))

        # Draw rungs
        for rung_offset in range(0, int(ladder.height), 20):
            rung_y = int(screen_pos[1] + rung_offset)
            rung_rect = pygame.Rect(int(screen_pos[0]), rung_y,
                                   int(ladder.width), rung_height)

            # Shadow first
            shadow_rect = rung_rect.copy()
            shadow_rect.y += 2
            shadow_surface = pygame.Surface((shadow_rect.width, shadow_rect.height), pygame.SRCALPHA)
            shadow_surface.fill((0, 0, 0, 60))
            self.screen.blit(shadow_surface, shadow_rect)

            # Gradient fill
            num_bands = rung_height
            for i in range(num_bands):
                t = i / (num_bands - 1) if num_bands > 1 else 0
                color = (
                    int(139 + (101 - 139) * t),
                    int(90 + (67 - 90) * t),
                    int(43 + (33 - 43) * t)
                )
                pygame.draw.line(self.screen, color,
                               (rung_rect.left, rung_rect.top + i),
                               (rung_rect.right, rung_rect.top + i))

            # Top highlight
            pygame.draw.line(self.screen, (180, 140, 90),
                            (rung_rect.left, rung_rect.top),
                            (rung_rect.right, rung_rect.top), 1)

    def _draw_ropes(self, ropes, camera):
        """Draw enhanced ropes with texture"""
        for rope in ropes:
            screen_pos = camera.world_to_screen((rope.x, rope.y))
            self._draw_enhanced_rope(rope, screen_pos)

    def _draw_enhanced_rope(self, rope, screen_pos):
        """Draw rope with texture, thickness variation, and frayed ends"""
        points = []

        # Generate rope center path with wave
        for i in range(int(rope.height)):
            # Primary wave
            wave = 3 * math.sin((rope.y + i) * 0.1)
            # Secondary wave for organic feel
            wave2 = 1.5 * math.sin((rope.y + i) * 0.05 + 1.5)
            x_offset = wave + wave2
            points.append((screen_pos[0] + x_offset, screen_pos[1] + i))

        if len(points) < 2:
            return

        # Draw rope with thickness variation
        for i in range(len(points) - 1):
            # Thickness varies with position
            thickness = 5 + int(2 * math.sin(i * 0.3))

            # Shadow/base layer (darker, offset right)
            shadow_p1 = (points[i][0] + 1, points[i][1] + 1)
            shadow_p2 = (points[i + 1][0] + 1, points[i + 1][1] + 1)
            pygame.draw.line(self.screen, (60, 40, 20),
                            shadow_p1, shadow_p2, thickness + 1)

            # Main rope (dark brown)
            pygame.draw.line(self.screen, (80, 53, 25),
                            points[i], points[i + 1], thickness)

            # Highlight (left side, thinner)
            if i % 2 == 0:  # Not every segment, for texture
                highlight_offset = -thickness // 2
                highlight_p1 = (points[i][0] + highlight_offset, points[i][1])
                highlight_p2 = (points[i + 1][0] + highlight_offset, points[i + 1][1])
                pygame.draw.line(self.screen, (120, 80, 40),
                               highlight_p1, highlight_p2, 2)

        # Add twist texture (perpendicular lines)
        for i in range(0, len(points), 12):
            if i >= len(points):
                break

            # Calculate perpendicular direction
            if i < len(points) - 1:
                dx = points[i + 1][0] - points[i][0]
                dy = points[i + 1][1] - points[i][1]
                length = math.sqrt(dx * dx + dy * dy)
                if length > 0:
                    # Perpendicular vector
                    perp_x = -dy / length * 3
                    perp_y = dx / length * 3

                    p1 = (points[i][0] - perp_x, points[i][1] - perp_y)
                    p2 = (points[i][0] + perp_x, points[i][1] + perp_y)
                    pygame.draw.line(self.screen, (60, 40, 20), p1, p2, 1)

        # Frayed ends
        import random

        # Top frayed strands
        seed_top = int(rope.x * 1000 + rope.y)
        random.seed(seed_top)
        for _ in range(4):
            offset_x = random.randint(-2, 2)
            length = random.randint(3, 8)
            start = (screen_pos[0] + offset_x, screen_pos[1])
            end = (screen_pos[0] + offset_x, screen_pos[1] - length)
            pygame.draw.line(self.screen, (140, 100, 60), start, end, 1)

        # Bottom frayed strands
        seed_bottom = int(rope.x * 1000 + rope.y + rope.height)
        random.seed(seed_bottom)
        for _ in range(4):
            offset_x = random.randint(-2, 2)
            length = random.randint(3, 8)
            start = (screen_pos[0] + offset_x, screen_pos[1] + rope.height)
            end = (screen_pos[0] + offset_x, screen_pos[1] + rope.height + length)
            pygame.draw.line(self.screen, (140, 100, 60), start, end, 1)

    def _draw_walls(self, walls, camera):
        """Draw enhanced climbable walls"""
        for wall in walls:
            screen_pos = camera.world_to_screen((wall.x, wall.y))
            self._draw_enhanced_wall(wall, screen_pos)

    def _draw_enhanced_wall(self, wall, screen_pos):
        """Draw climbable wall with rock texture and grip holds"""
        wall_rect = pygame.Rect(
            int(screen_pos[0]), int(screen_pos[1]),
            int(wall.width), int(wall.height)
        )

        # Base gradient (left to right, slight depth)
        num_vertical_bands = max(3, int(wall.width / 3))
        for i in range(num_vertical_bands):
            t = i / (num_vertical_bands - 1) if num_vertical_bands > 1 else 0
            color = (
                int(110 + (90 - 110) * t),  # Lighter left to darker right
                int(110 + (90 - 110) * t),
                int(120 + (100 - 120) * t)
            )
            band_rect = pygame.Rect(
                wall_rect.x + int(i * wall.width / num_vertical_bands),
                wall_rect.y,
                int(wall.width / num_vertical_bands) + 1,
                wall_rect.height
            )
            pygame.draw.rect(self.screen, color, band_rect)

        # Rock texture (random patches)
        import random
        seed = int(wall.x * 1000 + wall.y)
        random.seed(seed)

        num_patches = int(wall.width * wall.height / 100)
        for _ in range(num_patches):
            patch_x = wall_rect.x + random.randint(0, max(1, wall_rect.width - 5))
            patch_y = wall_rect.y + random.randint(0, max(1, wall_rect.height - 5))
            patch_size = random.randint(3, 6)
            shade = random.choice([
                (80, 80, 90),    # Dark
                (100, 100, 110), # Mid
                (120, 120, 130)  # Light
            ])
            pygame.draw.rect(self.screen, shade,
                            pygame.Rect(patch_x, patch_y, patch_size, patch_size))

        # Surface cracks
        num_cracks = random.randint(2, 4)
        random.seed(seed + 1)
        for i in range(num_cracks):
            crack_x = wall_rect.x + random.randint(2, max(3, wall_rect.width - 3))
            crack_points = []
            y = wall_rect.y
            while y < wall_rect.y + wall_rect.height:
                x_offset = random.randint(-2, 2)
                crack_points.append((crack_x + x_offset, y))
                y += random.randint(8, 15)

            if len(crack_points) >= 2:
                pygame.draw.lines(self.screen, (60, 60, 70),
                                False, crack_points, 1)

        # Enhanced grip holds
        random.seed(seed + 2)
        for grip_offset in range(15, int(wall.height), 15):
            grip_y = int(screen_pos[1] + grip_offset)
            grip_x = int(screen_pos[0] + wall.width // 2)

            # Vary grip position slightly
            grip_x += random.randint(-3, 3)

            # Draw grip as irregular polygon
            grip_size = 5
            num_sides = 6
            grip_points = []
            for i in range(num_sides):
                angle = (i / num_sides) * 2 * math.pi
                radius = grip_size + random.uniform(-1, 1)
                px = grip_x + radius * math.cos(angle)
                py = grip_y + radius * math.sin(angle)
                grip_points.append((px, py))

            # Shadow
            shadow_points = [(p[0] + 1, p[1] + 1) for p in grip_points]
            pygame.draw.polygon(self.screen, (60, 60, 70), shadow_points)

            # Main grip
            pygame.draw.polygon(self.screen, (140, 130, 100), grip_points)

            # Highlight on top
            if len(grip_points) >= 3:
                highlight_points = [grip_points[0], grip_points[1],
                                   ((grip_points[0][0] + grip_points[1][0]) / 2,
                                    (grip_points[0][1] + grip_points[1][1]) / 2 - 1)]
                pygame.draw.polygon(self.screen, (160, 150, 120), highlight_points)

        # Edge highlights and shadows
        pygame.draw.line(self.screen, (130, 130, 140),
                        (wall_rect.left, wall_rect.top),
                        (wall_rect.left, wall_rect.bottom), 1)
        pygame.draw.line(self.screen, (70, 70, 80),
                        (wall_rect.right - 1, wall_rect.top),
                        (wall_rect.right - 1, wall_rect.bottom), 2)

    def _draw_goal(self, goal, camera):
        """Draw enhanced goal with pulsing glow, checkered flag, and sparkles"""
        if not goal:
            return

        screen_pos = camera.world_to_screen((goal.x, goal.y))
        self._draw_enhanced_goal(goal, screen_pos, self.goal_wave_offset)

    def _draw_enhanced_goal(self, goal, screen_pos, wave_offset):
        """Draw goal with dramatic glow, animated checkered flag, and sparkles"""
        import math
        import random

        pole_height = 60
        pole_x = int(screen_pos[0])
        pole_bottom_y = int(screen_pos[1])
        pole_top_y = pole_bottom_y - pole_height

        # Step 1: Pulsing glow effect (4 concentric circles with varying alpha)
        # Pulse intensity varies with sine wave
        pulse_intensity = 0.7 + 0.3 * math.sin(wave_offset * 1.5)

        for i in range(4):
            radius = 30 + i * 12
            alpha = int((60 - i * 12) * pulse_intensity)
            glow_circle_surface = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow_circle_surface, (255, 215, 0, alpha), (radius, radius), radius)
            self.screen.blit(glow_circle_surface, (pole_x - radius, pole_top_y - radius))

        # Step 2: Pole shadow
        shadow_surface = pygame.Surface((6, pole_height + 2), pygame.SRCALPHA)
        shadow_surface.fill((0, 0, 0, 80))
        self.screen.blit(shadow_surface, (pole_x + 2, pole_top_y + 2))

        # Step 3: Gold gradient pole
        num_bands = max(3, pole_height // 3)
        pole_top_color = (255, 235, 150)  # Light gold
        pole_bottom_color = (200, 160, 50)  # Dark gold

        for i in range(num_bands):
            t = i / (num_bands - 1) if num_bands > 1 else 0
            color = (
                int(pole_top_color[0] + (pole_bottom_color[0] - pole_top_color[0]) * t),
                int(pole_top_color[1] + (pole_bottom_color[1] - pole_top_color[1]) * t),
                int(pole_top_color[2] + (pole_bottom_color[2] - pole_top_color[2]) * t)
            )
            band_y = pole_top_y + int(i * pole_height / num_bands)
            band_height = int(pole_height / num_bands) + 1
            pygame.draw.line(self.screen, color,
                           (pole_x, band_y),
                           (pole_x, band_y + band_height), 4)

        # Pole highlight
        pygame.draw.line(self.screen, (255, 255, 200),
                        (pole_x - 2, pole_top_y),
                        (pole_x - 2, pole_bottom_y), 1)

        # Step 4: Animated checkered flag (4x4 pattern with wave)
        flag_width = 40
        flag_height = 40
        checker_size = 10
        num_segments = 8

        # Generate waving flag points
        flag_top_points = []
        flag_bottom_points = []

        for i in range(num_segments + 1):
            t = i / num_segments
            x_offset = flag_width * t
            # Different wave for top and bottom
            wave_top = 4 * math.sin(wave_offset + t * math.pi * 1.5)
            wave_bottom = 4 * math.sin(wave_offset + 0.7 + t * math.pi * 1.5)

            flag_top_points.append((pole_x + x_offset, pole_top_y + wave_top))
            flag_bottom_points.append((pole_x + x_offset, pole_top_y + flag_height + wave_bottom))

        # Draw flag base (gold background)
        flag_polygon = flag_top_points + list(reversed(flag_bottom_points))
        pygame.draw.polygon(self.screen, (255, 215, 0), flag_polygon)

        # Draw checkered pattern (4x4 grid)
        # Use orange for alternating squares
        for row in range(4):
            for col in range(4):
                # Alternate pattern
                if (row + col) % 2 == 1:
                    # Calculate checker position with wave
                    checker_left = pole_x + col * checker_size
                    checker_right = pole_x + (col + 1) * checker_size
                    checker_top = pole_top_y + row * checker_size
                    checker_bottom = pole_top_y + (row + 1) * checker_size

                    # Sample wave at this position
                    t_left = col / 4.0
                    t_right = (col + 1) / 4.0
                    t_top = row / 4.0
                    t_bottom = (row + 1) / 4.0

                    wave_tl = 4 * math.sin(wave_offset + t_left * math.pi * 1.5 + t_top * 0.5)
                    wave_tr = 4 * math.sin(wave_offset + t_right * math.pi * 1.5 + t_top * 0.5)
                    wave_bl = 4 * math.sin(wave_offset + 0.7 + t_left * math.pi * 1.5 + t_bottom * 0.5)
                    wave_br = 4 * math.sin(wave_offset + 0.7 + t_right * math.pi * 1.5 + t_bottom * 0.5)

                    checker_points = [
                        (checker_left, checker_top + wave_tl),
                        (checker_right, checker_top + wave_tr),
                        (checker_right, checker_bottom + wave_br),
                        (checker_left, checker_bottom + wave_bl)
                    ]
                    pygame.draw.polygon(self.screen, (255, 140, 0), checker_points)  # Orange

        # Flag outline
        pygame.draw.polygon(self.screen, (200, 150, 0), flag_polygon, 2)

        # Step 5: Sparkle effects (8 random twinkles per frame)
        seed = int(wave_offset * 100) % 1000
        random.seed(seed)

        for _ in range(8):
            # Random position around goal
            sparkle_x = pole_x + random.randint(-40, 40)
            sparkle_y = pole_top_y + random.randint(-30, 30)

            # Random sparkle size and brightness
            sparkle_size = random.randint(2, 4)
            sparkle_alpha = random.randint(100, 200)

            # Draw sparkle as a small bright circle
            sparkle_surface = pygame.Surface((sparkle_size * 2, sparkle_size * 2), pygame.SRCALPHA)
            pygame.draw.circle(sparkle_surface, (255, 255, 200, sparkle_alpha),
                             (sparkle_size, sparkle_size), sparkle_size)
            self.screen.blit(sparkle_surface, (sparkle_x - sparkle_size, sparkle_y - sparkle_size))

            # Cross pattern for extra sparkle
            if sparkle_size >= 3:
                pygame.draw.line(self.screen, (255, 255, 255, sparkle_alpha // 2),
                               (sparkle_x - sparkle_size - 1, sparkle_y),
                               (sparkle_x + sparkle_size + 1, sparkle_y), 1)
                pygame.draw.line(self.screen, (255, 255, 255, sparkle_alpha // 2),
                               (sparkle_x, sparkle_y - sparkle_size - 1),
                               (sparkle_x, sparkle_y + sparkle_size + 1), 1)

    def _draw_racers(self, racers, camera):
        """Draw racers as circles with profile pictures"""
        for racer in racers:
            if not racer.alive:
                continue

            screen_pos = camera.world_to_screen((racer.x, racer.y))

            # Get or create racer surface
            cache_key = f"{racer.id}_{racer.alpha}"
            if cache_key not in self.racer_surfaces or racer.surface_needs_update:
                surface = self._create_racer_surface(racer)
                self.racer_surfaces[cache_key] = surface
                racer.surface_needs_update = False
            else:
                surface = self.racer_surfaces[cache_key]

            # Draw racer
            if surface:
                surface_rect = surface.get_rect(center=(int(screen_pos[0]), int(screen_pos[1])))
                self.screen.blit(surface, surface_rect)

    def _create_racer_surface(self, racer):
        """
        Create circular surface for racer with profile picture

        Args:
            racer: PlatformerRacer instance

        Returns:
            Pygame surface
        """
        size = int(racer.radius * 2)
        surface = pygame.Surface((size, size), pygame.SRCALPHA)

        # Draw circle with avatar or color
        if racer.avatar_image:
            # Convert PIL image to pygame surface
            try:
                from PIL import Image

                # Resize avatar to circle size
                avatar_resized = racer.avatar_image.resize((size, size), Image.Resampling.LANCZOS)

                # Convert to pygame surface
                mode = avatar_resized.mode
                avatar_size = avatar_resized.size
                avatar_data = avatar_resized.tobytes()

                pygame_avatar = pygame.image.fromstring(avatar_data, avatar_size, mode)

                # Create circular mask
                mask_surface = pygame.Surface((size, size), pygame.SRCALPHA)
                pygame.draw.circle(mask_surface, (255, 255, 255, 255), (size // 2, size // 2), size // 2)

                # Apply mask
                surface.blit(pygame_avatar, (0, 0))
                surface.blit(mask_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)

            except Exception as e:
                # Fallback to colored circle
                pygame.draw.circle(surface, racer.color, (size // 2, size // 2), size // 2)
        else:
            # No avatar - draw colored circle
            pygame.draw.circle(surface, racer.color, (size // 2, size // 2), size // 2)

        # Draw border
        pygame.draw.circle(surface, (255, 255, 255), (size // 2, size // 2), size // 2, 2)

        # Apply alpha if fading
        if racer.alpha < 255:
            surface.set_alpha(racer.alpha)

        return surface

    def _draw_day_counter(self, day, racer_count):
        """Draw day counter below game area with shadow"""
        day_text = f"Day {day}: {racer_count} racers"
        day_center = (config.SCREEN_WIDTH // 2, self.game_area_y + self.game_area_height + 30)
        self._draw_text_with_shadow(day_text, self.font_day, config.COLOR_TEXT, day_center, shadow_offset=2)

    def _draw_finish_counter(self, finished_count):
        """Draw finish counter showing progress to top 10 - positioned above game area"""
        # Position above the game area, below the subtitle
        y_position = self.game_area_y - 30

        # Create background panel
        panel_width = 250
        panel_height = 45
        panel_x = (config.SCREEN_WIDTH - panel_width) // 2
        panel_y = y_position - panel_height // 2

        # Draw semi-transparent background
        panel = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        panel.fill((20, 20, 30, 180))

        # Determine border and text color based on progress
        if finished_count >= 10:
            color = (100, 255, 100)  # Green when complete
        elif finished_count >= 7:
            color = (255, 200, 0)    # Yellow when close
        else:
            color = (100, 200, 255)  # Blue normally

        # Draw colored border
        pygame.draw.rect(panel, color, (0, 0, panel_width, panel_height), 3)
        self.screen.blit(panel, (panel_x, panel_y))

        # Draw text
        finish_text = f"FINISHERS: {finished_count}/10"
        finish_center = (config.SCREEN_WIDTH // 2, y_position)
        self._draw_text_with_shadow(finish_text, self.font_day, color, finish_center, shadow_offset=2)

    def _draw_top_5_leaderboard(self, top_5_data):
        """
        Draw horizontal top 5 leaderboard below day counter

        Args:
            top_5_data: List of tuples (username, progress)
        """
        if not top_5_data:
            return

        # Position colors for medals
        position_colors = [
            (255, 215, 0),    # 1st - Gold
            (192, 192, 192),  # 2nd - Silver
            (205, 127, 50),   # 3rd - Bronze
            (255, 255, 255),  # 4th - White
            (255, 255, 255),  # 5th - White
        ]

        # Starting Y position (below day counter)
        start_y = self.game_area_y + self.game_area_height + 70
        entry_width = 100  # Width per entry
        total_width = len(top_5_data) * entry_width
        start_x = (config.SCREEN_WIDTH - total_width) // 2

        for i, (username, progress) in enumerate(top_5_data):
            x = start_x + (i * entry_width)
            color = position_colors[i]

            # Position number
            position_text = f"{i+1}"
            if i == 0:
                position_text += "st"
            elif i == 1:
                position_text += "nd"
            elif i == 2:
                position_text += "rd"
            else:
                position_text += "th"

            # Draw position text with shadow
            pos_center = (x + entry_width // 2, start_y)
            self._draw_text_with_shadow(position_text, self.font_small, color, pos_center, shadow_offset=1)

            # Username (truncated if too long) with shadow
            display_name = username[:8] if len(username) > 8 else username
            name_center = (x + entry_width // 2, start_y + 25)
            self._draw_text_with_shadow(display_name, self.font_small, color, name_center, shadow_offset=1)

            # Progress percentage with shadow
            progress_pct = f"{int(progress * 100)}%"
            progress_center = (x + entry_width // 2, start_y + 45)
            self._draw_text_with_shadow(progress_pct, self.font_small, (200, 200, 200), progress_center, shadow_offset=1)

    def _draw_countdown_text(self):
        """Draw countdown text overlay (greenscreen video will be added during export)"""
        # Draw semi-transparent overlay
        overlay = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

        # Draw "GET READY!" text
        ready_text = "GET READY!"
        ready_surface = self.font_large.render(ready_text, True, (255, 255, 255))
        ready_rect = ready_surface.get_rect(center=(config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT // 2))
        self.screen.blit(ready_surface, ready_rect)

    def _draw_winner_display(self, winner, top_10):
        """
        Draw winner podium and leaderboards

        Args:
            winner: Winner racer object
            top_10: List of top 10 finishers
        """
        if not winner:
            return

        # Draw dark overlay
        overlay = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
        overlay.set_alpha(200)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))

        # Winner title with pulsing effect
        winner_text = "WINNER!"
        winner_surface = self.font_large.render(winner_text, True, (255, 215, 0))
        winner_rect = winner_surface.get_rect(center=(config.SCREEN_WIDTH // 2, 150))
        self.screen.blit(winner_surface, winner_rect)

        # Winner name
        name_surface = self.font_title.render(winner.username, True, (255, 255, 255))
        name_rect = name_surface.get_rect(center=(config.SCREEN_WIDTH // 2, 250))
        self.screen.blit(name_surface, name_rect)

        # Draw top 10 leaderboard with profile pictures
        if top_10:
            # Title for top 10
            top_10_title = self.font_medium.render("TOP 10 FINISHERS", True, (255, 215, 0))
            top_10_rect = top_10_title.get_rect(center=(config.SCREEN_WIDTH // 2, 350))
            self.screen.blit(top_10_title, top_10_rect)

            # Draw each finisher in two columns (5 per column)
            start_y = 400
            avatar_size = 40
            row_height = 50
            left_x = config.SCREEN_WIDTH // 2 - 250
            right_x = config.SCREEN_WIDTH // 2 + 50

            for i, racer in enumerate(top_10):
                # Determine column and row
                if i < 5:
                    x = left_x
                    y = start_y + (i * row_height)
                else:
                    x = right_x
                    y = start_y + ((i - 5) * row_height)

                # Draw placement number
                placement_text = f"#{i+1}"
                placement_surface = self.font_medium.render(placement_text, True, (255, 215, 0))
                self.screen.blit(placement_surface, (x, y + 10))

                # Draw avatar (profile picture)
                if racer.avatar_image:
                    # Convert PIL image to pygame surface and scale
                    avatar_surface = self._pil_to_pygame(racer.avatar_image, avatar_size)
                    self.screen.blit(avatar_surface, (x + 50, y))
                else:
                    # Draw colored circle if no avatar
                    pygame.draw.circle(self.screen, racer.color, (x + 70, y + 20), avatar_size // 2)

                # Draw username
                username_surface = self.font_small.render(racer.username[:15], True, (255, 255, 255))
                self.screen.blit(username_surface, (x + 100, y + 12))

                # Draw finish time
                time_text = f"{racer.finish_time:.2f}s"
                time_surface = self.font_small.render(time_text, True, (200, 200, 200))
                self.screen.blit(time_surface, (x + 100, y + 28))

    def _pil_to_pygame(self, pil_image: Image.Image, size: int) -> pygame.Surface:
        """Convert PIL image to pygame surface"""
        pil_image = pil_image.resize((size, size), Image.Resampling.LANCZOS)
        mode = pil_image.mode
        size = pil_image.size
        data = pil_image.tobytes()
        surface = pygame.image.fromstring(data, size, mode)
        return surface.convert_alpha()

    def _truncate_text_to_width(self, text, font, max_width):
        """
        Truncate text to fit within max_width pixels

        Args:
            text: Text to truncate
            font: Font to use for measuring
            max_width: Maximum width in pixels

        Returns:
            Truncated text with ".." if needed
        """
        # Check if text fits as-is
        text_surface = font.render(text, True, (255, 255, 255))
        if text_surface.get_width() <= max_width:
            return text

        # Binary search for the right length
        for length in range(len(text), 0, -1):
            truncated = text[:length] + ".."
            test_surface = font.render(truncated, True, (255, 255, 255))
            if test_surface.get_width() <= max_width:
                return truncated

        return ".."

    def _draw_text_with_shadow(self, text, font, color, position, shadow_offset=2):
        """Draw text with drop shadow for better readability"""
        # Shadow
        shadow_surface = font.render(text, True, (0, 0, 0))
        shadow_surface.set_alpha(120)
        shadow_rect = shadow_surface.get_rect(center=(position[0] + shadow_offset,
                                                       position[1] + shadow_offset))
        self.screen.blit(shadow_surface, shadow_rect)

        # Main text
        text_surface = font.render(text, True, color)
        text_rect = text_surface.get_rect(center=position)
        self.screen.blit(text_surface, text_rect)

        return text_rect

    def _draw_text_with_outline(self, text, font, color, outline_color, position, outline_width=1):
        """Draw text with outline for maximum readability"""
        # Draw outline in 8 directions
        offsets = [
            (-outline_width, -outline_width), (0, -outline_width), (outline_width, -outline_width),
            (-outline_width, 0), (outline_width, 0),
            (-outline_width, outline_width), (0, outline_width), (outline_width, outline_width)
        ]

        for offset in offsets:
            outline_surface = font.render(text, True, outline_color)
            outline_rect = outline_surface.get_rect(center=(position[0] + offset[0],
                                                            position[1] + offset[1]))
            self.screen.blit(outline_surface, outline_rect)

        # Main text
        text_surface = font.render(text, True, color)
        text_rect = text_surface.get_rect(center=position)
        self.screen.blit(text_surface, text_rect)

        return text_rect

    def _draw_leaderboards(self, game_state):
        """Draw current game and all-time leaderboards"""
        current_lb = game_state.get("current_game_leaderboard", [])
        all_time_lb = game_state.get("all_time_leaderboard", [])

        if not current_lb and not all_time_lb:
            return

        # Draw semi-transparent background overlay
        overlay = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, (0, 0))

        # Position leaderboards side by side
        start_y = int(config.SCREEN_HEIGHT * 0.25)
        board_width = int(config.SCREEN_WIDTH * 0.40)
        spacing = int(config.SCREEN_WIDTH * 0.05)
        left_x = (config.SCREEN_WIDTH - board_width * 2 - spacing) // 2
        right_x = left_x + board_width + spacing

        # Draw title
        title_text = "LEADERBOARDS"
        title_y = int(config.SCREEN_HEIGHT * 0.12)
        self._draw_text_with_shadow(title_text, self.font_large, (255, 215, 0),
                                    (config.SCREEN_WIDTH // 2, title_y), shadow_offset=3)

        if current_lb:
            self._draw_leaderboard_panel(
                "CURRENT GAME", "TOP 10",
                current_lb[:10], left_x, start_y, board_width,
                (0, 200, 255)
            )

        if all_time_lb:
            all_time_formatted = [(username, points) for username, points, _ in all_time_lb]
            self._draw_leaderboard_panel(
                "ALL-TIME", "TOP 10",
                all_time_formatted[:10], right_x, start_y, board_width,
                (255, 215, 0)
            )

    def _draw_leaderboard_panel(self, title_line1, title_line2,
                               leaderboard, x, y, width, color):
        """Draw a single leaderboard panel"""
        if not leaderboard:
            return

        entry_height = 35
        header_height = 60
        panel_height = header_height + len(leaderboard) * entry_height + 20

        # Panel background
        panel = pygame.Surface((width, panel_height), pygame.SRCALPHA)
        panel.fill((20, 20, 30, 220))
        pygame.draw.rect(panel, color, (0, 0, width, panel_height), 3)
        self.screen.blit(panel, (x, y))

        # Title lines
        title1_text = self.font_day.render(title_line1, True, color)
        title1_rect = title1_text.get_rect(center=(x + width // 2, y + 18))
        self.screen.blit(title1_text, title1_rect)

        title2_text = self.font_day.render(title_line2, True, color)
        title2_rect = title2_text.get_rect(center=(x + width // 2, y + 40))
        self.screen.blit(title2_text, title2_rect)

        # Entries
        medals = ["1st", "2nd", "3rd"]
        entry_y = y + header_height

        for i, (username, points) in enumerate(leaderboard):
            # Rank
            rank_str = medals[i] if i < 3 else f"{i + 1}."
            rank_text = self.font_small.render(rank_str, True, (200, 200, 200))
            self.screen.blit(rank_text, (x + 10, entry_y))

            # Username - truncate to fit available space
            # Calculate available width: panel width - rank space - points space - padding
            available_width = width - 60 - 80 - 10  # 60 for rank, 80 for points, 10 for padding
            display_name = self._truncate_text_to_width(username, self.font_small, available_width)
            name_text = self.font_small.render(display_name, True, (255, 255, 255))
            self.screen.blit(name_text, (x + 60, entry_y))

            # Points
            points_text = self.font_small.render(f"{points:.0f}", True, (0, 255, 150))
            points_rect = points_text.get_rect(right=x + width - 10, top=entry_y)
            self.screen.blit(points_text, points_rect)

            entry_y += entry_height
