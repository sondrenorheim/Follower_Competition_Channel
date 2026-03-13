"""
Renderer Module
Handles all visual rendering including followers, arena, UI, and animations
"""

import pygame
import math
import os
from typing import List, Tuple, Optional
from PIL import Image
import config
from shared.avatar_initials import draw_avatar_initials
from .follower import Follower
from .arena import Arena


class Renderer:
    """
    Handles all rendering operations for the battle royale game
    Manages sprites, UI elements, animations, and visual effects
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
        self.font_xlarge = pygame.font.Font(None, 36)
        self.font_large = pygame.font.Font(None, 48)
        self.font_huge = pygame.font.Font(None, 72)
        self.font_promo = pygame.font.Font(None, 24)
        self.promo_text_left = "Join Discord, link in bio"
        self.promo_text_right = "Check your results in bio"
        self.discord_logo = None
        self.trophy_logo = None
        self._load_promo_assets()

        # Cache for follower surfaces (avatar circles)
        self.follower_surfaces = {}

        # Animation state
        self.show_top_10 = False
        self.top_10_alpha = 0
        self.top_10_start_time = 0

        # Podium animation state
        self.show_podium = False
        self.podium_animation_progress = 0
        self.winners = []

        # Kill feed system
        self.kill_feed = []  # List of (username, timestamp) tuples
        self.kill_feed_duration = 3.0  # Seconds to show each elimination

        # Winner spotlight
        self.winner_zoom = 1.0  # Zoom level for winner
        self.winner_zoom_target = 1.5  # Target zoom level

        # Countdown video overlay
        self.countdown_video_frames = []
        self.countdown_video_fps = 30
        self.countdown_video_loaded = False
        self._load_countdown_video()

    def render_frame(self, followers: List[Follower], arena: Arena,
                    game_state: dict, particle_system=None):
        """
        Render complete frame

        Args:
            followers: List of all followers
            arena: Arena object
            game_state: Dictionary with game state info (includes game_phase, countdown_number, etc.)
            particle_system: Optional ParticleSystem for effects

        Returns:
            dict: Rendering statistics (rendered count, culled count)
        """
        # Clear screen
        self.screen.fill(config.COLOR_BACKGROUND)

        # Draw arena
        self._draw_arena(arena)

        # Draw followers and get rendering stats
        render_stats = self._draw_followers(followers, arena)

        # Draw particles (over followers but under UI)
        if particle_system:
            particle_system.render(self.screen)

        # Always draw scoreboard (title and bottom banner)
        self._draw_scoreboard(followers, arena, game_state)

        # Draw countdown overlay if in countdown phase
        if game_state.get("game_phase") == "countdown":
            self._draw_countdown(game_state.get("countdown_number", 3))
            self._draw_promo_overlay()
            return render_stats  # Skip other UI during countdown

        # Draw intro overlay if in intro phase
        if game_state.get("game_phase") == "intro":
            self._draw_intro(game_state.get("day_number", 1))
            self._draw_promo_overlay()
            return render_stats  # Skip other UI during intro

        # Draw zone shrink warning (only during playing phase)
        if game_state.get("game_phase") == "playing" and arena.get_time_until_next_shrink() < 1.0:
            self._draw_zone_warning()

        # Draw top 10 marquee if applicable
        alive_count = sum(1 for f in followers if f.alive)
        if alive_count == config.TOP_SURVIVORS_COUNT and not self.show_top_10:
            self.show_top_10 = True
            self.top_10_start_time = pygame.time.get_ticks() / 1000.0

        if self.show_top_10 and alive_count >= 2:
            self._draw_top_10_marquee(followers)

        # Draw podium if game is over
        if game_state.get("game_over", False) and not self.show_podium:
            self.show_podium = True
            self.podium_animation_progress = 0
            # Get final rankings
            self.winners = [f for f in followers if f.alive]
            # Store game state for leaderboard display
            self.game_state = game_state

        if self.show_podium:
            self._draw_podium(self.winners, self.game_state)

        self._draw_promo_overlay()

        # Return rendering statistics
        return render_stats

    def _draw_arena(self, arena: Arena):
        """
        Draw the arena background and safe zone (supports multiple shapes)

        Args:
            arena: Arena object
        """
        shape = arena.shape

        # Draw main arena shape (full size)
        self._draw_shape(shape, arena.center, arena.initial_radius, config.COLOR_ARENA, filled=True)

        # Draw danger zone (red outside safe zone)
        if arena.current_radius < arena.initial_radius:
            # Create a surface for the danger zone
            danger_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)

            # Draw full arena in solid red (sharper, more opaque)
            self._draw_shape(shape, arena.center, arena.initial_radius,
                           (*config.COLOR_DANGER_ZONE, 200), filled=True, surface=danger_surface)

            # Cut out the safe zone (make it transparent)
            self._draw_shape(shape, arena.center, arena.current_radius,
                           (0, 0, 0, 0), filled=True, surface=danger_surface)

            self.screen.blit(danger_surface, (0, 0))

        # Draw black outer border LAST (on top of everything)
        self._draw_shape(shape, arena.center, arena.initial_radius, (0, 0, 0), border_width=5)

    def _draw_shape(self, shape: str, center: Tuple[int, int], radius: int,
                   color: Tuple[int, ...], filled: bool = False,
                   border_width: int = 0, surface: Optional[pygame.Surface] = None):
        """
        Draw a shape (circle, square, hexagon, octagon)

        Args:
            shape: Shape type
            center: (x, y) center point
            radius: Radius or size
            color: Color tuple
            filled: Whether to fill the shape
            border_width: Border width (if not filled)
            surface: Surface to draw on (defaults to screen)
        """
        if surface is None:
            surface = self.screen

        cx, cy = center

        if shape == "circle":
            if filled or border_width == 0:
                pygame.draw.circle(surface, color, center, radius)
            else:
                pygame.draw.circle(surface, color, center, radius, border_width)

        elif shape == "square":
            rect = pygame.Rect(cx - radius, cy - radius, radius * 2, radius * 2)
            if filled or border_width == 0:
                pygame.draw.rect(surface, color, rect)
            else:
                pygame.draw.rect(surface, color, rect, border_width)

        elif shape == "hexagon":
            # Regular hexagon points
            points = []
            for i in range(6):
                angle = math.pi / 3 * i - math.pi / 2  # Start from top
                x = cx + radius * math.cos(angle)
                y = cy + radius * math.sin(angle)
                points.append((x, y))

            if filled or border_width == 0:
                pygame.draw.polygon(surface, color, points)
            else:
                pygame.draw.polygon(surface, color, points, border_width)

        elif shape == "octagon":
            # Regular octagon points
            points = []
            for i in range(8):
                angle = math.pi / 4 * i - math.pi / 2  # Start from top
                x = cx + radius * math.cos(angle)
                y = cy + radius * math.sin(angle)
                points.append((x, y))

            if filled or border_width == 0:
                pygame.draw.polygon(surface, color, points)
            else:
                pygame.draw.polygon(surface, color, points, border_width)

        else:
            # Default to circle
            if filled or border_width == 0:
                pygame.draw.circle(surface, color, center, radius)
            else:
                pygame.draw.circle(surface, color, center, radius, border_width)

    def _draw_followers(self, followers: List[Follower], arena: Arena):
        """
        Draw all followers with their avatars and names
        Uses view frustum culling for performance with large player counts

        Args:
            followers: List of all followers
            arena: Arena object
        """
        # View frustum culling bounds (with margin for partially visible followers)
        margin = config.FOLLOWER_RADIUS * 3
        screen_rect = pygame.Rect(-margin, -margin,
                                  config.SCREEN_WIDTH + margin * 2,
                                  config.SCREEN_HEIGHT + margin * 2)

        culled_count = 0
        drawn_count = 0

        for follower in followers:
            # Skip if completely faded out
            if not follower.alive and not follower.is_fading():
                continue

            # View frustum culling - skip if off-screen
            pos = follower.get_position()
            if not screen_rect.collidepoint(int(pos[0]), int(pos[1])):
                culled_count += 1
                continue

            drawn_count += 1

            # Get or create follower surface
            surface = self._get_follower_surface(follower)

            # Apply alpha for fade out
            if follower.alpha < 255:
                surface = surface.copy()
                surface.set_alpha(follower.alpha)

            # Draw follower
            rect = surface.get_rect(center=(int(pos[0]), int(pos[1])))
            self.screen.blit(surface, rect)

            # Draw name below follower (if enabled, alive or fading, and large enough)
            if config.SHOW_NAMETAGS and (follower.alive or follower.is_fading()):
                # Only show nametags when players are big enough to be visible
                if config.FOLLOWER_RADIUS >= config.NAMETAG_MIN_RADIUS_BATTLE_ROYALE:
                    self._draw_follower_name(follower)

        # Debug: Print culling stats occasionally
        # if drawn_count + culled_count > 0 and (drawn_count + culled_count) % 1000 == 0:
        #     print(f"Render: Drew {drawn_count}, Culled {culled_count}")

        # Return stats for performance monitoring
        return {"rendered": drawn_count, "culled": culled_count}

    def _get_follower_surface(self, follower: Follower) -> pygame.Surface:
        """
        Get or create cached surface for a follower
        Creates circular avatar with border

        Args:
            follower: Follower object

        Returns:
            Pygame surface with rendered avatar
        """
        # Check if we need to update the surface
        if follower.id in self.follower_surfaces and not follower.surface_needs_update:
            return self.follower_surfaces[follower.id]

        # Create new surface
        size = int(config.FOLLOWER_RADIUS * 2)
        radius = int(config.FOLLOWER_RADIUS)
        surface = pygame.Surface((size, size), pygame.SRCALPHA)

        # Draw avatar circle
        if follower.avatar_image:
            # Convert PIL image to pygame surface
            avatar_surface = self._pil_to_pygame(follower.avatar_image, size)
            # Clip to circle
            self._draw_circular_image(surface, avatar_surface, radius)
        else:
            # Draw colored circle for placeholder
            pygame.draw.circle(
                surface,
                follower.color,
                (radius, radius),
                radius - config.FOLLOWER_BORDER_WIDTH
            )
            draw_avatar_initials(
                surface,
                follower.username,
                center=(radius, radius),
                diameter=size,
            )

        # Draw white border
        pygame.draw.circle(
            surface,
            config.COLOR_BORDER,
            (radius, radius),
            radius,
            config.FOLLOWER_BORDER_WIDTH
        )

        # Cache the surface
        self.follower_surfaces[follower.id] = surface
        follower.surface_needs_update = False

        return surface

    def _draw_circular_image(self, surface: pygame.Surface,
                           image_surface: pygame.Surface, radius: int):
        """
        Draw an image clipped to a circle

        Args:
            surface: Surface to draw on
            image_surface: Image to clip
            radius: Radius of circle
        """
        # Create mask for circular clipping
        mask = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(mask, (255, 255, 255, 255), (radius, radius),
                         radius - config.FOLLOWER_BORDER_WIDTH)

        # Scale image to fit
        scaled_image = pygame.transform.scale(image_surface, (radius * 2, radius * 2))

        # Apply mask
        scaled_image.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        # Draw to surface
        surface.blit(scaled_image, (0, 0))

    def _draw_follower_name(self, follower: Follower):
        """
        Draw follower name below their avatar

        Args:
            follower: Follower object
        """
        pos = follower.get_position()

        # Truncate username using config
        username = follower.username[:config.NAMETAG_MAX_USERNAME_LENGTH]

        # Render name text using config colors
        text = self.font_small.render(username, True, config.NAMETAG_TEXT_COLOR)
        text_rect = text.get_rect(center=(int(pos[0]),
                                         int(pos[1] + config.FOLLOWER_RADIUS + config.NAMETAG_VERTICAL_OFFSET)))

        # Draw outline for better visibility using config
        outline = self.font_small.render(username, True, config.NAMETAG_OUTLINE_COLOR)
        for dx, dy in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
            outline_rect = outline.get_rect(center=(text_rect.centerx + dx, text_rect.centery + dy))
            self.screen.blit(outline, outline_rect)

        self.screen.blit(text, text_rect)

    def _draw_scoreboard(self, followers: List[Follower], arena: Arena,
                        game_state: dict):
        """
        Draw scoreboard with title above arena and stats banner below

        Args:
            followers: List of all followers
            arena: Arena object
            game_state: Game state dictionary
        """
        alive_count = sum(1 for f in followers if f.alive)
        total_count = len(followers)

        # === ABOVE CIRCLE: Title and subtitle ===
        arena_top = arena.center[1] - arena.initial_radius

        # "BATTLE ROYALE" title - positioned above subtitle
        title_font = pygame.font.Font(None, 56)
        title_text = title_font.render("BATTLE ROYALE", True, config.COLOR_TEXT)
        title_rect = title_text.get_rect(center=(self.width // 2, arena_top - 70))
        self.screen.blit(title_text, title_rect)

        # "Making my followers battle every day" - right above the circle
        subtitle_font = pygame.font.Font(None, 32)
        subtitle_text = subtitle_font.render("Making my followers battle every day", True, config.COLOR_TEXT)
        subtitle_rect = subtitle_text.get_rect(center=(self.width // 2, arena_top - 35))
        self.screen.blit(subtitle_text, subtitle_rect)

        prompt_text = getattr(config, "COMMENT_RESULT_PROMPT_TEXT", "")
        if prompt_text:
            prompt_font = pygame.font.Font(None, 24)
            prompt_surface = prompt_font.render(prompt_text, True, config.COLOR_TEXT)
            prompt_rect = prompt_surface.get_rect(center=(self.width // 2, subtitle_rect.bottom + 6))
            self.screen.blit(prompt_surface, prompt_rect)

        # === BELOW CIRCLE: "Day X: X followers" and stats ===
        day_number = game_state.get("day_number", getattr(config, 'DAY_NUMBER', 1))
        day_font = pygame.font.Font(None, 36)
        arena_bottom = arena.center[1] + arena.initial_radius
        day_text = day_font.render(f"Day {day_number}: 75032 followers", True, config.COLOR_TEXT)
        day_rect = day_text.get_rect(center=(self.width // 2, arena_bottom + 25))
        self.screen.blit(day_text, day_rect)

        # === ALIVE and ZONE stats right below day text ===
        stats_font = pygame.font.Font(None, 28)
        zone_pct = arena.get_safe_zone_percentage()

        # Color for zone based on percentage
        if zone_pct < 30:
            zone_color = (255, 50, 50)
        elif zone_pct < 60:
            zone_color = (200, 100, 0)
        else:
            zone_color = (50, 150, 50)

        # Alive stat
        alive_text = stats_font.render(f"Alive: {alive_count}/{total_count}", True, config.COLOR_TEXT)
        alive_rect = alive_text.get_rect(center=(self.width // 2 - 80, arena_bottom + 55))
        self.screen.blit(alive_text, alive_rect)

        # Zone stat
        zone_text = stats_font.render(f"Zone: {zone_pct:.0f}%", True, zone_color)
        zone_rect = zone_text.get_rect(center=(self.width // 2 + 80, arena_bottom + 55))
        self.screen.blit(zone_text, zone_rect)

    def _get_pill_size(self, text: str, logo_surface: Optional[pygame.Surface]) -> Tuple[int, int]:
        """Calculate pill size based on text and logo dimensions."""
        text_surface = self.font_promo.render(text, True, (245, 245, 245))
        text_width, text_height = text_surface.get_size()

        logo_width = logo_surface.get_width() if logo_surface else 0
        logo_height = logo_surface.get_height() if logo_surface else 0

        gap = 8 if logo_surface else 0
        padding_x = 16
        padding_y = 8

        content_width = text_width + logo_width + gap
        content_height = max(text_height, logo_height)
        pill_width = content_width + padding_x * 2
        pill_height = content_height + padding_y * 2

        return pill_width, pill_height

    def _draw_pill(self, text: str, logo_surface: Optional[pygame.Surface],
                  center_pos: Tuple[int, int]):
        """Draw a single promo pill with optional logo."""
        text_surface = self.font_promo.render(text, True, (245, 245, 245))
        text_width, text_height = text_surface.get_size()

        logo_width = logo_surface.get_width() if logo_surface else 0
        logo_height = logo_surface.get_height() if logo_surface else 0

        gap = 8 if logo_surface else 0
        padding_x = 16
        padding_y = 8

        content_width = text_width + logo_width + gap
        content_height = max(text_height, logo_height)
        pill_width = content_width + padding_x * 2
        pill_height = content_height + padding_y * 2

        pill_rect = pygame.Rect(0, 0, pill_width, pill_height)
        pill_rect.center = center_pos

        shadow_surface = pygame.Surface((pill_width, pill_height), pygame.SRCALPHA)
        pygame.draw.rect(
            shadow_surface,
            (0, 0, 0, 90),
            shadow_surface.get_rect(),
            border_radius=pill_height // 2
        )
        self.screen.blit(shadow_surface, (pill_rect.x + 2, pill_rect.y + 2))

        pill_surface = pygame.Surface((pill_width, pill_height), pygame.SRCALPHA)
        pygame.draw.rect(
            pill_surface,
            (30, 30, 35, 210),
            pill_surface.get_rect(),
            border_radius=pill_height // 2
        )
        pygame.draw.rect(
            pill_surface,
            (200, 200, 200, 40),
            pill_surface.get_rect(),
            width=1,
            border_radius=pill_height // 2
        )
        self.screen.blit(pill_surface, pill_rect.topleft)

        content_x = pill_rect.x + padding_x
        if logo_surface:
            logo_y = pill_rect.y + (pill_height - logo_height) // 2
            self.screen.blit(logo_surface, (content_x, logo_y))
            content_x += logo_width + gap

        text_center_y = pill_rect.y + pill_height // 2
        shadow_text = self.font_promo.render(text, True, (0, 0, 0))
        shadow_rect = shadow_text.get_rect(midleft=(content_x, text_center_y))
        self.screen.blit(shadow_text, shadow_rect.move(1, 1))

        text_rect = text_surface.get_rect(midleft=(content_x, text_center_y))
        self.screen.blit(text_surface, text_rect)

    def _draw_promo_overlay(self):
        """Draw promo pills in the bottom banner area."""
        base_y = self.height - 28
        gap_between = 12
        margin_x = 24

        left_width, left_height = self._get_pill_size(self.promo_text_left, self.discord_logo)
        right_width, right_height = self._get_pill_size(self.promo_text_right, self.trophy_logo)

        left_center = (margin_x + left_width // 2, base_y)
        right_center = (self.width - margin_x - right_width // 2, base_y)

        left_rect = pygame.Rect(0, 0, left_width, left_height)
        left_rect.center = left_center
        right_rect = pygame.Rect(0, 0, right_width, right_height)
        right_rect.center = right_center

        if left_rect.right + gap_between > right_rect.left:
            total_width = left_width + right_width + gap_between
            start_x = (self.width - total_width) // 2
            left_center = (start_x + left_width // 2, base_y)
            right_center = (start_x + left_width + gap_between + right_width // 2, base_y)

        self._draw_pill(self.promo_text_left, self.discord_logo, left_center)
        self._draw_pill(self.promo_text_right, self.trophy_logo, right_center)

    def _load_promo_assets(self):
        """Load and scale promo logos for the overlay pills."""
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        discord_path = os.path.join(base_dir, "discord_logo.png")
        self.discord_logo = self._load_logo([discord_path])

        trophy_paths = [
            os.path.join(base_dir, "trophy.png"),
            os.path.join(base_dir, "trophy_icon.png"),
            os.path.join(base_dir, "assets", "trophy.png"),
            os.path.join(base_dir, "website", "src", "assets", "trophy.png"),
            os.path.join(base_dir, "website", "public", "trophy.png"),
            os.path.join(base_dir, "website", "dist", "trophy.png"),
        ]
        self.trophy_logo = self._load_logo(trophy_paths)
        if self.trophy_logo is None:
            self.trophy_logo = self._render_emoji_icon("\U0001F3C6")

    def _load_logo(self, paths: List[str]) -> Optional[pygame.Surface]:
        """Load and scale a logo from the first existing path."""
        target_height = max(16, int(self.font_promo.get_height() * 1.2))
        for logo_path in paths:
            if not os.path.exists(logo_path):
                continue

            try:
                logo = pygame.image.load(logo_path).convert_alpha()
                if logo.get_height() <= 0:
                    return None
                scale = target_height / logo.get_height()
                target_width = max(1, int(logo.get_width() * scale))
                return pygame.transform.smoothscale(logo, (target_width, target_height))
            except Exception:
                return None

        return None

    def _render_emoji_icon(self, emoji_text: str) -> Optional[pygame.Surface]:
        """Render a small emoji icon as a surface fallback."""
        target_height = max(16, int(self.font_promo.get_height() * 1.2))
        try:
            emoji_font = pygame.font.SysFont("Segoe UI Emoji", target_height)
            emoji_surface = emoji_font.render(emoji_text, True, (255, 255, 255))
            if emoji_surface is None:
                return None
            return emoji_surface.convert_alpha()
        except Exception:
            return None

    def _draw_zone_warning(self):
        """
        Draw warning when zone is about to shrink
        """
        # Pulsing red border
        pulse = abs(math.sin(pygame.time.get_ticks() / 100.0))
        color = (255, int(100 * pulse), int(100 * pulse))

        # Draw border
        pygame.draw.rect(
            self.screen,
            color,
            (0, 0, self.width, self.height),
            10
        )

        # Warning text
        warning_text = self.font_large.render(
            "⚠ ZONE SHRINKING ⚠",
            True,
            color
        )
        rect = warning_text.get_rect(center=(self.width // 2, 50))
        self.screen.blit(warning_text, rect)

    def _draw_top_10_marquee(self, followers: List[Follower]):
        """
        Draw "Top 10 Survivors" marquee animation

        Args:
            followers: List of all followers
        """
        # Fade in animation
        current_time = pygame.time.get_ticks() / 1000.0
        elapsed = current_time - self.top_10_start_time

        if elapsed < 1.0:
            self.top_10_alpha = int(255 * elapsed)
        elif elapsed < 4.0:
            self.top_10_alpha = 255
        elif elapsed < 5.0:
            self.top_10_alpha = int(255 * (5.0 - elapsed))
        else:
            self.show_top_10 = False
            return

        # Create marquee surface - scaled to screen size
        marquee_height = int(self.height * 0.104)  # ~10.4% of screen height
        marquee_surface = pygame.Surface((self.width, marquee_height), pygame.SRCALPHA)

        # Draw background
        pygame.draw.rect(
            marquee_surface,
            (0, 0, 0, int(200 * (self.top_10_alpha / 255))),
            (0, 0, self.width, marquee_height)
        )

        # Draw title with scaled font
        title = self.font_large.render("TOP 10 SURVIVORS!", True, (255, 215, 0))
        title.set_alpha(self.top_10_alpha)
        title_y = int(marquee_height * 0.3)  # 30% down the marquee
        title_rect = title.get_rect(center=(self.width // 2, title_y))
        marquee_surface.blit(title, title_rect)

        # Draw survivor avatars - scaled to screen size
        alive_followers = [f for f in followers if f.alive][:10]
        avatar_spacing = int(self.width * 0.065)  # ~6.5% of screen width
        total_width = len(alive_followers) * avatar_spacing
        start_x = (self.width - total_width) // 2

        for i, follower in enumerate(alive_followers):
            x = start_x + i * avatar_spacing
            y = int(marquee_height * 0.65)  # 65% down the marquee

            # Draw small avatar - scaled to screen size
            avatar_size = int(self.width * 0.046)  # ~4.6% of screen width
            small_surface = self._get_follower_surface(follower)
            small_surface = pygame.transform.scale(small_surface, (avatar_size, avatar_size))
            small_surface.set_alpha(self.top_10_alpha)
            marquee_surface.blit(small_surface, (x, y))

        # Position at top of screen (below zone warning area)
        self.screen.blit(marquee_surface, (0, 100))

    def _draw_podium(self, winners: List[Follower], game_state: dict):
        """
        Draw final podium with top 3 winners and celebration effects

        Args:
            winners: List of winning followers (ranked)
            game_state: Game state dictionary with leaderboard data
        """
        # Increment animation progress
        self.podium_animation_progress += 0.02
        if self.podium_animation_progress > 1.0:
            self.podium_animation_progress = 1.0

        # Semi-transparent overlay
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, int(180 * self.podium_animation_progress)))
        self.screen.blit(overlay, (0, 0))

        if self.podium_animation_progress < 1.0:
            return

        # Animate winner zoom
        if self.winner_zoom < self.winner_zoom_target:
            self.winner_zoom += 0.01

        # Draw animated spotlights on the winner
        if winners:
            winner_x = self.width // 2
            # Spotlight should be at the avatar position (above podium)
            podium_y = int(self.height * 0.26)
            avatar_offset = int(self.height * 0.031)
            winner_y = podium_y - avatar_offset  # Match avatar position

            # Pulsing spotlight effect
            pulse = abs(math.sin(pygame.time.get_ticks() / 500.0))
            spotlight_radius = int(60 + pulse * 15)  # Scaled down for smaller screen

            # Draw multiple layered spotlights for glow effect
            for i in range(3):
                spotlight = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
                radius = spotlight_radius + i * 20
                alpha = int(50 / (i + 1))
                pygame.draw.circle(spotlight, (255, 255, 0, alpha),
                                 (winner_x, winner_y), radius)
                self.screen.blit(spotlight, (0, 0))

        # Draw title with animation
        title_scale = min(1.0, self.podium_animation_progress * 2)
        title = self.font_huge.render("WINNERS!", True, (255, 215, 0))

        # Add pulsing effect to title
        pulse = abs(math.sin(pygame.time.get_ticks() / 300.0))
        title_color = (255, int(215 + pulse * 40), 0)
        title = self.font_huge.render("WINNERS!", True, title_color)

        # Scale title position based on screen height
        title_y = int(self.height * 0.08)  # ~8% down the screen
        title_rect = title.get_rect(center=(self.width // 2, title_y))
        self.screen.blit(title, title_rect)

        # Draw podium (top 3) - scaled to screen size
        podium_y_base = int(self.height * 0.26)  # ~26% down the screen
        podium_offset = int(self.width * 0.185)   # ~18.5% from center
        podium_positions = [
            (self.width // 2, podium_y_base, "1ST", (255, 215, 0), int(self.height * 0.078)),           # 1st - center, tallest
            (self.width // 2 - podium_offset, podium_y_base + 25, "2ND", (192, 192, 192), int(self.height * 0.063)),  # 2nd - left
            (self.width // 2 + podium_offset, podium_y_base + 40, "3RD", (205, 127, 50), int(self.height * 0.052))    # 3rd - right
        ]

        for i, (x, y, rank, color, height) in enumerate(podium_positions):
            if i >= len(winners):
                break

            winner = winners[i]

            # Draw podium block
            pygame.draw.rect(
                self.screen,
                color,
                (x - 60, y, 120, height),
                border_radius=10
            )

            # Draw rank text
            rank_text = self.font_huge.render(rank, True, (255, 255, 255))
            rank_rect = rank_text.get_rect(center=(x, y + height // 2))
            self.screen.blit(rank_text, rank_rect)

            # Draw avatar above podium - scaled to screen size
            avatar_size = int(self.width * 0.074)  # ~7.4% of screen width
            avatar = self._get_follower_surface(winner)
            avatar = pygame.transform.scale(avatar, (avatar_size, avatar_size))
            avatar_offset = int(self.height * 0.031)  # ~3.1% of screen height
            avatar_rect = avatar.get_rect(center=(x, y - avatar_offset))
            self.screen.blit(avatar, avatar_rect)

            # Draw username - scaled position
            name_text = self.font_medium.render(winner.username, True, (255, 255, 255))
            name_offset = int(self.height * 0.063)  # ~6.3% of screen height
            name_rect = name_text.get_rect(center=(x, y - name_offset))
            self.screen.blit(name_text, name_rect)

        # Draw leaderboards below podium
        # Need to pass followers for avatar lookup
        all_followers = game_state.get("all_followers", [])
        self._draw_leaderboards(game_state, all_followers)

    def _draw_leaderboards(self, game_state: dict, followers: list):
        """
        Draw current game leaderboard (centered).
        """
        current_lb = game_state.get("current_game_leaderboard", [])
        if not current_lb:
            return

        # Create username to follower mapping for avatar lookup
        follower_map = {f.username: f for f in followers}

        # Position centered below podium
        start_y = int(self.height * 0.365)  # ~36.5% down the screen
        board_width = int(self.width * 0.6)  # widen since single board
        left_x = (self.width - board_width) // 2

        self._draw_leaderboard_panel(
            "CURRENT GAME",
            "TOP 10",
            current_lb[:10],
            left_x,
            start_y,
            board_width,
            (0, 200, 255),  # Cyan
            follower_map
        )

    def _draw_leaderboard_panel(self, title_line1: str, title_line2: str, leaderboard: list, x: int, y: int, width: int, color: tuple, follower_map: dict):
        """
        Draw a single leaderboard panel

        Args:
            title_line1: First line of title
            title_line2: Second line of title
            leaderboard: List of (username, points) tuples
            x: X position
            y: Y position
            width: Panel width
            color: Title color
            follower_map: Dictionary mapping usernames to follower objects
        """
        if not leaderboard:
            return

        # Draw semi-transparent background - scaled to screen size
        entry_height = int(self.height * 0.026)  # ~2.6% of screen height
        header_height = int(self.height * 0.047)  # ~4.7% of screen height
        panel_height = header_height + len(leaderboard) * entry_height + 20
        panel = pygame.Surface((width, panel_height), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 200))
        self.screen.blit(panel, (x, y))

        # Draw two-line title with scaled font
        title1_text = self.font_medium.render(title_line1, True, color)
        title1_rect = title1_text.get_rect(center=(x + width // 2, y + int(self.height * 0.013)))
        self.screen.blit(title1_text, title1_rect)

        title2_text = self.font_medium.render(title_line2, True, color)
        title2_rect = title2_text.get_rect(center=(x + width // 2, y + int(self.height * 0.029)))
        self.screen.blit(title2_text, title2_rect)

        # Draw entries with scaled fonts
        medals = ["🥇", "🥈", "🥉"]
        entry_y = y + header_height

        for i, (username, points) in enumerate(leaderboard):
            rank = i + 1

            # Medal or number with scaled font
            if i < 3:
                rank_text = self.font_medium.render(medals[i], True, (255, 255, 255))
            else:
                rank_text = self.font_small.render(f"{rank}.", True, (200, 200, 200))

            # Draw profile picture or black circle - scaled to screen
            avatar_size = int(self.height * 0.018)  # ~1.8% of screen height
            avatar_x = x + int(width * 0.16)  # ~16% into the panel
            avatar_y = entry_y

            follower = follower_map.get(username)
            if follower:
                # Draw follower's avatar
                avatar_surface = self._get_follower_surface(follower)
                avatar_surface = pygame.transform.scale(avatar_surface, (avatar_size, avatar_size))
                avatar_rect = avatar_surface.get_rect(center=(avatar_x, avatar_y))
                self.screen.blit(avatar_surface, avatar_rect)
            else:
                # Draw black circle as placeholder
                pygame.draw.circle(self.screen, (0, 0, 0), (avatar_x, avatar_y), avatar_size // 2)
                draw_avatar_initials(
                    self.screen,
                    username,
                    center=(avatar_x, avatar_y),
                    diameter=avatar_size,
                )
                # Draw white border around black circle
                pygame.draw.circle(self.screen, (255, 255, 255), (avatar_x, avatar_y), avatar_size // 2, 2)

            # Username (truncate if too long) with smaller font for leaderboard
            max_username_length = 18  # Allow longer usernames
            display_name = username if len(username) <= max_username_length else username[:max_username_length-2] + ".."
            leaderboard_name_font = pygame.font.Font(None, 14)  # Smaller font to fit more text
            name_text = leaderboard_name_font.render(display_name, True, (255, 255, 255))

            # Points with scaled font
            points_text = self.font_small.render(f"{points:.1f}", True, (0, 255, 150))

            # Position elements (adjusted for avatar and screen size)
            rank_rect = rank_text.get_rect(left=x + int(width * 0.04), centery=entry_y)
            name_rect = name_text.get_rect(left=avatar_x + int(avatar_size * 0.7), centery=entry_y)
            points_rect = points_text.get_rect(right=x + width - int(width * 0.04), centery=entry_y)

            # Draw
            self.screen.blit(rank_text, rank_rect)
            self.screen.blit(name_text, name_rect)
            self.screen.blit(points_text, points_rect)

            entry_y += entry_height

    def _pil_to_pygame(self, pil_image: Image.Image, size: int) -> pygame.Surface:
        """
        Convert PIL image to pygame surface

        Args:
            pil_image: PIL Image object
            size: Target size

        Returns:
            Pygame surface
        """
        # Resize
        pil_image = pil_image.resize((size, size), Image.Resampling.LANCZOS)

        # Convert to pygame surface
        mode = pil_image.mode
        size = pil_image.size
        data = pil_image.tobytes()

        surface = pygame.image.fromstring(data, size, mode)
        return surface.convert_alpha()

    def _draw_intro(self, day_number: int):
        """
        Draw intro overlay with "Day X of making my followers fight each other"

        Args:
            day_number: Day number
        """
        # Semi-transparent overlay
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

        # Draw intro text
        intro_text = f"Day {day_number} of making my"
        intro_text2 = "followers fight each other"

        text1 = self.font_large.render(intro_text, True, (255, 255, 255))
        text2 = self.font_large.render(intro_text2, True, (255, 255, 255))

        rect1 = text1.get_rect(center=(self.width // 2, self.height // 2 - 40))
        rect2 = text2.get_rect(center=(self.width // 2, self.height // 2 + 20))

        self.screen.blit(text1, rect1)
        self.screen.blit(text2, rect2)

    def _load_countdown_video(self):
        """
        Load countdown video frames from green screen video file
        """
        video_path = "assets/3 2 1 fight.mp4"
        if not os.path.exists(video_path):
            print(f"Countdown video not found: {video_path}")
            return

        try:
            import cv2
            cap = cv2.VideoCapture(video_path)
            self.countdown_video_fps = cap.get(cv2.CAP_PROP_FPS) or 30

            frames = []
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                # Convert BGR to RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # Apply chroma key (remove green screen)
                frame_with_alpha = self._apply_chroma_key(frame_rgb)

                # Convert to pygame surface
                pygame_surface = pygame.image.frombuffer(
                    frame_with_alpha.tobytes(),
                    (frame_with_alpha.shape[1], frame_with_alpha.shape[0]),
                    'RGBA'
                )
                frames.append(pygame_surface)

            cap.release()
            self.countdown_video_frames = frames
            self.countdown_video_loaded = len(frames) > 0
            print(f"Loaded countdown video: {len(frames)} frames at {self.countdown_video_fps:.0f} FPS")

        except ImportError:
            print("OpenCV not installed. Install with: pip install opencv-python")
        except Exception as e:
            print(f"Error loading countdown video: {e}")

    def _apply_chroma_key(self, frame_rgb, tolerance: int = 80):
        """
        Remove green screen from frame and return RGBA image

        Args:
            frame_rgb: RGB numpy array
            tolerance: How much green variation to remove (higher = more green removed)

        Returns:
            RGBA numpy array with green pixels made transparent
        """
        import numpy as np

        # Create alpha channel (default fully opaque)
        alpha = np.ones((frame_rgb.shape[0], frame_rgb.shape[1]), dtype=np.uint8) * 255

        # Extract RGB channels
        r = frame_rgb[:, :, 0].astype(np.int16)
        g = frame_rgb[:, :, 1].astype(np.int16)
        b = frame_rgb[:, :, 2].astype(np.int16)

        # Green screen detection: green is significantly higher than red and blue
        # Pure green screen is (0, 255, 0) or similar bright greens
        green_mask = (
            (g > 100) &  # Green must be reasonably bright
            (g > r + 30) &  # Green must be stronger than red
            (g > b + 30)  # Green must be stronger than blue
        )

        # Make green pixels transparent
        alpha[green_mask] = 0

        # Combine RGB with alpha
        frame_rgba = np.dstack((frame_rgb, alpha))

        return frame_rgba

    def _draw_countdown(self, number: int):
        """
        Draw countdown using video overlay or fallback to text
        Skip if exporting video (recorder handles it with greenscreen)

        Args:
            number: Countdown number (0 for "FIGHT!")
        """
        import config

        # Don't draw countdown overlay during video export - the recorder's greenscreen handles it
        if config.EXPORT_VIDEO:
            return

        # Try to use video overlay
        if self.countdown_video_loaded and hasattr(self, 'countdown_start_time'):
            self._draw_countdown_video()
            return

        # Fallback to text-based countdown
        self._draw_countdown_text(number)

    def _draw_countdown_video(self):
        """
        Draw the current frame of the countdown video overlay
        """
        import time

        if not hasattr(self, 'countdown_start_time') or self.countdown_start_time is None:
            return

        elapsed = time.time() - self.countdown_start_time
        frame_index = int(elapsed * self.countdown_video_fps)

        if frame_index >= len(self.countdown_video_frames):
            # Video finished
            return

        frame = self.countdown_video_frames[frame_index]

        # Scale frame to be smaller (about 40% of screen height)
        frame_width = frame.get_width()
        frame_height = frame.get_height()

        # Make it 30% of screen height
        target_height = int(self.height * 0.3)
        scale = target_height / frame_height
        new_width = int(frame_width * scale)
        new_height = target_height

        scaled_frame = pygame.transform.scale(frame, (new_width, new_height))

        # Center on screen
        x = (self.width - new_width) // 2
        y = (self.height - new_height) // 2

        self.screen.blit(scaled_frame, (x, y))

    def _draw_countdown_text(self, number: int):
        """
        Fallback text-based countdown display

        Args:
            number: Countdown number (0 for "FIGHT!")
        """
        # Semi-transparent overlay
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 100))
        self.screen.blit(overlay, (0, 0))

        # Pulsing effect
        pulse = abs(math.sin(pygame.time.get_ticks() / 150.0))
        scale = 1.0 + pulse * 0.2

        if number == 0:
            # Draw "FIGHT!"
            text = "FIGHT!"
            color = (255, 50, 50)  # Red
        else:
            # Draw countdown number
            text = str(number)
            color = (255, 215, 0)  # Gold

        # Create extra large font for countdown
        countdown_font = pygame.font.Font(None, int(200 * scale))
        countdown_text = countdown_font.render(text, True, color)
        rect = countdown_text.get_rect(center=(self.width // 2, self.height // 2))

        # Draw shadow for depth
        shadow_font = pygame.font.Font(None, int(200 * scale))
        shadow_text = shadow_font.render(text, True, (0, 0, 0))
        shadow_rect = shadow_text.get_rect(center=(self.width // 2 + 5, self.height // 2 + 5))
        self.screen.blit(shadow_text, shadow_rect)

        # Draw main text
        self.screen.blit(countdown_text, rect)

    def start_countdown_video(self):
        """
        Start the countdown video playback timer
        """
        import time
        self.countdown_start_time = time.time()
        print("Countdown video started")

    def add_elimination(self, username: str):
        """
        Add an elimination to the kill feed

        Args:
            username: Username of eliminated follower
        """
        import time
        self.kill_feed.append((username, time.time()))

        # Keep only the last 5 eliminations
        if len(self.kill_feed) > 5:
            self.kill_feed.pop(0)

    def _draw_kill_feed(self):
        """
        Draw the scrolling kill feed showing recent eliminations
        """
        import time
        current_time = time.time()

        # Remove old eliminations
        self.kill_feed = [(name, timestamp) for name, timestamp in self.kill_feed
                         if current_time - timestamp < self.kill_feed_duration]

        if not self.kill_feed:
            return

        # Draw kill feed on the left side
        feed_x = 20
        feed_y = 20
        entry_height = 30

        for i, (username, timestamp) in enumerate(reversed(self.kill_feed)):
            age = current_time - timestamp
            alpha = int(255 * (1 - age / self.kill_feed_duration))

            # Create semi-transparent background
            bg_width = 250
            bg_surface = pygame.Surface((bg_width, entry_height), pygame.SRCALPHA)
            pygame.draw.rect(bg_surface, (20, 20, 20, min(180, alpha)),
                           (0, 0, bg_width, entry_height), border_radius=5)
            self.screen.blit(bg_surface, (feed_x, feed_y + i * (entry_height + 5)))

            # Draw elimination icon and text
            text = self.font_small.render(f"❌ {username}", True, (255, 100, 100))
            text.set_alpha(alpha)
            self.screen.blit(text, (feed_x + 10, feed_y + i * (entry_height + 5) + 8))

    def reset(self):
        """
        Reset renderer state
        """
        self.follower_surfaces.clear()
        self.show_top_10 = False
        self.top_10_alpha = 0
        self.show_podium = False
        self.podium_animation_progress = 0
        self.winners = []
        self.kill_feed = []
        self.winner_zoom = 1.0
