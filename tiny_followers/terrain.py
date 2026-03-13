import math
import random
from typing import List, Tuple

import config


class TinyTerrain:
    """
    Procedural cosine-hill terrain inspired by the original Tiny Wings remake.
    """

    def __init__(self, arena, seed: int | None = None):
        self.arena = arena
        self.seed = int(seed if seed is not None else getattr(config, "DAY_NUMBER", 1))
        self.rng = random.Random(self.seed)

        self.min_dx = float(getattr(config, "TINY_KEYPOINT_MIN_DX", 130.0))
        self.max_dx = float(getattr(config, "TINY_KEYPOINT_MAX_DX", 220.0))
        self.min_dy = float(getattr(config, "TINY_KEYPOINT_MIN_DY", 55.0))
        self.max_dy = float(getattr(config, "TINY_KEYPOINT_MAX_DY", 120.0))
        sharpness = float(getattr(config, "TINY_TERRAIN_SHARPNESS", 0.0))
        self.terrain_sharpness = max(0.0, min(0.95, sharpness))
        self.render_step = int(getattr(config, "TINY_TERRAIN_RENDER_STEP", 2))

        self.points_first: List[Tuple[float, float]] = []
        self.points_second: List[Tuple[float, float]] = []
        self.water_ranges: List[Tuple[float, float]] = []

        self.world_start_x = 0.0
        self.world_end_x = 0.0
        self.first_island_end_x = 0.0
        self.second_island_start_x = 0.0
        self.second_island_end_x = 0.0
        self.finish_x = 0.0

        self._x_offset = 0
        self._height_map: List[float] = []
        self._slope_map: List[float] = []
        self._ground_map: List[bool] = []
        self._water_floor_y = float(self.arena.bottom + getattr(config, "TINY_WATER_FLOOR_OFFSET", 280.0))

        self._build()

    def _build(self):
        top = float(self.arena.top)
        bottom = float(self.arena.bottom)
        height = float(self.arena.height)

        min_height = top + float(getattr(config, "TINY_MIN_HEIGHT_PADDING", 24.0))
        max_height = bottom - float(getattr(config, "TINY_MAX_HEIGHT_PADDING", 20.0))

        start_x = -self.arena.width * 0.25
        start_y = top + height * float(getattr(config, "TINY_START_HEIGHT_RATIO", 0.75))
        anchor_x = 0.0
        anchor_y = top + height * float(getattr(config, "TINY_ANCHOR_HEIGHT_RATIO", 0.55))

        self.points_first = [(start_x, start_y), (anchor_x, anchor_y)]
        x = anchor_x
        y = anchor_y
        sign = -1.0
        first_length = float(getattr(config, "TINY_FIRST_ISLAND_LENGTH", 1900.0))
        first_target_end = anchor_x + first_length

        while x < first_target_end:
            dx = self.rng.uniform(self.min_dx, self.max_dx)
            x += dx
            dy = self.rng.uniform(self.min_dy, self.max_dy)
            y = max(min_height, min(max_height, y + dy * sign))
            self.points_first.append((x, y))
            sign *= -1.0

        enable_gap = bool(getattr(config, "TINY_ENABLE_ISLAND_GAP", True))
        gap_width = float(getattr(config, "TINY_WATER_GAP_WIDTH", 240.0))
        if enable_gap and gap_width > 0.0:
            cliff_dx = self.rng.uniform(self.min_dx, self.max_dx)
            x += cliff_dx
            cliff_drop = float(getattr(config, "TINY_CLIFF_DROP", 180.0))
            cliff_y = bottom + cliff_drop
            self.points_first.append((x, cliff_y))
            self.first_island_end_x = x
            self.second_island_start_x = self.first_island_end_x + gap_width
            second_start_y = top + height * float(getattr(config, "TINY_SECOND_ISLAND_START_HEIGHT_RATIO", 0.68))
        else:
            self.first_island_end_x = x
            self.second_island_start_x = x
            second_start_y = y

        second_entry_dx = float(getattr(config, "TINY_SECOND_ISLAND_ENTRY_LENGTH", 140.0))
        second_entry_rise = float(getattr(config, "TINY_SECOND_ISLAND_ENTRY_RISE", 84.0))
        if not (enable_gap and gap_width > 0.0):
            second_entry_dx *= 0.65
            second_entry_rise *= 0.5
        second_entry_y = max(min_height, min(max_height, second_start_y - second_entry_rise))

        self.points_second = [
            (self.second_island_start_x, second_start_y),
            (self.second_island_start_x + second_entry_dx, second_entry_y),
        ]

        x = self.points_second[-1][0]
        y = self.points_second[-1][1]
        sign = 1.0
        second_length = float(getattr(config, "TINY_SECOND_ISLAND_LENGTH", 1400.0))
        second_target_end = self.second_island_start_x + second_length

        while x < second_target_end:
            dx = self.rng.uniform(self.min_dx * 0.9, self.max_dx * 1.1)
            x += dx
            dy = self.rng.uniform(self.min_dy * 0.9, self.max_dy)
            y = max(min_height, min(max_height, y + dy * sign))
            self.points_second.append((x, y))
            sign *= -1.0

        self.second_island_end_x = self.points_second[-1][0]
        finish_offset = float(getattr(config, "TINY_FINISH_OFFSET", 260.0))
        self.finish_x = self.second_island_start_x + finish_offset

        self.world_start_x = self.points_first[0][0]
        self.world_end_x = max(self.second_island_end_x + 280.0, self.finish_x + 180.0)
        if enable_gap and gap_width > 0.0 and self.second_island_start_x > self.first_island_end_x:
            self.water_ranges = [(self.first_island_end_x, self.second_island_start_x)]
        else:
            self.water_ranges = []

        self._build_maps()

    def _build_maps(self):
        self._x_offset = int(math.floor(self.world_start_x)) - 2
        max_x = int(math.ceil(self.world_end_x)) + 2
        map_size = max(8, max_x - self._x_offset + 1)

        self._height_map = [self._water_floor_y for _ in range(map_size)]
        self._slope_map = [0.0 for _ in range(map_size)]
        self._ground_map = [False for _ in range(map_size)]

        self._rasterize_island(self.points_first)
        self._rasterize_island(self.points_second)

    def _rasterize_island(self, points: List[Tuple[float, float]]):
        if len(points) < 2:
            return

        for i in range(len(points) - 1):
            x0, y0 = points[i]
            x1, y1 = points[i + 1]
            if x1 <= x0:
                continue

            segment_width = x1 - x0
            ymid = (y0 + y1) * 0.5
            amplitude = (y0 - y1) * 0.5

            xi_start = int(math.floor(x0))
            xi_end = int(math.ceil(x1))

            for xi in range(xi_start, xi_end + 1):
                if xi < self._x_offset:
                    continue
                idx = xi - self._x_offset
                if idx < 0 or idx >= len(self._height_map):
                    continue

                t = (xi - x0) / segment_width
                if t < 0.0:
                    t = 0.0
                elif t > 1.0:
                    t = 1.0

                cosine_y = ymid + amplitude * math.cos(math.pi * t)
                cosine_slope = -amplitude * math.sin(math.pi * t) * (math.pi / max(segment_width, 1e-6))

                linear_y = y0 + (y1 - y0) * t
                linear_slope = (y1 - y0) / max(segment_width, 1e-6)

                sharp = self.terrain_sharpness
                y = cosine_y * (1.0 - sharp) + linear_y * sharp
                slope = cosine_slope * (1.0 - sharp) + linear_slope * sharp

                self._height_map[idx] = y
                self._slope_map[idx] = slope
                self._ground_map[idx] = True

    def sample(self, x: float) -> tuple[float, float, bool]:
        fx = x - self._x_offset
        i = int(math.floor(fx))
        frac = fx - i

        if i < 0 or i + 1 >= len(self._height_map):
            return self._water_floor_y, 0.0, False

        ground_a = self._ground_map[i]
        ground_b = self._ground_map[i + 1]
        has_ground = bool(ground_a and ground_b)

        if not has_ground:
            return self._water_floor_y, 0.0, False

        y0 = self._height_map[i]
        y1 = self._height_map[i + 1]
        s0 = self._slope_map[i]
        s1 = self._slope_map[i + 1]

        y = y0 + (y1 - y0) * frac
        slope = s0 + (s1 - s0) * frac
        return y, slope, True

    def clamp_camera_x(self, camera_x: float) -> float:
        lead_in = float(getattr(config, "TINY_CAMERA_LEAD_IN", 60.0))
        finish_padding = float(getattr(config, "TINY_CAMERA_FINISH_PADDING", 120.0))
        min_x = self.world_start_x - lead_in
        max_x = max(min_x, self.finish_x + finish_padding - self.arena.width)
        return max(min_x, min(max_x, camera_x))

    def get_visible_ground_segments(self, camera_x: float, width: float, step: int | None = None):
        sample_step = int(step if step is not None else self.render_step)
        sample_step = max(1, sample_step)
        width_int = int(max(0, width))

        segments: List[List[Tuple[float, float]]] = []
        current: List[Tuple[float, float]] = []

        x = 0
        while x <= width_int:
            world_x = camera_x + x
            y, _, ground = self.sample(world_x)
            if ground:
                current.append((float(x), float(y)))
            else:
                if len(current) >= 2:
                    segments.append(current)
                current = []
            x += sample_step

        if len(current) >= 2:
            segments.append(current)

        return segments

    def get_visible_water_ranges(self, camera_x: float, width: float):
        view_left = camera_x
        view_right = camera_x + width
        visible = []

        for start, end in self.water_ranges:
            left = max(start, view_left)
            right = min(end, view_right)
            if right > left:
                visible.append((left - view_left, right - view_left))

        return visible
