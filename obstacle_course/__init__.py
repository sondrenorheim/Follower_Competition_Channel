"""
Obstacle Course game module
"""

from .racer import Racer
from .course import ObstacleCourse
from .obstacles import StaticWall, MovingWall, Spinner, SpeedBoost, SlowZone, Bumper, Crusher
from .generator import CourseGenerator
from .camera import ObstacleCourseCamera
from .renderer import ObstacleCourseRenderer
from .game import ObstacleCourseGame

__all__ = [
    'Racer',
    'ObstacleCourse',
    'StaticWall',
    'MovingWall',
    'Spinner',
    'SpeedBoost',
    'SlowZone',
    'Bumper',
    'Crusher',
    'CourseGenerator',
    'ObstacleCourseCamera',
    'ObstacleCourseRenderer',
    'ObstacleCourseGame',
]
