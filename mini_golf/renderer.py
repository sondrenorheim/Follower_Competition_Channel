import pygame

import config
from shared import RendererTemplate
from shared.club_panel import draw_club_panel


class MiniGolfRenderer(RendererTemplate):
    GAME_TITLE = "MINI GOLF"
    PLAYER_LABEL = "players"
    GAME_WIDTH = getattr(config, "MAZE_RUSH_ARENA_RECT", config.FIGHTER_ARENA_RECT)[2]
    GAME_HEIGHT = getattr(config, "MAZE_RUSH_ARENA_RECT", config.FIGHTER_ARENA_RECT)[3]

    def __init__(self, screen: pygame.Surface):
        super().__init__(screen)
        arena_x, arena_y, arena_w, arena_h = getattr(
            config,
            "MAZE_RUSH_ARENA_RECT",
            config.FIGHTER_ARENA_RECT,
        )
        self.game_left = arena_x
        self.game_top = arena_y
        self.game_right = arena_x + arena_w
        self.game_bottom = arena_y + arena_h

        self.wall_color = getattr(config, "MINIGOLF_WALL_COLOR", (30, 30, 30))
        self.floor_color = getattr(config, "MINIGOLF_FLOOR_COLOR", (180, 180, 190))
        self.border_color = getattr(config, "MINIGOLF_BORDER_COLOR", (0, 0, 0))
        self.start_color = getattr(config, "MINIGOLF_START_COLOR", (80, 200, 120))
        self.hole_color = getattr(config, "MINIGOLF_HOLE_COLOR", (40, 40, 40))
        self.wall_thickness = int(getattr(config, "MINIGOLF_WALL_THICKNESS", 3))
        self.start_marker_scale = float(getattr(config, "MINIGOLF_START_MARKER_SCALE", 0.55))
        self.hole_radius = float(getattr(config, "MINIGOLF_HOLE_RADIUS", 8.0))
        self.player_size = float(getattr(config, "MINIGOLF_PLAYER_SIZE", 12))
        self.day_counter_offset = int(
            getattr(
                config,
                "MINIGOLF_DAY_COUNTER_OFFSET",
                getattr(config, "MAZE_RUSH_DAY_COUNTER_OFFSET", 14),
            )
        )
        day_counter_size = int(
            getattr(
                config,
                "MINIGOLF_DAY_COUNTER_FONT_SIZE",
                getattr(config, "MAZE_RUSH_DAY_COUNTER_FONT_SIZE", 32),
            )
        )
        self.day_counter_font = pygame.font.Font(None, day_counter_size)
        self.prompt_above_arena_margin = int(
            getattr(
                config,
                "MINIGOLF_PROMPT_ABOVE_ARENA_MARGIN",
                getattr(config, "MAZE_RUSH_PROMPT_ABOVE_ARENA_MARGIN", 8),
            )
        )
        self.finisher_list_size = int(getattr(config, "MINIGOLF_FINISHER_LIST_SIZE", 4))
        finisher_text_size = int(getattr(config, "MINIGOLF_FINISHER_TEXT_SIZE", 18))
        self.finisher_text_size = max(12, finisher_text_size)
        self.finisher_name_length = int(getattr(config, "MINIGOLF_FINISHER_NAME_LENGTH", 16))
        self.finisher_label = str(getattr(config, "MINIGOLF_FINISHER_LABEL", "In hole:"))
        self.finisher_list_x_offset = int(getattr(config, "MINIGOLF_FINISHER_LIST_X_OFFSET", 0))
        self.font_finishers = pygame.font.Font(None, self.finisher_text_size)
        club_text_size = int(getattr(config, "CLUB_PANEL_TEXT_SIZE", 16))
        self.font_club_panel = pygame.font.Font(None, club_text_size)
        self._club_panel_bottom = None

        self._course_surface = None
        self._course_signature = None

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
        arena_top = self.game_top
        subtitle_rect = None

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
            prompt_y = int(arena_top - self.prompt_above_arena_margin)
            if subtitle_rect is not None:
                prompt_y = max(prompt_y, subtitle_rect.bottom + 6)
            prompt_rect = prompt_surface.get_rect(center=(self.width // 2, prompt_y))
            self.screen.blit(prompt_surface, prompt_rect)

    def _draw_game_area(self, players, game_state: dict):
        course = game_state.get("course")
        if course:
            self._ensure_course_surface(course)
            if self._course_surface:
                self.screen.blit(self._course_surface, (course.origin_x, course.origin_y))

        arena_rect = pygame.Rect(
            self.game_left,
            self.game_top,
            self.game_right - self.game_left,
            self.game_bottom - self.game_top,
        )
        pygame.draw.rect(self.screen, self.border_color, arena_rect, 3)

    def _ensure_course_surface(self, course):
        if self._course_signature == course.signature and self._course_surface is not None:
            return

        self._course_signature = course.signature
        surface = pygame.Surface((course.width, course.height))
        surface.fill(self.floor_color)

        marker_size = max(4, int(course.cell_size * self.start_marker_scale))
        start_center = course.cell_center(course.start_cell, local=True)
        hole_center = course.cell_center(course.hole_cell, local=True)
        start_rect = pygame.Rect(0, 0, marker_size, marker_size)
        start_rect.center = (int(start_center[0]), int(start_center[1]))
        pygame.draw.rect(surface, self.start_color, start_rect)

        pygame.draw.circle(
            surface,
            self.hole_color,
            (int(hole_center[0]), int(hole_center[1])),
            int(self.hole_radius)
        )
        pygame.draw.circle(
            surface,
            (0, 0, 0),
            (int(hole_center[0]), int(hole_center[1])),
            int(self.hole_radius),
            2
        )

        for (x1, y1), (x2, y2) in course.wall_segments:
            pygame.draw.line(
                surface,
                self.wall_color,
                (int(x1), int(y1)),
                (int(x2), int(y2)),
                self.wall_thickness,
            )

        self._course_surface = surface

    def _draw_players(self, players, game_state: dict):
        club_players = []
        for player in players:
            if player.eliminated or player.finished:
                continue
            if getattr(player, "is_club_member", False):
                club_players.append(player)
                continue
            self._draw_player_avatar(player, size=self.player_size)

        for player in club_players:
            self._draw_club_glow(player, size=self.player_size)
            self._draw_player_avatar(player, size=self.player_size)

    def _draw_day_counter(self, players, game_state: dict):
        total_count = len(players)
        day_text = f"Day {config.DAY_NUMBER}: {total_count} {self.PLAYER_LABEL}"
        y_pos = int(self.game_bottom + self.day_counter_offset)
        day_surface = self.day_counter_font.render(day_text, True, config.COLOR_TEXT)
        day_rect = day_surface.get_rect(center=(self.width // 2, y_pos))
        self.screen.blit(day_surface, day_rect)

        anchor_y = day_rect.bottom

        elimination_text = getattr(
            config,
            "MINIGOLF_ELIMINATION_TEXT",
            "Make it to the hole in 10 shots or get eliminated",
        )
        instruction_rect = None
        if elimination_text:
            instruction_surface = self.font_small.render(elimination_text, True, config.COLOR_TEXT)
            instruction_rect = instruction_surface.get_rect(
                center=(self.width // 2, anchor_y + 10)
            )
            self.screen.blit(instruction_surface, instruction_rect)
            anchor_y = instruction_rect.bottom

        panel_rect = draw_club_panel(
            self.screen,
            game_state.get("club_spotlight"),
            anchor_y=anchor_y,
            font=self.font_club_panel,
            get_avatar_surface=self._get_avatar_surface,
            glow_cache=self._club_glow_cache,
        )
        if panel_rect is not None:
            anchor_y = panel_rect.bottom
        self._club_panel_bottom = anchor_y

        finishers = game_state.get("recent_finishers") or []
        if finishers:
            finisher_center_x = self.width // 2 + self.finisher_list_x_offset
            label_surface = self.font_finishers.render(self.finisher_label, True, config.COLOR_TEXT)
            label_rect = label_surface.get_rect(center=(finisher_center_x, anchor_y + 8))
            self.screen.blit(label_surface, label_rect)

            line_height = self.font_finishers.get_linesize()
            start_y = label_rect.bottom + 4
            max_entries = self.finisher_list_size
            if max_entries <= 0:
                available_height = max(0, self.height - start_y - 6)
                max_entries = max(0, available_height // line_height)
            for idx, username in enumerate(finishers[:max_entries]):
                display_name = username
                if len(display_name) > self.finisher_name_length:
                    display_name = display_name[:self.finisher_name_length] + "..."
                entry_surface = self.font_finishers.render(display_name, True, config.COLOR_TEXT)
                entry_rect = entry_surface.get_rect(
                    center=(finisher_center_x, start_y + idx * line_height)
                )
                self.screen.blit(entry_surface, entry_rect)

    def _draw_game_ui(self, players, game_state: dict):
        round_number = game_state.get("round_number")
        total_rounds = game_state.get("total_rounds")
        shot_number = game_state.get("shot_number")
        max_shots = game_state.get("max_shots")
        finished_count = game_state.get("finished_count")
        active_count = game_state.get("active_count", len(players))
        moving_count = game_state.get("moving_count")
        next_shot_in = game_state.get("next_shot_in")
        leader_name = game_state.get("leader_name")
        round_state = game_state.get("round_state", "active")
        elimination_mode = game_state.get("elimination_mode", False)
        sudden_death = game_state.get("sudden_death", False)

        if round_number is None:
            return

        panel_w = 240
        panel_h = 92
        panel_x = self.game_left + 10
        panel_y = self.game_top + 10
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 110))
        self.screen.blit(panel, (panel_x, panel_y))

        line_y = panel_y + 6
        if elimination_mode or not total_rounds:
            round_text = f"Round {round_number}"
        else:
            round_text = f"Round {round_number}/{total_rounds}"
        self.screen.blit(self.font_stats.render(round_text, True, (255, 255, 255)), (panel_x + 10, line_y))
        line_y += 22

        if sudden_death and shot_number is not None and max_shots is not None and shot_number > max_shots:
            shot_text = f"Shots used: {shot_number}"
        else:
            shot_text = f"Shots used: {shot_number}/{max_shots}"
        self.screen.blit(self.font_stats.render(shot_text, True, (255, 255, 255)), (panel_x + 10, line_y))
        line_y += 22

        finished_text = f"Finished {finished_count}/{active_count}"
        self.screen.blit(self.font_small.render(finished_text, True, (255, 255, 255)), (panel_x + 10, line_y))
        line_y += 18

        # Status text intentionally omitted to keep HUD compact.

        if leader_name:
            leader_surface = self.font_small.render(f"Leader: {leader_name}", True, (255, 255, 255))
            self.screen.blit(leader_surface, (panel_x + 10, panel_y + panel_h - 18))
