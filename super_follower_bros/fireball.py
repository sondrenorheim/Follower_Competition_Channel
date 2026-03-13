from dataclasses import dataclass


@dataclass
class SuperFollowerBrosFireball:
    x: float
    y: float
    vx: float
    vy: float
    spawn_time: float
    expires_at: float | None = None
