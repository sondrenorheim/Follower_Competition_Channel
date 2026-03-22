import random
import time

import config
from shared import EntityTemplate


class CrossyFollower(EntityTemplate):
    def _init_entity(self, follower_data: dict):
        self.radius = float(getattr(config, "CROSSY_PLAYER_RADIUS", config.FOLLOWER_RADIUS))
        self.move_cooldown_min = float(getattr(config, "CROSSY_MOVE_COOLDOWN_MIN", 0.33))
        self.move_cooldown_max = float(getattr(config, "CROSSY_MOVE_COOLDOWN_MAX", 0.45))
        if self.move_cooldown_max < self.move_cooldown_min:
            self.move_cooldown_min, self.move_cooldown_max = self.move_cooldown_max, self.move_cooldown_min
        self.move_cooldown_min = max(0.05, self.move_cooldown_min)
        self.move_cooldown_max = max(self.move_cooldown_min, self.move_cooldown_max)
        self.base_move_cooldown_min = self.move_cooldown_min
        self.base_move_cooldown_max = self.move_cooldown_max
        self.move_pace_multiplier = 1.0
        self.move_cooldown = (self.move_cooldown_min + self.move_cooldown_max) * 0.5

        self.grid_lane = 0
        self.grid_row = 0
        self.start_row = 0
        self.max_row = 0

        self.next_move_time = 0.0
        self.last_move_time = 0.0
        self.last_progress_time = 0.0

        day_seed = int(getattr(config, "DAY_NUMBER", 1))
        self.rng = random.Random(self._seed_from_id(self.id) + day_seed * 7919)
        self.decision_jitter = self.rng.uniform(-0.3, 0.3)
        self.is_club_member = False

    @staticmethod
    def _seed_from_id(value) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            text = str(value)
            seed = 0
            for idx, char in enumerate(text):
                seed += (idx + 1) * ord(char)
            return seed

    def set_grid_position(self, lane: int, row: int, arena):
        self.grid_lane = int(lane)
        self.grid_row = int(row)
        self.x = arena.lane_to_x(self.grid_lane)
        self.y = float(self.grid_row)
        if self.start_row == 0 and self.max_row == 0:
            self.start_row = self.grid_row
        self.max_row = max(self.max_row, self.grid_row)

    def can_move(self, game_time: float) -> bool:
        return self.alive and game_time >= self.next_move_time

    def apply_move(self, lane: int, row: int, arena, game_time: float):
        self.grid_lane = int(lane)
        self.grid_row = int(row)
        self.x = arena.lane_to_x(self.grid_lane)
        self.y = float(self.grid_row)
        previous_max = self.max_row
        self.max_row = max(self.max_row, self.grid_row)
        if self.max_row > previous_max:
            self.last_progress_time = float(game_time)
        self.last_move_time = game_time
        pace_multiplier = max(0.4, float(getattr(self, "move_pace_multiplier", 1.0)))
        base_min = max(0.05, float(getattr(self, "base_move_cooldown_min", self.move_cooldown_min)))
        base_max = max(base_min, float(getattr(self, "base_move_cooldown_max", self.move_cooldown_max)))
        interval = self.rng.uniform(base_min * pace_multiplier, base_max * pace_multiplier)
        self.move_cooldown = interval
        self.next_move_time = game_time + interval

    def eliminate_at(self, game_time: float):
        if not self.alive:
            return
        self.alive = False
        self.elimination_time = time.time()
        self.survival_time = float(game_time)

    def progress_score(self, start_row: int) -> int:
        return max(0, int(self.max_row - start_row))
