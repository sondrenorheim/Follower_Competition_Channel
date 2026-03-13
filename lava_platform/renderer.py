"""
Lava Platform Renderer - draws arena, platform, lava, players, and UI.
"""

import math
import time
from typing import List

import pygame

import config
from shared.renderer_template import RendererTemplate


class LavaPlatformRenderer(RendererTemplate):
    """Renderer for the Lava Platform game."""

    GAME_TITLE = "LAVA ESCAPE"
    GAME_SUBTITLE = "Making my Discord Members battle every day"
    GAME_SUBTITLE_LINE2 = 'Comment "RESULT: yourDiscordUsername" to see how you did'
    PLAYER_LABEL = "players"

    def __init__(self, screen: pygame.Surface):
        super().__init__(screen)

        self.font_status = pygame.font.Font(None, 26)
        self.font_round = pygame.font.Font(None, 30)
        self.font_timer = pygame.font.Font(None, 56)
        self.font_name = pygame.font.Font(None, 12)
        self.subtitle_fonts = {
            size: pygame.font.Font(None, size) for size in (24, 22, 20, 18, 16)
        }

        self.arena_fill = (100, 100, 100)
        self.arena_border = (40, 40, 40)
        self.platform_fill = (80, 180, 80)
        self.platform_border = (50, 120, 50)
        self.platform_glow = (120, 220, 120)

        self.lava_colors = [
            (255, 100, 0),
            (255, 60, 0),
            (220, 20, 0),
            (180, 10, 0),
        ]

        self.lava_bubble_time = 0.0

    def _draw_title_and_subtitle(self):
        """Draw game title and subtitle."""
        center_x = self.width // 2
        title_y = self.game_top - 100
        subtitle_y = self.game_top - 60

        title_surface = self.font_title.render(self.GAME_TITLE, True, config.COLOR_TEXT)
        title_rect = title_surface.get_rect(center=(center_x, title_y))
        self.screen.blit(title_surface, title_rect)

        subtitle_surface = self.font_subtitle.render(self.GAME_SUBTITLE, True, config.COLOR_TEXT)
        subtitle_rect = subtitle_surface.get_rect(center=(center_x, subtitle_y))
        self.screen.blit(subtitle_surface, subtitle_rect)

        max_width = self.game_right - self.game_left
        line2_surface = self._render_subtitle_line(self.GAME_SUBTITLE_LINE2, max_width)
        line2_rect = line2_surface.get_rect(
            center=(center_x, subtitle_rect.bottom + 6 + (line2_surface.get_height() // 2))
        )
        self.screen.blit(line2_surface, line2_rect)

    def _draw_day_counter(self, players: List, game_state: dict):
        """Draw day counter and join message."""
        total_count = game_state.get("total_count", len(players))
        day_text = f"Day {config.DAY_NUMBER}: {total_count} {self.PLAYER_LABEL}"
        day_padding = 2

        arena = game_state.get("arena")
        bottom_edge = arena.bottom if arena else self.game_bottom
        max_width = self.game_right - self.game_left
        day_surface = self.font_day.render(day_text, True, config.COLOR_TEXT)
        day_rect = day_surface.get_rect(midtop=(self.width // 2, int(bottom_edge + day_padding)))
        self.screen.blit(day_surface, day_rect)

        round_number = game_state.get("round_number", 0)
        part_index = game_state.get("round_part_index", 1)
        part_count = max(1, game_state.get("round_part_count", 1))
        alive_count = game_state.get("alive_count", len(players))
        active_count = max(1, game_state.get("active_count", len(players)))

        info_text = (
            f"Round {round_number} | Part {part_index}/{part_count} | "
            f"Players {alive_count}/{active_count}"
        )
        info_surface = self._render_subtitle_line(info_text, max_width)
        info_rect = info_surface.get_rect(midtop=(self.width // 2, int(day_rect.bottom + day_padding)))
        self.screen.blit(info_surface, info_rect)

        credit_text = 'Game idea given on Discord by "WiseBall17"'
        credit_surface = self._render_subtitle_line(credit_text, max_width)
        credit_rect = credit_surface.get_rect(midtop=(self.width // 2, int(info_rect.bottom + day_padding)))
        self.screen.blit(credit_surface, credit_rect)

    def _render_subtitle_line(self, text: str, max_width: int) -> pygame.Surface:
        """Render subtitle line, scaling font if needed."""
        for size in sorted(self.subtitle_fonts.keys(), reverse=True):
            font = self.subtitle_fonts[size]
            surface = font.render(text, True, config.COLOR_TEXT)
            if surface.get_width() <= max_width:
                return surface

        smallest_font = self.subtitle_fonts[min(self.subtitle_fonts.keys())]
        return smallest_font.render(text, True, config.COLOR_TEXT)

    def _draw_game_area(self, players: List, game_state: dict):
        """Draw arena, platform, and lava."""
        arena = game_state.get("arena")
        if not arena:
            return

        self._draw_arena_floor(arena)
        self._draw_obstacles(arena)
        self._draw_safe_platform(arena, game_state)

        if arena.lava_active:
            self._draw_lava(arena, game_state)

    def _draw_arena_floor(self, arena):
        """Draw the square arena floor."""
        rect = pygame.Rect(
            arena.left, arena.top,
            arena.WIDTH, arena.HEIGHT
        )
        pygame.draw.rect(self.screen, self.arena_fill, rect)
        pygame.draw.rect(self.screen, self.arena_border, rect, 4)

    def _draw_obstacles(self, arena):
        """Draw obstacle blocks."""
        obstacle_color = (60, 60, 60)  # Dark gray
        obstacle_border = (40, 40, 40)

        for obs in arena.obstacles:
            rect = pygame.Rect(obs.x, obs.y, obs.width, obs.height)
            pygame.draw.rect(self.screen, obstacle_color, rect)
            pygame.draw.rect(self.screen, obstacle_border, rect, 2)

    def _draw_safe_platform(self, arena, game_state: dict):
        """Draw the circular safe platform (only visible during scramble phase and after)."""
        platform = arena.safe_platform
        if not platform or not platform.active:
            return

        # Hide platform during waiting phase - only show when players can move to it
        round_phase = game_state.get("round_phase", "")
        if round_phase == "waiting":
            return

        cx, cy = platform.center
        radius = platform.radius

        pygame.draw.circle(
            self.screen,
            self.platform_glow,
            (int(cx), int(cy)),
            int(radius + 4)
        )

        pygame.draw.circle(
            self.screen,
            self.platform_fill,
            (int(cx), int(cy)),
            int(radius)
        )

        pygame.draw.circle(
            self.screen,
            self.platform_border,
            (int(cx), int(cy)),
            int(radius),
            3
        )

    def _draw_lava(self, arena, game_state: dict):
        """
        Draw animated lava filling the arena except platform area.
        """
        progress = game_state.get("lava_animation_progress", 1.0)
        platform = arena.safe_platform

        lava_surface = pygame.Surface((arena.WIDTH, arena.HEIGHT), pygame.SRCALPHA)

        base_alpha = int(200 * min(1.0, progress * 2))
        lava_surface.fill((255, 80, 0, base_alpha))

        self._draw_lava_bubbles(lava_surface, arena, progress)

        if platform and platform.active and progress >= 0.5:
            platform_local_x = platform.center[0] - arena.left
            platform_local_y = platform.center[1] - arena.top

            pygame.draw.circle(
                lava_surface,
                (0, 0, 0, 0),
                (int(platform_local_x), int(platform_local_y)),
                int(platform.radius + 2),
            )

            for r in range(4):
                glow_alpha = max(0, 150 - r * 40)
                pygame.draw.circle(
                    lava_surface,
                    (255, 200, 100, glow_alpha),
                    (int(platform_local_x), int(platform_local_y)),
                    int(platform.radius + 2 + r * 3),
                    2
                )

        self.screen.blit(lava_surface, (arena.left, arena.top))

    def _draw_lava_bubbles(self, surface: pygame.Surface, arena, progress: float):
        """Draw animated lava bubble effect."""
        self.lava_bubble_time = time.time()
        time_offset = self.lava_bubble_time * 2.0

        bubble_count = int(30 * progress)
        for i in range(bubble_count):
            angle = (i / max(1, bubble_count)) * 2 * math.pi
            wobble = math.sin(time_offset * 3 + i * 0.5) * 15
            base_dist = 30 + i * 12

            bx = arena.WIDTH // 2 + math.cos(angle + time_offset * 0.3) * (base_dist + wobble)
            by = arena.HEIGHT // 2 + math.sin(angle + time_offset * 0.3) * (base_dist + wobble)

            bx = max(10, min(arena.WIDTH - 10, bx))
            by = max(10, min(arena.HEIGHT - 10, by))

            color_idx = i % len(self.lava_colors)
            color = self.lava_colors[color_idx]

            bubble_radius = 8 + int(math.sin(time_offset + i) * 4)
            bubble_radius = max(4, min(18, bubble_radius))

            pygame.draw.circle(
                surface,
                (*color, 220),
                (int(bx), int(by)),
                bubble_radius
            )

    def _draw_players(self, players: List):
        """Draw all players (dead fading first, then alive)."""
        for player in players:
            if not player.alive and player.is_fading():
                self._draw_player_avatar(player)

        for player in players:
            if player.alive:
                self._draw_player_avatar(player)
                self._draw_player_name(player)

    def _draw_player_name(self, player):
        name_surface = self.font_name.render(player.username, True, config.COLOR_TEXT)
        offset_y = int(player.radius + (name_surface.get_height() / 2) + 2)
        name_rect = name_surface.get_rect(center=(int(player.x), int(player.y) + offset_y))
        self.screen.blit(name_surface, name_rect)

    def _draw_game_ui(self, players: List, game_state: dict):
        """Draw game-specific UI elements."""
        phase = game_state.get("phase", "playing")
        round_phase = game_state.get("round_phase", "")
        time_left = game_state.get("phase_time_left", 0)

        if phase == "finished":
            return

        if round_phase == "scramble":
            timer_text = f"{int(math.ceil(time_left))}s"
            timer_color = (255, 50, 50) if time_left < 3 else config.COLOR_TEXT
            timer_surface = self.font_timer.render(timer_text, True, timer_color)
            timer_rect = timer_surface.get_rect(center=(self.width // 2, self.game_top + 60))
            self.screen.blit(timer_surface, timer_rect)
