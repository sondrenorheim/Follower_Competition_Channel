import math

try:
    import numpy as np
    from numba import njit
    NUMBA_AVAILABLE = True
except Exception:
    np = None
    njit = None
    NUMBA_AVAILABLE = False


def build_course_cache(course, padding: float):
    if not NUMBA_AVAILABLE:
        return None

    rows = int(course.rows)
    cols = int(course.cols)
    walls = np.zeros((rows, cols), dtype=np.uint8)
    for row in range(rows):
        for col in range(cols):
            cell_walls = course.walls[row][col]
            mask = 0
            if cell_walls["N"]:
                mask |= 1
            if cell_walls["S"]:
                mask |= 2
            if cell_walls["W"]:
                mask |= 4
            if cell_walls["E"]:
                mask |= 8
            walls[row, col] = mask

    dist = np.full((rows, cols), np.inf, dtype=np.float64)
    for (col, row), distance in course.distance_to_hole.items():
        if 0 <= row < rows and 0 <= col < cols:
            dist[row, col] = float(distance)

    return {
        "walls": walls,
        "dist": dist,
        "origin_x": float(course.origin_x),
        "origin_y": float(course.origin_y),
        "cell_size": float(course.cell_size),
        "cols": cols,
        "rows": rows,
        "width": float(course.width),
        "height": float(course.height),
        "padding": float(padding),
    }


