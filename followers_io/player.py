import math
import random
import time

import config


class IOFollower:
    __slots__ = (
        "id",
        "username",
        "avatar_image",
        "color",
        "x",
        "y",
        "vx",
        "vy",
        "mass",
        "radius",
        "alive",
        "elimination_time",
        "elimination_step",
        "survival_time",
        "placement",
        "alpha",
        "is_club_member",
        "kills",
        "consumed_mass",
        "split_boost_end",
        "last_split_time",
        "next_turn_time",
        "render_hash",
        "mass_at_elimination",
    )

    def __init__(self, follower_data: dict, position: tuple[float, float], mass: float, radius_scale: float):
        self.id = follower_data.get("id")
        self.username = follower_data.get("username", "unknown")
        self.avatar_image = follower_data.get("avatar_image")
        self.color = follower_data.get("color", random.choice(config.RANDOM_COLORS))

        self.x = float(position[0])
        self.y = float(position[1])

        angle = random.random() * math.tau
        self.vx = math.cos(angle) * 1.0
        self.vy = math.sin(angle) * 1.0

        self.mass = float(mass)
        self.radius = 1.0
        self.update_radius(radius_scale)

        self.alive = True
        self.elimination_time = 0.0
        self.elimination_step = None
        self.survival_time = 0.0
        self.placement = 0
        self.alpha = 255

        self.is_club_member = False
        self.kills = 0
        self.consumed_mass = 0.0
        self.split_boost_end = 0.0
        self.last_split_time = -9999.0
        self.next_turn_time = 0.0
        self.render_hash = hash((self.id, self.username)) & 0xFFFFFFFF
        self.mass_at_elimination = 0.0

    def update_radius(self, radius_scale: float):
        self.radius = max(1.2, math.sqrt(max(0.0, self.mass)) * radius_scale)

    def apply_mass_decay(self, dt: float, decay_rate: float, min_mass: float, radius_scale: float):
        if self.mass <= min_mass or decay_rate <= 0.0:
            return
        decay_factor = max(0.0, 1.0 - decay_rate * dt)
        self.mass = max(min_mass, self.mass * decay_factor)
        self.update_radius(radius_scale)

    def gain_mass(self, amount: float, radius_scale: float):
        if amount <= 0.0:
            return
        self.mass += amount
        self.update_radius(radius_scale)

    def lose_mass(self, amount: float, min_mass: float, radius_scale: float):
        if amount <= 0.0:
            return
        self.mass = max(min_mass, self.mass - amount)
        self.update_radius(radius_scale)

    def mark_eliminated(self, step: int, game_time: float):
        if not self.alive:
            return
        self.alive = False
        self.elimination_step = step
        self.survival_time = game_time
        self.mass_at_elimination = self.mass
        self.elimination_time = time.time()
        self.alpha = 255

    def is_fading(self, fade_duration: float) -> bool:
        if self.alive:
            return False
        return (time.time() - self.elimination_time) < fade_duration

    def update_fade(self, fade_duration: float):
        if self.alive:
            self.alpha = 255
            return
        elapsed = time.time() - self.elimination_time
        if elapsed >= fade_duration:
            self.alpha = 0
        else:
            progress = max(0.0, min(1.0, elapsed / max(1e-6, fade_duration)))
            self.alpha = int(255 * (1.0 - progress))

    def can_split(self, game_time: float, min_mass: float, cooldown: float) -> bool:
        if not self.alive or self.mass < min_mass:
            return False
        return (game_time - self.last_split_time) >= cooldown

    def trigger_split_dash(self, game_time: float, boost_duration: float, mass_cost_ratio: float, min_mass: float, radius_scale: float):
        if not self.alive:
            return
        self.last_split_time = game_time
        self.split_boost_end = game_time + boost_duration
        loss = self.mass * max(0.0, min(0.95, mass_cost_ratio))
        self.lose_mass(loss, min_mass=min_mass, radius_scale=radius_scale)
