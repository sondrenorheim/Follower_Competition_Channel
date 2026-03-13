import random

import config
from shared import EntityTemplate


class SubwayFollower(EntityTemplate):
    def __init__(self, follower_data: dict, position: tuple, lane_index: int):
        self.lane_index = lane_index
        super().__init__(follower_data, position)

    def _init_entity(self, follower_data: dict):
        self.size = float(getattr(config, "SUBWAY_PLAYER_SIZE", 30.0))
        self.radius = self.size * 0.5

        self.move_speed = float(getattr(config, "SUBWAY_MOVE_SPEED", 160.0))
        self.vertical_speed = float(getattr(config, "SUBWAY_VERTICAL_SPEED", 120.0))
        self.lane_change_speed = float(getattr(config, "SUBWAY_LANE_CHANGE_SPEED", 220.0))
        self.lane_change_cooldown_time = float(getattr(config, "SUBWAY_LANE_CHANGE_COOLDOWN", 0.35))
        self.lane_change_cooldown = 0.0

        self.reaction_distance = float(getattr(config, "SUBWAY_REACTION_DISTANCE", 210.0))
        self.safe_distance = float(getattr(config, "SUBWAY_SAFE_DISTANCE", 120.0))
        self.decision_interval_range = getattr(config, "SUBWAY_DECISION_INTERVAL_RANGE", (0.25, 0.6))
        self.decision_timer = 0.0
        self.decision_interval = random.uniform(*self.decision_interval_range)

        self.skill = random.uniform(0.55, 1.0)
        self.miss_chance = (1.0 - self.skill) * 0.35

        self.target_lane = self.lane_index
        self.target_y = self.y
        self.base_y = self.y

        self.wander_timer = 0.0
        self.wander_interval = random.uniform(0.6, 1.4)

    def update(self, dt, arena, obstacles, difficulty=0.0):
        if not self.alive:
            self.update_fade()
            return

        self.decision_timer += dt
        if self.lane_change_cooldown > 0:
            self.lane_change_cooldown = max(0.0, self.lane_change_cooldown - dt)

        current_lane = arena.get_lane_for_x(self.x)
        self.lane_index = current_lane

        danger = self._find_danger_obstacle(current_lane, obstacles)
        if danger and self.decision_timer >= self.decision_interval:
            if random.random() >= self.miss_chance:
                self._evade(arena, obstacles)
            self._reset_decision_timer()
        elif self.decision_timer >= self.decision_interval:
            self._wander(arena, self.decision_timer)
            self._reset_decision_timer()

        target_x = arena.lane_center(self.target_lane)
        self._move_toward(target_x, self.target_y, dt)

        self.x, self.y = arena.clamp_position(self.x, self.y, self.radius)

    def _reset_decision_timer(self):
        self.decision_timer = 0.0
        self.decision_interval = random.uniform(*self.decision_interval_range)

    def _find_danger_obstacle(self, lane_index, obstacles):
        closest = None
        closest_dist = None
        for obstacle in obstacles:
            if not self._obstacle_in_lane(obstacle, lane_index):
                continue
            if obstacle.y > self.y + self.radius:
                continue
            distance = self.y - obstacle.y
            if distance < 0:
                continue
            if distance > self.reaction_distance:
                continue
            if closest_dist is None or distance < closest_dist:
                closest = obstacle
                closest_dist = distance
        return closest

    def _obstacle_in_lane(self, obstacle, lane_index: int) -> bool:
        span = max(1, int(getattr(obstacle, "lane_span", 1)))
        return obstacle.lane_index <= lane_index < obstacle.lane_index + span

    def _lane_clearance(self, lane_index, obstacles):
        nearest = None
        for obstacle in obstacles:
            if not self._obstacle_in_lane(obstacle, lane_index):
                continue
            if obstacle.y > self.y + self.radius:
                continue
            distance = self.y - obstacle.y
            if distance < 0:
                continue
            if nearest is None or distance < nearest:
                nearest = distance
        return float("inf") if nearest is None else nearest

    def _evade(self, arena, obstacles):
        lane_count = arena.lane_count
        candidate_lanes = list(range(lane_count))
        random.shuffle(candidate_lanes)

        best_lane = self.lane_index
        best_clearance = -1.0
        for lane in candidate_lanes:
            clearance = self._lane_clearance(lane, obstacles)
            if clearance > best_clearance:
                best_clearance = clearance
                best_lane = lane

        if best_lane != self.lane_index and self.lane_change_cooldown <= 0:
            self.target_lane = best_lane
            self.lane_change_cooldown = self.lane_change_cooldown_time

        if best_clearance < self.safe_distance * 0.6:
            self._push_down(arena)

    def _push_down(self, arena):
        run_top, run_bottom = self._runner_band(arena)
        self.target_y = min(run_bottom, self.y + self.radius * 3.0)

    def _wander(self, arena, elapsed):
        run_top, run_bottom = self._runner_band(arena)
        self.wander_timer += elapsed
        if self.wander_timer >= self.wander_interval:
            self.wander_timer = 0.0
            self.wander_interval = random.uniform(0.6, 1.4)
            self.target_y = random.uniform(run_top, run_bottom)

        if self.lane_change_cooldown <= 0 and random.random() < 0.12:
            self.target_lane = random.randint(0, arena.lane_count - 1)
            self.lane_change_cooldown = self.lane_change_cooldown_time

    def _runner_band(self, arena):
        band = getattr(config, "SUBWAY_RUNNER_Y_RANGE", (0.6, 0.9))
        band_top_ratio = min(0.95, max(0.0, float(band[0])))
        band_bottom_ratio = min(1.0, max(band_top_ratio + 0.05, float(band[1])))
        run_top = arena.top + arena.height * band_top_ratio
        run_bottom = arena.top + arena.height * band_bottom_ratio
        return run_top, run_bottom

    def _move_toward(self, target_x, target_y, dt):
        dx = target_x - self.x
        dy = target_y - self.y

        max_dx = self.lane_change_speed * dt
        max_dy = self.vertical_speed * dt

        if abs(dx) > max_dx:
            dx = max_dx if dx > 0 else -max_dx
        if abs(dy) > max_dy:
            dy = max_dy if dy > 0 else -max_dy

        self.x += dx
        self.y += dy
