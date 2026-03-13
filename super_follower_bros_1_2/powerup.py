from dataclasses import dataclass


@dataclass
class SuperFollowerBrosPowerup:
    kind: str
    x: float
    y: float
    spawn_time: float
    block_index: int
    state: str = "reveal"
    block_top: float = 0.0
    block_height: float = 0.0
    expires_at: float | None = None
    vx: float = 0.0
    vy: float = 0.0
