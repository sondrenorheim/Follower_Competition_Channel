"""
Renderer Template - Blueprint for game rendering
Copy this file to your new game folder and customize it.

This template provides:
- Standard UI layout:
  * Title above game area (56pt font)
  * "Making my followers battle every day" subtitle (32pt font)
  * Main game area (centered, 500px width default)
  * Day counter below game area ("Day X: XX players")
- End-game display:
  * Winner spotlight with avatar
  * Current Game Top 10 leaderboard
  * All-Time Top 10 leaderboard
  * Semi-transparent black overlay

Usage:
1. Copy this file to your_game/renderer.py
2. Rename the class to match your game (e.g., YourGameRenderer)
3. Implement _draw_game_area() and _draw_players() for your game
4. Customize colors and layout as needed
"""

import pygame
import math
from typing import List, Any, Optional, Tuple

import config
from .avatar_initials import draw_avatar_initials


# =============================================================================
# LAYOUT CONSTANTS - Standard positioning for all games
# =============================================================================

# Game area dimensions (same as obstacle course track width)
DEFAULT_GAME_WIDTH = 500
DEFAULT_GAME_HEIGHT = 700

# Calculate positions based on screen size
GAME_AREA_LEFT = (config.SCREEN_WIDTH - DEFAULT_GAME_WIDTH) // 2
GAME_AREA_TOP = 160
GAME_AREA_RIGHT = GAME_AREA_LEFT + DEFAULT_GAME_WIDTH
GAME_AREA_BOTTOM = GAME_AREA_TOP + DEFAULT_GAME_HEIGHT

# Title and text positions
TITLE_Y = GAME_AREA_TOP - 100  # Title above game area
SUBTITLE_Y = GAME_AREA_TOP - 60  # Subtitle right above game area
DAY_COUNTER_Y = GAME_AREA_BOTTOM + 30  # Day counter below game area

# Leaderboard panel dimensions (as percentage of screen)
PANEL_WIDTH_PCT = 0.44  # 44% of screen width
PANEL_SPACING_PCT = 0.037  # 3.7% spacing between panels
PANEL_START_Y_PCT = 0.365  # 36.5% down screen


