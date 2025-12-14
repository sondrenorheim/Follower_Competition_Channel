"""
Gorillas vs Followers Renderer
Handles rendering for the Gorillas vs Followers game mode
Includes gorilla arm animation and HP bars
"""

import pygame
import math
import os
from typing import List, Tuple, Optional
from PIL import Image
import config


class GorillasRenderer:
    """
    Handles all rendering operations for the Gorillas vs Followers game mode
    Renders followers, animated gorillas with arms, and HP bars
    """

    def __init__(self, screen: pygame.Surface):
        """
        Initialize the renderer

        Args:
            screen: Pygame display surface to render to
        """
        self.screen = screen
        self.width = config.SCREEN_WIDTH
        self.height = config.SCREEN_HEIGHT

        # Initialize fonts
        pygame.font.init()
        self.font_small = pygame.font.Font(None, config.FOLLOWER_NAME_FONT_SIZE)
        self.font_medium = pygame.font.Font(None, config.SCOREBOARD_FONT_SIZE)
        self.font_large = pygame.font.Font(None, 48)
        self.font_huge = pygame.font.Font(None, 72)

        # Cache for follower surfaces
        self.follower_surfaces = {}
        self.cached_radius = {}

        # Animation state
        self.show_podium = False
        self.podium_animation_progress = 0
        self.winners = []

    def render_frame(self, followers: List, gorillas: List, arena,
                    game_state: dict, particle_system=None):
        """
        Render complete frame

        Args:
            followers: List of all follower fighters
            gorillas: List of all gorilla enemies
            arena: GorillasArena object
            game_state: Dictionary with game state info
            particle_system: Optional ParticleSystem for effects
        """
        # Clear screen
        self.screen.fill(config.COLOR_BACKGROUND)

        # Draw arena (with gate)
        self._draw_arena(arena, gate_progress=game_state.get("gate_progress", 0.0))

        # Draw followers
        self._draw_followers(followers)

        # Draw gorillas with arms and HP bars
        self._draw_gorillas(gorillas)

        # Draw particles
        if particle_system:
            particle_system.render(self.screen)

        # Draw UI
        self._draw_scoreboard(followers, gorillas, game_state)

        # Draw combined gorilla health bar (during combat)
        if game_state.get("game_phase") in ("countdown", "playing"):
            self._draw_combined_gorilla_health_bar(gorillas)

        # Draw intro overlay if in intro phase
        if game_state.get("game_phase") == "intro":
            self._draw_intro(game_state.get("day_number", 1))
            return

        # Draw countdown if in countdown phase
        if game_state.get("game_phase") == "countdown":
            self._draw_countdown(game_state.get("countdown_number", 3))
            return

        # Draw victory screen if game is over
        if game_state.get("game_over", False):
            if not self.show_podium:
                self.show_podium = True
                self.podium_animation_progress = 0
                self.winners = game_state.get("victory_team", "followers")
                self.game_state = game_state

            self._draw_victory_screen(self.winners, followers, gorillas, self.game_state)

    def _draw_arena(self, arena, gate_progress: float = 0.0):
        """
        Draw the rectangular arena

        Args:
            arena: GorillasArena object
            gate_progress: 0 (closed) to 1 (fully open)
        """
        rect = arena.get_rect()

        # Draw arena floor
        pygame.draw.rect(
            self.screen,
            config.COLOR_FIGHTER_ARENA,
            rect
        )

        # Draw arena border
        pygame.draw.rect(
            self.screen,
            (0, 0, 0),
            rect,
            3  # Border width
        )

        # Draw gate (horizontal band) during intro/countdown/opening; opens horizontally from center
        if gate_progress < 1.0:
            left, top, right, bottom = arena.get_bounds()
            gate_y = (top + bottom) / 2
            gate_height = 12
            total_width = rect[2]
            gap_width = total_width * gate_progress
            color = (80, 80, 80, 220)

            if total_width > gap_width:
                side_width = (total_width - gap_width) / 2
                # Left segment
                left_surface = pygame.Surface((side_width, gate_height), pygame.SRCALPHA)
                left_surface.fill(color)
                self.screen.blit(left_surface, (rect[0], gate_y - gate_height // 2))
                # Right segment
                right_surface = pygame.Surface((side_width, gate_height), pygame.SRCALPHA)
                right_surface.fill(color)
                self.screen.blit(right_surface, (rect[0] + side_width + gap_width, gate_y - gate_height // 2))

    def _draw_followers(self, followers: List):
        """
        Draw all followers with their avatars (NO HP bars for followers)

        Args:
            followers: List of all followers
        """
        for follower in followers:
            # Skip if completely faded out
            if not follower.alive and not follower.is_fading():
                continue

            # Get or create follower surface
            surface = self._get_follower_surface(follower)

            # Apply alpha for fade out
            if follower.alpha < 255:
                surface = surface.copy()
                surface.set_alpha(follower.alpha)

            # Draw follower
            pos = follower.get_position()
            display_size = int(config.FOLLOWER_RADIUS * 2)

            # Scale down if needed
            if surface.get_width() != display_size:
                display_surface = pygame.transform.smoothscale(surface, (display_size, display_size))
            else:
                display_surface = surface

            rect = display_surface.get_rect(center=(int(pos[0]), int(pos[1])))
            self.screen.blit(display_surface, rect)

            # Draw username nametag (always visible for constant-size game)
            if config.SHOW_NAMETAGS:
                username = follower.username[:config.NAMETAG_MAX_USERNAME_LENGTH]
                text_x = int(pos[0])
                text_y = int(pos[1] + display_size // 2 + config.NAMETAG_VERTICAL_OFFSET)

                text_surface = self.font_small.render(username, True, config.NAMETAG_TEXT_COLOR)
                text_rect = text_surface.get_rect(center=(text_x, text_y))

                # Apply alpha matching follower fade-out
                if follower.alpha < 255:
                    text_surface.set_alpha(follower.alpha)

                # Outline using config colors
                outline_surface = self.font_small.render(username, True, config.NAMETAG_OUTLINE_COLOR)
                if follower.alpha < 255:
                    outline_surface.set_alpha(follower.alpha)

                for dx, dy in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
                    self.screen.blit(outline_surface, text_rect.move(dx, dy))

                self.screen.blit(text_surface, text_rect)

    def _draw_gorillas(self, gorillas: List):
        """
        Draw all gorillas with animated arms and HP bars

        Args:
            gorillas: List of all Gorilla objects
        """
        for gorilla in gorillas:
            if not gorilla.alive:
                continue

            # Draw gorilla body and arms
            self._draw_gorilla(gorilla)

            # Draw HP bar above gorilla
            self._draw_gorilla_hp_bar(gorilla)

    def _draw_gorilla(self, gorilla):
        """
        Draw a single gorilla with animated arms

        Args:
            gorilla: Gorilla object to render
        """
        pos = (int(gorilla.x), int(gorilla.y))
        radius = int(gorilla.radius)

        # Draw arms first (behind body)
        self._draw_gorilla_arms(gorilla)

        # Draw gorilla body (circular)
        pygame.draw.circle(
            self.screen,
            gorilla.color,
            pos,
            radius
        )

        # Draw body outline
        pygame.draw.circle(
            self.screen,
            (0, 0, 0),
            pos,
            radius,
            3  # Border width
        )

    def _draw_gorilla_arms(self, gorilla):
        """
        Draw animated arms for a gorilla

        Args:
            gorilla: Gorilla object with arm animation state
        """
        # Get arm endpoints from gorilla
        (left_end, right_end) = gorilla.get_arm_endpoints()

        # Shoulder positions
        shoulder_offset = gorilla.radius * 0.7
        left_shoulder = (gorilla.x - shoulder_offset, gorilla.y)
        right_shoulder = (gorilla.x + shoulder_offset, gorilla.y)

        # Arm dimensions
        arm_width = int(gorilla.radius * config.GORILLA_ARM_WIDTH_MULTIPLIER)

        # Draw left arm
        self._draw_arm(left_shoulder, left_end, arm_width, gorilla.color)

        # Draw right arm
        self._draw_arm(right_shoulder, right_end, arm_width, gorilla.color)

    def _draw_arm(self, start: Tuple[float, float], end: Tuple[float, float],
                  width: int, color: Tuple[int, int, int]):
        """
        Draw a single arm as a rotated rectangle

        Args:
            start: (x, y) shoulder position
            end: (x, y) arm endpoint
            width: Arm width in pixels
            color: RGB color tuple
        """
        # Calculate arm vector
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        length = math.sqrt(dx * dx + dy * dy)

        if length == 0:
            return

        # Calculate perpendicular vector for width
        perp_x = -dy / length * width / 2
        perp_y = dx / length * width / 2

        # Create arm polygon (rectangle)
        points = [
            (start[0] + perp_x, start[1] + perp_y),
            (start[0] - perp_x, start[1] - perp_y),
            (end[0] - perp_x, end[1] - perp_y),
            (end[0] + perp_x, end[1] + perp_y)
        ]

        # Draw filled arm
        pygame.draw.polygon(self.screen, color, points)

        # Draw arm outline
        pygame.draw.polygon(self.screen, (0, 0, 0), points, 2)

    def _draw_gorilla_hp_bar(self, gorilla):
        """
        Draw green-to-red gradient HP bar above a gorilla

        Args:
            gorilla: Gorilla object
        """
        hp_pct = gorilla.get_hp_percentage()

        # HP bar dimensions
        bar_width = config.GORILLA_HP_BAR_WIDTH
        bar_height = config.GORILLA_HP_BAR_HEIGHT
        bar_x = int(gorilla.x - bar_width // 2)
        bar_y = int(gorilla.y - gorilla.radius - 15)

        # Interpolate color from green to red based on HP
        # 100% HP = (0, 255, 0) green
        # 0% HP = (255, 0, 0) red
        red = int(255 * (1 - hp_pct))
        green = int(255 * hp_pct)
        hp_color = (red, green, 0)

        # Draw HP fill
        fill_width = int((bar_width - 2) * hp_pct)
        if fill_width > 0:
            pygame.draw.rect(
                self.screen,
                hp_color,
                (bar_x + 1, bar_y + 1, fill_width, bar_height - 2)
            )

        # Draw background for unfilled portion
        unfilled_width = (bar_width - 2) - fill_width
        if unfilled_width > 0:
            pygame.draw.rect(
                self.screen,
                config.COLOR_HP_BAR_BG,
                (bar_x + 1 + fill_width, bar_y + 1, unfilled_width, bar_height - 2)
            )

        # Draw border around entire bar
        pygame.draw.rect(
            self.screen,
            (0, 0, 0),
            (bar_x, bar_y, bar_width, bar_height),
            1
        )

    def _draw_combined_gorilla_health_bar(self, gorillas: List):
        """
        Draw large combined health bar for all gorillas at top of screen
        Shows total HP percentage remaining

        Args:
            gorillas: List of all Gorilla objects
        """
        if not gorillas:
            return

        # Calculate total HP
        total_max_hp = sum(g.max_hp for g in gorillas)
        total_current_hp = sum(g.current_hp for g in gorillas)

        if total_max_hp <= 0:
            return

        hp_percentage = (total_current_hp / total_max_hp) * 100

        # Health bar dimensions (large, centered at top)
        bar_width = 600
        bar_height = 30
        bar_x = (self.width - bar_width) // 2
        bar_y = 20

        # Background (dark semi-transparent)
        bg_surface = pygame.Surface((bar_width + 10, bar_height + 10), pygame.SRCALPHA)
        bg_surface.fill((0, 0, 0, 180))
        self.screen.blit(bg_surface, (bar_x - 5, bar_y - 5))

        # HP bar fill color (green to red gradient)
        hp_pct_normalized = total_current_hp / total_max_hp
        red = int(255 * (1 - hp_pct_normalized))
        green = int(255 * hp_pct_normalized)
        hp_color = (red, green, 0)

        # Draw background (empty portion)
        pygame.draw.rect(
            self.screen,
            (60, 60, 60),
            (bar_x, bar_y, bar_width, bar_height)
        )

        # Draw HP fill
        fill_width = int(bar_width * hp_pct_normalized)
        if fill_width > 0:
            pygame.draw.rect(
                self.screen,
                hp_color,
                (bar_x, bar_y, fill_width, bar_height)
            )

        # Draw border
        pygame.draw.rect(
            self.screen,
            (255, 255, 255),
            (bar_x, bar_y, bar_width, bar_height),
            3
        )

        # Draw percentage text (centered on bar)
        percentage_font = pygame.font.Font(None, 36)
        percentage_text = percentage_font.render(f"{hp_percentage:.1f}%", True, (255, 255, 255))
        text_rect = percentage_text.get_rect(center=(bar_x + bar_width // 2, bar_y + bar_height // 2))

        # Draw text shadow for readability
        shadow_text = percentage_font.render(f"{hp_percentage:.1f}%", True, (0, 0, 0))
        shadow_rect = shadow_text.get_rect(center=(bar_x + bar_width // 2 + 2, bar_y + bar_height // 2 + 2))
        self.screen.blit(shadow_text, shadow_rect)
        self.screen.blit(percentage_text, text_rect)

        # Draw label above bar
        label_font = pygame.font.Font(None, 24)
        label_text = label_font.render("GORILLA ARMY HP", True, (255, 255, 255))
        label_rect = label_text.get_rect(center=(bar_x + bar_width // 2, bar_y - 15))
        self.screen.blit(label_text, label_rect)

    def _get_follower_surface(self, follower) -> pygame.Surface:
        """
        Get or create cached surface for a follower

        Args:
            follower: Follower object

        Returns:
            Pygame surface with rendered avatar
        """
        # Use composite key (id, username) to prevent any ID collisions
        cache_key = (follower.id, follower.username)

        # Check if cache is valid
        cache_valid = (
            cache_key in self.follower_surfaces and
            not follower.surface_needs_update and
            cache_key in self.cached_radius and
            abs(self.cached_radius[cache_key] - config.FOLLOWER_RADIUS) < 0.01
        )

        if cache_valid:
            return self.follower_surfaces[cache_key]

        # Create new surface
        size = int(config.FOLLOWER_RADIUS * 2)
        radius = int(config.FOLLOWER_RADIUS)

        # Use higher resolution for better quality when upscaling video
        upscale_multiplier = config.UPSCALE_FACTOR if config.UPSCALE_VIDEO else 1.0
        render_size = int(size * upscale_multiplier)
        render_radius = int(radius * upscale_multiplier)

        surface = pygame.Surface((render_size, render_size), pygame.SRCALPHA)

        # Draw avatar circle
        if follower.avatar_image:
            avatar_surface = self._pil_to_pygame(follower.avatar_image, render_size)
            self._draw_circular_image(surface, avatar_surface, render_radius)
        else:
            # Draw colored circle for placeholder
            pygame.draw.circle(
                surface,
                follower.color,
                (render_radius, render_radius),
                render_radius - int(config.FOLLOWER_BORDER_WIDTH * upscale_multiplier)
            )

        # Draw black border
        pygame.draw.circle(
            surface,
            config.COLOR_BORDER,
            (render_radius, render_radius),
            render_radius,
            int(config.FOLLOWER_BORDER_WIDTH * upscale_multiplier)
        )

        # Cache the surface
        self.follower_surfaces[cache_key] = surface
        self.cached_radius[cache_key] = config.FOLLOWER_RADIUS
        follower.surface_needs_update = False

        return surface

    def _draw_circular_image(self, surface: pygame.Surface,
                           image_surface: pygame.Surface, radius: int):
        """Draw an image clipped to a circle"""
        mask = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(mask, (255, 255, 255, 255), (radius, radius),
                         radius - config.FOLLOWER_BORDER_WIDTH)

        scaled_image = pygame.transform.scale(image_surface, (radius * 2, radius * 2))
        scaled_image.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        surface.blit(scaled_image, (0, 0))

    def _draw_scoreboard(self, followers: List, gorillas: List, game_state: dict):
        """
        Draw scoreboard with title and stats

        Args:
            followers: List of all followers
            gorillas: List of all gorillas
            game_state: Game state dictionary
        """
        alive_followers = sum(1 for f in followers if f.alive)
        alive_gorillas = sum(1 for g in gorillas if g.alive)
        total_followers = len(followers)
        total_gorillas = len(gorillas)

        # Get arena for positioning
        arena_rect = config.GORILLAS_ARENA_RECT
        arena_top = arena_rect[1]
        arena_bottom = arena_rect[1] + arena_rect[3]

        # === TOP: GORILLAS VS FOLLOWERS title ===
        title_font = pygame.font.Font(None, 56)
        title_text = title_font.render("GORILLAS VS FOLLOWERS", True, config.COLOR_TEXT)
        title_rect = title_text.get_rect(center=(self.width // 2, arena_top - 50))
        self.screen.blit(title_text, title_rect)

        # "Making my followers battle every day" subtitle
        subtitle_font = pygame.font.Font(None, 32)
        subtitle_text = subtitle_font.render("Making my followers battle every day", True, config.COLOR_TEXT)
        subtitle_rect = subtitle_text.get_rect(center=(self.width // 2, arena_top - 20))
        self.screen.blit(subtitle_text, subtitle_rect)

        # === BELOW ARENA: Day and stats ===
        day_number = game_state.get("day_number", getattr(config, 'DAY_NUMBER', 1))
        day_font = pygame.font.Font(None, 36)
        day_text = day_font.render(
            f"Day {day_number}: {total_followers} followers vs {total_gorillas} gorillas",
            True, config.COLOR_TEXT
        )
        day_rect = day_text.get_rect(center=(self.width // 2, arena_bottom + 25))
        self.screen.blit(day_text, day_rect)

        # Alive stat
        stats_font = pygame.font.Font(None, 28)
        alive_text = stats_font.render(
            f"Followers: {alive_followers}/{total_followers} | Gorillas: {alive_gorillas}/{total_gorillas}",
            True, config.COLOR_TEXT
        )
        alive_rect = alive_text.get_rect(center=(self.width // 2, arena_bottom + 55))
        self.screen.blit(alive_text, alive_rect)

    def _draw_intro(self, day_number: int):
        """Draw intro overlay"""
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

        intro_text = f"Day {day_number} of making my"
        intro_text2 = "followers fight gorillas"

        text1 = self.font_large.render(intro_text, True, (255, 255, 255))
        text2 = self.font_large.render(intro_text2, True, (255, 255, 255))

        rect1 = text1.get_rect(center=(self.width // 2, self.height // 2 - 40))
        rect2 = text2.get_rect(center=(self.width // 2, self.height // 2 + 20))

        self.screen.blit(text1, rect1)
        self.screen.blit(text2, rect2)

    def _draw_countdown(self, number: int):
        """Draw countdown overlay"""
        # Don't draw countdown overlay during video export
        if config.EXPORT_VIDEO:
            return

        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 100))
        self.screen.blit(overlay, (0, 0))

        pulse = abs(math.sin(pygame.time.get_ticks() / 150.0))
        scale = 1.0 + pulse * 0.2

        if number == 0:
            text = "FIGHT!"
            color = (255, 50, 50)
        else:
            text = str(number)
            color = (255, 215, 0)

        countdown_font = pygame.font.Font(None, int(200 * scale))
        countdown_text = countdown_font.render(text, True, color)
        rect = countdown_text.get_rect(center=(self.width // 2, self.height // 2))

        # Shadow
        shadow_text = countdown_font.render(text, True, (0, 0, 0))
        shadow_rect = shadow_text.get_rect(center=(self.width // 2 + 5, self.height // 2 + 5))
        self.screen.blit(shadow_text, shadow_rect)
        self.screen.blit(countdown_text, rect)

    def _draw_victory_screen(self, victory_team: str, followers: List, gorillas: List, game_state: dict):
        """Draw victory screen with team result and scoring"""
        self.podium_animation_progress += 0.02
        if self.podium_animation_progress > 1.0:
            self.podium_animation_progress = 1.0

        # Semi-transparent overlay
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, int(180 * self.podium_animation_progress)))
        self.screen.blit(overlay, (0, 0))

        if self.podium_animation_progress < 1.0:
            return

        # Draw victory title
        pulse = abs(math.sin(pygame.time.get_ticks() / 300.0))

        if victory_team == "followers":
            title_color = (50, int(200 + pulse * 55), 50)  # Green
            title_text = "FOLLOWERS WIN!"
        else:
            title_color = (int(200 + pulse * 55), 50, 50)  # Red
            title_text = "GORILLAS WIN!"

        title = self.font_huge.render(title_text, True, title_color)
        title_y = int(self.height * 0.08)
        title_rect = title.get_rect(center=(self.width // 2, title_y))
        self.screen.blit(title, title_rect)

        # Draw leaderboard (only if followers won)
        if victory_team == "followers":
            self._draw_leaderboards(game_state, followers)
        else:
            # Show "No points awarded" message
            no_points_font = pygame.font.Font(None, 40)
            no_points_text = no_points_font.render(
                "No points awarded - Team was defeated",
                True, (200, 200, 200)
            )
            no_points_rect = no_points_text.get_rect(center=(self.width // 2, self.height // 2))
            self.screen.blit(no_points_text, no_points_rect)

    def _draw_leaderboards(self, game_state: dict, followers: list):
        """Draw current game leaderboard (centered)."""
        current_lb = game_state.get("current_game_leaderboard", [])

        if not current_lb:
            return

        follower_map = {f.username: f for f in followers}

        start_y = int(self.height * 0.25)
        board_width = int(self.width * 0.55)
        left_x = (self.width - board_width) // 2

        self._draw_leaderboard_panel(
            "TOP DAMAGE DEALERS", "GORILLA HUNTERS",
            current_lb[:10], left_x, start_y, board_width,
            (0, 200, 255), follower_map
        )

    def _draw_leaderboard_panel(self, title_line1: str, title_line2: str,
                               leaderboard: list, x: int, y: int, width: int,
                               color: tuple, follower_map: dict):
        """Draw a single leaderboard panel"""
        if not leaderboard:
            return

        entry_height = int(self.height * 0.026)
        header_height = int(self.height * 0.047)
        panel_height = header_height + len(leaderboard) * entry_height + 20

        panel = pygame.Surface((width, panel_height), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 200))
        self.screen.blit(panel, (x, y))

        # Titles
        title1_text = self.font_medium.render(title_line1, True, color)
        title1_rect = title1_text.get_rect(center=(x + width // 2, y + int(self.height * 0.013)))
        self.screen.blit(title1_text, title1_rect)

        title2_text = self.font_medium.render(title_line2, True, color)
        title2_rect = title2_text.get_rect(center=(x + width // 2, y + int(self.height * 0.029)))
        self.screen.blit(title2_text, title2_rect)

        # Entries
        medals = ["1.", "2.", "3."]
        entry_y = y + header_height

        for i, (username, points) in enumerate(leaderboard):
            rank = i + 1
            rank_str = medals[i] if i < 3 else f"{rank}."
            rank_text = self.font_small.render(rank_str, True, (200, 200, 200))

            max_len = 16
            display_name = username if len(username) <= max_len else username[:max_len-2] + ".."
            name_font = pygame.font.Font(None, 14)
            name_text = name_font.render(display_name, True, (255, 255, 255))

            points_text = self.font_small.render(f"{points:.1f} dmg", True, (0, 255, 150))

            rank_rect = rank_text.get_rect(left=x + 10, centery=entry_y)
            name_rect = name_text.get_rect(left=x + 40, centery=entry_y)
            points_rect = points_text.get_rect(right=x + width - 10, centery=entry_y)

            self.screen.blit(rank_text, rank_rect)
            self.screen.blit(name_text, name_rect)
            self.screen.blit(points_text, points_rect)

            entry_y += entry_height

    def _pil_to_pygame(self, pil_image: Image.Image, size: int) -> pygame.Surface:
        """Convert PIL image to pygame surface"""
        pil_image = pil_image.resize((size, size), Image.Resampling.LANCZOS)
        mode = pil_image.mode
        size = pil_image.size
        data = pil_image.tobytes()
        surface = pygame.image.fromstring(data, size, mode)
        return surface.convert_alpha()

    def reset(self):
        """Reset renderer state"""
        self.follower_surfaces.clear()
        self.show_podium = False
        self.podium_animation_progress = 0
        self.winners = []
