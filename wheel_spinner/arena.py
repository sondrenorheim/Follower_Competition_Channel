"""
Wheel Spinner arena.
"""

import config
from shared import ArenaTemplate, ArenaShape


class WheelSpinnerArena(ArenaTemplate):
    WIDTH = int(getattr(config, "WHEEL_SPINNER_ARENA_WIDTH", 500))
    HEIGHT = int(getattr(config, "WHEEL_SPINNER_ARENA_HEIGHT", 700))
    SHAPE = ArenaShape.RECTANGLE
    SHRINKS = False