class RendererTemplate:
    """
    Template for game rendering.

    Provides standard UI layout:
    - Title and subtitle above game area
    - Main game area (centered)
    - Day counter below game area
    - End-game leaderboards with winner display

    Override methods to customize rendering for your specific game.
    """

    # =============================================================================
    # CONFIGURATION - Override in subclass
    # =============================================================================

    GAME_TITLE = "GAME TITLE"  # Override with your game title
    GAME_SUBTITLE = "Making my followers battle every day"  # Standard subtitle
    PLAYER_LABEL = "players"  # e.g., "racers", "fighters", "followers"

    # Game area dimensions (override if needed)
    GAME_WIDTH = DEFAULT_GAME_WIDTH
    GAME_HEIGHT = DEFAULT_GAME_HEIGHT

    def __init__(self, screen: pygame.Surface):
        """
        Initialize the renderer.

        Args:
            screen: Pygame screen surface
        """
        self.screen = screen
        self.width = screen.get_width()
        self.height = screen.get_height()

        # Calculate game area bounds
        self.game_left = (self.width - self.GAME_WIDTH) // 2
        self.game_top = GAME_AREA_TOP
        self.game_right = self.game_left + self.GAME_WIDTH
        self.game_bottom = self.game_top + self.GAME_HEIGHT

        # Initialize fonts
        self._init_fonts()

        # Avatar cache for high-res rendering
        self.avatar_cache = {}
        self._club_glow_cache = {}

    def _init_fonts(self):
        """Initialize standard fonts."""
        self.font_title = pygame.font.Font(None, 56)      # Main title
        self.font_subtitle = pygame.font.Font(None, 32)   # Subtitle
        self.font_day = pygame.font.Font(None, 36)        # Day counter
        self.font_stats = pygame.font.Font(None, 28)      # Stats display
        self.font_small = pygame.font.Font(None, 24)      # Small text
        self.font_leaderboard_header = pygame.font.Font(None, 28)
        self.font_leaderboard_entry = pygame.font.Font(None, 14)
        self.font_winner = pygame.font.Font(None, 72)     # Winner title
        self.font_winner_name = pygame.font.Font(None, 48)

    # =============================================================================
    # MAIN RENDER METHOD
    # =============================================================================

    def render_frame(self, players: List[Any], game_state: dict):
        """
        Render a complete frame.

        Args:
            players: List of player entities
            game_state: Dictionary containing:
                - phase: "intro", "countdown", "playing", "finished"
                - alive_count: Number of alive players
                - total_count: Total players
                - show_leaderboards: Whether to show end-game leaderboards
                - current_game_leaderboard: List for current game top 10
                - all_time_leaderboard: List for all-time top 10
                - winner: Winner player object (optional)
                - Additional game-specific state
        """
        # Clear screen
        self.screen.fill(config.COLOR_BACKGROUND)

        # Draw main game area
        self._draw_game_area(players, game_state)

        # Draw players
        self._draw_players(players)

        # Draw title and day counter (always visible, overlaid on top)
        self._draw_title_and_subtitle()
        self._draw_day_counter(players, game_state)

        # Draw game-specific UI
        self._draw_game_ui(players, game_state)

        # Draw end-game leaderboards if game is finished
        if game_state.get('show_leaderboards'):
            self._draw_end_game_display(
                game_state.get('current_game_leaderboard', []),
                game_state.get('all_time_leaderboard', []),
                game_state.get('winner')
            )

    # =============================================================================
    # TITLE AND DAY COUNTER
    # =============================================================================

    def _draw_title_and_subtitle(self):
        """Draw the title and subtitle above the game area."""
        center_x = self.width // 2

        # Draw title
        title_surface = self.font_title.render(self.GAME_TITLE, True, config.COLOR_TEXT)
        title_rect = title_surface.get_rect(center=(center_x, TITLE_Y))
        self.screen.blit(title_surface, title_rect)

        # Draw subtitle
        subtitle_surface = self.font_subtitle.render(self.GAME_SUBTITLE, True, config.COLOR_TEXT)
        subtitle_rect = subtitle_surface.get_rect(center=(center_x, SUBTITLE_Y))
        self.screen.blit(subtitle_surface, subtitle_rect)

    def _draw_day_counter(self, players: List[Any], game_state: dict):
        """
        Draw the day counter below the game area.

        Args:
            players: List of players
            game_state: Game state dictionary
        """
        total_count = len(players)
        day_text = f"Day {config.DAY_NUMBER}: {total_count} {self.PLAYER_LABEL}"

        day_surface = self.font_day.render(day_text, True, config.COLOR_TEXT)
        day_rect = day_surface.get_rect(center=(self.width // 2, DAY_COUNTER_Y))
        self.screen.blit(day_surface, day_rect)

    # =============================================================================
    # GAME AREA - Override these methods
    # =============================================================================

    def _draw_game_area(self, players: List[Any], game_state: dict):
        """
        Draw the main game area (arena, track, etc.).
        Override this method to implement your game's background/arena.

        The game area should be drawn within these bounds:
        - Left: self.game_left
        - Top: self.game_top
        - Right: self.game_right
        - Bottom: self.game_bottom

        Example:
            # Draw arena background
            arena_rect = pygame.Rect(self.game_left, self.game_top,
                                    self.GAME_WIDTH, self.GAME_HEIGHT)
            pygame.draw.rect(self.screen, config.COLOR_ARENA, arena_rect)

            # Draw arena border
            pygame.draw.rect(self.screen, (100, 100, 100), arena_rect, 3)
        """
        # Default: Draw a simple bordered rectangle
        arena_rect = pygame.Rect(self.game_left, self.game_top,
                                self.GAME_WIDTH, self.GAME_HEIGHT)
        pygame.draw.rect(self.screen, config.COLOR_ARENA, arena_rect)
        pygame.draw.rect(self.screen, (100, 100, 100), arena_rect, 3)

    def _draw_players(self, players: List[Any]):
        """
        Draw all players.
        Override this method to implement player rendering.

        Args:
            players: List of player entities

        Example:
            for player in players:
                if not player.alive:
                    continue

                # Draw player circle with avatar
                self._draw_player_avatar(player)

                # Draw player name if enabled
                if config.SHOW_FOLLOWER_NAMES:
                    self._draw_player_name(player)
        """
        # TODO: Implement player rendering
        pass

    def _draw_game_ui(self, players: List[Any], game_state: dict):
        """
        Draw game-specific UI elements.
        Override this method to add custom UI (stats, progress bars, etc.).

        Args:
            players: List of players
            game_state: Game state dictionary

        Example:
            # Draw alive counter
            alive_count = game_state.get('alive_count', 0)
            text = f"Alive: {alive_count}"
            surface = self.font_stats.render(text, True, (255, 255, 255))
            self.screen.blit(surface, (10, 10))
        """
        pass

    # =============================================================================
    # PLAYER RENDERING HELPERS
    # =============================================================================

    def _draw_player_avatar(self, player, size: Optional[int] = None):
        """
        Draw a player's avatar at their position.

        Args:
            player: Player entity with x, y, color, avatar_image attributes
            size: Optional override for avatar size (default: config.FOLLOWER_RADIUS * 2)
        """
        if size is None:
            size = config.FOLLOWER_RADIUS * 2
        # Ensure size is a valid integer for surface creation and PIL resize.
        size = max(1, int(round(size)))

        # Get or create avatar surface
        avatar_surface = self._get_avatar_surface(player, size)

        # Apply fade if player has alpha < 255
        if hasattr(player, 'alpha') and player.alpha < 255:
            avatar_surface = avatar_surface.copy()
            avatar_surface.set_alpha(player.alpha)

        # Draw at player position
        rect = avatar_surface.get_rect(center=(int(player.x), int(player.y)))
        self.screen.blit(avatar_surface, rect)

    def _draw_club_glow(self, player, size: Optional[int] = None, pos: Optional[Tuple[int, int]] = None):
        """
        Draw a glowing ring behind a club member avatar.
        """
        if size is None:
            size = config.FOLLOWER_RADIUS * 2
        size = max(1, int(round(size)))
        radius = max(1, size // 2)

        color = getattr(config, "CLUB_GLOW_COLOR", (255, 240, 190))
        alpha = int(getattr(config, "CLUB_GLOW_ALPHA", 180))
        layers = int(getattr(config, "CLUB_GLOW_LAYERS", 3))
        padding = int(getattr(config, "CLUB_GLOW_PADDING", 3))

        cache_key = (radius, color, alpha, layers, padding)
        surface = self._club_glow_cache.get(cache_key)
        if surface is None:
            glow_radius = radius + padding + layers
            size_px = glow_radius * 2 + 4
            surface = pygame.Surface((size_px, size_px), pygame.SRCALPHA)
            center = (size_px // 2, size_px // 2)

            base_radius = radius + padding
            for i in range(max(1, layers)):
                layer_alpha = int(alpha * (1.0 - (i / max(1, layers))))
                ring_radius = base_radius + i
                pygame.draw.circle(
                    surface,
                    (*color, layer_alpha),
                    center,
                    ring_radius,
                    width=2,
                )

            inner_alpha = min(255, alpha + 40)
            pygame.draw.circle(
                surface,
                (*color, inner_alpha),
                center,
                radius + 1,
                width=2,
            )

            self._club_glow_cache[cache_key] = surface

        if pos is None:
            pos = (int(player.x), int(player.y))
        rect = surface.get_rect(center=(int(pos[0]), int(pos[1])))
        self.screen.blit(surface, rect)

    def _get_avatar_surface(self, player, size: int) -> pygame.Surface:
        """
        Get or create a circular avatar surface for a player.

        Args:
            player: Player entity
            size: Desired size in pixels

        Returns:
            Pygame surface with circular avatar
        """
        # Normalize size and check cache.
        size = max(1, int(round(size)))
        username = str(getattr(player, "username", "") or "")
        avatar_image = getattr(player, "avatar_image", None)
        has_avatar = bool(avatar_image)
        fallback_color = tuple(getattr(player, "color", (100, 100, 255)))
        cache_key = (username, size, has_avatar, fallback_color)
        if cache_key in self.avatar_cache:
            return self.avatar_cache[cache_key]

        # Create surface
        surface = pygame.Surface((size, size), pygame.SRCALPHA)

        if has_avatar:
            # Use profile picture
            pil_image = avatar_image
            pil_resized = pil_image.resize((size, size))
            mode = pil_resized.mode
            data = pil_resized.tobytes()
            img_surface = pygame.image.fromstring(data, (size, size), mode)

            # Create circular mask
            mask = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.circle(mask, (255, 255, 255, 255),
                             (size // 2, size // 2), size // 2)

            # Apply mask
            img_surface = img_surface.convert_alpha()
            img_surface.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            surface.blit(img_surface, (0, 0))
        else:
            # Use colored circle with username initials.
            pygame.draw.circle(surface, fallback_color, (size // 2, size // 2), size // 2)
            draw_avatar_initials(
                surface,
                username,
                center=(size // 2, size // 2),
                diameter=size,
            )

        # Add black border
        pygame.draw.circle(surface, (0, 0, 0),
                          (size // 2, size // 2), size // 2, config.FOLLOWER_BORDER_WIDTH)

        # Cache and return
        self.avatar_cache[cache_key] = surface
        return surface

    def _draw_player_name(self, player, offset_y: int = 20):
        """
        Draw a player's username below their avatar.

        Args:
            player: Player entity with x, y, username attributes
            offset_y: Vertical offset from player position
        """
        name_surface = self.font_small.render(player.username, True, config.COLOR_TEXT)
        name_rect = name_surface.get_rect(center=(int(player.x), int(player.y) + offset_y))
        self.screen.blit(name_surface, name_rect)

    # =============================================================================
    # END-GAME DISPLAY
    # =============================================================================

    def _draw_end_game_display(self, current_game_board: list, all_time_board: list,
                               winner=None):
        """
        Draw end-game display with winner and a single current-game leaderboard.
        """
        # Draw semi-transparent overlay
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        # Draw winner display
        if winner:
            self._draw_winner_display(winner)

        # Calculate panel dimensions
        panel_width = int(self.width * PANEL_WIDTH_PCT * 1.2)  # widen since single panel
        start_y = int(self.height * PANEL_START_Y_PCT)

        center_panel_x = (self.width - panel_width) // 2

        # Draw centered panel - Current Game
        self._draw_leaderboard_panel(
            entries=current_game_board[:10],
            x=center_panel_x,
            y=start_y,
            width=panel_width,
            title_line1="CURRENT GAME",
            title_line2="TOP 10",
            title_color=(0, 200, 255),  # Cyan
            is_current_game=True
        )

    def _draw_winner_display(self, winner):
        """
        Draw the winner spotlight above the leaderboards.

        Args:
            winner: Winner player object
        """
        # Pulsing effect
        pulse = abs(math.sin(pygame.time.get_ticks() / 300.0))
        title_color = (255, int(215 + pulse * 40), 0)

        # Draw "WINNER!" title
        title = self.font_winner.render("WINNER!", True, title_color)
        title_y = int(self.height * 0.08)
        title_rect = title.get_rect(center=(self.width // 2, title_y))
        self.screen.blit(title, title_rect)

        # Winner avatar position
        winner_y = int(self.height * 0.22)

        # Spotlight effect
        spotlight_radius = int(60 + pulse * 15)
        for i in range(3):
            spotlight = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            radius = spotlight_radius + i * 20
            alpha = int(50 / (i + 1))
            pygame.draw.circle(spotlight, (255, 255, 0, alpha),
                             (self.width // 2, winner_y), radius)
            self.screen.blit(spotlight, (0, 0))

        # Draw winner avatar
        avatar_size = int(self.width * 0.15)
        avatar_surface = self._get_avatar_surface(winner, avatar_size)
        avatar_rect = avatar_surface.get_rect(center=(self.width // 2, winner_y))
        self.screen.blit(avatar_surface, avatar_rect)

        # Draw winner username
        name_text = self.font_winner_name.render(winner.username, True, (255, 255, 255))
        name_rect = name_text.get_rect(center=(self.width // 2, winner_y + avatar_size // 2 + 30))
        self.screen.blit(name_text, name_rect)

    def _draw_leaderboard_panel(self, entries: list, x: int, y: int, width: int,
                                title_line1: str, title_line2: str, title_color: tuple,
                                is_current_game: bool):
        """
        Draw a single leaderboard panel.

        Args:
            entries: List of tuples (username, points) or (username, points, stats)
            x, y: Top-left position
            width: Panel width
            title_line1, title_line2: Two-line title
            title_color: Title text color
            is_current_game: True if current game, False if all-time
        """
        entry_height = int(self.height * 0.026)
        header_height = 60
        panel_height = header_height + (len(entries) * entry_height) + 20

        # Draw background
        bg_surface = pygame.Surface((width, panel_height), pygame.SRCALPHA)
        bg_surface.fill((0, 0, 0, 200))
        self.screen.blit(bg_surface, (x, y))

        # Draw title
        title1 = self.font_leaderboard_header.render(title_line1, True, title_color)
        title1_rect = title1.get_rect(center=(x + width // 2, y + 20))
        self.screen.blit(title1, title1_rect)

        title2 = self.font_leaderboard_header.render(title_line2, True, title_color)
        title2_rect = title2.get_rect(center=(x + width // 2, y + 42))
        self.screen.blit(title2, title2_rect)

        # Draw entries
        medals = ["1", "2", "3"]
        for i, entry in enumerate(entries):
            entry_y = y + header_height + (i * entry_height)

            # Rank/medal
            if i < 3:
                rank_text = medals[i]
            else:
                rank_text = f"{i + 1}."

            # Extract data
            if is_current_game:
                username, points = entry[0], entry[2] if len(entry) > 2 else entry[1]
            else:
                username = entry[0]
                points = entry[1]

            # Draw rank
            rank_surface = self.font_leaderboard_entry.render(rank_text, True, (255, 255, 255))
            self.screen.blit(rank_surface, (x + 10, entry_y + 2))

            # Draw username (truncated)
            max_len = 18
            display_name = username[:max_len] + "..." if len(username) > max_len else username
            name_surface = self.font_leaderboard_entry.render(display_name, True, (255, 255, 255))
            self.screen.blit(name_surface, (x + 50, entry_y + 2))

            # Draw points
            points_text = f"{points:.1f}"
            points_surface = self.font_leaderboard_entry.render(points_text, True, (0, 255, 150))
            points_rect = points_surface.get_rect(right=x + width - 10, top=entry_y + 2)
            self.screen.blit(points_surface, points_rect)

    # =============================================================================
    # UTILITY METHODS
    # =============================================================================

    def get_game_area_rect(self) -> pygame.Rect:
        """Get the game area as a pygame Rect."""
        return pygame.Rect(self.game_left, self.game_top,
                          self.GAME_WIDTH, self.GAME_HEIGHT)

    def world_to_screen(self, pos: Tuple[float, float]) -> Tuple[int, int]:
        """
        Convert world coordinates to screen coordinates.
        Override this method if your game uses a camera or scrolling.

        Args:
            pos: (x, y) world position

        Returns:
            (x, y) screen position
        """
        return (int(pos[0]), int(pos[1]))

    def clear_avatar_cache(self):
        """Clear the avatar cache (call when avatars need to be regenerated)."""
        self.avatar_cache.clear()
