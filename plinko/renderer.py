"""
Plinko renderer.
"""

from typing import List

import pygame

import config
from shared.renderer_template import RendererTemplate


class PlinkoRenderer(RendererTemplate):
    GAME_TITLE = "PLINKO"
    GAME_SUBTITLE = "Making my Discord Members battle every day"
    GAME_SUBTITLE_LINE2 = 'Comment "RESULT: yourDiscordUsername" to see how you did'
    PLAYER_LABEL = "players"
    GAME_WIDTH = int(config.FIGHTER_ARENA_RECT[2])
    GAME_HEIGHT = int(config.FIGHTER_ARENA_RECT[3])

    def __init__(self, screen: pygame.Surface):
        super().__init__(screen)
        arena_x, arena_y, arena_w, arena_h = config.FIGHTER_ARENA_RECT
        self.game_left = arena_x
        self.game_top = arena_y
        self.game_right = arena_x + arena_w
        self.game_bottom = arena_y + arena_h

        self.font_stage = pygame.font.Font(None, 28)
        self.font_slot = pygame.font.Font(None, int(getattr(config, "PLINKO_HOLE_LABEL_SIZE", 16)))
        self.font_count = pygame.font.Font(None, int(getattr(config, "PLINKO_HOLE_COUNT_SIZE", 16)))
        elimination_text_size = int(getattr(config, "PLINKO_ELIMINATION_TEXT_SIZE", 18))
        self.font_eliminations = pygame.font.Font(None, max(12, elimination_text_size))
        self.subtitle_fonts = {
            size: pygame.font.Font(None, size) for size in (24, 22, 20, 18, 16)
        }

        self.background_fill = getattr(config, "PLINKO_BG", (36, 34, 76))
        self.text_color = config.COLOR_TEXT
        self.board_fill = getattr(config, "PLINKO_BOARD_FILL", (42, 40, 86))
        self.board_border = getattr(config, "PLINKO_BOARD_BORDER", (70, 70, 110))
        self.peg_color = getattr(config, "PLINKO_PEG_COLOR", (245, 245, 255))
        self.hole_color = getattr(config, "PLINKO_HOLE_COLOR", (90, 40, 40))
        self.hole_border = getattr(config, "PLINKO_HOLE_BORDER", (20, 15, 30))
        self.hole_colors = getattr(config, "PLINKO_HOLE_COLORS", [])
        self.hole_outer_color = getattr(config, "PLINKO_HOLE_OUTER_COLOR", None)
        self.hole_inner_color = getattr(config, "PLINKO_HOLE_INNER_COLOR", None)
        self.hole_safe_color = getattr(config, "PLINKO_SAFE_HOLE_COLOR", None)
        self.hole_elim_color = getattr(config, "PLINKO_ELIM_HOLE_COLOR", None)
        self.hole_labels = getattr(config, "PLINKO_HOLE_LABELS", [])
        self.hole_count_color = getattr(config, "PLINKO_HOLE_COUNT_COLOR", (20, 10, 10))
        self.hole_count_offset = int(getattr(config, "PLINKO_HOLE_COUNT_OFFSET", 6))
        self.hole_count_below_offset = int(
            getattr(config, "PLINKO_HOLE_COUNT_BELOW_OFFSET", self.hole_count_offset)
        )
        self.stage_colors = getattr(
            config,
            "PLINKO_STAGE_COLORS",
            [(130, 170, 220), (140, 210, 160), (230, 190, 90), (210, 120, 140)],
        )

        self.day_counter_offset = int(getattr(config, "PLINKO_DAY_COUNTER_OFFSET", 12))
        self.elimination_list_size = int(getattr(config, "PLINKO_ELIMINATION_LIST_SIZE", 6))
        self.elimination_name_length = int(getattr(config, "PLINKO_ELIMINATION_NAME_LENGTH", 16))
        self.elimination_label = str(getattr(config, "PLINKO_ELIMINATION_LABEL", "Eliminated:"))
        self.elimination_list_x_offset = int(getattr(config, "PLINKO_ELIMINATION_LIST_X_OFFSET", 0))

    def render_frame(self, players, game_state: dict):
        self.screen.fill(config.COLOR_BACKGROUND)

        self._draw_game_area(players, game_state)
        self._draw_players(players, game_state)
        self._draw_title_and_subtitle()
        self._draw_day_counter(players, game_state)
        self._draw_game_ui(players, game_state)

        if game_state.get('show_leaderboards'):
            self._draw_end_game_display(
                game_state.get('current_game_leaderboard', []),
                game_state.get('all_time_leaderboard', []),
                game_state.get('winner')
            )

    def _draw_title_and_subtitle(self):
        center_x = self.width // 2
        title_y = self.game_top - 100
        subtitle_y = self.game_top - 60

        title_surface = self.font_title.render(self.GAME_TITLE, True, self.text_color)
        title_rect = title_surface.get_rect(center=(center_x, title_y))
        self.screen.blit(title_surface, title_rect)

        subtitle_surface = self.font_subtitle.render(self.GAME_SUBTITLE, True, self.text_color)
        subtitle_rect = subtitle_surface.get_rect(center=(center_x, subtitle_y))
        self.screen.blit(subtitle_surface, subtitle_rect)

        max_width = self.game_right - self.game_left
        line2_surface = self._render_subtitle_line(self.GAME_SUBTITLE_LINE2, max_width)
        line2_rect = line2_surface.get_rect(
            center=(center_x, subtitle_rect.bottom + 6 + (line2_surface.get_height() // 2))
        )
        self.screen.blit(line2_surface, line2_rect)

    def _draw_day_counter(self, players: List, game_state: dict):
        total_count = len(players)
        day_text = f"Day {config.DAY_NUMBER}: {total_count} {self.PLAYER_LABEL}"
        day_y = self.game_bottom + self.day_counter_offset

        day_surface = self.font_day.render(day_text, True, self.text_color)
        day_rect = day_surface.get_rect(center=(self.width // 2, day_y))
        self.screen.blit(day_surface, day_rect)

        eliminations = game_state.get("recent_eliminations") or []
        if eliminations:
            list_center_x = self.width // 2 + self.elimination_list_x_offset
            label_surface = self.font_eliminations.render(self.elimination_label, True, self.text_color)
            label_rect = label_surface.get_rect(center=(list_center_x, day_rect.bottom + 8))
            self.screen.blit(label_surface, label_rect)

            line_height = self.font_eliminations.get_linesize()
            start_y = label_rect.bottom + 4
            max_entries = max(0, self.elimination_list_size)
            if max_entries == 0:
                available_height = max(0, self.height - start_y - 6)
                max_entries = max(0, available_height // line_height)

            for idx, username in enumerate(eliminations[:max_entries]):
                display_name = username
                if len(display_name) > self.elimination_name_length:
                    display_name = display_name[:self.elimination_name_length] + "..."
                entry_surface = self.font_eliminations.render(display_name, True, self.text_color)
                entry_rect = entry_surface.get_rect(
                    center=(list_center_x, start_y + idx * line_height)
                )
                self.screen.blit(entry_surface, entry_rect)

    def _draw_game_area(self, players, game_state: dict):
        arena = game_state.get("arena")
        if arena is None:
            return

        board_rect = pygame.Rect(
            int(arena.left),
            int(arena.top),
            int(arena.right - arena.left),
            int(arena.bottom - arena.top),
        )
        pygame.draw.rect(self.screen, self.board_fill, board_rect)

        total_holes = len(arena.holes)
        safe_holes = game_state.get("safe_holes")
        hole_counts = game_state.get("hole_counts") or []
        for idx, (left, right) in enumerate(arena.holes):
            if safe_holes is not None and self.hole_safe_color is not None and self.hole_elim_color is not None:
                hole_color = self.hole_safe_color if idx in safe_holes else self.hole_elim_color
            elif self.hole_outer_color is not None and self.hole_inner_color is not None:
                if idx == 0 or idx == total_holes - 1:
                    hole_color = self.hole_outer_color
                else:
                    hole_color = self.hole_inner_color
            elif self.hole_colors:
                hole_color = self.hole_colors[idx % len(self.hole_colors)]
            else:
                hole_color = self.hole_color
            hole_rect = pygame.Rect(
                int(left),
                int(arena.hole_top),
                int(right - left),
                int(arena.bottom - arena.hole_top),
            )
            pygame.draw.rect(self.screen, hole_color, hole_rect)
            pygame.draw.rect(self.screen, self.hole_border, hole_rect, 2)

            if self.hole_labels:
                label = self.hole_labels[idx % len(self.hole_labels)]
                if label:
                    label_surface = self.font_slot.render(str(label), True, (20, 10, 10))
                    label_rect = label_surface.get_rect(center=hole_rect.center)
                    self.screen.blit(label_surface, label_rect)

            if idx < len(hole_counts):
                count_text = str(hole_counts[idx])
                count_surface = self.font_count.render(count_text, True, self.hole_count_color)
                count_rect = count_surface.get_rect(
                    center=(hole_rect.centerx, arena.bottom + self.hole_count_below_offset)
                )
                self.screen.blit(count_surface, count_rect)

        for x, y in arena.peg_positions:
            pygame.draw.circle(self.screen, self.peg_color, (int(x), int(y)), int(arena.peg_radius))

        pygame.draw.rect(self.screen, self.board_border, board_rect, 3)

    def _draw_players(self, players, game_state: dict = None):
        for player in players:
            self._draw_player_avatar(player, size=player.radius * 2)

    def _get_stage_color(self, player):
        if not self.stage_colors:
            return (120, 120, 120)
        index = getattr(player, "stage_index", 0)
        if index < 0:
            index = 0
        if index >= len(self.stage_colors):
            index = len(self.stage_colors) - 1
        return self.stage_colors[index]

    def _draw_game_ui(self, players, game_state: dict):
        round_number = int(game_state.get("round_number", 1))
        leader_name = game_state.get("leader_name")

        panel_w = 210
        panel_h = 76
        panel_x = self.game_left + 10
        panel_y = self.game_top + 10
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 110))
        self.screen.blit(panel, (panel_x, panel_y))

        stage_text = self.font_stage.render(
            f"Round {round_number}",
            True,
            (245, 245, 255),
        )
        self.screen.blit(stage_text, (panel_x + 10, panel_y + 8))

        alive_count = game_state.get("alive_count")
        if alive_count is not None:
            alive_surface = self.font_small.render(
                f"Alive: {alive_count}",
                True,
                (235, 235, 235),
            )
            self.screen.blit(alive_surface, (panel_x + 10, panel_y + 32))

        if leader_name:
            leader_surface = self.font_small.render(
                f"Leader: {leader_name}",
                True,
                (235, 235, 235),
            )
            self.screen.blit(leader_surface, (panel_x + 10, panel_y + 52))

    def _render_subtitle_line(self, text: str, max_width: int) -> pygame.Surface:
        for size in sorted(self.subtitle_fonts.keys(), reverse=True):
            font = self.subtitle_fonts[size]
            surface = font.render(text, True, self.text_color)
            if surface.get_width() <= max_width:
                return surface

        smallest_font = self.subtitle_fonts[min(self.subtitle_fonts.keys())]
        return smallest_font.render(text, True, self.text_color)
