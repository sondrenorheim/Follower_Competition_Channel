import pygame

import config

from .level_data import (
    LEVEL_HEIGHT,
    LEVEL_WIDTH,
    GROUND_Y,
    FLAG_X,
    GROUND_RECTS,
    PIPE_RECTS,
    STEP_RECTS,
    BRICK_SIZE,
    BRICK_POSITIONS,
    COIN_BOX_POSITIONS,
    BRICK_CONTENTS,
    COIN_BOX_CONTENTS,
)


class SuperFollowerBrosLevel:
    def __init__(self, arena_height: float = None):
        target_height = arena_height or getattr(config, "SUPER_FOLLOWER_BROS_ARENA_RECT", config.FIGHTER_ARENA_RECT)[3]
        self.scale = float(target_height) / float(LEVEL_HEIGHT)

        self.solid_rects = []
        self.blocks = []
        self.block_rect_map = {}
        self._build_colliders()

        self.pixel_height = int(round(target_height))
        self.pixel_width = int(round(float(LEVEL_WIDTH) * self.scale))
        self.ground_y = float(GROUND_Y) * self.scale
        self.flag_x = float(FLAG_X) * self.scale
        self.brick_size = float(BRICK_SIZE) * self.scale

    def _scale_rect(self, rect):
        x, y, w, h = rect
        return pygame.Rect(
            int(round(x * self.scale)),
            int(round(y * self.scale)),
            max(1, int(round(w * self.scale))),
            max(1, int(round(h * self.scale))),
        )

    def _build_colliders(self):
        for rect in GROUND_RECTS:
            self.solid_rects.append(self._scale_rect(rect))
        for rect in PIPE_RECTS:
            self.solid_rects.append(self._scale_rect(rect))
        for rect in STEP_RECTS:
            self.solid_rects.append(self._scale_rect(rect))

        brick_size = max(1, int(round(BRICK_SIZE * self.scale)))
        for x, y in BRICK_POSITIONS:
            rect = pygame.Rect(
                int(round(x * self.scale)),
                int(round(y * self.scale)),
                brick_size,
                brick_size,
            )
            self.solid_rects.append(rect)
            block = {
                "kind": "brick",
                "rect": rect,
                "contents": BRICK_CONTENTS.get((x, y)),
            }
            if block["contents"]:
                block["state"] = "closed"
                block["cooldown_until"] = None
                block["mushroom_toggle"] = False
            else:
                block["state"] = "solid"
            block["index"] = len(self.blocks)
            self.blocks.append(block)
            self.block_rect_map[id(rect)] = block

        for x, y in COIN_BOX_POSITIONS:
            rect = pygame.Rect(
                int(round(x * self.scale)),
                int(round(y * self.scale)),
                brick_size,
                brick_size,
            )
            self.solid_rects.append(rect)
            block = {
                "kind": "coin_box",
                "rect": rect,
                "contents": COIN_BOX_CONTENTS.get((x, y), "coin"),
                "state": "closed",
                "cooldown_until": None,
                "mushroom_toggle": False,
            }
            block["index"] = len(self.blocks)
            self.blocks.append(block)
            self.block_rect_map[id(rect)] = block

    def is_solid_at(self, x: float, y: float) -> bool:
        if x < 0 or y < 0:
            return False
        point = pygame.Rect(int(x), int(y), 1, 1)
        for rect in self.solid_rects:
            if rect.colliderect(point):
                return True
        return False

    def iter_solid_tiles(self, rect: pygame.Rect):
        for solid in self.solid_rects:
            if rect.colliderect(solid):
                yield solid

    def get_block_for_rect(self, rect: pygame.Rect):
        return self.block_rect_map.get(id(rect))
