import math
import random
from typing import Tuple

import config


class MiniGolfPlayer:
    def __init__(self, follower_data: dict, start_pos: Tuple[float, float],
                 rng_seed: int, size: float = None):
        self.id = follower_data.get("id", "")
        self.username = follower_data.get("username", "")
        self.avatar_image = follower_data.get("avatar_image") or follower_data.get("avatar")
        self.color = follower_data.get("color", random.choice(config.RANDOM_COLORS))

        if size is None:
            size = float(getattr(config, "MINIGOLF_PLAYER_SIZE", 12))
        self.size = float(size)
        self.radius = self.size * 0.5

        self.x, self.y = start_pos
        self.vx = 0.0
        self.vy = 0.0

        self.finished = False
        self.eliminated = False
        self.round_shots = 0
        self.total_shots = 0
        self.total_distance_remaining = 0.0
        self.placement = None
        self.survival_time = None
        self.rounds_completed = 0

        self.rng = random.Random(rng_seed)

    def reset_for_round(self, start_pos: Tuple[float, float]):
        self.x, self.y = start_pos
        self.vx = 0.0
        self.vy = 0.0
        self.finished = False
        self.round_shots = 0

    def apply_shot(self, angle: float, power: float):
        self.vx = math.cos(angle) * power
        self.vy = math.sin(angle) * power

    def is_moving(self, stop_speed: float) -> bool:
        return (self.vx * self.vx + self.vy * self.vy) > (stop_speed * stop_speed)

    def update(self, dt: float, course, friction: float, stop_speed: float,
               hole_center: Tuple[float, float], hole_radius: float):
        if self.finished:
            self.vx = 0.0
            self.vy = 0.0
            return

        if not self.is_moving(stop_speed):
            self.vx = 0.0
            self.vy = 0.0
            dx = self.x - hole_center[0]
            dy = self.y - hole_center[1]
            if (dx * dx + dy * dy) <= (hole_radius * hole_radius):
                self.finished = True
            return

        distance = math.hypot(self.vx, self.vy) * dt
        max_step = max(2.0, min(self.radius * 0.5, course.cell_size * 0.2))
        steps = max(1, int(distance / max_step) + 1)
        step_dt = dt / steps
        step_decay = friction ** (step_dt * 60.0)
        hole_radius_sq = hole_radius * hole_radius

        for _ in range(steps):
            prev_x, prev_y = self.x, self.y
            dx = self.vx * step_dt
            dy = self.vy * step_dt

            if dx != 0.0 and dy != 0.0:
                # Resolve in the order we would hit cell boundaries to reduce corner tunneling.
                if self._should_move_x_first(course, prev_x, prev_y, dx, dy):
                    self._step_axis(course, dx, 0.0, prev_x, prev_y)
                    prev_x, prev_y = self.x, self.y
                    self._step_axis(course, 0.0, dy, prev_x, prev_y)
                else:
                    self._step_axis(course, 0.0, dy, prev_x, prev_y)
                    prev_x, prev_y = self.x, self.y
                    self._step_axis(course, dx, 0.0, prev_x, prev_y)
            else:
                self._step_axis(course, dx, dy, prev_x, prev_y)

            self.vx *= step_decay
            self.vy *= step_decay

            dx = self.x - hole_center[0]
            dy = self.y - hole_center[1]
            if (dx * dx + dy * dy) <= hole_radius_sq:
                self.finished = True
                self.vx = 0.0
                self.vy = 0.0
                return

        if not self.is_moving(stop_speed):
            self.vx = 0.0
            self.vy = 0.0

    def _step_axis(self, course, dx: float, dy: float, prev_x: float, prev_y: float):
        if dx == 0.0 and dy == 0.0:
            return
        self.x += dx
        self.y += dy
        self._resolve_wall_collisions(course, prev_x, prev_y)
        self.x, self.y = course.clamp_position(self.x, self.y, self.radius)

    def _should_move_x_first(self, course, x: float, y: float, dx: float, dy: float) -> bool:
        if dx == 0.0:
            return False
        if dy == 0.0:
            return True

        col, row = course.world_to_cell(x, y)
        left, top, right, bottom = course.cell_bounds((col, row))
        padding = self._wall_padding()
        walls = course.walls[row][col]

        if dx > 0.0:
            x_limit = right - padding - self.radius if walls["E"] else right
        else:
            x_limit = left + padding + self.radius if walls["W"] else left
        if dy > 0.0:
            y_limit = bottom - padding - self.radius if walls["S"] else bottom
        else:
            y_limit = top + padding + self.radius if walls["N"] else top

        tx = (x_limit - x) / dx
        ty = (y_limit - y) / dy
        if tx < 0.0:
            tx = 0.0
        if ty < 0.0:
            ty = 0.0
        return tx <= ty

    def _wall_padding(self) -> float:
        return max(0.0, float(getattr(config, "MINIGOLF_WALL_THICKNESS", 3)) * 0.45)

    def _resolve_wall_collisions(self, course, prev_x: float, prev_y: float):
        padding = self._wall_padding()
        prev_col, prev_row = course.world_to_cell(prev_x, prev_y)
        col, row = course.world_to_cell(self.x, self.y)
        bounced = False

        if col > prev_col:
            if course.walls[prev_row][prev_col]["E"]:
                boundary = course.cell_bounds((prev_col, prev_row))[2] - padding
                self.x = boundary - self.radius
                self.vx = -abs(self.vx)
                bounced = True
                col = prev_col
        elif col < prev_col:
            if course.walls[prev_row][prev_col]["W"]:
                boundary = course.cell_bounds((prev_col, prev_row))[0] + padding
                self.x = boundary + self.radius
                self.vx = abs(self.vx)
                bounced = True
                col = prev_col

        if row > prev_row:
            if course.walls[prev_row][prev_col]["S"]:
                boundary = course.cell_bounds((prev_col, prev_row))[3] - padding
                self.y = boundary - self.radius
                self.vy = -abs(self.vy)
                bounced = True
                row = prev_row
        elif row < prev_row:
            if course.walls[prev_row][prev_col]["N"]:
                boundary = course.cell_bounds((prev_col, prev_row))[1] + padding
                self.y = boundary + self.radius
                self.vy = abs(self.vy)
                bounced = True
                row = prev_row

        col, row = course.world_to_cell(self.x, self.y)
        left, top, right, bottom = course.cell_bounds((col, row))
        walls = course.walls[row][col]

        if walls["W"] and self.x - self.radius < left + padding:
            self.x = left + padding + self.radius
            self.vx = abs(self.vx)
            bounced = True
        if walls["E"] and self.x + self.radius > right - padding:
            self.x = right - padding - self.radius
            self.vx = -abs(self.vx)
            bounced = True
        if walls["N"] and self.y - self.radius < top + padding:
            self.y = top + padding + self.radius
            self.vy = abs(self.vy)
            bounced = True
        if walls["S"] and self.y + self.radius > bottom - padding:
            self.y = bottom - padding - self.radius
            self.vy = -abs(self.vy)
            bounced = True

        if bounced:
            self.vx *= 0.9
            self.vy *= 0.9
