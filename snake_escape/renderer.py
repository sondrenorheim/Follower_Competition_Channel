"""
Snake Escape Renderer - Handles all visual rendering for the game.
"""

import os
import pygame
import math
from typing import List, Optional, Tuple

import config
from shared.renderer_template import RendererTemplate


class SnakeEscapeRenderer(RendererTemplate):
    """
    Renderer for the Snake Escape game.

    Uses a 500x500 square arena centered on screen with title above
    and day counter below.
    """

    GAME_TITLE = "SNAKE ESCAPE"
    GAME_SUBTITLE = "Making my followers battle every day"
    PLAYER_LABEL = "survivors"

    # Override dimensions for square arena
    GAME_WIDTH = 500
    GAME_HEIGHT = 500

    def __init__(self, screen: pygame.Surface):
        """Initialize the renderer."""
        super().__init__(screen)

        # Recalculate game area for 500x500 centered vertically
        # Screen is 540x960, arena is 500x500
        # Center vertically: (960 - 500) / 2 = 230
        self.game_left = (self.width - self.GAME_WIDTH) // 2  # 20
        self.game_top = (self.height - self.GAME_HEIGHT) // 2  # 230
        self.game_right = self.game_left + self.GAME_WIDTH
        self.game_bottom = self.game_top + self.GAME_HEIGHT

        # Text positions relative to arena
        self.title_y = self.game_top - 100  # 130
        self.subtitle_y = self.game_top - 60  # 170
        self.day_counter_y = self.game_bottom + 40  # 770
        self.survivors_y = self.game_bottom + 80  # 810

        # Arena colors
        self.arena_color = (220, 220, 210)  # Light tan/cream color
        self.arena_border_color = (100, 100, 100)
        self.arena_border_width = 4

        # Additional fonts
        self.font_status = pygame.font.Font(None, 28)
        self.font_small = pygame.font.Font(None, 12)  # Smaller nametag font
        self.font_prompt = pygame.font.Font(None, 24)
        self.font_promo = pygame.font.Font(None, 24)
        self.promo_text_left = "Join Discord, link in bio"
        self.promo_text_right = "Check your results in bio"
        self.discord_logo = None
        self.trophy_logo = None
        self._load_promo_assets()

    def _draw_game_area(self, players: List, game_state: dict):
        """Draw the arena background."""
        arena = game_state.get('arena')

        if arena:
            # Draw arena background at our calculated position
            arena_rect = pygame.Rect(self.game_left, self.game_top,
                                    self.GAME_WIDTH, self.GAME_HEIGHT)
            pygame.draw.rect(self.screen, self.arena_color, arena_rect)

            # Draw arena border
            pygame.draw.rect(self.screen, self.arena_border_color,
                           arena_rect, self.arena_border_width)

    def _draw_ground_pattern(self, arena_rect: pygame.Rect):
        """Draw a subtle ground pattern on the arena."""
        line_color = (200, 200, 190)
        spacing = 40

        for x in range(arena_rect.left, arena_rect.right, spacing):
            pygame.draw.line(self.screen, line_color,
                           (x, arena_rect.top), (x, arena_rect.bottom), 1)

        for y in range(arena_rect.top, arena_rect.bottom, spacing):
            pygame.draw.line(self.screen, line_color,
                           (arena_rect.left, y), (arena_rect.right, y), 1)

    def _draw_title_and_subtitle(self):
        """Draw the title and subtitle above the arena."""
        center_x = self.width // 2

        # Draw title
        title_surface = self.font_title.render(self.GAME_TITLE, True, config.COLOR_TEXT)
        title_rect = title_surface.get_rect(center=(center_x, self.title_y))
        self.screen.blit(title_surface, title_rect)

        # Draw subtitle
        subtitle_surface = self.font_subtitle.render(self.GAME_SUBTITLE, True, config.COLOR_TEXT)
        subtitle_rect = subtitle_surface.get_rect(center=(center_x, self.subtitle_y))
        self.screen.blit(subtitle_surface, subtitle_rect)

        prompt_text = getattr(config, "COMMENT_RESULT_PROMPT_TEXT", "")
        if prompt_text:
            prompt_surface = self.font_prompt.render(prompt_text, True, config.COLOR_TEXT)
            prompt_rect = prompt_surface.get_rect(center=(center_x, subtitle_rect.bottom + 6))
            self.screen.blit(prompt_surface, prompt_rect)

    def _draw_day_counter(self, players: List, game_state: dict):
        """Draw the day counter below the arena."""
        total_count = len(players)
        day_text = f"Day {config.DAY_NUMBER}: {total_count} {self.PLAYER_LABEL}"

        day_surface = self.font_day.render(day_text, True, config.COLOR_TEXT)
        day_rect = day_surface.get_rect(center=(self.width // 2, self.day_counter_y))
        self.screen.blit(day_surface, day_rect)

    def _draw_players(self, players: List):
        """Draw all followers."""
        # Draw fading followers first (so alive ones are on top)
        for follower in players:
            if not follower.alive and follower.is_fading():
                self._draw_follower(follower)

        # Draw alive followers
        for follower in players:
            if follower.alive:
                self._draw_follower(follower)

    def _draw_follower(self, follower):
        """Draw a single follower."""
        size = int(follower.radius * 2)
        avatar_surface = self._get_avatar_surface(follower, size)

        # Apply fade
        if follower.alpha < 255:
            avatar_surface = avatar_surface.copy()
            avatar_surface.set_alpha(follower.alpha)

        # Draw at position
        rect = avatar_surface.get_rect(center=(int(follower.x), int(follower.y)))
        self.screen.blit(avatar_surface, rect)

        # Draw nametag (only when player is large enough)
        if follower.radius >= config.NAMETAG_MIN_RADIUS_SNAKE_ESCAPE:
            self._draw_follower_name(follower)

    def _draw_follower_name(self, follower):
        """
        Draw follower name below their avatar
        Only shown when follower is large enough to be visible

        Args:
            follower: Follower to draw name for
        """
        # Truncate username using config
        username = follower.username[:config.NAMETAG_MAX_USERNAME_LENGTH]
        text_x = int(follower.x)
        text_y = int(follower.y + follower.radius + config.NAMETAG_VERTICAL_OFFSET)

        # Render text using config colors
        text_surface = self.font_small.render(username, True, config.NAMETAG_TEXT_COLOR)
        text_rect = text_surface.get_rect(center=(text_x, text_y))

        # Draw outline using config
        outline_surface = self.font_small.render(username, True, config.NAMETAG_OUTLINE_COLOR)
        for dx, dy in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
            self.screen.blit(outline_surface, text_rect.move(dx, dy))

        self.screen.blit(text_surface, text_rect)

    def _draw_game_ui(self, players: List, game_state: dict):
        """Draw game-specific UI elements."""
        # Get snakes from game state
        snakes = game_state.get('snakes', [])

        # Draw all snakes
        for snake in snakes:
            snake.draw(self.screen)

        # Draw survivors count
        alive_count = sum(1 for p in players if p.alive)
        self._draw_survivors_count(alive_count, len(players))

        # Draw snake speed indicator (show fastest snake's speed)
        if snakes:
            fastest_snake = max(snakes, key=lambda s: s.speed_multiplier)
            self._draw_snake_speed_indicator(fastest_snake, len(snakes))

    def _draw_survivors_count(self, alive: int, total: int):
        """Draw the survivors count below the day counter."""
        text = f"Survivors: {alive}/{total}"
        surface = self.font_status.render(text, True, config.COLOR_TEXT)
        rect = surface.get_rect(center=(self.width // 2, self.survivors_y))
        self.screen.blit(surface, rect)

    def _draw_snake_speed_indicator(self, snake, snake_count: int = 1):
        """Draw an indicator showing the snake's current speed."""
        # Position in the top-left of game area
        x_pos = self.game_left + 10
        y_pos = self.game_top + 10

        # Calculate speed percentage
        speed_pct = int(snake.speed_multiplier * 100)

        # Color changes based on speed (green -> yellow -> red)
        if speed_pct < 120:
            color = (50, 200, 50)  # Green
        elif speed_pct < 150:
            color = (200, 200, 50)  # Yellow
        else:
            color = (200, 50, 50)  # Red

        # Show snake count if more than 1
        if snake_count > 1:
            text = f"Snakes: {snake_count} | Speed: {speed_pct}%"
        else:
            text = f"Snake Speed: {speed_pct}%"
        surface = self.font_small.render(text, True, color)

        # Draw background
        bg_rect = surface.get_rect(topleft=(x_pos, y_pos))
        bg_rect.inflate_ip(10, 4)
        bg_surface = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
        bg_surface.fill((0, 0, 0, 128))
        self.screen.blit(bg_surface, bg_rect)

        # Draw text
        self.screen.blit(surface, (x_pos, y_pos))

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

    def render_frame(self, players: List, game_state: dict):
        """Render a complete frame."""
        # Clear screen
        self.screen.fill(config.COLOR_BACKGROUND)

        # Draw main game area
        self._draw_game_area(players, game_state)

        # Draw players (followers)
        self._draw_players(players)

        # Draw game-specific UI (snake, status)
        self._draw_game_ui(players, game_state)

        # Draw title and subtitle
        self._draw_title_and_subtitle()

        # Draw day counter
        self._draw_day_counter(players, game_state)

        # Draw end-game display if needed
        if game_state.get('show_leaderboards'):
            self._draw_end_game_display(
                game_state.get('current_game_leaderboard', []),
                game_state.get('all_time_leaderboard', []),
                game_state.get('winner')
            )

        self._draw_promo_overlay()
