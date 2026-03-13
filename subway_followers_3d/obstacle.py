from dataclasses import dataclass


@dataclass
class SubwayObstacle3D:
    node: object
    kind: str
    lane_index: int
    lane_span: int
    width: float
    length: float
    height: float
    required_action: str
    speed_multiplier: float

    def update(self, dt: float, speed: float):
        self.node.setY(self.node.getY() - speed * self.speed_multiplier * dt)

    def y(self) -> float:
        return self.node.getY()

    def x(self) -> float:
        return self.node.getX()
