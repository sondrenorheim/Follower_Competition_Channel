import pygame

import config
from shared import RendererTemplate
from shared.club_panel import draw_club_panel


class JetpackFollowersRenderer(RendererTemplate):
    GAME_TITLE = "JETPACK FOLLOWERS"
    GAME_SUBTITLE = "Making my club members jetpack every day"
    PLAYER_LABEL = "club members"
    GAME_WIDTH = config.SCREEN_WIDTH
    GAME_HEIGHT = config.FIGHTER_ARENA_RECT[3]

    def __init__(self, screen: pygame.Surface):
        super().__init__(screen)
        arena_y = config.FIGHTER_ARENA_RECT[1]
        arena_h = config.FIGHTER_ARENA_RECT[3]
        self.game_left = 0
        self.game_top = arena_y
        self.game_right = config.SCREEN_WIDTH
        self.game_bottom = arena_y + arena_h

        self.bg_color = getattr(config, "JETPACK_BG_COLOR", (172, 214, 246))
        self.day_counter_offset = int(getattr(config, "JETPACK_DAY_COUNTER_OFFSET", 18))
        self.player_size = float(getattr(config, "JETPACK_PLAYER_SIZE", 30.0))
        self.show_thrust_fire = bool(getattr(config, "JETPACK_SHOW_THRUST_FIRE", False))

        self.elimination_list_size = int(getattr(config, "JETPACK_ELIMINATION_LIST_SIZE", 0))
        elimination_text_size = int(getattr(config, "JETPACK_ELIMINATION_TEXT_SIZE", 18))
        self.elimination_text_size = max(12, elimination_text_size)
        self.elimination_name_length = int(getattr(config, "JETPACK_ELIMINATION_NAME_LENGTH", 16))
        self.elimination_label = str(getattr(config, "JETPACK_ELIMINATION_LABEL", "Eliminated:"))
        self.elimination_list_x_offset = int(getattr(config, "JETPACK_ELIMINATION_LIST_X_OFFSET", 0))
        self.font_eliminations = pygame.font.Font(None, self.elimination_text_size)
        club_text_size = int(getattr(config, "CLUB_PANEL_TEXT_SIZE", 16))
        self.font_club_panel = pygame.font.Font(None, club_text_size)
        self._club_panel_bottom = None

        self._background_surface = None
        self._zapper_surfaces = []
        self._zapper_cache = {}
        self._rocket_surface = None
        self._rocket_warning_surface = None
        self._fire_surface = None
        self._elapsed_time = 0.0
        self.zapper_animation_fps = float(getattr(config, "JETPACK_ZAPPER_ANIMATION_FPS", 10.0))
        self._load_assets()

    def _safe_load_image(self, path: str, alpha: bool = True):
        try:
            image = pygame.image.load(path)
            return image.convert_alpha() if alpha else image.convert()
        except Exception:
            return None

    def _load_assets(self):
        bg_path = str(getattr(config, "JETPACK_BACKGROUND_IMAGE", "assets/jetpack_followers/BackdropMain.png"))
        background = self._safe_load_image(bg_path, alpha=False)
        if background is not None:
            target_h = int(self.game_bottom - self.game_top)
            scale = target_h / max(1, background.get_height())
            target_w = max(int(self.game_right - self.game_left), int(background.get_width() * scale))
            self._background_surface = pygame.transform.smoothscale(background, (target_w, target_h))

        zapper_paths = getattr(
            config,
            "JETPACK_ZAPPER_IMAGES",
            [
                "assets/jetpack_followers/Zapper1.png",
                "assets/jetpack_followers/Zapper2.png",
                "assets/jetpack_followers/Zapper3.png",
                "assets/jetpack_followers/Zapper4.png",
            ],
        )
        for path in zapper_paths:
            surface = self._safe_load_image(str(path), alpha=True)
            if surface is not None:
                self._zapper_surfaces.append(surface)

        self._rocket_surface = self._safe_load_image(
            str(getattr(config, "JETPACK_ROCKET_IMAGE", "assets/jetpack_followers/Rocket.png")),
            alpha=True,
        )
        self._rocket_warning_surface = self._safe_load_image(
            str(getattr(config, "JETPACK_ROCKET_WARNING_IMAGE", "assets/jetpack_followers/RocketWarning.png")),
            alpha=True,
        )
        if self.show_thrust_fire:
            fire_surface = self._safe_load_image(
                str(getattr(config, "JETPACK_FIRE_IMAGE", "assets/jetpack_followers/FlyFire2.png")),
                alpha=True,
            )
            if fire_surface is not None:
                # Use opposite vertical orientation from previous setup.
                self._fire_surface = fire_surface
            else:
                self._fire_surface = None
        else:
            self._fire_surface = None

    def render_frame(self, players, game_state: dict):
        self._elapsed_time = float(game_state.get("elapsed_time", 0.0) or 0.0)
        self.screen.fill(config.COLOR_BACKGROUND)
        self._draw_game_area(players, game_state)
        self._draw_players(players)
        self._draw_title_and_subtitle()
        self._draw_day_counter(players, game_state)
        self._draw_game_ui(players, game_state)

        if game_state.get("show_leaderboards"):
            self._draw_end_game_display(
                game_state.get("current_game_leaderboard", []),
                game_state.get("all_time_leaderboard", []),
                game_state.get("winner"),
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
        arena_rect = pygame.Rect(
            self.game_left,
            self.game_top,
            self.game_right - self.game_left,
            self.game_bottom - self.game_top,
        )
        pygame.draw.rect(self.screen, self.bg_color, arena_rect)

        if self._background_surface is not None:
            scroll = float(game_state.get("bg_scroll", 0.0))
            width = self._background_surface.get_width()
            if width > 0:
                offset = int(scroll) % width
                x = self.game_left - offset
                while x < self.game_right:
                    self.screen.blit(self._background_surface, (x, self.game_top))
                    x += width

        shade = pygame.Surface((arena_rect.width, arena_rect.height), pygame.SRCALPHA)
        shade.fill((18, 24, 32, 45))
        self.screen.blit(shade, (arena_rect.x, arena_rect.y))

        pygame.draw.line(
            self.screen,
            (92, 110, 128),
            (self.game_left, self.game_top + 2),
            (self.game_right, self.game_top + 2),
            3,
        )
        pygame.draw.line(
            self.screen,
            (92, 110, 128),
            (self.game_left, self.game_bottom - 2),
            (self.game_right, self.game_bottom - 2),
            3,
        )

        for obstacle in game_state.get("obstacles", []):
            self._draw_obstacle(obstacle)
        for rocket in game_state.get("rockets", []):
            self._draw_rocket(rocket)

    def _draw_obstacle(self, obstacle):
        width = max(8, int(obstacle.width))
        height = max(8, int(obstacle.height))

        if self._zapper_surfaces:
            frame_count = len(self._zapper_surfaces)
            if frame_count > 1 and self.zapper_animation_fps > 0:
                phase = float(getattr(obstacle, "animation_phase", 0.0) or 0.0)
                speed = float(getattr(obstacle, "animation_speed", 1.0) or 1.0)
                frame_value = (self._elapsed_time * self.zapper_animation_fps * speed) + (phase * frame_count)
                idx = int(frame_value) % frame_count
            else:
                idx = int(obstacle.sprite_index) % frame_count
            key = (idx, width, height)
            sprite = self._zapper_cache.get(key)
            if sprite is None:
                sprite = pygame.transform.smoothscale(self._zapper_surfaces[idx], (width, height))
                self._zapper_cache[key] = sprite
            rect = sprite.get_rect(center=(int(obstacle.x), int(obstacle.y)))
            self.screen.blit(sprite, rect)
        else:
            rect = pygame.Rect(0, 0, width, height)
            rect.center = (int(obstacle.x), int(obstacle.y))
            pygame.draw.rect(self.screen, (255, 190, 40), rect, border_radius=10)
            pygame.draw.rect(self.screen, (95, 130, 170), rect, 3, border_radius=10)

    def _draw_rocket(self, rocket):
        rocket_w = max(8, int(rocket.width))
        rocket_h = max(8, int(rocket.height))

        if rocket.warning_active and self._rocket_warning_surface is not None:
            warning_rect = self._rocket_warning_surface.get_rect(
                midright=(self.game_right - 8, int(rocket.y))
            )
            self.screen.blit(self._rocket_warning_surface, warning_rect)

        if self._rocket_surface is not None:
            sprite = pygame.transform.smoothscale(self._rocket_surface, (rocket_w, rocket_h))
            rect = sprite.get_rect(center=(int(rocket.x), int(rocket.y)))
            self.screen.blit(sprite, rect)
        else:
            rect = pygame.Rect(0, 0, rocket_w, rocket_h)
            rect.center = (int(rocket.x), int(rocket.y))
            pygame.draw.rect(self.screen, (220, 80, 70), rect, border_radius=6)
            pygame.draw.rect(self.screen, (70, 25, 20), rect, 2, border_radius=6)

    def _draw_players(self, players):
        for player in players:
            if not (player.alive or player.is_fading()):
                continue

            if (
                self.show_thrust_fire
                and player.alive
                and getattr(player, "thrusting", False)
                and self._fire_surface is not None
            ):
                # Keep exhaust below the avatar center so placement reads clearly in motion.
                fire_anchor_x = int(player.x)
                fire_anchor_y = int(player.y + player.radius * 0.30)
                fire_rect = self._fire_surface.get_rect(
                    midtop=(fire_anchor_x, fire_anchor_y)
                )
                self.screen.blit(self._fire_surface, fire_rect)

            if getattr(player, "is_club_member", False):
                self._draw_club_glow(player, size=self.player_size)
            self._draw_player_avatar(player, size=self.player_size)

    def _draw_day_counter(self, players, game_state: dict):
        total_count = len(players)
        day_number = game_state.get("club_day_number")
        if day_number is None:
            global_day = int(getattr(config, "DAY_NUMBER", 1))
            day_offset = int(getattr(config, "SUPER_FOLLOWER_BROS_DAY_OFFSET", 71))
            day_number = max(1, global_day - day_offset)
        day_text = f"Day {day_number}: {total_count} {self.PLAYER_LABEL}"
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
        if eliminations:
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

    def _draw_game_ui(self, players, game_state: dict):
        alive_count = game_state.get("alive_count")
        speed = game_state.get("speed")
        elapsed_time = game_state.get("elapsed_time")
        distance = game_state.get("distance")
        record = game_state.get("highscore") or {}
        record_score = record.get("score", 0) or 0
        record_name = record.get("username", "") or ""
        show_record = record_score > 0

        panel_lines = []
        if alive_count is not None:
            panel_lines.append(("stat", f"Alive: {alive_count}"))
        if speed is not None:
            panel_lines.append(("small", f"Speed: {speed:.0f}"))
        if distance is not None:
            panel_lines.append(("small", f"Distance: {distance:.0f}m"))
        if elapsed_time is not None:
            panel_lines.append(("small", f"Time: {elapsed_time:.1f}s"))
        if show_record:
            record_text = f"Highscore: {int(record_score)}m"
            if record_name:
                display_name = record_name if len(record_name) <= 12 else record_name[:12] + "..."
                record_text = f"{record_text} - {display_name}"
            panel_lines.append(("small", record_text))

        if not panel_lines:
            return

        rendered = []
        max_w = 0
        for kind, text in panel_lines:
            font = self.font_stats if kind == "stat" else self.font_small
            surface = font.render(text, True, (255, 255, 255))
            rendered.append(surface)
            max_w = max(max_w, surface.get_width())

        pad_x = 12
        pad_y = 8
        line_gap = 20
        panel_w = max(160, max_w + pad_x * 2)
        panel_h = pad_y * 2 + line_gap * len(rendered)
        panel_x = self.game_left + 10
        panel_y = self.game_top + 10

        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 110))
        self.screen.blit(panel, (panel_x, panel_y))

        y_cursor = panel_y + pad_y
        for surface in rendered:
            self.screen.blit(surface, (panel_x + pad_x, y_cursor))
            y_cursor += line_gap