if NUMBA_AVAILABLE:
    @njit(cache=True)
    def _world_to_cell(x, y, origin_x, origin_y, cell_size, cols, rows):
        local_x = x - origin_x
        local_y = y - origin_y
        col = int(local_x // cell_size)
        row = int(local_y // cell_size)
        if col < 0:
            col = 0
        elif col >= cols:
            col = cols - 1
        if row < 0:
            row = 0
        elif row >= rows:
            row = rows - 1
        return col, row

    @njit(cache=True)
    def _cell_bounds(col, row, origin_x, origin_y, cell_size):
        left = origin_x + col * cell_size
        top = origin_y + row * cell_size
        right = left + cell_size
        bottom = top + cell_size
        return left, top, right, bottom

    @njit(cache=True)
    def _clamp_position(x, y, origin_x, origin_y, width, height, radius):
        left = origin_x + radius
        top = origin_y + radius
        right = origin_x + width - radius
        bottom = origin_y + height - radius
        if x < left:
            x = left
        elif x > right:
            x = right
        if y < top:
            y = top
        elif y > bottom:
            y = bottom
        return x, y

    @njit(cache=True)
    def _should_move_x_first(x, y, dx, dy, radius,
                             origin_x, origin_y, cell_size, cols, rows, walls, padding):
        if dx == 0.0:
            return False
        if dy == 0.0:
            return True

        col, row = _world_to_cell(x, y, origin_x, origin_y, cell_size, cols, rows)
        left, top, right, bottom = _cell_bounds(col, row, origin_x, origin_y, cell_size)
        mask = walls[row, col]

        if dx > 0.0:
            x_limit = right - padding - radius if (mask & 8) else right
        else:
            x_limit = left + padding + radius if (mask & 4) else left
        if dy > 0.0:
            y_limit = bottom - padding - radius if (mask & 2) else bottom
        else:
            y_limit = top + padding + radius if (mask & 1) else top

        tx = (x_limit - x) / dx
        ty = (y_limit - y) / dy
        if tx < 0.0:
            tx = 0.0
        if ty < 0.0:
            ty = 0.0
        return tx <= ty

    @njit(cache=True)
    def _resolve_wall_collisions_sim(x, y, vx, vy,
                                     prev_x, prev_y, radius,
                                     origin_x, origin_y, cell_size, cols, rows, walls, padding):
        bounced = False
        prev_col, prev_row = _world_to_cell(prev_x, prev_y, origin_x, origin_y, cell_size, cols, rows)
        col, row = _world_to_cell(x, y, origin_x, origin_y, cell_size, cols, rows)

        if col > prev_col:
            if walls[prev_row, prev_col] & 8:
                right = origin_x + (prev_col + 1) * cell_size
                boundary = right - padding
                x = boundary - radius
                vx = -abs(vx)
                bounced = True
                col = prev_col
        elif col < prev_col:
            if walls[prev_row, prev_col] & 4:
                left = origin_x + prev_col * cell_size
                boundary = left + padding
                x = boundary + radius
                vx = abs(vx)
                bounced = True
                col = prev_col

        if row > prev_row:
            if walls[prev_row, prev_col] & 2:
                bottom = origin_y + (prev_row + 1) * cell_size
                boundary = bottom - padding
                y = boundary - radius
                vy = -abs(vy)
                bounced = True
                row = prev_row
        elif row < prev_row:
            if walls[prev_row, prev_col] & 1:
                top = origin_y + prev_row * cell_size
                boundary = top + padding
                y = boundary + radius
                vy = abs(vy)
                bounced = True
                row = prev_row

        col, row = _world_to_cell(x, y, origin_x, origin_y, cell_size, cols, rows)
        left, top, right, bottom = _cell_bounds(col, row, origin_x, origin_y, cell_size)
        mask = walls[row, col]

        if (mask & 4) and x - radius < left + padding:
            x = left + padding + radius
            vx = abs(vx)
            bounced = True
        if (mask & 8) and x + radius > right - padding:
            x = right - padding - radius
            vx = -abs(vx)
            bounced = True
        if (mask & 1) and y - radius < top + padding:
            y = top + padding + radius
            vy = abs(vy)
            bounced = True
        if (mask & 2) and y + radius > bottom - padding:
            y = bottom - padding - radius
            vy = -abs(vy)
            bounced = True

        if bounced:
            vx *= 0.9
            vy *= 0.9

        return x, y, vx, vy, bounced

    @njit(cache=True)
    def simulate_shot_score_numba(x, y, angle, power, radius,
                                  stop_speed, friction, shot_sim_steps, shot_sim_time,
                                  shot_sim_max_bounces,
                                  origin_x, origin_y, cell_size, cols, rows,
                                  width, height, padding, walls, dist):
        vx = math.cos(angle) * power
        vy = math.sin(angle) * power

        col, row = _world_to_cell(x, y, origin_x, origin_y, cell_size, cols, rows)
        best_dist = dist[row, col]
        final_dist = best_dist

        steps = shot_sim_steps
        dt = shot_sim_time / steps
        decay = friction ** (dt * 60.0)
        stop_speed_sq = stop_speed * stop_speed
        bounce_count = 0

        for _ in range(steps):
            if (vx * vx + vy * vy) <= stop_speed_sq:
                break

            prev_x = x
            prev_y = y
            dx = vx * dt
            dy = vy * dt

            if dx != 0.0 and dy != 0.0:
                if _should_move_x_first(x, y, dx, dy, radius,
                                        origin_x, origin_y, cell_size, cols, rows, walls, padding):
                    x += dx
                    x, y, vx, vy, bounced = _resolve_wall_collisions_sim(
                        x, y, vx, vy, prev_x, prev_y, radius,
                        origin_x, origin_y, cell_size, cols, rows, walls, padding
                    )
                    prev_x = x
                    prev_y = y
                    y += dy
                    x, y, vx, vy, bounced2 = _resolve_wall_collisions_sim(
                        x, y, vx, vy, prev_x, prev_y, radius,
                        origin_x, origin_y, cell_size, cols, rows, walls, padding
                    )
                    bounced = bounced or bounced2
                else:
                    y += dy
                    x, y, vx, vy, bounced = _resolve_wall_collisions_sim(
                        x, y, vx, vy, prev_x, prev_y, radius,
                        origin_x, origin_y, cell_size, cols, rows, walls, padding
                    )
                    prev_x = x
                    prev_y = y
                    x += dx
                    x, y, vx, vy, bounced2 = _resolve_wall_collisions_sim(
                        x, y, vx, vy, prev_x, prev_y, radius,
                        origin_x, origin_y, cell_size, cols, rows, walls, padding
                    )
                    bounced = bounced or bounced2
            else:
                x += dx
                y += dy
                x, y, vx, vy, bounced = _resolve_wall_collisions_sim(
                    x, y, vx, vy, prev_x, prev_y, radius,
                    origin_x, origin_y, cell_size, cols, rows, walls, padding
                )

            if bounced:
                bounce_count += 1
                if shot_sim_max_bounces > 0 and bounce_count >= shot_sim_max_bounces:
                    x, y = _clamp_position(x, y, origin_x, origin_y, width, height, radius)
                    col, row = _world_to_cell(x, y, origin_x, origin_y, cell_size, cols, rows)
                    final_dist = dist[row, col]
                    if final_dist < best_dist:
                        best_dist = final_dist
                    break

            x, y = _clamp_position(x, y, origin_x, origin_y, width, height, radius)
            vx *= decay
            vy *= decay

            col, row = _world_to_cell(x, y, origin_x, origin_y, cell_size, cols, rows)
            final_dist = dist[row, col]
            if final_dist < best_dist:
                best_dist = final_dist

        return best_dist, final_dist

else:
    def simulate_shot_score_numba(*_args, **_kwargs):
        raise RuntimeError("Numba is not available")
