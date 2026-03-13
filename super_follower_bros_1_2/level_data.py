LEVEL_HEIGHT = 600
LEVEL_WIDTH = 8256
GROUND_Y = 514
# World 1-2 goal anchor aligned with the horizontal goal pipe section.
FLAG_X = 7240

# The 1-2 map art is the source of truth for static geometry.
SOURCE_TILEMAP_PATH = "assets/super_follower_bros_1_2/level_2.png"
SOURCE_MAP_WIDTH = 3072
SOURCE_MAP_HEIGHT = 224
SOURCE_TILE_SIZE = 16
SOURCE_SOLID_PIXEL_THRESHOLD = 120
SOURCE_NON_BLACK_THRESHOLD = 24

# Legacy rect groups are intentionally empty. Static colliders are generated
# from SOURCE_TILEMAP_PATH in level.py.
GROUND_RECTS = []
PIPE_RECTS = []
STEP_RECTS = []

BRICK_SIZE = 43
BRICK_TILE_POSITIONS = []
BRICK_CONTENTS = {}

# Question blocks from the 1-2 tilemap (top-left tile coordinates).
COIN_BOX_TILE_POSITIONS = [
    (10, 8),
    (11, 8),
    (12, 8),
    (13, 8),
    (14, 8),
]
COIN_BOX_CONTENTS = {}

ENEMY_GROUPS = [
    {"checkpoint": 500, "count": 2, "kind": "goomba"},
    {"checkpoint": 1100, "count": 1, "kind": "goomba"},
    {"checkpoint": 1600, "count": 1, "kind": "koopa"},
    {"checkpoint": 2100, "count": 2, "kind": "goomba"},
    {"checkpoint": 2600, "count": 1, "kind": "goomba"},
    {"checkpoint": 3200, "count": 2, "kind": "goomba"},
    {"checkpoint": 3800, "count": 1, "kind": "koopa"},
    {"checkpoint": 4400, "count": 2, "kind": "goomba"},
    {"checkpoint": 5100, "count": 2, "kind": "goomba"},
    {"checkpoint": 5800, "count": 1, "kind": "koopa"},
    {"checkpoint": 6500, "count": 2, "kind": "goomba"},
    {"checkpoint": 7200, "count": 2, "kind": "goomba"},
]

# Vertical moving platforms from remastered world 1-2.
# These coordinates are already converted to design-space pixels.
MOVING_PLATFORMS = [
    # Lift columns centered on the two 1-2 pit lanes in the large cavern gap.
    {"x": 6085, "y_min": -80, "y_max": 560, "start_y": 257, "width": 129, "height": 21, "speed": 134.0, "dir": 1.0},
    {"x": 6085, "y_min": -80, "y_max": 560, "start_y": 514, "width": 129, "height": 21, "speed": 134.0, "dir": 1.0},
    {"x": 6730, "y_min": -80, "y_max": 560, "start_y": 150, "width": 129, "height": 21, "speed": 134.0, "dir": -1.0},
    {"x": 6730, "y_min": -80, "y_max": 560, "start_y": 493, "width": 129, "height": 21, "speed": 134.0, "dir": -1.0},
]
