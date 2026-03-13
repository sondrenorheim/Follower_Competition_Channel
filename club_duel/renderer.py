"""Club Duel renderer."""

import math
from typing import List

import pygame

import config
from shared.renderer_template import RendererTemplate


class ClubDuelRenderer(RendererTemplate):
    """Renderer for the Club Duel game."""

    GAME_TITLE = "CLUB DUEL"
    GAME_SUBTITLE = "Making my Club Members battle every day"
    GAME_SUBTITLE_LINE2 = 'Comment "RESULT" to see how you did'
    PLAYER_LABEL = "members"
    GAME_WIDTH = config.FIGHTER_ARENA_RECT[2]
    GAME_HEIGHT = config.FIGHTER_ARENA_RECT[3]

    def __init__(self, screen: pygame.Surface):
        super().__init__(screen)
        arena_x, arena_y, arena_w, arena_h = config.FIGHTER_ARENA_RECT
        self.game_left = arena_x
        self.game_top = arena_y
        self.game_right = arena_x + arena_w
        self.game_bottom = arena_y + arena_h

        self.subtitle_fonts = {size: pygame.font.Font(None, size) for size in (24, 22, 20, 18, 16)}
        self.font_status = pygame.font.Font(None, 26)
        self.font_name = pygame.font.Font(None, 18)
        self.day_counter_offset = int(getattr(config, "CLUB_DUEL_DAY_COUNTER_OFFSET", 16))

        self.arena_fill = (200, 200, 205)
        self.arena_border = (40, 40, 40)
        self.ring_color = (120, 120, 140)
        self.duel_spot_color = (255, 220, 150)

    def _draw_title_and_subtitle(self):
        center_x = self.width // 2
        title_y = self.game_top - 70
        subtitle_y = self.game_top - 40

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

    def _render_subtitle_line(self, text: str, max_width: int) -> pygame.Surface:
        for size in sorted(self.subtitle_fonts.keys(), reverse=True):
            font = self.subtitle_fonts[size]
            surface = font.render(text, True, config.COLOR_TEXT)
            if surface.get_width() <= max_width:
                return surface
        smallest_font = self.subtitle_fonts[min(self.subtitle_fonts.keys())]
        return smallest_font.render(text, True, config.COLOR_TEXT)

    def _draw_day_counter(self, players: List, game_state: dict):
        total_count = len(players)
        day_text = f"Day {config.DAY_NUMBER}: {total_count} {self.PLAYER_LABEL}"
        y_pos = int(self.game_bottom + self.day_counter_offset)
        day_surface = self.font_day.render(day_text, True, config.COLOR_TEXT)
        day_rect = day_surface.get_rect(center=(self.width // 2, y_pos))
        self.screen.blit(day_surface, day_rect)

    def _draw_game_area(self, players: List, game_state: dict):
        arena = game_state.get("arena")
        if not arena:
            return

        rect = pygame.Rect(
            int(arena.left),
            int(arena.top),
            int(arena.right - arena.left),
            int(arena.bottom - arena.top),
        )
        pygame.draw.rect(self.screen, self.arena_fill, rect)
        pygame.draw.rect(self.screen, self.arena_border, rect, 3)

        pygame.draw.circle(
            self.screen,
            self.ring_color,
            (int(arena.center_x), int(arena.center_y)),
            int(arena.ring_radius),
            2,
        )

        duel_positions = game_state.get("duel_positions", [])
        for pos in duel_positions:
            pygame.draw.circle(self.screen, self.duel_spot_color, (int(pos[0]), int(pos[1])), 10)
            pygame.draw.circle(self.screen, self.arena_border, (int(pos[0]), int(pos[1])), 10, 2)

    def _draw_players(self, players: List, game_state: dict = None):
        elapsed = 0.0
        if game_state:
            elapsed = float(game_state.get("elapsed_time", 0.0))
        fade_duration = float(getattr(config, "CLUB_DUEL_FADE_DURATION", config.FADE_DURATION))

        for player in players:
            if not player.alive and not player.is_fading(elapsed, fade_duration):
                continue
            player.update_alpha(elapsed, fade_duration)
            self._draw_player_avatar(player)
            if player.alive:
                self._draw_player_name(player)

    def _draw_player_name(self, player):
        name_surface = self.font_name.render(player.username, True, config.COLOR_TEXT)
        offset_y = int(player.radius + (name_surface.get_height() / 2) + 2)
        name_rect = name_surface.get_rect(center=(int(player.x), int(player.y) + offset_y))
        self.screen.blit(name_surface, name_rect)

    def _draw_game_ui(self, players: List, game_state: dict):
        round_number = game_state.get("round_number", 0)
        phase = game_state.get("round_phase", "")
        time_left = game_state.get("phase_time_left", 0.0)
        alive_count = game_state.get("alive_count", len(players))

        panel_x = self.game_left + 12
        panel_y = self.game_top + 12
        panel = pygame.Surface((220, 80), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 110))
        self.screen.blit(panel, (panel_x, panel_y))

        round_text = self.font_status.render(f"Round {round_number}", True, (255, 255, 255))
        self.screen.blit(round_text, (panel_x + 12, panel_y + 8))

        phase_label = "Approach" if phase == "approach" else "Duel"
        timer_text = self.font_status.render(f"{phase_label}: {time_left:.1f}s", True, (255, 255, 255))
        self.screen.blit(timer_text, (panel_x + 12, panel_y + 30))

        alive_text = self.font_status.render(f"Alive: {alive_count}", True, (255, 255, 255))
        self.screen.blit(alive_text, (panel_x + 12, panel_y + 52))
