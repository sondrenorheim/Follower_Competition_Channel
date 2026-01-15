import random
from collections import deque
from typing import Dict, List, Tuple

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


class Maze:
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

        maze_width = cols * cell_size
        maze_height = rows * cell_size
        self.origin_x = arena_x + (arena_w - maze_width) // 2
        self.origin_y = arena_y + (arena_h - maze_height) // 2
        self.width = maze_width
        self.height = maze_height

        if start_cell is None:
            start_cell = (0, rows - 1)
        self.start_cell = (max(0, min(cols - 1, start_cell[0])),
                           max(0, min(rows - 1, start_cell[1])))

        self._init_walls()
        self._generate_maze()
        self.neighbor_map = self._build_neighbor_map()
        self.distance_from_start = self._compute_distances(self.start_cell)
        self.exit_cell = self._choose_exit_cell()
        self.distance_to_exit = self._compute_distances(self.exit_cell)
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

    def _choose_exit_cell(self) -> Tuple[int, int]:
        if not self.distance_from_start:
            return self.start_cell

        max_distance = max(self.distance_from_start.values())
        candidates = [
            cell for cell, dist in self.distance_from_start.items()
            if dist == max_distance
        ]
        return self.rng.choice(candidates) if candidates else self.start_cell

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

    def cell_center(self, cell: Tuple[int, int], local: bool = False) -> Tuple[float, float]:
        col, row = cell
        x = col * self.cell_size + self.cell_size * 0.5
        y = row * self.cell_size + self.cell_size * 0.5
        if local:
            return (x, y)
        return (self.origin_x + x, self.origin_y + y)

    def get_bounds(self) -> Tuple[int, int, int, int]:
        left = self.origin_x
        top = self.origin_y
        right = left + self.width
        bottom = top + self.height
        return (left, top, right, bottom)

    def get_rect(self) -> Tuple[int, int, int, int]:
        return (self.origin_x, self.origin_y, self.width, self.height)
