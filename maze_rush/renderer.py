import pygame

import config
from shared import RendererTemplate


class MazeRushRenderer(RendererTemplate):
    GAME_TITLE = "MAZE RUSH"
    PLAYER_LABEL = "players"
    GAME_WIDTH = config.FIGHTER_ARENA_RECT[2]
    GAME_HEIGHT = config.FIGHTER_ARENA_RECT[3]

    def __init__(self, screen: pygame.Surface):
        super().__init__(screen)
        arena_x, arena_y, arena_w, arena_h = config.FIGHTER_ARENA_RECT
        self.game_left = arena_x
        self.game_top = arena_y
        self.game_right = arena_x + arena_w
        self.game_bottom = arena_y + arena_h

        self.wall_color = getattr(config, "MAZE_RUSH_WALL_COLOR", (30, 30, 30))
        self.floor_color = getattr(config, "MAZE_RUSH_FLOOR_COLOR", (180, 180, 190))
        self.border_color = getattr(config, "MAZE_RUSH_BORDER_COLOR", (0, 0, 0))
        self.start_color = getattr(config, "MAZE_RUSH_START_COLOR", (80, 200, 120))
        self.exit_color = getattr(config, "MAZE_RUSH_EXIT_COLOR", (255, 120, 80))
        self.wall_thickness = int(getattr(config, "MAZE_RUSH_WALL_THICKNESS", 3))
        self.marker_scale = float(getattr(config, "MAZE_RUSH_MARKER_SCALE", 0.55))
        self.player_size = float(getattr(config, "MAZE_RUSH_PLAYER_SIZE", 12))
        self.day_counter_offset = int(getattr(config, "MAZE_RUSH_DAY_COUNTER_OFFSET", 18))

        self._maze_surface = None
        self._maze_signature = None

    def render_frame(self, players, game_state: dict):
        self.screen.fill(config.COLOR_BACKGROUND)
        self._draw_game_area(players, game_state)
        self._draw_players(players)
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
        arena_top = config.FIGHTER_ARENA_RECT[1]

        title_font = pygame.font.Font(None, 56)
        title_text = title_font.render(self.GAME_TITLE, True, config.COLOR_TEXT)
        title_rect = title_text.get_rect(center=(self.width // 2, arena_top - 70))
        self.screen.blit(title_text, title_rect)

        subtitle_font = pygame.font.Font(None, 32)
        subtitle_text = subtitle_font.render(self.GAME_SUBTITLE, True, config.COLOR_TEXT)
        subtitle_rect = subtitle_text.get_rect(center=(self.width // 2, arena_top - 40))
        self.screen.blit(subtitle_text, subtitle_rect)

        prompt_text = getattr(config, "COMMENT_RESULT_PROMPT_TEXT", "")
        if prompt_text:
            prompt_font = pygame.font.Font(None, 24)
            prompt_surface = prompt_font.render(prompt_text, True, config.COLOR_TEXT)
            prompt_rect = prompt_surface.get_rect(center=(self.width // 2, subtitle_rect.bottom + 6))
            self.screen.blit(prompt_surface, prompt_rect)

    def _draw_game_area(self, players, game_state: dict):
        maze = game_state.get("maze")
        if maze:
            self._ensure_maze_surface(maze)
            if self._maze_surface:
                self.screen.blit(self._maze_surface, (maze.origin_x, maze.origin_y))

        arena_rect = pygame.Rect(
            self.game_left,
            self.game_top,
            self.game_right - self.game_left,
            self.game_bottom - self.game_top,
        )
        pygame.draw.rect(self.screen, self.border_color, arena_rect, 3)

    def _ensure_maze_surface(self, maze):
        if self._maze_signature == maze.signature and self._maze_surface is not None:
            return

        self._maze_signature = maze.signature
        surface = pygame.Surface((maze.width, maze.height))
        surface.fill(self.floor_color)

        marker_size = max(4, int(maze.cell_size * self.marker_scale))
        start_center = maze.cell_center(maze.start_cell, local=True)
        exit_center = maze.cell_center(maze.exit_cell, local=True)
        start_rect = pygame.Rect(0, 0, marker_size, marker_size)
        start_rect.center = (int(start_center[0]), int(start_center[1]))
        exit_rect = pygame.Rect(0, 0, marker_size, marker_size)
        exit_rect.center = (int(exit_center[0]), int(exit_center[1]))
        pygame.draw.rect(surface, self.start_color, start_rect)
        pygame.draw.rect(surface, self.exit_color, exit_rect)

        for (x1, y1), (x2, y2) in maze.wall_segments:
            pygame.draw.line(
                surface,
                self.wall_color,
                (int(x1), int(y1)),
                (int(x2), int(y2)),
                self.wall_thickness,
            )

        self._maze_surface = surface

    def _draw_players(self, players):
        for player in players:
            self._draw_player_avatar(player, size=self.player_size)

    def _draw_day_counter(self, players, game_state: dict):
        total_count = len(players)
        day_text = f"Day {config.DAY_NUMBER}: {total_count} {self.PLAYER_LABEL}"
        y_pos = int(self.game_bottom + self.day_counter_offset)
        day_surface = self.font_day.render(day_text, True, config.COLOR_TEXT)
        day_rect = day_surface.get_rect(center=(self.width // 2, y_pos))
        self.screen.blit(day_surface, day_rect)

    def _draw_game_ui(self, players, game_state: dict):
        elapsed = game_state.get("elapsed_time")
        leader_name = game_state.get("leader_name")
        if elapsed is None and not leader_name:
            return

        panel_w = 220
        panel_h = 56
        panel_x = self.game_left + 10
        panel_y = self.game_top + 10
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 110))
        self.screen.blit(panel, (panel_x, panel_y))

        if elapsed is not None:
            time_text = self.font_stats.render(f"Time {elapsed:.1f}s", True, (255, 255, 255))
            self.screen.blit(time_text, (panel_x + 12, panel_y + 8))

        if leader_name:
            leader_surface = self.font_small.render(f"Leader: {leader_name}", True, (255, 255, 255))
            self.screen.blit(leader_surface, (panel_x + 12, panel_y + 30))
