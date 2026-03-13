import math
import random
from typing import Optional, Tuple

import config


class MazeRushPlayer:
    def __init__(self, follower_data: dict, start_cell: Tuple[int, int],
                 start_pos: Tuple[float, float], rng_seed: int,
                 size: float = None, is_club_member: bool = False):
        self.username = follower_data.get("username", "")
        self.avatar_image = follower_data.get("avatar_image") or follower_data.get("avatar")
        self.color = follower_data.get("color", random.choice(config.RANDOM_COLORS))
        self.is_club_member = bool(is_club_member)

        if size is None:
            size = float(getattr(config, "MAZE_RUSH_PLAYER_SIZE", 12))
        self.size = float(size)
        self.radius = self.size * 0.5

        self.x, self.y = start_pos
        self.current_cell = start_cell
        self.target_cell: Optional[Tuple[int, int]] = None
        self.prev_cell: Optional[Tuple[int, int]] = None

        self.finished = False
        self.finish_time = None
        self.placement = None
        self.survival_time = None

        self.rng = random.Random(rng_seed)
        self.speed_min = float(getattr(config, "MAZE_RUSH_SPEED_MULTIPLIER_MIN", 0.5))
        self.speed_max = float(getattr(config, "MAZE_RUSH_SPEED_MULTIPLIER_MAX", 1.5))
        if self.speed_max < self.speed_min:
            self.speed_max = self.speed_min
        self.speed_change_interval = float(getattr(config, "MAZE_RUSH_SPEED_CHANGE_INTERVAL", 2.0))
        if self.speed_change_interval <= 0:
            self.speed_change_interval = 2.0
        self.speed_change_timer = 0.0
        self.speed_multiplier = self.rng.uniform(self.speed_min, self.speed_max)
        self.speed_change_timer = self.speed_change_interval

    def update(self, dt: float, maze, speed: float, exit_cell: Optional[Tuple[int, int]] = None) -> None:
        if self.finished:
            return
        self._update_speed(dt)

        remaining = (speed * self.speed_multiplier) * dt
        steps = 0
        max_steps = 5

        while remaining > 0 and steps < max_steps and not self.finished:
            if self.target_cell is None:
                self.target_cell = self._choose_next_cell(maze)
                if self.target_cell is None:
                    return

            target_x, target_y = maze.cell_center(self.target_cell)
            dx = target_x - self.x
            dy = target_y - self.y
            dist = math.hypot(dx, dy)

            if dist <= 1e-6:
                self._arrive_at_target()
                if exit_cell is not None and self.current_cell == exit_cell:
                    self.finished = True
                    return
                steps += 1
                continue

            if dist <= remaining:
                self.x = target_x
                self.y = target_y
                remaining -= dist
                self._arrive_at_target()
                if exit_cell is not None and self.current_cell == exit_cell:
                    self.finished = True
                    return
                steps += 1
            else:
                nx = dx / dist
                ny = dy / dist
                self.x += nx * remaining
                self.y += ny * remaining
                remaining = 0

    def _arrive_at_target(self) -> None:
        if self.target_cell is None:
            return
        self.prev_cell = self.current_cell
        self.current_cell = self.target_cell
        self.target_cell = None

    def _choose_next_cell(self, maze) -> Optional[Tuple[int, int]]:
        options = maze.get_neighbors(self.current_cell)
        if not options:
            return None
        if self.prev_cell is None:
            return self.rng.choice(options)
        if len(options) == 1:
            return options[0]
        forward_options = [cell for cell in options if cell != self.prev_cell]
        if not forward_options:
            return self.prev_cell
        return self.rng.choice(forward_options)

    def _update_speed(self, dt: float) -> None:
        self.speed_change_timer -= dt
        if self.speed_change_timer > 0:
            return
        self.speed_multiplier = self.rng.uniform(self.speed_min, self.speed_max)
        self.speed_change_timer = self.speed_change_interval
