import math
import random

from panda3d.core import CardMaker, Texture, TransparencyAttrib

try:
    from PIL import Image, ImageDraw
except Exception:  # pragma: no cover - optional dependency
    Image = None
    ImageDraw = None


class SubwayRunner3D:
    def __init__(self, follower_data: dict, render, track, config, index: int, y_offset: float):
        self.config = config
        self.username = follower_data.get("username", f"runner_{index}")
        avatar = follower_data.get("avatar_image") or follower_data.get("avatar")

        self.skill = random.uniform(0.55, 1.0)
        self.miss_chance = (1.0 - self.skill) * 0.35

        self.alive = True
        self.placement = None
        self.elimination_time = None
        self.survival_time = 0.0

        self.lane_index = random.randint(0, track.lane_count - 1)
        self.target_lane = self.lane_index
        self.x = track.lane_center(self.lane_index)
        self.y = y_offset
        self.z = 0.0

        self.base_y = y_offset

        self.state = "run"
        self.jump_velocity = 0.0
        self.roll_timer = 0.0
        self.lane_change_cooldown = 0.0
        self.decision_timer = 0.0
        self.decision_interval = random.uniform(0.25, 0.6)

        self.radius = float(getattr(config, "SUBWAY_3D_RUNNER_RADIUS", 0.35))
        self.depth = float(getattr(config, "SUBWAY_3D_RUNNER_DEPTH", 0.5))
        self.height = float(getattr(config, "SUBWAY_3D_RUNNER_HEIGHT", 1.5))
        self.jump_height = float(getattr(config, "SUBWAY_3D_JUMP_HEIGHT", 1.6))
        self.jump_gravity = float(getattr(config, "SUBWAY_3D_JUMP_GRAVITY", 9.2))
        self.roll_duration = float(getattr(config, "SUBWAY_3D_ROLL_DURATION", 0.6))
        self.roll_height = float(getattr(config, "SUBWAY_3D_ROLL_HEIGHT", 0.7))

        self.lane_change_speed = float(getattr(config, "SUBWAY_3D_LANE_CHANGE_SPEED", 6.0))

        self.node = self._build_avatar(render, avatar)
        self._apply_transform()

    def _build_avatar(self, render, avatar):
        size = float(getattr(self.config, "SUBWAY_3D_AVATAR_SIZE", 1.1))
        card = CardMaker("runner_card")
        card.setFrame(-size * 0.5, size * 0.5, 0, size)
        node = render.attachNewNode(card.generate())
        node.setBillboardPointEye()
        node.setTransparency(TransparencyAttrib.MAlpha)
        if avatar is not None:
            tex = self._texture_from_avatar(avatar)
            if tex:
                node.setTexture(tex, 1)
                return node

        color = random.choice(getattr(self.config, "RANDOM_COLORS", [(200, 200, 200)]))
        tex = self._color_circle_texture(color)
        if tex:
            node.setTexture(tex, 1)
        else:
            if max(color) > 1.0:
                color = (color[0] / 255.0, color[1] / 255.0, color[2] / 255.0)
            node.setColor(color[0], color[1], color[2], 1.0)
        return node

    @staticmethod
    def _texture_from_avatar(avatar):
        try:
            pil = avatar.convert("RGBA")
            pil = SubwayRunner3D._apply_circle_mask(pil)
            width, height = pil.size
            tex = Texture()
            tex.setup2dTexture(width, height, Texture.T_unsigned_byte, Texture.F_rgba)
            tex.setRamImage(pil.tobytes())
            return tex
        except Exception:
            return None

    @staticmethod
    def _apply_circle_mask(pil):
        if Image is None or ImageDraw is None:
            return pil
        size = min(pil.size)
        if pil.size[0] != pil.size[1]:
            left = (pil.size[0] - size) // 2
            top = (pil.size[1] - size) // 2
            pil = pil.crop((left, top, left + size, top + size))
        if size != 256:
            pil = pil.resize((256, 256), Image.LANCZOS)
        mask = Image.new("L", pil.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, pil.size[0] - 1, pil.size[1] - 1), fill=255)
        pil.putalpha(mask)
        return pil

    @staticmethod
    def _color_circle_texture(color, size=128):
        if Image is None or ImageDraw is None:
            return None
        if max(color) <= 1.0:
            rgb = (int(color[0] * 255), int(color[1] * 255), int(color[2] * 255))
        else:
            rgb = (int(color[0]), int(color[1]), int(color[2]))
        pil = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(pil)
        draw.ellipse((0, 0, size - 1, size - 1), fill=(rgb[0], rgb[1], rgb[2], 255))
        tex = Texture()
        tex.setup2dTexture(size, size, Texture.T_unsigned_byte, Texture.F_rgba)
        tex.setRamImage(pil.tobytes())
        return tex

    def update(self, dt: float, track, obstacles: list, current_time: float):
        if not self.alive:
            return

        self.decision_timer += dt
        if self.lane_change_cooldown > 0:
            self.lane_change_cooldown = max(0.0, self.lane_change_cooldown - dt)

        self._update_state(dt)

        if self.decision_timer >= self.decision_interval:
            self._decide(obstacles, track)
            self.decision_timer = 0.0
            self.decision_interval = random.uniform(0.25, 0.6)

        self._update_lane_position(track, dt)
        self._apply_transform()

        self.survival_time = current_time

    def _update_state(self, dt: float):
        if self.state == "jump":
            self.jump_velocity -= self.jump_gravity * dt
            self.z += self.jump_velocity * dt
            if self.z <= 0.0:
                self.z = 0.0
                self.state = "run"
        elif self.state == "roll":
            self.roll_timer -= dt
            if self.roll_timer <= 0:
                self.state = "run"

    def _decide(self, obstacles: list, track):
        target = self._find_next_obstacle(obstacles, track)
        if not target:
            self._maybe_shuffle_lane(track)
            return

        if random.random() < self.miss_chance:
            return

        action = target.required_action
        if action == "jump":
            self.jump()
        elif action == "roll":
            self.roll()
        else:
            self._evade_lane(target, track, obstacles)

    def _find_next_obstacle(self, obstacles: list, track):
        best = None
        best_dist = None
        for obstacle in obstacles:
            if not self._lanes_overlap(self.lane_index, 1, obstacle.lane_index, obstacle.lane_span):
                continue
            if obstacle.y() <= self.y:
                continue
            dist = obstacle.y() - self.y
            if dist > float(getattr(self.config, "SUBWAY_3D_REACTION_DISTANCE", 12.0)):
                continue
            if best_dist is None or dist < best_dist:
                best = obstacle
                best_dist = dist
        return best

    def _maybe_shuffle_lane(self, track):
        if self.lane_change_cooldown > 0:
            return
        if random.random() < 0.08:
            self.target_lane = random.randint(0, track.lane_count - 1)
            self.lane_change_cooldown = float(getattr(self.config, "SUBWAY_3D_LANE_CHANGE_COOLDOWN", 0.35))

    def _lane_clearance(self, lane_index, obstacles):
        nearest = None
        for obstacle in obstacles:
            if not self._lanes_overlap(lane_index, 1, obstacle.lane_index, obstacle.lane_span):
                continue
            if obstacle.y() <= self.y:
                continue
            dist = obstacle.y() - self.y
            if nearest is None or dist < nearest:
                nearest = dist
        return float("inf") if nearest is None else nearest

    def _evade_lane(self, obstacle, track, obstacles):
        best_lane = self.lane_index
        best_clearance = -1.0
        for lane in range(track.lane_count):
            clearance = self._lane_clearance(lane, obstacles)
            if clearance > best_clearance:
                best_clearance = clearance
                best_lane = lane

        if best_lane != self.lane_index and self.lane_change_cooldown <= 0:
            self.target_lane = best_lane
            self.lane_change_cooldown = float(getattr(self.config, "SUBWAY_3D_LANE_CHANGE_COOLDOWN", 0.35))

    def _update_lane_position(self, track, dt: float):
        target_x = track.lane_center(self.target_lane)
        dx = target_x - self.x
        max_step = self.lane_change_speed * dt
        if abs(dx) <= max_step:
            self.x = target_x
        else:
            self.x += max_step if dx > 0 else -max_step

    def _apply_transform(self):
        height = self.height
        if self.state == "roll":
            height = self.roll_height
        self.node.setScale(1.0, 1.0, height / max(self.height, 0.1))
        self.node.setPos(self.x, self.y, self.z)

    def jump(self):
        if self.state == "run":
            self.state = "jump"
            self.jump_velocity = math.sqrt(2 * self.jump_gravity * self.jump_height)

    def roll(self):
        if self.state == "run":
            self.state = "roll"
            self.roll_timer = self.roll_duration

    def hit(self, current_time: float):
        if not self.alive:
            return
        self.alive = False
        self.elimination_time = current_time
        self.survival_time = current_time

    def collider_height(self) -> float:
        return self.roll_height if self.state == "roll" else self.height

    @staticmethod
    def _lanes_overlap(start_a: int, span_a: int, start_b: int, span_b: int) -> bool:
        end_a = start_a + max(1, span_a) - 1
        end_b = start_b + max(1, span_b) - 1
        return not (end_a < start_b or end_b < start_a)
