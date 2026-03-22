import math
import random
from typing import Iterable

import pygame

import config
from shared import RendererTemplate
from shared.club_panel import draw_club_panel


class FollowersIORenderer(RendererTemplate):
    GAME_TITLE = "FOLLOWERS.IO"
    GAME_SUBTITLE = "Making my followers fight every day"
    PLAYER_LABEL = "followers"
    GAME_WIDTH = config.FOLLOWERS_IO_ARENA_RECT[2]
    GAME_HEIGHT = config.FOLLOWERS_IO_ARENA_RECT[3]

    def __init__(self, screen: pygame.Surface):
        super().__init__(screen)

        arena_x, arena_y, arena_w, arena_h = config.FOLLOWERS_IO_ARENA_RECT
        self.world_left = float(arena_x)
        self.world_top = float(arena_y)
        self.world_width = float(arena_w)
        self.world_height = float(arena_h)

        self.game_left = int(arena_x)
        self.game_top = int(arena_y)
        self.game_right = int(arena_x + arena_w)
        self.game_bottom = int(arena_y + arena_h)

        self.bg_color = tuple(getattr(config, "FOLLOWERS_IO_BG_COLOR", (232, 239, 244)))
        self.grid_color = tuple(getattr(config, "FOLLOWERS_IO_GRID_COLOR", (202, 216, 225)))
        self.border_color = tuple(getattr(config, "FOLLOWERS_IO_BORDER_COLOR", (20, 20, 20)))
        self.food_color = tuple(getattr(config, "FOLLOWERS_IO_FOOD_COLOR", (115, 168, 121)))
        self.highlight_ring_color = tuple(
            getattr(config, "FOLLOWERS_IO_HIGHLIGHT_RING_COLOR", (255, 188, 67))
        )
        self.highlight_text_color = tuple(
            getattr(config, "FOLLOWERS_IO_HIGHLIGHT_TEXT_COLOR", (20, 20, 20))
        )

        self.cull_render_limit = int(getattr(config, "FOLLOWERS_IO_CULL_RENDER_LIMIT", 3200))
        self.full_avatar_alive_threshold = int(
            getattr(config, "FOLLOWERS_IO_FULL_AVATAR_ALIVE_THRESHOLD", 700)
        )
        self.food_draw_limit = int(getattr(config, "FOLLOWERS_IO_FOOD_DRAW_LIMIT", 1800))
        self.leader_avatar_min_size = int(
            getattr(config, "FOLLOWERS_IO_LEADER_AVATAR_MIN_SIZE", 16)
        )
        self.live_leader_count = int(getattr(config, "FOLLOWERS_IO_LIVE_LEADER_COUNT", 5))

        leader_font_size = int(getattr(config, "FOLLOWERS_IO_LEADER_LABEL_FONT_SIZE", 18))
        self.font_leader_label = pygame.font.Font(None, max(12, leader_font_size))
        self.font_leaderboard = pygame.font.Font(None, 22)
        self.font_phase = pygame.font.Font(None, 28)
        self.font_phase_small = pygame.font.Font(None, 21)
        self.font_eliminations = pygame.font.Font(
            None,
            max(12, int(getattr(config, "FOLLOWERS_IO_ELIMINATION_TEXT_SIZE", 18))),
        )
        self.font_club_panel = pygame.font.Font(
            None,
            int(getattr(config, "CLUB_PANEL_TEXT_SIZE", 16)),
        )

        self.day_counter_offset = int(getattr(config, "FOLLOWERS_IO_DAY_COUNTER_OFFSET", 18))
        self.elimination_list_size = int(getattr(config, "FOLLOWERS_IO_ELIMINATION_LIST_SIZE", 0))
        self.elimination_name_length = int(
            getattr(config, "FOLLOWERS_IO_ELIMINATION_NAME_LENGTH", 16)
        )
        self.elimination_label = str(
            getattr(config, "FOLLOWERS_IO_ELIMINATION_LABEL", "Consumed:")
        )
        self.elimination_list_x_offset = int(
            getattr(config, "FOLLOWERS_IO_ELIMINATION_LIST_X_OFFSET", 0)
        )
        self._club_panel_bottom = None

        self._background_surface = None
        self._build_background()

    def _build_background(self):
        width = int(self.world_width)
        height = int(self.world_height)
        if width <= 0 or height <= 0:
            return

        rng = random.Random(int(getattr(config, "DAY_NUMBER", 1)))
        surface = pygame.Surface((width, height), pygame.SRCALPHA)
        surface.fill(self.bg_color)

        for _ in range(22):
            radius = rng.randint(18, 88)
            cx = rng.randint(0, width)
            cy = rng.randint(0, height)
            alpha = rng.randint(10, 28)
            pygame.draw.circle(surface, (255, 255, 255, alpha), (cx, cy), radius)

        grid_step = max(24, int(getattr(config, "FOLLOWERS_IO_GRID_STEP", 32)))
        for x in range(0, width, grid_step):
            pygame.draw.line(surface, self.grid_color, (x, 0), (x, height), 1)
        for y in range(0, height, grid_step):
            pygame.draw.line(surface, self.grid_color, (0, y), (width, y), 1)

        self._background_surface = surface

    def render_frame(self, players, game_state: dict):
        self.screen.fill(config.COLOR_BACKGROUND)
        self._draw_game_area(players, game_state)
        self._draw_players(players, game_state)
        self._draw_title_and_subtitle()
        self._draw_day_counter(players, game_state)
        self._draw_game_ui(players, game_state)

        if game_state.get("show_leaderboards"):
            self._draw_end_game_display(
                game_state.get("current_game_leaderboard", []),
                game_state.get("all_time_leaderboard", []),
                game_state.get("winner"),
            )

    def _get_area_rect(self) -> pygame.Rect:
        return pygame.Rect(
            self.game_left,
            self.game_top,
            self.game_right - self.game_left,
            self.game_bottom - self.game_top,
        )

    def _get_camera_rect(self, game_state: dict) -> tuple[float, float, float, float]:
        camera_rect = game_state.get("camera_rect")
        if camera_rect and len(camera_rect) == 4:
            return tuple(float(value) for value in camera_rect)
        return (
            self.world_left,
            self.world_top,
            self.world_width,
            self.world_height,
        )

    def _get_camera_scales(self, camera_rect: tuple[float, float, float, float]) -> tuple[float, float]:
        cam_w = max(1.0, float(camera_rect[2]))
        cam_h = max(1.0, float(camera_rect[3]))
        area_rect = self._get_area_rect()
        return (area_rect.width / cam_w, area_rect.height / cam_h)

    def _world_to_screen(
        self,
        x: float,
        y: float,
        camera_rect: tuple[float, float, float, float],
    ) -> tuple[int, int]:
        cam_x, cam_y, _, _ = camera_rect
        scale_x, scale_y = self._get_camera_scales(camera_rect)
        sx = self.game_left + ((x - cam_x) * scale_x)
        sy = self.game_top + ((y - cam_y) * scale_y)
        return (int(round(sx)), int(round(sy)))

    def _world_to_screen_radius(
        self,
        radius: float,
        camera_rect: tuple[float, float, float, float],
    ) -> float:
        scale_x, scale_y = self._get_camera_scales(camera_rect)
        return max(1.0, radius * min(scale_x, scale_y))

    def _player_in_camera(
        self,
        player,
        camera_rect: tuple[float, float, float, float],
        margin: float = 16.0,
    ) -> bool:
        cam_x, cam_y, cam_w, cam_h = camera_rect
        return (
            (player.x + player.radius) >= (cam_x - margin)
            and (player.x - player.radius) <= (cam_x + cam_w + margin)
            and (player.y + player.radius) >= (cam_y - margin)
            and (player.y - player.radius) <= (cam_y + cam_h + margin)
        )

    def _draw_title_and_subtitle(self):
        arena_top = self.game_top
        title_text = self.font_title.render(self.GAME_TITLE, True, config.COLOR_TEXT)
        title_rect = title_text.get_rect(center=(self.width // 2, arena_top - 70))
        self.screen.blit(title_text, title_rect)

        subtitle_text = self.font_subtitle.render(self.GAME_SUBTITLE, True, config.COLOR_TEXT)
        subtitle_rect = subtitle_text.get_rect(center=(self.width // 2, arena_top - 40))
        self.screen.blit(subtitle_text, subtitle_rect)

        prompt_text = getattr(config, "COMMENT_RESULT_PROMPT_TEXT", "")
        if prompt_text:
            prompt_font = pygame.font.Font(None, 24)
            prompt_surface = prompt_font.render(prompt_text, True, config.COLOR_TEXT)
            prompt_rect = prompt_surface.get_rect(center=(self.width // 2, subtitle_rect.bottom + 6))
            self.screen.blit(prompt_surface, prompt_rect)

    def _draw_game_area(self, players, game_state: dict):
        area_rect = self._get_area_rect()
        camera_rect = self._get_camera_rect(game_state)

        if self._background_surface is not None:
            cam_x, cam_y, cam_w, cam_h = camera_rect
            src_left = int(math.floor(cam_x - self.world_left))
            src_top = int(math.floor(cam_y - self.world_top))
            src_right = int(math.ceil((cam_x + cam_w) - self.world_left))
            src_bottom = int(math.ceil((cam_y + cam_h) - self.world_top))

            src_left = max(0, min(self._background_surface.get_width() - 1, src_left))
            src_top = max(0, min(self._background_surface.get_height() - 1, src_top))
            src_right = max(src_left + 1, min(self._background_surface.get_width(), src_right))
            src_bottom = max(src_top + 1, min(self._background_surface.get_height(), src_bottom))

            src_rect = pygame.Rect(
                src_left,
                src_top,
                src_right - src_left,
                src_bottom - src_top,
            )
            crop = self._background_surface.subsurface(src_rect).copy()
            if crop.get_size() != area_rect.size:
                crop = pygame.transform.smoothscale(crop, area_rect.size)
            self.screen.blit(crop, area_rect.topleft)
        else:
            pygame.draw.rect(self.screen, self.bg_color, area_rect)

        pygame.draw.rect(self.screen, self.border_color, area_rect, 3)

    def _collect_renderable_players(self, players: Iterable) -> list:
        fade_duration = float(getattr(config, "FADE_DURATION", 0.5))
        renderable = []
        for player in players:
            if player.alive:
                player.alpha = 255
                renderable.append(player)
                continue
            if player.is_fading(fade_duration):
                player.update_fade(fade_duration)
                renderable.append(player)
        return renderable

    def _draw_food(self, food_particles, camera_rect: tuple[float, float, float, float]):
        if not food_particles:
            return

        food_list = list(food_particles)
        if len(food_list) > self.food_draw_limit > 0:
            step = len(food_list) / float(self.food_draw_limit)
            food_list = [food_list[int(idx * step)] for idx in range(self.food_draw_limit)]

        for orb in food_list:
            sx, sy = self._world_to_screen(orb.x, orb.y, camera_rect)
            radius = int(
                max(
                    1.0,
                    min(
                        6.0,
                        self._world_to_screen_radius(max(0.9, math.sqrt(max(0.0, orb.mass)) * 0.55), camera_rect),
                    ),
                )
            )
            pygame.draw.circle(self.screen, self.food_color, (sx, sy), radius)

    def _draw_cull_players(self, players, camera_rect: tuple[float, float, float, float]):
        for player in players:
            if not self._player_in_camera(player, camera_rect):
                continue
            sx, sy = self._world_to_screen(player.x, player.y, camera_rect)
            radius = max(1, min(4, int(round(self._world_to_screen_radius(player.radius * 0.9, camera_rect)))))
            if getattr(player, "is_club_member", False):
                self._draw_club_glow(player, size=max(10, radius * 4), pos=(sx, sy))
            pygame.draw.circle(self.screen, tuple(getattr(player, "color", (100, 100, 255))), (sx, sy), radius)
            pygame.draw.circle(self.screen, (0, 0, 0), (sx, sy), radius, 1)

    def _draw_player_circle(self, player, pos: tuple[int, int], radius: int):
        radius = max(1, int(radius))
        color = tuple(getattr(player, "color", (100, 100, 255)))
        alpha = int(getattr(player, "alpha", 255))
        if alpha >= 255:
            pygame.draw.circle(self.screen, color, pos, radius)
            pygame.draw.circle(self.screen, (0, 0, 0), pos, radius, 1)
            return

        surface = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
        center = (radius + 2, radius + 2)
        pygame.draw.circle(surface, (*color, alpha), center, radius)
        pygame.draw.circle(surface, (0, 0, 0, alpha), center, radius, 1)
        rect = surface.get_rect(center=pos)
        self.screen.blit(surface, rect)

    def _draw_highlight_ring(self, pos: tuple[int, int], radius: int, alpha: int = 255):
        ring_radius = max(6, radius + 5)
        ring_surface = pygame.Surface((ring_radius * 2 + 8, ring_radius * 2 + 8), pygame.SRCALPHA)
        center = (ring_radius + 4, ring_radius + 4)
        pygame.draw.circle(
            ring_surface,
            (*self.highlight_ring_color, min(255, alpha)),
            center,
            ring_radius,
            3,
        )
        self.screen.blit(ring_surface, ring_surface.get_rect(center=pos))

    def _draw_avatar_at(self, player, pos: tuple[int, int], size: int):
        size = max(1, int(round(size)))
        avatar_surface = self._get_avatar_surface(player, size)
        alpha = int(getattr(player, "alpha", 255))
        if alpha < 255:
            avatar_surface = avatar_surface.copy()
            avatar_surface.set_alpha(alpha)
        self.screen.blit(avatar_surface, avatar_surface.get_rect(center=pos))

    def _draw_leader_label(
        self,
        player,
        pos: tuple[int, int],
        radius: int,
        rank: int,
    ):
        display_name = player.username
        if len(display_name) > 12:
            display_name = display_name[:12] + "..."
        label_text = f"{rank}. {display_name}  {int(player.mass)}"
        label_surface = self.font_leader_label.render(label_text, True, self.highlight_text_color)
        pad_x = 8
        pad_y = 5
        bubble = pygame.Surface(
            (label_surface.get_width() + pad_x * 2, label_surface.get_height() + pad_y * 2),
            pygame.SRCALPHA,
        )
        bubble.fill((255, 246, 224, 225))
        pygame.draw.rect(
            bubble,
            self.highlight_ring_color,
            bubble.get_rect(),
            2,
            border_radius=10,
        )
        bubble.blit(label_surface, (pad_x, pad_y))

        label_x = pos[0] - (bubble.get_width() // 2)
        label_y = pos[1] - radius - bubble.get_height() - 8
        label_x = max(self.game_left + 4, min(self.game_right - bubble.get_width() - 4, label_x))
        label_y = max(self.game_top + 4, min(self.game_bottom - bubble.get_height() - 4, label_y))
        self.screen.blit(bubble, (label_x, label_y))

    def _draw_readable_players(self, players, game_state: dict, camera_rect: tuple[float, float, float, float]):
        alive_count = int(game_state.get("alive_count", len(players)))
        live_leaders = list(game_state.get("live_leaders") or [])
        leader_lookup = {id(player): rank + 1 for rank, player in enumerate(live_leaders)}
        full_avatar_mode = alive_count <= self.full_avatar_alive_threshold

        renderable = [player for player in players if self._player_in_camera(player, camera_rect)]
        renderable.sort(key=lambda player: (not player.alive, player.radius, player.username))

        for player in renderable:
            pos = self._world_to_screen(player.x, player.y, camera_rect)
            radius = int(round(self._world_to_screen_radius(player.radius, camera_rect)))
            radius = max(2, min(72, radius))

            is_leader = id(player) in leader_lookup
            is_club_member = bool(getattr(player, "is_club_member", False))
            use_avatar = full_avatar_mode or is_leader or is_club_member

            if is_leader:
                self._draw_highlight_ring(pos, radius, alpha=int(getattr(player, "alpha", 255)))
            if is_club_member:
                glow_size = max(self.leader_avatar_min_size, radius * 2 + 8)
                self._draw_club_glow(player, size=glow_size, pos=pos)

            if use_avatar:
                avatar_size = max(
                    self.leader_avatar_min_size if is_leader else 12,
                    min(84, radius * 2),
                )
                self._draw_avatar_at(player, pos, avatar_size)
            else:
                self._draw_player_circle(player, pos, radius)

        for player in live_leaders:
            if not player.alive or not self._player_in_camera(player, camera_rect, margin=6.0):
                continue
            pos = self._world_to_screen(player.x, player.y, camera_rect)
            radius = int(round(self._world_to_screen_radius(player.radius, camera_rect)))
            self._draw_leader_label(player, pos, max(2, radius), leader_lookup[id(player)])

    def _draw_players(self, players, game_state: dict):
        renderable = self._collect_renderable_players(players)
        camera_rect = self._get_camera_rect(game_state)
        area_rect = self._get_area_rect()

        previous_clip = self.screen.get_clip()
        self.screen.set_clip(area_rect)
        try:
            phase_name = str(game_state.get("phase_name", "playing") or "playing")
            if phase_name in ("readable", "showdown"):
                self._draw_food(game_state.get("food_particles", []) or [], camera_rect)
                self._draw_readable_players(renderable, game_state, camera_rect)
            else:
                self._draw_cull_players(renderable, camera_rect)
        finally:
            self.screen.set_clip(previous_clip)

    def _draw_day_counter(self, players, game_state: dict):
        total_count = int(game_state.get("total_count", len(players)))
        day_text = f"Day {config.DAY_NUMBER}: {total_count:,} {self.PLAYER_LABEL}"
        y_pos = int(self.game_bottom + self.day_counter_offset)
        day_surface = self.font_day.render(day_text, True, config.COLOR_TEXT)
        day_rect = day_surface.get_rect(center=(self.width // 2, y_pos))
        self.screen.blit(day_surface, day_rect)

        anchor_y = day_rect.bottom
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

        eliminations = game_state.get("recent_eliminations") or []
        if not eliminations:
            return

        list_center_x = self.width // 2 + self.elimination_list_x_offset
        label_surface = self.font_eliminations.render(self.elimination_label, True, config.COLOR_TEXT)
        label_rect = label_surface.get_rect(center=(list_center_x, anchor_y + 8))
        self.screen.blit(label_surface, label_rect)

        line_height = self.font_eliminations.get_linesize()
        start_y = label_rect.bottom + 4
        max_entries = self.elimination_list_size
        if max_entries <= 0:
            available_height = max(0, self.height - start_y - 6)
            max_entries = max(0, available_height // line_height)

        for idx, username in enumerate(eliminations[:max_entries]):
            display_name = username
            if len(display_name) > self.elimination_name_length:
                display_name = display_name[:self.elimination_name_length] + "..."
            entry_surface = self.font_eliminations.render(display_name, True, config.COLOR_TEXT)
            entry_rect = entry_surface.get_rect(center=(list_center_x, start_y + idx * line_height))
            self.screen.blit(entry_surface, entry_rect)

    def _draw_status_panel(self, game_state: dict):
        phase_name = str(game_state.get("phase_name", "playing") or "playing")
        pretty_phase = phase_name.upper()
        phase_progress = float(game_state.get("phase_progress", 0.0) or 0.0)
        alive_count = int(game_state.get("alive_count", 0) or 0)
        consumed = int(game_state.get("total_consumptions", 0) or 0)
        recorded_time = float(game_state.get("recorded_time", 0.0) or 0.0)
        detail_stride = int(game_state.get("detail_stride", 1) or 1)

        phase_copy = {
            "cull": "Random early cull to reach a readable field",
            "readable": "Food, hunting, fleeing, and live growth",
            "showdown": "Camera tracks the top contenders",
            "countdown": "Final seconds before the start",
            "finished": "Match complete",
        }.get(phase_name, "Simulation running")

        lines = [
            (self.font_phase, pretty_phase),
            (self.font_phase_small, phase_copy),
            (self.font_phase_small, f"Alive: {alive_count:,}"),
            (self.font_phase_small, f"Consumed: {consumed:,}"),
            (self.font_phase_small, f"Video time: {recorded_time:.1f}s"),
        ]
        if detail_stride > 1:
            lines.append((self.font_phase_small, f"Detailed updates: 1/{detail_stride}"))

        rendered = [font.render(text, True, (255, 255, 255)) for font, text in lines]
        panel_w = max(surface.get_width() for surface in rendered) + 24
        panel_h = sum(surface.get_height() for surface in rendered) + 20 + (len(rendered) - 1) * 4 + 20
        panel_rect = pygame.Rect(self.game_left + 10, self.game_top + 10, panel_w, panel_h)

        panel = pygame.Surface(panel_rect.size, pygame.SRCALPHA)
        panel.fill((0, 0, 0, 130))
        self.screen.blit(panel, panel_rect.topleft)

        y = panel_rect.y + 10
        for index, surface in enumerate(rendered):
            self.screen.blit(surface, (panel_rect.x + 12, y))
            y += surface.get_height()
            if index < len(rendered) - 1:
                y += 4

        bar_rect = pygame.Rect(panel_rect.x + 12, panel_rect.bottom - 16, panel_rect.width - 24, 8)
        pygame.draw.rect(self.screen, (70, 70, 70), bar_rect, border_radius=4)
        fill_width = max(0, min(bar_rect.width, int(round(bar_rect.width * phase_progress))))
        if fill_width > 0:
            fill_rect = pygame.Rect(bar_rect.x, bar_rect.y, fill_width, bar_rect.height)
            pygame.draw.rect(self.screen, self.highlight_ring_color, fill_rect, border_radius=4)

    def _draw_live_leaderboard(self, game_state: dict):
        live_leaders = list(game_state.get("live_leaders") or [])[: self.live_leader_count]
        if not live_leaders:
            return

        line_surfaces = []
        title_surface = self.font_phase.render("LIVE TOP 5", True, (255, 255, 255))
        max_width = title_surface.get_width()
        for rank, player in enumerate(live_leaders, start=1):
            username = player.username
            if len(username) > 14:
                username = username[:14] + "..."
            text = f"{rank}. {username}"
            mass = f"{int(player.mass):,}"
            left_surface = self.font_leaderboard.render(text, True, (255, 255, 255))
            right_surface = self.font_leaderboard.render(mass, True, self.highlight_ring_color)
            line_surfaces.append((left_surface, right_surface))
            max_width = max(max_width, left_surface.get_width() + right_surface.get_width() + 22)

        panel_w = max_width + 24
        row_h = max(title_surface.get_height(), self.font_leaderboard.get_height()) + 4
        panel_h = 18 + title_surface.get_height() + (len(line_surfaces) * row_h)
        panel_rect = pygame.Rect(self.game_right - panel_w - 10, self.game_top + 10, panel_w, panel_h)

        panel = pygame.Surface(panel_rect.size, pygame.SRCALPHA)
        panel.fill((0, 0, 0, 135))
        self.screen.blit(panel, panel_rect.topleft)
        self.screen.blit(title_surface, (panel_rect.x + 12, panel_rect.y + 10))

        y = panel_rect.y + 14 + title_surface.get_height()
        for left_surface, right_surface in line_surfaces:
            self.screen.blit(left_surface, (panel_rect.x + 12, y))
            right_rect = right_surface.get_rect(right=panel_rect.right - 12, top=y)
            self.screen.blit(right_surface, right_rect)
            y += row_h

    def _draw_game_ui(self, players, game_state: dict):
        self._draw_status_panel(game_state)
        self._draw_live_leaderboard(game_state)
