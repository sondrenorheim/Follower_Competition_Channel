import math
import random
from collections import deque
from typing import Dict, List, Tuple, Optional

DIRECTIONS = {
    "N": (0, -1),
    "S": (0, 1),
    "W": (-1, 0),
    "E": (1, 0),
}
OPPOSITE = {
    "N": "S",
    "S": "N",
    "W": "E",
    "E": "W",
}


class MiniGolfCourse:
    def __init__(self, rect: Tuple[int, int, int, int], cell_size: int, seed: int,
                 start_cell: Tuple[int, int] = None):
        self.rect = rect
        self.seed = int(seed)
        self.rng = random.Random(self.seed)

        arena_x, arena_y, arena_w, arena_h = rect
        cell_size = max(4, int(cell_size))
        cols = max(2, arena_w // cell_size)
        rows = max(2, arena_h // cell_size)

        self.cell_size = cell_size
        self.cols = cols
        self.rows = rows

        course_width = cols * cell_size
        course_height = rows * cell_size
        self.origin_x = arena_x + (arena_w - course_width) // 2
        self.origin_y = arena_y + (arena_h - course_height) // 2
        self.width = course_width
        self.height = course_height

        if start_cell is None:
            start_cell = (0, rows - 1)
        self.start_cell = (max(0, min(cols - 1, start_cell[0])),
                           max(0, min(rows - 1, start_cell[1])))

        self._init_walls()
        self._generate_maze()
        self.neighbor_map = self._build_neighbor_map()
        self.distance_from_start = self._compute_distances(self.start_cell)
        self.hole_cell = self._choose_hole_cell()
        self.distance_to_hole = self._compute_distances(self.hole_cell)
        self.best_neighbor_map = self._build_best_neighbor_map()
        self.wall_segments = self._build_wall_segments()
        self.signature = (self.seed, self.cols, self.rows, self.cell_size)

    def _init_walls(self) -> None:
        self.walls: List[List[Dict[str, bool]]] = []
        for _ in range(self.rows):
            row = []
            for _ in range(self.cols):
                row.append({"N": True, "S": True, "W": True, "E": True})
            self.walls.append(row)

    def _generate_maze(self) -> None:
        stack = [self.start_cell]
        visited = {self.start_cell}

        while stack:
            col, row = stack[-1]
            neighbors = []
            for direction, (dx, dy) in DIRECTIONS.items():
                ncol = col + dx
                nrow = row + dy
                if not self._in_bounds(ncol, nrow):
                    continue
                if (ncol, nrow) in visited:
                    continue
                neighbors.append((direction, ncol, nrow))

            if not neighbors:
                stack.pop()
                continue

            direction, ncol, nrow = self.rng.choice(neighbors)
            self.walls[row][col][direction] = False
            self.walls[nrow][ncol][OPPOSITE[direction]] = False
            visited.add((ncol, nrow))
            stack.append((ncol, nrow))

    def _build_neighbor_map(self) -> List[List[List[Tuple[int, int]]]]:
        neighbors: List[List[List[Tuple[int, int]]]] = []
        for row in range(self.rows):
            row_neighbors = []
            for col in range(self.cols):
                cell_neighbors = []
                for direction, (dx, dy) in DIRECTIONS.items():
                    if self.walls[row][col][direction]:
                        continue
                    ncol = col + dx
                    nrow = row + dy
                    if not self._in_bounds(ncol, nrow):
                        continue
                    cell_neighbors.append((ncol, nrow))
                row_neighbors.append(cell_neighbors)
            neighbors.append(row_neighbors)
        return neighbors

    def _compute_distances(self, start_cell: Tuple[int, int]) -> Dict[Tuple[int, int], int]:
        distances: Dict[Tuple[int, int], int] = {start_cell: 0}
        queue = deque([start_cell])

        while queue:
            cell = queue.popleft()
            for neighbor in self.get_neighbors(cell):
                if neighbor in distances:
                    continue
                distances[neighbor] = distances[cell] + 1
                queue.append(neighbor)

        return distances

    def _choose_hole_cell(self) -> Tuple[int, int]:
        if not self.distance_from_start:
            return self.start_cell

        max_distance = max(self.distance_from_start.values())
        candidates = [
            cell for cell, dist in self.distance_from_start.items()
            if dist == max_distance
        ]
        return self.rng.choice(candidates) if candidates else self.start_cell

    def _build_best_neighbor_map(self) -> Dict[Tuple[int, int], Optional[Tuple[int, int]]]:
        best_map: Dict[Tuple[int, int], Optional[Tuple[int, int]]] = {}
        for row in range(self.rows):
            for col in range(self.cols):
                cell = (col, row)
                neighbors = self.get_neighbors(cell)
                best_cell = None
                best_distance = None
                for neighbor in neighbors:
                    dist = self.distance_to_hole.get(neighbor)
                    if dist is None:
                        continue
                    if best_distance is None or dist < best_distance:
                        best_distance = dist
                        best_cell = neighbor
                best_map[cell] = best_cell
        return best_map

    def _build_wall_segments(self) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
        segments = []
        size = self.cell_size
        for row in range(self.rows):
            for col in range(self.cols):
                x = col * size
                y = row * size
                walls = self.walls[row][col]
                if walls["N"]:
                    segments.append(((x, y), (x + size, y)))
                if walls["W"]:
                    segments.append(((x, y), (x, y + size)))
                if row == self.rows - 1 and walls["S"]:
                    segments.append(((x, y + size), (x + size, y + size)))
                if col == self.cols - 1 and walls["E"]:
                    segments.append(((x + size, y), (x + size, y + size)))
        return segments

    def _in_bounds(self, col: int, row: int) -> bool:
        return 0 <= col < self.cols and 0 <= row < self.rows

    def get_neighbors(self, cell: Tuple[int, int]) -> List[Tuple[int, int]]:
        col, row = cell
        if not self._in_bounds(col, row):
            return []
        return self.neighbor_map[row][col]

    def get_best_neighbor(self, cell: Tuple[int, int]) -> Optional[Tuple[int, int]]:
        return self.best_neighbor_map.get(cell)

    def get_lookahead_cell(self, cell: Tuple[int, int], steps: int) -> Tuple[int, int]:
        current = cell
        for _ in range(max(0, steps)):
            next_cell = self.best_neighbor_map.get(current)
            if next_cell is None:
                break
            current = next_cell
        return current

    def get_straight_path_target(self, cell: Tuple[int, int], max_steps: int) -> Tuple[int, int]:
        if max_steps <= 0:
            return cell
        next_cell = self.best_neighbor_map.get(cell)
        if next_cell is None:
            return cell

        dir_x = next_cell[0] - cell[0]
        dir_y = next_cell[1] - cell[1]
        target = next_cell

        for _ in range(1, max_steps):
            candidate = self.best_neighbor_map.get(target)
            if candidate is None:
                break
            step_x = candidate[0] - target[0]
            step_y = candidate[1] - target[1]
            if step_x != dir_x or step_y != dir_y:
                break
            target = candidate

        return target

    def get_line_of_sight_target(self, cell: Tuple[int, int], max_steps: int) -> Tuple[int, int]:
        if max_steps <= 0:
            return cell

        current = cell
        target = cell
        for _ in range(max_steps):
            next_cell = self.best_neighbor_map.get(current)
            if next_cell is None:
                break
            if not self._has_line_of_sight(cell, next_cell):
                break
            target = next_cell
            current = next_cell

        return target

    def get_visible_cell_along_direction(self, start_pos: Tuple[float, float],
                                         angle: float, max_cells: int) -> Tuple[int, int]:
        col, row = self.world_to_cell(start_pos[0], start_pos[1])
        if max_cells <= 0:
            return (col, row)

        dx = math.cos(angle)
        dy = math.sin(angle)
        if abs(dx) < 1e-6 and abs(dy) < 1e-6:
            return (col, row)

        step_x = 1 if dx > 0 else -1 if dx < 0 else 0
        step_y = 1 if dy > 0 else -1 if dy < 0 else 0

        cell_size = self.cell_size
        max_distance = max_cells * cell_size
        x0, y0 = start_pos

        if step_x != 0:
            if step_x > 0:
                next_vert = self.origin_x + (col + 1) * cell_size
            else:
                next_vert = self.origin_x + col * cell_size
            t_max_x = (next_vert - x0) / dx
            t_delta_x = cell_size / abs(dx)
        else:
            t_max_x = float("inf")
            t_delta_x = float("inf")

        if step_y != 0:
            if step_y > 0:
                next_horiz = self.origin_y + (row + 1) * cell_size
            else:
                next_horiz = self.origin_y + row * cell_size
            t_max_y = (next_horiz - y0) / dy
            t_delta_y = cell_size / abs(dy)
        else:
            t_max_y = float("inf")
            t_delta_y = float("inf")

        while True:
            if t_max_x < t_max_y:
                if t_max_x > max_distance:
                    break
                if step_x > 0 and self.walls[row][col]["E"]:
                    break
                if step_x < 0 and self.walls[row][col]["W"]:
                    break
                next_col = col + step_x
                if not self._in_bounds(next_col, row):
                    break
                col = next_col
                t_max_x += t_delta_x
            elif t_max_y < t_max_x:
                if t_max_y > max_distance:
                    break
                if step_y > 0 and self.walls[row][col]["S"]:
                    break
                if step_y < 0 and self.walls[row][col]["N"]:
                    break
                next_row = row + step_y
                if not self._in_bounds(col, next_row):
                    break
                row = next_row
                t_max_y += t_delta_y
            else:
                if t_max_x > max_distance:
                    break
                if step_x > 0 and self.walls[row][col]["E"]:
                    break
                if step_x < 0 and self.walls[row][col]["W"]:
                    break
                if step_y > 0 and self.walls[row][col]["S"]:
                    break
                if step_y < 0 and self.walls[row][col]["N"]:
                    break
                next_col = col + step_x
                next_row = row + step_y
                if not self._in_bounds(next_col, next_row):
                    break
                col = next_col
                row = next_row
                t_max_x += t_delta_x
                t_max_y += t_delta_y

        return (col, row)

    def _has_line_of_sight(self, start_cell: Tuple[int, int], end_cell: Tuple[int, int]) -> bool:
        if start_cell == end_cell:
            return True

        x0, y0 = self.cell_center(start_cell)
        x1, y1 = self.cell_center(end_cell)
        dx = x1 - x0
        dy = y1 - y0

        col, row = start_cell
        target_col, target_row = end_cell

        step_x = 1 if dx > 0 else -1 if dx < 0 else 0
        step_y = 1 if dy > 0 else -1 if dy < 0 else 0

        if step_x == 0 and step_y == 0:
            return True

        cell_size = self.cell_size

        if step_x != 0:
            if step_x > 0:
                next_vert = self.origin_x + (col + 1) * cell_size
            else:
                next_vert = self.origin_x + col * cell_size
            t_max_x = (next_vert - x0) / dx
            t_delta_x = cell_size / abs(dx)
        else:
            t_max_x = float("inf")
            t_delta_x = float("inf")

        if step_y != 0:
            if step_y > 0:
                next_horiz = self.origin_y + (row + 1) * cell_size
            else:
                next_horiz = self.origin_y + row * cell_size
            t_max_y = (next_horiz - y0) / dy
            t_delta_y = cell_size / abs(dy)
        else:
            t_max_y = float("inf")
            t_delta_y = float("inf")

        while (col, row) != (target_col, target_row):
            if t_max_x < t_max_y:
                if step_x > 0 and self.walls[row][col]["E"]:
                    return False
                if step_x < 0 and self.walls[row][col]["W"]:
                    return False
                col += step_x
                if not self._in_bounds(col, row):
                    return False
                t_max_x += t_delta_x
            elif t_max_y < t_max_x:
                if step_y > 0 and self.walls[row][col]["S"]:
                    return False
                if step_y < 0 and self.walls[row][col]["N"]:
                    return False
                row += step_y
                if not self._in_bounds(col, row):
                    return False
                t_max_y += t_delta_y
            else:
                if step_x > 0 and self.walls[row][col]["E"]:
                    return False
                if step_x < 0 and self.walls[row][col]["W"]:
                    return False
                if step_y > 0 and self.walls[row][col]["S"]:
                    return False
                if step_y < 0 and self.walls[row][col]["N"]:
                    return False
                col += step_x
                row += step_y
                if not self._in_bounds(col, row):
                    return False
                t_max_x += t_delta_x
                t_max_y += t_delta_y

        return True

    def world_to_cell(self, x: float, y: float) -> Tuple[int, int]:
        local_x = x - self.origin_x
        local_y = y - self.origin_y
        col = int(local_x // self.cell_size)
        row = int(local_y // self.cell_size)
        col = max(0, min(self.cols - 1, col))
        row = max(0, min(self.rows - 1, row))
        return (col, row)

    def cell_center(self, cell: Tuple[int, int], local: bool = False) -> Tuple[float, float]:
        col, row = cell
        x = col * self.cell_size + self.cell_size * 0.5
        y = row * self.cell_size + self.cell_size * 0.5
        if local:
            return (x, y)
        return (self.origin_x + x, self.origin_y + y)

    def cell_bounds(self, cell: Tuple[int, int]) -> Tuple[float, float, float, float]:
        col, row = cell
        left = self.origin_x + col * self.cell_size
        top = self.origin_y + row * self.cell_size
        right = left + self.cell_size
        bottom = top + self.cell_size
        return (left, top, right, bottom)

    def clamp_position(self, x: float, y: float, radius: float) -> Tuple[float, float]:
        left = self.origin_x + radius
        top = self.origin_y + radius
        right = self.origin_x + self.width - radius
        bottom = self.origin_y + self.height - radius
        x = max(left, min(right, x))
        y = max(top, min(bottom, y))
        return (x, y)

    def get_rect(self) -> Tuple[int, int, int, int]:
        return (self.origin_x, self.origin_y, self.width, self.height)

    def get_bounds(self) -> Tuple[int, int, int, int]:
        left = self.origin_x
        top = self.origin_y
        right = left + self.width
        bottom = top + self.height
        return (left, top, right, bottom)
