from dataclasses import dataclass

import pygame

import config


@dataclass
class SuperFollowerBrosEnemy:
    x: float
    y: float
    vx: float
    vy: float
    width: float
    height: float
    kind: str = "goomba"
    state: str = "walk"
    spawn_x: float = 0.0
    spawn_y: float = 0.0
    base_speed: float = 0.0
    walk_width: float = 0.0
    walk_height: float = 0.0
    shell_width: float = 0.0
    shell_height: float = 0.0
    respawn_at: float | None = None

    def rect(self) -> pygame.Rect:
        return pygame.Rect(
            int(self.x - self.width / 2),
            int(self.y - self.height / 2),
            int(self.width),
            int(self.height),
        )

    def update(self, dt: float, level) -> None:
        if self.state == "dead":
            return
        if self.state == "shell":
            self.vx = 0.0

        # Horizontal movement and wall flips
        self.x += self.vx * dt
        rect = self.rect()
        for tile in level.iter_solid_tiles(rect):
            if rect.colliderect(tile):
                if self.vx > 0:
                    self.x = tile.left - self.width / 2 - 0.5
                    self.vx = -abs(self.vx)
                elif self.vx < 0:
                    self.x = tile.right + self.width / 2 + 0.5
                    self.vx = abs(self.vx)
                rect = self.rect()

        # Gravity + vertical collision
        gravity = float(getattr(config, "SUPER_FOLLOWER_BROS_ENEMY_GRAVITY", 1200.0))
        max_fall = float(getattr(config, "SUPER_FOLLOWER_BROS_ENEMY_MAX_FALL_SPEED", 900.0))
        self.vy += gravity * dt
        if self.vy > max_fall:
            self.vy = max_fall
        self.y += self.vy * dt
        rect = self.rect()
        for tile in level.iter_solid_tiles(rect):
            if rect.colliderect(tile):
                if self.vy > 0:
                    self.y = tile.top - self.height / 2 - 0.5
                    self.vy = 0.0
                    rect = self.rect()
                elif self.vy < 0:
                    self.y = tile.bottom + self.height / 2 + 0.5
                    self.vy = 0.0
                    rect = self.rect()

    def set_state(self, state: str) -> None:
        if state == self.state:
            return
        bottom = self.y + self.height / 2
        if state in ("shell", "shell_slide") and self.shell_width and self.shell_height:
            self.width = self.shell_width
            self.height = self.shell_height
        elif self.walk_width and self.walk_height:
            self.width = self.walk_width
            self.height = self.walk_height
        self.y = bottom - self.height / 2
        self.state = state

    def respawn(self) -> None:
        self.x = self.spawn_x
        self.y = self.spawn_y
        self.vx = -abs(self.base_speed)
        self.vy = 0.0
        self.set_state("walk")
        self.respawn_at = None
