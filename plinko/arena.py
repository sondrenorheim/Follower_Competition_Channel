import random

import config


class PlinkoArena:
    """Defines the Plinko board geometry and helper utilities."""

    def __init__(self):
        self.x, self.y, self.width, self.height = config.FIGHTER_ARENA_RECT
        self.left = float(self.x)
        self.top = float(self.y)
        self.right = float(self.x + self.width)
        self.bottom = float(self.y + self.height)
        self.center_x = (self.left + self.right) * 0.5
        self.center_y = (self.top + self.bottom) * 0.5

        # Layout tuning
        self.triangle_mode = bool(getattr(config, "PLINKO_TRIANGLE_MODE", True))
        self.side_padding = float(getattr(config, "PLINKO_SIDE_PADDING", 14))
        self.top_padding = float(getattr(config, "PLINKO_STAGE_TOP_PADDING", 10))
        self.bottom_padding = float(getattr(config, "PLINKO_STAGE_BOTTOM_PADDING", 22))
        self.row_spacing = float(getattr(config, "PLINKO_ROW_SPACING", 34))
        self.peg_radius = float(getattr(config, "PLINKO_PEG_RADIUS", 4))
        self.peg_columns = int(getattr(config, "PLINKO_PEG_COLUMNS", 10))
        self.peg_rows_count = int(getattr(config, "PLINKO_PEG_ROWS", 11))
        self.peg_max_per_row = int(getattr(config, "PLINKO_PEG_MAX_PER_ROW", self.peg_rows_count))

        self.hole_count = int(getattr(config, "PLINKO_HOLE_COUNT", 6))
        self.hole_width = float(getattr(config, "PLINKO_HOLE_WIDTH", 24))
        self.hole_height = float(getattr(config, "PLINKO_HOLE_HEIGHT", 18))
        self.hole_gap = float(getattr(config, "PLINKO_HOLE_GAP", 12))

        self.play_left = self.left + self.side_padding
        self.play_right = self.right - self.side_padding
        self.play_width = max(10.0, self.play_right - self.play_left)

        self.stage_top = self.top + self.top_padding
        self.hole_top = max(self.stage_top + 10.0, self.bottom - self.hole_height)
        self.stage_bottom = max(self.stage_top + 10.0, self.hole_top - 2.0)

        self.row_ys = []
        self.row_spacing_actual = float(self.row_spacing)
        self.row_start_y = self.stage_top
        self.peg_positions = []
        self.peg_rows = []
        self.peg_row_offsets = []
        self.peg_row_start_x = []
        self.peg_row_counts = []
        self.peg_spacing_x = None
        self.triangle_top_y = self.stage_top
        self.triangle_bottom_y = self.hole_top
        self.triangle_top_half_width = None
        self.triangle_bottom_half_width = None
        self.holes = []
        self.hole_centers = []

        self._build_rows()
        self._build_pegs()
        self._build_holes()

    def _build_rows(self):
        spacing = max(10.0, self.row_spacing)
        max_y = self.hole_top - spacing * 0.5

        if self.triangle_mode:
            rows = max(3, self.peg_rows_count)
            available = max(10.0, max_y - self.stage_top)
            max_spacing = available / (rows + 1)
            if spacing <= 0 or spacing > max_spacing:
                spacing = max_spacing
            self.row_ys = [self.stage_top + (i + 1) * spacing for i in range(rows)]
        else:
            y = self.stage_top + spacing
            while y < max_y and len(self.row_ys) < 50:
                self.row_ys.append(float(y))
                y += spacing

        if not self.row_ys:
            # Fallback: evenly space a few rows if spacing is too large.
            rows = max(6, int((self.stage_bottom - self.stage_top) / max(1.0, spacing)))
            if rows > 0:
                step = (self.stage_bottom - self.stage_top) / (rows + 1)
                self.row_ys = [self.stage_top + (i + 1) * step for i in range(rows)]

        if len(self.row_ys) >= 2:
            self.row_spacing_actual = max(1.0, float(self.row_ys[1] - self.row_ys[0]))
        else:
            self.row_spacing_actual = max(1.0, spacing)
        self.row_start_y = self.row_ys[0] if self.row_ys else self.stage_top

    def _build_pegs(self):
        if self.triangle_mode:
            rows = max(3, self.peg_rows_count)
            max_per_row = max(2, self.peg_max_per_row)
            spacing_x = self.play_width / (max_per_row - 1)
            self.peg_spacing_x = spacing_x
            self.peg_rows = []
            self.peg_row_offsets = []
            self.peg_row_start_x = []
            self.peg_row_counts = []

            for row_index, y in enumerate(self.row_ys):
                peg_count = min(max_per_row, row_index + 1)
                row_width = (peg_count - 1) * spacing_x
                start_x = self.center_x - row_width * 0.5
                self.peg_row_offsets.append(0.0)
                self.peg_row_start_x.append(start_x)
                self.peg_row_counts.append(peg_count)

                row_positions = []
                for i in range(peg_count):
                    x = start_x + i * spacing_x
                    if self.play_left <= x <= self.play_right:
                        self.peg_positions.append((float(x), float(y)))
                        row_positions.append(float(x))
                self.peg_rows.append(row_positions)
        else:
            columns = max(4, int(self.peg_columns))
            if columns < 2:
                return

            spacing_x = self.play_width / (columns - 1)
            self.peg_spacing_x = spacing_x
            self.peg_rows = []
            self.peg_row_offsets = []
            self.peg_row_start_x = []
            self.peg_row_counts = []
            for row_index, y in enumerate(self.row_ys):
                offset = spacing_x * 0.5 if row_index % 2 == 1 else 0.0
                self.peg_row_offsets.append(offset)
                row_positions = []
                start_x = self.play_left + offset
                self.peg_row_start_x.append(start_x)
                x = start_x
                count = 0
                while x <= self.play_right:
                    if self.play_left <= x <= self.play_right:
                        self.peg_positions.append((float(x), float(y)))
                        row_positions.append(float(x))
                        count += 1
                    x += spacing_x
                self.peg_row_counts.append(count)
                self.peg_rows.append(row_positions)

        if self.peg_spacing_x:
            self.triangle_top_y = self.row_start_y
            self.triangle_bottom_y = self.hole_top
            top_half = max(self.peg_spacing_x * 0.5, self.peg_radius * 2.0)
            bottom_half = (self.peg_max_per_row - 1) * self.peg_spacing_x * 0.5
            self.triangle_top_half_width = top_half
            self.triangle_bottom_half_width = bottom_half

    def _build_holes(self):
        count = max(1, int(self.hole_count))
        gap = max(2.0, self.hole_gap)
        available = self.play_width

        hole_width = min(self.hole_width, available / max(1.0, count))
        total_width = (count * hole_width) + (count + 1) * gap
        if total_width > available:
            hole_width = max(6.0, (available - (count + 1) * gap) / count)
            total_width = (count * hole_width) + (count + 1) * gap
            if hole_width < 6.0:
                hole_width = max(6.0, available / (count + 1))
                gap = max(2.0, (available - count * hole_width) / (count + 1))

        start_x = self.play_left + (available - total_width) * 0.5 + gap
        x = start_x
        self.holes = []
        self.hole_centers = []

        for _ in range(count):
            left = float(x)
            right = float(x + hole_width)
            self.holes.append((left, right))
            self.hole_centers.append((left + right) * 0.5)
            x = right + gap

    def get_rect(self):
        return (self.left, self.top, self.width, self.height)

    def get_bounds(self):
        return (self.left, self.top, self.right, self.bottom)

    def get_spawn_position(self, radius: float, rng=None):
        if rng is None:
            rng = random
        min_x = self.play_left + radius
        max_x = self.play_right - radius
        spread = float(getattr(config, "PLINKO_SPAWN_SPREAD_X", self.play_width * 0.25))
        center_x = (self.play_left + self.play_right) * 0.5
        x = center_x + rng.uniform(-spread, spread)
        if x < min_x:
            x = min_x
        elif x > max_x:
            x = max_x
        jitter = float(getattr(config, "PLINKO_SPAWN_JITTER", max(2.0, self.row_spacing_actual * 0.25)))
        y = self.stage_top + radius + rng.uniform(0.0, jitter)
        return (float(x), float(y))

    def clamp_x(self, x: float, radius: float):
        min_x = self.play_left + radius
        max_x = self.play_right - radius
        if x < min_x:
            return min_x
        if x > max_x:
            return max_x
        return x

    def check_hole(self, x: float):
        for index, (left, right) in enumerate(self.holes):
            if left <= x <= right:
                return True, index
        return False, None

    def get_nearest_hole_index(self, x: float):
        if not self.hole_centers:
            return None
        return min(range(len(self.hole_centers)), key=lambda i: abs(x - self.hole_centers[i]))

    def get_hole_rects(self):
        rects = []
        for left, right in self.holes:
            rects.append((left, self.hole_top, right, self.bottom))
        return rects

    def get_horizontal_bounds(self, y: float, radius: float):
        if not self.triangle_mode or not self.peg_spacing_x:
            return (self.play_left + radius, self.play_right - radius)

        top_y = self.triangle_top_y
        bottom_y = self.triangle_bottom_y
        height = max(1.0, bottom_y - top_y)
        t = (y - top_y) / height
        if t < 0.0:
            t = 0.0
        elif t > 1.0:
            t = 1.0

        top_half = self.triangle_top_half_width or (self.peg_spacing_x * 0.5)
        bottom_half = self.triangle_bottom_half_width or (self.play_width * 0.5)
        half_width = top_half + (bottom_half - top_half) * t
        min_x = self.center_x - half_width + radius
        max_x = self.center_x + half_width - radius
        return (min_x, max_x)

    def iter_nearby_pegs(self, x: float, y: float, radius: float):
        if not self.row_ys or not self.peg_rows or not self.peg_spacing_x:
            return

        spacing = self.row_spacing_actual or 1.0
        row_float = (y - self.row_start_y) / spacing
        base_index = int(round(row_float))

        min_distance = radius + self.peg_radius + spacing * 0.55
        for row_index in (base_index - 1, base_index, base_index + 1):
            if row_index < 0 or row_index >= len(self.row_ys):
                continue
            row_y = self.row_ys[row_index]
            if abs(y - row_y) > min_distance:
                continue
            row = self.peg_rows[row_index]
            if not row:
                continue
            start_x = self.peg_row_start_x[row_index] if self.peg_row_start_x else (self.play_left + self.peg_row_offsets[row_index])
            col_float = (x - start_x) / self.peg_spacing_x
            col_index = int(round(col_float))
            for col in (col_index - 1, col_index, col_index + 1):
                if 0 <= col < len(row):
                    yield row[col], row_y
