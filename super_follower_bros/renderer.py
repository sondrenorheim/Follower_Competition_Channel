import math
import pygame

import config
from shared import RendererTemplate


class SuperFollowerBrosRenderer(RendererTemplate):
    GAME_TITLE = "SUPER FOLLOWER BROS."
    GAME_SUBTITLE = "Making my club members fight every day"
    PLAYER_LABEL = "club members"
    GAME_WIDTH = config.FIGHTER_ARENA_RECT[2]
    GAME_HEIGHT = config.FIGHTER_ARENA_RECT[3]

    def __init__(self, screen: pygame.Surface):
        super().__init__(screen)
        arena_x, arena_y, arena_w, arena_h = config.FIGHTER_ARENA_RECT
        self.game_left = arena_x
        self.game_top = arena_y
        self.game_right = arena_x + arena_w
        self.game_bottom = arena_y + arena_h

        self.sky_color = getattr(config, "SUPER_FOLLOWER_BROS_BG_COLOR", (92, 148, 252))
        self.ground_color = getattr(config, "SUPER_FOLLOWER_BROS_GROUND_COLOR", (228, 130, 35))
        self.brick_color = getattr(config, "SUPER_FOLLOWER_BROS_BRICK_COLOR", (200, 92, 32))
        self.question_color = getattr(config, "SUPER_FOLLOWER_BROS_QUESTION_COLOR", (240, 168, 48))
        self.pipe_color = getattr(config, "SUPER_FOLLOWER_BROS_PIPE_COLOR", (0, 168, 0))
        self.flag_color = getattr(config, "SUPER_FOLLOWER_BROS_FLAG_COLOR", (248, 216, 48))

        self.player_size = float(getattr(config, "SUPER_FOLLOWER_BROS_PLAYER_SIZE", 18.0))
        self.day_counter_offset = int(getattr(config, "SUPER_FOLLOWER_BROS_DAY_COUNTER_OFFSET", 18))

        self.background_path = "assets/super_follower_bros/level_1.png"
        self._background_surface = None
        self._background_size = None
        self._minimap_surface = None
        self._minimap_size = None

        self.logo_path = config.project_path("super_follower_Bros_logo.png")
        self._logo_surface = None
        self._logo_size = None
        self._day_counter_rect = None
        self._minimap_rect = None

        self.enemy_sheet_path = getattr(
            config,
            "SUPER_FOLLOWER_BROS_ENEMY_SHEET_PATH",
            "assets/super_follower_bros/smb_enemies_sheet.png",
        )
        self._enemy_sheet = None
        self._enemy_frames = None
        self._enemy_frames_scale = None

        self.tileset_path = getattr(
            config,
            "SUPER_FOLLOWER_BROS_TILESET_PATH",
            "assets/super_follower_bros/tile_set.png",
        )
        self.item_objects_path = getattr(
            config,
            "SUPER_FOLLOWER_BROS_ITEM_OBJECTS_PATH",
            "assets/super_follower_bros/item_objects.png",
        )
        self._tileset_sheet = None
        self._tileset_frames = None
        self._tileset_scale = None
        self._coin_sheet = None
        self._coin_frames = None
        self._coin_scale = None
        self._fireball_frames = None
        self._fireball_scale = None
        self._flagpole_frames = None
        self._flagpole_tile_scale = None
        self._flagpole_item_scale = None

    def render_frame(self, players, game_state: dict):
        self.screen.fill(config.COLOR_BACKGROUND)
        self._draw_game_area(players, game_state)
        self._draw_players(players, game_state)
        self._draw_day_counter(players, game_state)
        self._draw_minimap(players, game_state)
        self._draw_minimap_avatars(players, game_state)
        self._draw_title_and_subtitle()
        self._draw_subtitle_and_prompt()
        self._draw_game_ui(players, game_state)

        if game_state.get("show_leaderboards"):
            self._draw_end_game_display(
                game_state.get("current_game_leaderboard", []),
                game_state.get("all_time_leaderboard", []),
                game_state.get("winner"),
            )

    def _draw_title_and_subtitle(self):
        arena_top = config.FIGHTER_ARENA_RECT[1]

        logo_surface = self._get_logo_surface()
        if logo_surface:
            title_rect = logo_surface.get_rect(center=(self.width // 2, arena_top - 70))
            self.screen.blit(logo_surface, title_rect)
        else:
            title_font = pygame.font.Font(None, 56)
            title_text = title_font.render(self.GAME_TITLE, True, config.COLOR_TEXT)
            title_rect = title_text.get_rect(center=(self.width // 2, arena_top - 70))
            self.screen.blit(title_text, title_rect)

    def _draw_subtitle_and_prompt(self):
        subtitle_font = pygame.font.Font(None, 32)
        prompt_font = pygame.font.Font(None, 24)

        if self._minimap_rect:
            offset = int(getattr(config, "SUPER_FOLLOWER_BROS_SUBTITLE_BELOW_MINIMAP_OFFSET", 34))
            base_y = self._minimap_rect.bottom + offset
        else:
            arena_top = config.FIGHTER_ARENA_RECT[1]
            base_y = arena_top - 40

        subtitle_text = subtitle_font.render(self.GAME_SUBTITLE, True, config.COLOR_TEXT)
        subtitle_rect = subtitle_text.get_rect(center=(self.width // 2, base_y))
        self.screen.blit(subtitle_text, subtitle_rect)

        prompt_text = getattr(config, "COMMENT_RESULT_PROMPT_TEXT", "")
        if prompt_text:
            prompt_surface = prompt_font.render(prompt_text, True, config.COLOR_TEXT)
            prompt_rect = prompt_surface.get_rect(center=(self.width // 2, subtitle_rect.bottom + 6))
            self.screen.blit(prompt_surface, prompt_rect)

    def _get_logo_surface(self):
        max_width = int(self.width * 0.85)
        max_height = 140
        target_size = (max_width, max_height)
        if self._logo_surface is not None and self._logo_size == target_size:
            return self._logo_surface
        try:
            base = pygame.image.load(self.logo_path).convert_alpha()
            width, height = base.get_size()
            scale = min(max_width / width, max_height / height, 1.0)
            new_size = (max(1, int(round(width * scale))), max(1, int(round(height * scale))))
            self._logo_surface = pygame.transform.smoothscale(base, new_size)
            self._logo_size = target_size
        except Exception:
            self._logo_surface = None
            self._logo_size = None
        return self._logo_surface

    def _get_enemy_frames(self, level):
        if level is None:
            return None
        scale_multiplier = float(getattr(config, "SUPER_FOLLOWER_BROS_SPRITE_SCALE", 2.5))
        scale = scale_multiplier * float(getattr(level, "scale", 1.0))
        if scale <= 0:
            return None
        if self._enemy_frames is not None and self._enemy_frames_scale == scale:
            return self._enemy_frames

        sheet = self._load_enemy_sheet()
        if sheet is None:
            self._enemy_frames = None
            self._enemy_frames_scale = None
            return None

        def slice_frame(x, y, w, h):
            image = pygame.Surface((w, h), pygame.SRCALPHA)
            image.blit(sheet, (0, 0), (x, y, w, h))
            if scale != 1.0:
                image = pygame.transform.scale(
                    image,
                    (max(1, int(round(w * scale))), max(1, int(round(h * scale)))),
                )
            return image

        goomba_frames = [
            slice_frame(0, 4, 16, 16),
            slice_frame(30, 4, 16, 16),
        ]
        koopa_frames = [
            slice_frame(150, 0, 16, 24),
            slice_frame(180, 0, 16, 24),
        ]
        shell_frame = slice_frame(360, 5, 16, 15)

        self._enemy_frames = {
            "goomba": {
                "right": goomba_frames,
                "left": [pygame.transform.flip(f, True, False) for f in goomba_frames],
            },
            "koopa": {
                "left": koopa_frames,
                "right": [pygame.transform.flip(f, True, False) for f in koopa_frames],
            },
            "koopa_shell": {
                "left": [shell_frame],
                "right": [shell_frame],
            },
        }
        self._enemy_frames_scale = scale
        return self._enemy_frames

    def _load_enemy_sheet(self):
        if self._enemy_sheet is not None:
            return self._enemy_sheet
        try:
            self._enemy_sheet = pygame.image.load(self.enemy_sheet_path).convert_alpha()
        except Exception:
            self._enemy_sheet = None
        return self._enemy_sheet

    def _get_tileset_frames(self, level):
        if level is None:
            return None
        scale_multiplier = float(getattr(config, "SUPER_FOLLOWER_BROS_TILESET_SCALE", 2.69))
        scale = scale_multiplier * float(getattr(level, "scale", 1.0))
        if scale <= 0:
            return None
        if self._tileset_frames is not None and self._tileset_scale == scale:
            return self._tileset_frames

        sheet = self._load_tileset_sheet()
        if sheet is None:
            self._tileset_frames = None
            self._tileset_scale = None
            return None

        def slice_frame(x, y, w, h):
            image = pygame.Surface((w, h), pygame.SRCALPHA)
            image.blit(sheet, (0, 0), (x, y, w, h))
            if scale != 1.0:
                image = pygame.transform.scale(
                    image,
                    (max(1, int(round(w * scale))), max(1, int(round(h * scale)))),
                )
            return image

        brick_frame = slice_frame(16, 0, 16, 16)
        open_frame = slice_frame(432, 0, 16, 16)
        question_frames = [
            slice_frame(384, 0, 16, 16),
            slice_frame(400, 0, 16, 16),
            slice_frame(416, 0, 16, 16),
        ]

        self._tileset_frames = {
            "brick": brick_frame,
            "open": open_frame,
            "question": question_frames,
        }
        self._tileset_scale = scale
        return self._tileset_frames

    def _load_tileset_sheet(self):
        if self._tileset_sheet is not None:
            return self._tileset_sheet
        try:
            self._tileset_sheet = pygame.image.load(self.tileset_path).convert_alpha()
        except Exception:
            self._tileset_sheet = None
        return self._tileset_sheet

    def _get_coin_frames(self, level):
        if level is None:
            return None
        scale_multiplier = float(getattr(config, "SUPER_FOLLOWER_BROS_ITEM_SCALE", 2.5))
        scale = scale_multiplier * float(getattr(level, "scale", 1.0))
        if scale <= 0:
            return None
        if self._coin_frames is not None and self._coin_scale == scale:
            return self._coin_frames

        sheet = self._load_coin_sheet()
        if sheet is None:
            self._coin_frames = None
            self._coin_scale = None
            return None

        def slice_frame(x, y, w, h):
            image = pygame.Surface((w, h), pygame.SRCALPHA)
            image.blit(sheet, (0, 0), (x, y, w, h))
            if scale != 1.0:
                image = pygame.transform.scale(
                    image,
                    (max(1, int(round(w * scale))), max(1, int(round(h * scale)))),
                )
            return image

        self._coin_frames = [
            slice_frame(52, 113, 8, 14),
            slice_frame(4, 113, 8, 14),
            slice_frame(20, 113, 8, 14),
            slice_frame(36, 113, 8, 14),
        ]
        self._coin_scale = scale
        return self._coin_frames

    def _get_powerup_frames(self, level):
        if level is None:
            return None
        scale_multiplier = float(getattr(config, "SUPER_FOLLOWER_BROS_ITEM_SCALE", 2.5))
        scale = scale_multiplier * float(getattr(level, "scale", 1.0))
        if scale <= 0:
            return None
        if getattr(self, "_powerup_frames", None) is not None and getattr(self, "_powerup_scale", None) == scale:
            return self._powerup_frames

        sheet = self._load_coin_sheet()
        if sheet is None:
            self._powerup_frames = None
            self._powerup_scale = None
            return None

        def slice_frame(x, y, w, h):
            image = pygame.Surface((w, h), pygame.SRCALPHA)
            image.blit(sheet, (0, 0), (x, y, w, h))
            if scale != 1.0:
                image = pygame.transform.scale(
                    image,
                    (max(1, int(round(w * scale))), max(1, int(round(h * scale)))),
                )
            return image

        self._powerup_frames = {
            "mushroom": [slice_frame(0, 0, 16, 16)],
            "fireflower": [
                slice_frame(0, 32, 16, 16),
                slice_frame(16, 32, 16, 16),
                slice_frame(32, 32, 16, 16),
                slice_frame(48, 32, 16, 16),
            ],
            "star": [
                slice_frame(1, 48, 15, 16),
                slice_frame(17, 48, 15, 16),
                slice_frame(33, 48, 15, 16),
                slice_frame(49, 48, 15, 16),
            ],
        }
        self._powerup_scale = scale
        return self._powerup_frames

    def _load_coin_sheet(self):
        if self._coin_sheet is not None:
            return self._coin_sheet
        try:
            self._coin_sheet = pygame.image.load(self.item_objects_path).convert_alpha()
        except Exception:
            self._coin_sheet = None
        return self._coin_sheet

    def _get_fireball_frames(self, level):
        if level is None:
            return None
        scale_multiplier = float(getattr(config, "SUPER_FOLLOWER_BROS_ITEM_SCALE", 2.5))
        scale = scale_multiplier * float(getattr(level, "scale", 1.0))
        if scale <= 0:
            return None
        if self._fireball_frames is not None and self._fireball_scale == scale:
            return self._fireball_frames

        sheet = self._load_coin_sheet()
        if sheet is None:
            self._fireball_frames = None
            self._fireball_scale = None
            return None

        def slice_frame(x, y, w, h):
            image = pygame.Surface((w, h), pygame.SRCALPHA)
            image.blit(sheet, (0, 0), (x, y, w, h))
            if scale != 1.0:
                image = pygame.transform.scale(
                    image,
                    (max(1, int(round(w * scale))), max(1, int(round(h * scale)))),
                )
            return image

        self._fireball_frames = [
            slice_frame(96, 144, 8, 8),
            slice_frame(104, 144, 8, 8),
            slice_frame(96, 152, 8, 8),
            slice_frame(104, 152, 8, 8),
        ]
        self._fireball_scale = scale
        return self._fireball_frames

    def _draw_game_area(self, players, game_state: dict):
        level = game_state.get("level")
        camera_x = float(game_state.get("camera_x", 0.0))
        if level:
            self._draw_level(level, camera_x)
            self._draw_blocks(level, camera_x, game_state.get("elapsed_time", 0.0))
            self._draw_powerups(game_state.get("powerups", []), level, camera_x, game_state.get("elapsed_time", 0.0))
            self._draw_flag(level, camera_x)
        self._draw_enemies(
            game_state.get("enemies", []),
            camera_x,
            level,
            game_state.get("elapsed_time", 0.0),
        )
        self._draw_fireballs(
            game_state.get("fireballs", []),
            camera_x,
            level,
            game_state.get("elapsed_time", 0.0),
        )

        arena_rect = pygame.Rect(
            self.game_left,
            self.game_top,
            self.game_right - self.game_left,
            self.game_bottom - self.game_top,
        )
        if getattr(config, "SUPER_FOLLOWER_BROS_ARENA_BORDER", False):
            pygame.draw.rect(self.screen, (0, 0, 0), arena_rect, 2)

    def _draw_enemies(self, enemies, camera_x: float, level, elapsed_time: float):
        if not enemies:
            return
        margin = int(getattr(config, "SUPER_FOLLOWER_BROS_RENDER_MARGIN", 140))
        body_color = getattr(config, "SUPER_FOLLOWER_BROS_ENEMY_COLOR", (168, 80, 32))
        koopa_color = getattr(config, "SUPER_FOLLOWER_BROS_KOOPA_COLOR", (40, 148, 72))
        outline = getattr(config, "SUPER_FOLLOWER_BROS_ENEMY_OUTLINE", (70, 35, 15))
        eye_color = getattr(config, "SUPER_FOLLOWER_BROS_ENEMY_EYE_COLOR", (245, 245, 245))
        pupil_color = getattr(config, "SUPER_FOLLOWER_BROS_ENEMY_PUPIL_COLOR", (30, 30, 30))
        frames = self._get_enemy_frames(level)
        frame_time = float(getattr(config, "SUPER_FOLLOWER_BROS_ENEMY_ANIM_TIME", 0.125))
        if frame_time <= 0:
            frame_index = 0
        else:
            frame_index = int(elapsed_time / frame_time) % 2

        for enemy in enemies:
            state = getattr(enemy, "state", "walk")
            if state == "dead":
                continue
            screen_x = int(self.game_left + enemy.x - camera_x)
            screen_y = int(self.game_top + enemy.y)
            width = max(2, int(enemy.width))
            height = max(2, int(enemy.height))

            if screen_x < self.game_left - width - margin or screen_x > self.game_right + width + margin:
                continue
            if screen_y < self.game_top - height - margin or screen_y > self.game_bottom + height + margin:
                continue

            kind = getattr(enemy, "kind", "goomba")
            frame_kind = "koopa_shell" if kind == "koopa" and state in ("shell", "shell_slide") else kind
            facing = "right" if enemy.vx > 0 else "left"
            sprite = None
            if frames:
                kind_frames = frames.get(frame_kind)
                if kind_frames:
                    sprite_list = kind_frames.get(facing)
                    if sprite_list:
                        sprite = sprite_list[frame_index % len(sprite_list)]

            if sprite:
                rect = sprite.get_rect(center=(screen_x, screen_y))
                self.screen.blit(sprite, rect)
            else:
                rect = pygame.Rect(
                    screen_x - width // 2,
                    screen_y - height // 2,
                    width,
                    height,
                )
                color = koopa_color if kind == "koopa" else body_color
                pygame.draw.ellipse(self.screen, color, rect)
                pygame.draw.ellipse(self.screen, outline, rect, 2)

                eye_radius = max(1, int(width * 0.12))
                eye_offset_x = max(2, int(width * 0.18))
                eye_offset_y = -max(1, int(height * 0.1))

                left_eye = (screen_x - eye_offset_x, screen_y + eye_offset_y)
                right_eye = (screen_x + eye_offset_x, screen_y + eye_offset_y)
                pygame.draw.circle(self.screen, eye_color, left_eye, eye_radius)
                pygame.draw.circle(self.screen, eye_color, right_eye, eye_radius)
                pygame.draw.circle(self.screen, pupil_color, left_eye, max(1, eye_radius // 2))
                pygame.draw.circle(self.screen, pupil_color, right_eye, max(1, eye_radius // 2))

    def _draw_flag(self, level, camera_x: float):
        if level is None or not hasattr(level, "flag_x"):
            return
        margin = int(getattr(config, "SUPER_FOLLOWER_BROS_RENDER_MARGIN", 140))
        pole_color = getattr(config, "SUPER_FOLLOWER_BROS_FLAG_POLE_COLOR", (245, 245, 245))
        flag_color = getattr(config, "SUPER_FOLLOWER_BROS_FLAG_COLOR", (248, 216, 48))
        pole_width = float(getattr(config, "SUPER_FOLLOWER_BROS_FLAG_POLE_WIDTH", 4.0)) * float(getattr(level, "scale", 1.0))
        pole_height = float(getattr(config, "SUPER_FOLLOWER_BROS_FLAG_HEIGHT", 600.0)) * float(getattr(level, "scale", 1.0))
        flag_width = float(getattr(config, "SUPER_FOLLOWER_BROS_FLAG_WIDTH", 18.0)) * float(getattr(level, "scale", 1.0))

        pole_x = self.game_left + level.flag_x - camera_x
        block_height = float(getattr(level, "brick_size", 0.0))
        base_y = self.game_top + level.ground_y - block_height
        top_y = base_y - pole_height

        if pole_x < self.game_left - margin or pole_x > self.game_right + margin:
            return
        frames = self._get_flagpole_frames(level)
        if frames:
            pole_sprite = frames.get("pole")
            finial_sprite = frames.get("finial")
            flag_sprite = frames.get("flag")

            if pole_sprite and finial_sprite and flag_sprite:
                seg_h = pole_sprite.get_height()
                seg_w = pole_sprite.get_width()
                pole_top = int(top_y)
                pole_bottom = int(base_y)

                y = pole_top
                while y < pole_bottom:
                    seg_rect = pole_sprite.get_rect(midtop=(int(pole_x), y))
                    self.screen.blit(pole_sprite, seg_rect)
                    y += seg_h

                finial_rect = finial_sprite.get_rect(centerx=int(pole_x), bottom=pole_top)
                self.screen.blit(finial_sprite, finial_rect)

                flag_rect = flag_sprite.get_rect()
                flag_rect.right = int(pole_x)
                flag_rect.y = int(pole_top + seg_h)
                self.screen.blit(flag_sprite, flag_rect)
                return

        pole_rect = pygame.Rect(
            int(pole_x - pole_width / 2),
            int(top_y),
            max(1, int(pole_width)),
            max(1, int(pole_height)),
        )
        pygame.draw.rect(self.screen, pole_color, pole_rect)

        flag_rect = pygame.Rect(
            int(pole_rect.left - flag_width),
            int(top_y + pole_height * 0.15),
            max(1, int(flag_width)),
            max(1, int(pole_height * 0.18)),
        )
        pygame.draw.rect(self.screen, flag_color, flag_rect)

    def _get_flagpole_frames(self, level):
        if level is None:
            return None
        tile_scale = float(getattr(config, "SUPER_FOLLOWER_BROS_TILESET_SCALE", 2.69)) * float(getattr(level, "scale", 1.0))
        item_scale = float(getattr(config, "SUPER_FOLLOWER_BROS_ITEM_SCALE", 2.5)) * float(getattr(level, "scale", 1.0))
        if tile_scale <= 0 or item_scale <= 0:
            return None

        if (
            self._flagpole_frames is not None
            and self._flagpole_tile_scale == tile_scale
            and self._flagpole_item_scale == item_scale
        ):
            return self._flagpole_frames

        tileset = self._load_tileset_sheet()
        item_sheet = self._load_coin_sheet()
        if tileset is None or item_sheet is None:
            self._flagpole_frames = None
            self._flagpole_tile_scale = None
            self._flagpole_item_scale = None
            return None

        def slice_frame(sheet, x, y, w, h, scale):
            image = pygame.Surface((w, h), pygame.SRCALPHA)
            image.blit(sheet, (0, 0), (x, y, w, h))
            if scale != 1.0:
                image = pygame.transform.scale(
                    image,
                    (max(1, int(round(w * scale))), max(1, int(round(h * scale)))),
                )
            return image

        pole_frame = slice_frame(tileset, 263, 144, 2, 16, tile_scale)
        finial_frame = slice_frame(tileset, 228, 120, 8, 8, tile_scale)
        flag_frame = slice_frame(item_sheet, 128, 32, 16, 16, item_scale)

        self._flagpole_frames = {
            "pole": pole_frame,
            "finial": finial_frame,
            "flag": flag_frame,
        }
        self._flagpole_tile_scale = tile_scale
        self._flagpole_item_scale = item_scale
        return self._flagpole_frames

    def _draw_level(self, level, camera_x: float):
        target_size = (int(level.pixel_width), int(level.pixel_height))
        if self._background_surface is None or self._background_size != target_size:
            try:
                base = pygame.image.load(self.background_path).convert()
                self._background_surface = pygame.transform.scale(base, target_size)
                self._background_size = target_size
            except Exception:
                self._background_surface = None
                self._background_size = None

        if self._background_surface:
            self.screen.blit(self._background_surface, (self.game_left - camera_x, self.game_top))
        else:
            arena_rect = pygame.Rect(
                self.game_left,
                self.game_top,
                self.game_right - self.game_left,
                self.game_bottom - self.game_top,
            )
            pygame.draw.rect(self.screen, self.sky_color, arena_rect)

    def _draw_blocks(self, level, camera_x: float, elapsed_time: float):
        if not getattr(level, "blocks", None):
            return
        margin = int(getattr(config, "SUPER_FOLLOWER_BROS_RENDER_MARGIN", 140))
        brick_color = getattr(config, "SUPER_FOLLOWER_BROS_BRICK_COLOR", (200, 92, 32))
        question_color = getattr(config, "SUPER_FOLLOWER_BROS_QUESTION_COLOR", (240, 168, 48))
        border_color = getattr(config, "SUPER_FOLLOWER_BROS_BLOCK_BORDER", (60, 36, 18))
        bump_height = float(getattr(config, "SUPER_FOLLOWER_BROS_BLOCK_BUMP_HEIGHT", 6.0)) * float(getattr(level, "scale", 1.0))
        bump_time = float(getattr(config, "SUPER_FOLLOWER_BROS_BLOCK_BUMP_TIME", 0.16))

        tileset = self._get_tileset_frames(level)
        question_frames = tileset.get("question") if tileset else None
        brick_frame = tileset.get("brick") if tileset else None
        open_frame = tileset.get("open") if tileset else None
        question_time = float(getattr(config, "SUPER_FOLLOWER_BROS_QUESTION_ANIM_TIME", 0.125))
        question_index = 0
        if question_frames:
            if question_time > 0:
                question_index = int(elapsed_time / question_time) % len(question_frames)
            question_index = max(0, min(question_index, len(question_frames) - 1))

        for block in level.blocks:
            rect = block.get("rect")
            if rect is None:
                continue
            bump_offset = 0.0
            bump_start = block.get("bump_start")
            if bump_start is not None and bump_time > 0:
                t = max(0.0, min(1.0, (elapsed_time - bump_start) / bump_time))
                bump_offset = bump_height * (1.0 - abs(2.0 * t - 1.0))

            screen_rect = pygame.Rect(
                int(self.game_left + rect.x - camera_x),
                int(self.game_top + rect.y - bump_offset),
                rect.width,
                rect.height,
            )
            if screen_rect.right < self.game_left - margin or screen_rect.left > self.game_right + margin:
                continue
            kind = block.get("kind", "brick")
            state = block.get("state", "closed")
            if state == "opened" and open_frame is not None:
                sprite_rect = open_frame.get_rect(center=screen_rect.center)
                self.screen.blit(open_frame, sprite_rect)
            elif kind == "coin_box" and question_frames:
                sprite = question_frames[question_index]
                sprite_rect = sprite.get_rect(center=screen_rect.center)
                self.screen.blit(sprite, sprite_rect)
            elif kind == "brick" and brick_frame:
                sprite_rect = brick_frame.get_rect(center=screen_rect.center)
                self.screen.blit(brick_frame, sprite_rect)
            else:
                color = question_color if kind == "coin_box" else brick_color
                pygame.draw.rect(self.screen, color, screen_rect)
                pygame.draw.rect(self.screen, border_color, screen_rect, 2)

        self._draw_block_coins(level, camera_x, elapsed_time)

    def _draw_block_coins(self, level, camera_x: float, elapsed_time: float):
        if not getattr(config, "SUPER_FOLLOWER_BROS_SHOW_BLOCK_COINS", True):
            return
        margin = int(getattr(config, "SUPER_FOLLOWER_BROS_RENDER_MARGIN", 140))
        frames = self._get_coin_frames(level)
        if not frames:
            return
        frame_time = float(getattr(config, "SUPER_FOLLOWER_BROS_COIN_ANIM_TIME", 0.08))
        if frame_time <= 0:
            frame_index = 0
        else:
            frame_index = int(elapsed_time / frame_time) % len(frames)
        coin_frame = frames[frame_index]
        coin_offset = float(getattr(config, "SUPER_FOLLOWER_BROS_COIN_FLOAT_OFFSET", 0.2))

        pop_time = float(getattr(config, "SUPER_FOLLOWER_BROS_COIN_POP_TIME", 0.4))

        for block in level.blocks:
            contents = block.get("contents")
            if contents not in ("coin", "6coins"):
                continue
            if block.get("state") != "opened":
                continue
            last_bump = block.get("last_bump_time")
            if last_bump is None:
                continue
            if pop_time > 0 and (elapsed_time - last_bump) > pop_time:
                continue
            rect = block.get("rect")
            if rect is None:
                continue
            screen_x = int(self.game_left + rect.centerx - camera_x)
            screen_y = int(self.game_top + rect.y - rect.height * coin_offset)
            if screen_x < self.game_left - rect.width - margin or screen_x > self.game_right + rect.width + margin:
                continue
            if screen_y < self.game_top - rect.height - margin or screen_y > self.game_bottom + rect.height + margin:
                continue
            coin_rect = coin_frame.get_rect(center=(screen_x, screen_y))
            self.screen.blit(coin_frame, coin_rect)

    def _draw_powerups(self, powerups, level, camera_x: float, elapsed_time: float):
        if not powerups:
            return
        margin = int(getattr(config, "SUPER_FOLLOWER_BROS_RENDER_MARGIN", 140))
        frames = self._get_powerup_frames(level)
        if not frames:
            return

        fire_time = float(getattr(config, "SUPER_FOLLOWER_BROS_FIREFLOWER_ANIM_TIME", 0.03))
        star_time = float(getattr(config, "SUPER_FOLLOWER_BROS_STAR_ANIM_TIME", 0.03))
        reveal_time = float(getattr(config, "SUPER_FOLLOWER_BROS_POWERUP_REVEAL_TIME", 0.6))

        for powerup in powerups:
            kind = getattr(powerup, "kind", None)
            if kind not in frames:
                continue
            kind_frames = frames[kind]
            if kind == "fireflower" and fire_time > 0:
                index = int(elapsed_time / fire_time) % len(kind_frames)
            elif kind == "star" and star_time > 0:
                index = int(elapsed_time / star_time) % len(kind_frames)
            else:
                index = 0

            sprite = kind_frames[index]
            if sprite is None:
                continue

            x = powerup.x
            y = powerup.y
            if reveal_time > 0 and powerup.state == "reveal":
                t = max(0.0, min(1.0, (elapsed_time - powerup.spawn_time) / reveal_time))
                start_y = powerup.block_top + powerup.block_height - sprite.get_height() / 2
                end_y = powerup.block_top - sprite.get_height() / 2
                y = start_y + (end_y - start_y) * t

            screen_x = int(self.game_left + x - camera_x)
            screen_y = int(self.game_top + y)
            if screen_x < self.game_left - margin or screen_x > self.game_right + margin:
                continue
            if screen_y < self.game_top - margin or screen_y > self.game_bottom + margin:
                continue
            rect = sprite.get_rect(center=(screen_x, screen_y))
            self.screen.blit(sprite, rect)

    def _draw_fireballs(self, fireballs, camera_x: float, level, elapsed_time: float):
        if not fireballs:
            return
        margin = int(getattr(config, "SUPER_FOLLOWER_BROS_RENDER_MARGIN", 140))
        frames = self._get_fireball_frames(level)
        if not frames:
            return

        frame_time = float(getattr(config, "SUPER_FOLLOWER_BROS_FIREBALL_ANIM_TIME", 0.12))
        if frame_time <= 0:
            frame_index = 0
        else:
            frame_index = int(elapsed_time / frame_time) % len(frames)
        sprite = frames[frame_index]

        for fireball in fireballs:
            screen_x = int(self.game_left + fireball.x - camera_x)
            screen_y = int(self.game_top + fireball.y)
            if screen_x < self.game_left - margin or screen_x > self.game_right + margin:
                continue
            if screen_y < self.game_top - margin or screen_y > self.game_bottom + margin:
                continue
            rect = sprite.get_rect(center=(screen_x, screen_y))
            self.screen.blit(sprite, rect)

    def _draw_players(self, players, game_state: dict):
        camera_x = float(game_state.get("camera_x", 0.0))
        margin = int(getattr(config, "SUPER_FOLLOWER_BROS_RENDER_MARGIN", 140))
        player_size = game_state.get("player_size")
        if not player_size:
            level = game_state.get("level")
            if level and bool(getattr(config, "SUPER_FOLLOWER_BROS_PLAYER_MATCH_TILESET", True)):
                base = float(getattr(config, "SUPER_FOLLOWER_BROS_PLAYER_SIZE", 16.0))
                tile_scale = float(getattr(config, "SUPER_FOLLOWER_BROS_TILESET_SCALE", 2.69))
                player_size = base * tile_scale * float(getattr(level, "scale", 1.0))
            else:
                player_size = self.player_size
        for player in players:
            if not player.alive and not player.is_fading():
                continue
            screen_x = int(self.game_left + player.x - camera_x)
            screen_y = int(self.game_top + player.y)
            if screen_x < self.game_left - margin or screen_x > self.game_right + margin:
                continue
            if screen_y < self.game_top - margin or screen_y > self.game_bottom + margin:
                continue
            size = player_size
            if hasattr(player, "radius") and player.radius:
                size = max(1.0, float(player.radius) * 2.0)
            self._draw_avatar_at(player, screen_x, screen_y, size)
            if hasattr(player, "is_star_active") and player.is_star_active(game_state.get("elapsed_time", 0.0)):
                self._draw_star_glow(screen_x, screen_y, size, game_state.get("elapsed_time", 0.0))

    def _draw_star_glow(self, screen_x: int, screen_y: int, size: float, elapsed: float) -> None:
        glow_scale = float(getattr(config, "SUPER_FOLLOWER_BROS_STAR_GLOW_SCALE", 1.8))
        glow_thickness = int(getattr(config, "SUPER_FOLLOWER_BROS_STAR_GLOW_THICKNESS", 4))
        pulse_speed = float(getattr(config, "SUPER_FOLLOWER_BROS_STAR_GLOW_SPEED", 6.0))
        base_alpha = int(getattr(config, "SUPER_FOLLOWER_BROS_STAR_GLOW_ALPHA", 140))
        accent_alpha = int(getattr(config, "SUPER_FOLLOWER_BROS_STAR_GLOW_ACCENT_ALPHA", 200))

        radius = max(2, int(size * 0.5 * glow_scale))
        pulse = 0.5 + 0.5 * math.sin(elapsed * pulse_speed)
        outer_alpha = max(30, min(255, int(base_alpha + pulse * 40)))
        inner_alpha = max(40, min(255, int(accent_alpha + pulse * 40)))

        glow_surface = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
        outer_color = (255, 232, 126, outer_alpha)
        inner_color = (255, 255, 255, inner_alpha)

        pygame.draw.circle(glow_surface, outer_color, (radius + 2, radius + 2), radius, glow_thickness)
        pygame.draw.circle(glow_surface, inner_color, (radius + 2, radius + 2), max(2, radius - glow_thickness), 2)

        rect = glow_surface.get_rect(center=(screen_x, screen_y))
        self.screen.blit(glow_surface, rect)

    def _draw_minimap(self, players, game_state: dict):
        if not getattr(config, "SUPER_FOLLOWER_BROS_MINIMAP_ENABLED", True):
            return
        level = game_state.get("level")
        if level is None:
            return

        map_w, map_h = getattr(config, "SUPER_FOLLOWER_BROS_MINIMAP_SIZE", (200, 60))
        padding = int(getattr(config, "SUPER_FOLLOWER_BROS_MINIMAP_PADDING", 12))

        max_w = int(self.width - 2 * padding)
        max_h = int(self.height - 2 * padding)
        map_w = max(60, min(int(map_w), max_w))
        map_h = max(30, min(int(map_h), max_h))

        if self._day_counter_rect:
            map_w = max_w
            map_x = padding
            map_y = int(self._day_counter_rect.bottom + padding)
        else:
            map_x = int(self.game_right - map_w - padding)
            map_y = int(self.game_top + padding)

        if map_y + map_h > self.height - padding:
            map_y = max(padding, self.height - map_h - padding)

        panel = pygame.Surface((map_w, map_h), pygame.SRCALPHA)
        panel.fill(getattr(config, "SUPER_FOLLOWER_BROS_MINIMAP_BG", (0, 0, 0, 120)))
        self.screen.blit(panel, (map_x, map_y))

        minimap_bg = self._get_minimap_background(map_w, map_h)
        if minimap_bg:
            self.screen.blit(minimap_bg, (map_x, map_y))

        pygame.draw.rect(self.screen, getattr(config, "SUPER_FOLLOWER_BROS_MINIMAP_BORDER", (40, 40, 40)),
                         pygame.Rect(map_x, map_y, map_w, map_h), 2)
        self._minimap_rect = pygame.Rect(map_x, map_y, map_w, map_h)

        level_width = max(1.0, float(level.pixel_width))
        level_height = max(1.0, float(level.pixel_height))

        dot_radius = max(1, int(getattr(config, "SUPER_FOLLOWER_BROS_MINIMAP_DOT_RADIUS", 2)))
        max_dots = int(getattr(config, "SUPER_FOLLOWER_BROS_MINIMAP_MAX_DOTS", 2000))
        step = max(1, len(players) // max_dots) if len(players) > max_dots else 1

        alive_color = getattr(config, "SUPER_FOLLOWER_BROS_MINIMAP_ALIVE_COLOR", (80, 200, 120))
        dead_color = getattr(config, "SUPER_FOLLOWER_BROS_MINIMAP_DEAD_COLOR", (200, 80, 80))

        for idx, player in enumerate(players[::step]):
            if not player.alive and not player.is_fading():
                continue
            px = max(0.0, min(level_width, player.x))
            py = max(0.0, min(level_height, player.y))
            dot_x = map_x + int((px / level_width) * map_w)
            dot_y = map_y + int((py / level_height) * map_h)
            color = alive_color if player.alive else dead_color
            pygame.draw.circle(self.screen, color, (dot_x, dot_y), dot_radius)

        # Draw camera viewport on minimap
        camera_x = float(game_state.get("camera_x", 0.0))
        view_w = int((self.game_right - self.game_left) / level_width * map_w)
        view_x = map_x + int((camera_x / level_width) * map_w)
        view_rect = pygame.Rect(view_x, map_y, max(4, view_w), map_h)
        pygame.draw.rect(self.screen, getattr(config, "SUPER_FOLLOWER_BROS_MINIMAP_VIEWPORT", (255, 255, 255, 80)),
                         view_rect, 1)

    def _draw_minimap_avatars(self, players, game_state: dict):
        if not getattr(config, "SUPER_FOLLOWER_BROS_MINIMAP_ENABLED", True):
            return
        if not self._minimap_rect:
            return
        level = game_state.get("level")
        if level is None:
            return

        size = int(getattr(config, "SUPER_FOLLOWER_BROS_MINIMAP_AVATAR_SIZE", 14))
        offset = int(getattr(config, "SUPER_FOLLOWER_BROS_MINIMAP_AVATAR_OFFSET", 14))
        max_avatars = int(getattr(config, "SUPER_FOLLOWER_BROS_MINIMAP_AVATAR_MAX", 200))

        if size <= 0:
            return

        level_width = max(1.0, float(level.pixel_width))
        map_x = self._minimap_rect.x
        map_w = self._minimap_rect.width
        hover_y = int(self._minimap_rect.bottom + offset)
        if hover_y - size // 2 > self.height:
            return

        step = max(1, len(players) // max_avatars) if len(players) > max_avatars else 1
        for player in players[::step]:
            if not player.alive and not player.is_fading():
                continue
            px = max(0.0, min(level_width, player.x))
            dot_x = map_x + int((px / level_width) * map_w)
            self._draw_avatar_at(player, dot_x, hover_y, size)

    def _get_minimap_background(self, map_w: int, map_h: int):
        target_size = (int(map_w), int(map_h))
        if self._minimap_surface is not None and self._minimap_size == target_size:
            return self._minimap_surface
        try:
            base = pygame.image.load(self.background_path).convert()
            self._minimap_surface = pygame.transform.scale(base, target_size)
            self._minimap_size = target_size
        except Exception:
            self._minimap_surface = None
            self._minimap_size = None
        return self._minimap_surface

    def _draw_avatar_at(self, player, screen_x: int, screen_y: int, size_value: float = None):
        if size_value is None:
            size_value = self.player_size
        size = max(1, int(round(size_value)))
        avatar_surface = self._get_avatar_surface(player, size)
        if hasattr(player, "alpha") and player.alpha < 255:
            avatar_surface = avatar_surface.copy()
            avatar_surface.set_alpha(player.alpha)
        rect = avatar_surface.get_rect(center=(screen_x, screen_y))
        self.screen.blit(avatar_surface, rect)

    def _draw_day_counter(self, players, game_state: dict):
        total_count = len(players)
        day_number = game_state.get("club_day_number")
        if day_number is None:
            day_number = max(1, int(getattr(config, "DAY_NUMBER", 1)) - 71)
        day_text = f"Day {day_number}: {total_count} {self.PLAYER_LABEL}"
        y_pos = int(self.game_bottom + self.day_counter_offset)
        day_surface = self.font_day.render(day_text, True, config.COLOR_TEXT)
        day_rect = day_surface.get_rect(center=(self.width // 2, y_pos))
        self.screen.blit(day_surface, day_rect)
        self._day_counter_rect = day_rect

    def _draw_game_ui(self, players, game_state: dict):
        elapsed = game_state.get("elapsed_time")
        if elapsed is None:
            return

        world_label = getattr(config, "SUPER_FOLLOWER_BROS_WORLD_LABEL", "1-1")
        time_limit = int(getattr(config, "SUPER_FOLLOWER_BROS_TIME_LIMIT", 400))
        remaining = max(0, time_limit - int(elapsed))

        panel_x = self.game_left + 12
        panel_y = self.game_top + 8

        world_surface = self.font_small.render(f"WORLD {world_label}", True, (255, 255, 255))
        time_surface = self.font_small.render(f"TIME {remaining:03d}", True, (255, 255, 255))

        self.screen.blit(world_surface, (panel_x, panel_y))
        self.screen.blit(time_surface, (panel_x, panel_y + 18))
