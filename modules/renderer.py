"""
Renderer Module
Handles all visual rendering including followers, arena, UI, and animations
"""

import pygame
import math
from typing import List, Tuple, Optional
from PIL import Image
import config
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
        self.font_large = pygame.font.Font(None, 48)
        self.font_huge = pygame.font.Font(None, 72)

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

    def render_frame(self, followers: List[Follower], arena: Arena,
                    game_state: dict):
        """
        Render complete frame

        Args:
            followers: List of all followers
            arena: Arena object
            game_state: Dictionary with game state info
        """
        # Clear screen
        self.screen.fill(config.COLOR_BACKGROUND)

        # Draw arena
        self._draw_arena(arena)

        # Draw followers
        self._draw_followers(followers, arena)

        # Draw UI elements
        self._draw_scoreboard(followers, arena, game_state)

        # Draw zone shrink warning
        if arena.get_time_until_next_shrink() < 1.0:
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

        if self.show_podium:
            self._draw_podium(self.winners)

    def _draw_arena(self, arena: Arena):
        """
        Draw the arena background and safe zone

        Args:
            arena: Arena object
        """
        # Draw main arena circle (full size)
        pygame.draw.circle(
            self.screen,
            config.COLOR_ARENA,
            arena.center,
            arena.initial_radius
        )

        # Draw danger zone (red tint outside safe zone)
        if arena.current_radius < arena.initial_radius:
            # Create a surface for the danger zone
            danger_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)

            # Draw full arena circle in red
            pygame.draw.circle(
                danger_surface,
                (*config.COLOR_DANGER_ZONE, 80),  # Semi-transparent red
                arena.center,
                arena.initial_radius
            )

            # Cut out the safe zone (make it transparent)
            pygame.draw.circle(
                danger_surface,
                (0, 0, 0, 0),  # Fully transparent
                arena.center,
                arena.current_radius
            )

            self.screen.blit(danger_surface, (0, 0))

        # Draw safe zone border
        pygame.draw.circle(
            self.screen,
            config.COLOR_SAFE_ZONE,
            arena.center,
            arena.current_radius,
            3  # Border width
        )

        # Draw pulsing effect when zone is small
        if arena.current_radius < arena.initial_radius * 0.3:
            pulse = abs(math.sin(pygame.time.get_ticks() / 200.0))
            pygame.draw.circle(
                self.screen,
                (*config.COLOR_SAFE_ZONE, int(pulse * 100)),
                arena.center,
                arena.current_radius,
                5
            )

    def _draw_followers(self, followers: List[Follower], arena: Arena):
        """
        Draw all followers with their avatars and names

        Args:
            followers: List of all followers
            arena: Arena object
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
            rect = surface.get_rect(center=(int(pos[0]), int(pos[1])))
            self.screen.blit(surface, rect)

            # Draw name below follower (if alive or fading)
            if follower.alive or follower.is_fading():
                self._draw_follower_name(follower)

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
        size = config.FOLLOWER_RADIUS * 2
        surface = pygame.Surface((size, size), pygame.SRCALPHA)

        # Draw avatar circle
        if follower.avatar_image:
            # Convert PIL image to pygame surface
            avatar_surface = self._pil_to_pygame(follower.avatar_image, size)
            # Clip to circle
            self._draw_circular_image(surface, avatar_surface, config.FOLLOWER_RADIUS)
        else:
            # Draw colored circle for placeholder
            pygame.draw.circle(
                surface,
                follower.color,
                (config.FOLLOWER_RADIUS, config.FOLLOWER_RADIUS),
                config.FOLLOWER_RADIUS - config.FOLLOWER_BORDER_WIDTH
            )

        # Draw white border
        pygame.draw.circle(
            surface,
            config.COLOR_BORDER,
            (config.FOLLOWER_RADIUS, config.FOLLOWER_RADIUS),
            config.FOLLOWER_RADIUS,
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

        # Render name text
        text = self.font_small.render(follower.username, True, config.COLOR_TEXT)
        text_rect = text.get_rect(center=(int(pos[0]),
                                         int(pos[1] + config.FOLLOWER_RADIUS + 10)))

        # Draw shadow for better visibility
        shadow = self.font_small.render(follower.username, True, (0, 0, 0))
        shadow_rect = shadow.get_rect(center=(text_rect.centerx + 1,
                                              text_rect.centery + 1))
        self.screen.blit(shadow, shadow_rect)
        self.screen.blit(text, text_rect)

    def _draw_scoreboard(self, followers: List[Follower], arena: Arena,
                        game_state: dict):
        """
        Draw scoreboard with game statistics

        Args:
            followers: List of all followers
            arena: Arena object
            game_state: Game state dictionary
        """
        alive_count = sum(1 for f in followers if f.alive)
        total_count = len(followers)

        # Create semi-transparent background
        scoreboard_surface = pygame.Surface(
            (config.SCOREBOARD_WIDTH, 200),
            pygame.SRCALPHA
        )
        pygame.draw.rect(
            scoreboard_surface,
            config.SCOREBOARD_BG_COLOR,
            (0, 0, config.SCOREBOARD_WIDTH, 200),
            border_radius=10
        )
        self.screen.blit(scoreboard_surface, (config.SCOREBOARD_X, config.SCOREBOARD_Y))

        # Draw text
        y_offset = config.SCOREBOARD_Y + 15

        # Title
        title = self.font_large.render("BATTLE ROYALE", True, config.COLOR_TEXT)
        self.screen.blit(title, (config.SCOREBOARD_X + 10, y_offset))
        y_offset += 50

        # Alive count
        alive_text = self.font_medium.render(
            f"Alive: {alive_count}/{total_count}",
            True,
            (100, 255, 100)
        )
        self.screen.blit(alive_text, (config.SCOREBOARD_X + 10, y_offset))
        y_offset += 35

        # Zone info
        zone_pct = arena.get_safe_zone_percentage()
        zone_text = self.font_medium.render(
            f"Zone: {zone_pct:.1f}%",
            True,
            config.COLOR_TEXT
        )
        self.screen.blit(zone_text, (config.SCOREBOARD_X + 10, y_offset))
        y_offset += 35

        # Next shrink timer
        time_left = arena.get_time_until_next_shrink()
        timer_color = (255, 100, 100) if time_left < 1.0 else config.COLOR_TEXT
        timer_text = self.font_medium.render(
            f"Next: {time_left:.1f}s",
            True,
            timer_color
        )
        self.screen.blit(timer_text, (config.SCOREBOARD_X + 10, y_offset))

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

        # Create marquee surface
        marquee_surface = pygame.Surface((self.width, 200), pygame.SRCALPHA)

        # Draw background
        pygame.draw.rect(
            marquee_surface,
            (0, 0, 0, int(200 * (self.top_10_alpha / 255))),
            (0, 0, self.width, 200)
        )

        # Draw title
        title = self.font_huge.render("TOP 10 SURVIVORS!", True, (255, 215, 0))
        title.set_alpha(self.top_10_alpha)
        title_rect = title.get_rect(center=(self.width // 2, 60))
        marquee_surface.blit(title, title_rect)

        # Draw survivor avatars
        alive_followers = [f for f in followers if f.alive][:10]
        total_width = len(alive_followers) * 70
        start_x = (self.width - total_width) // 2

        for i, follower in enumerate(alive_followers):
            x = start_x + i * 70
            y = 130

            # Draw small avatar
            small_surface = self._get_follower_surface(follower)
            small_surface = pygame.transform.scale(small_surface, (50, 50))
            small_surface.set_alpha(self.top_10_alpha)
            marquee_surface.blit(small_surface, (x, y))

        self.screen.blit(marquee_surface, (0, self.height // 2 - 100))

    def _draw_podium(self, winners: List[Follower]):
        """
        Draw final podium with top 3 winners

        Args:
            winners: List of winning followers (ranked)
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

        # Draw title
        title = self.font_huge.render("WINNERS!", True, (255, 215, 0))
        title_rect = title.get_rect(center=(self.width // 2, 100))
        self.screen.blit(title, title_rect)

        # Draw podium (top 3)
        podium_positions = [
            (self.width // 2, 400, "1ST", (255, 215, 0), 150),      # 1st - center, tallest
            (self.width // 2 - 200, 450, "2ND", (192, 192, 192), 120),  # 2nd - left
            (self.width // 2 + 200, 480, "3RD", (205, 127, 50), 100)    # 3rd - right
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

            # Draw avatar above podium
            avatar = self._get_follower_surface(winner)
            avatar = pygame.transform.scale(avatar, (80, 80))
            avatar_rect = avatar.get_rect(center=(x, y - 60))
            self.screen.blit(avatar, avatar_rect)

            # Draw username
            name_text = self.font_medium.render(winner.username, True, (255, 255, 255))
            name_rect = name_text.get_rect(center=(x, y - 120))
            self.screen.blit(name_text, name_rect)

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
