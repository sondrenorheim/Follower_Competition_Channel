"""
Configuration file for Follower Battle Royale
Modify these values to customize game behavior
"""

# ===== GAME SETTINGS =====
SCREEN_WIDTH = 1080
SCREEN_HEIGHT = 1080
FPS = 60

# ===== ARENA SETTINGS =====
ARENA_CENTER = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
ARENA_INITIAL_RADIUS = 500  # Starting safe zone radius
ARENA_MIN_RADIUS = 100      # Minimum safe zone radius before game ends
SHRINK_INTERVAL = 3.0       # Seconds between each shrink
SHRINK_PERCENTAGE = 0.02    # 2% shrink per interval

# ===== FOLLOWER SETTINGS =====
FOLLOWER_COUNT = 500        # Number of followers (can be 500-1000)
FOLLOWER_RADIUS = 32        # Radius of each follower circle
FOLLOWER_BORDER_WIDTH = 3   # White border thickness
FOLLOWER_NAME_FONT_SIZE = 12

# ===== PHYSICS SETTINGS =====
BASE_SPEED = 2.0            # Base movement speed (pixels per frame)
FRICTION = 0.95             # Friction multiplier (lower = more friction)
PUSH_FORCE = 5.0            # Force applied during collisions
BUMP_COOLDOWN = 0.5         # Cooldown between bumps (seconds)
COLLISION_DISTANCE = FOLLOWER_RADIUS * 2  # Distance for collision detection
MOVEMENT_RANDOMNESS = 0.3   # Randomness factor for natural movement (0-1)

# ===== ELIMINATION SETTINGS =====
FADE_DURATION = 0.5         # Duration of elimination fade animation (seconds)
TOP_SURVIVORS_COUNT = 10    # When to show "Top 10 Survivors" marquee

# ===== UI SETTINGS =====
SCOREBOARD_WIDTH = 250
SCOREBOARD_X = SCREEN_WIDTH - SCOREBOARD_WIDTH - 20
SCOREBOARD_Y = 20
SCOREBOARD_FONT_SIZE = 24
SCOREBOARD_BG_COLOR = (0, 0, 0, 180)  # Semi-transparent black

# ===== COLORS =====
COLOR_BACKGROUND = (20, 20, 30)
COLOR_ARENA = (40, 40, 50)
COLOR_SAFE_ZONE = (50, 150, 50)
COLOR_DANGER_ZONE = (200, 50, 50)
COLOR_TEXT = (255, 255, 255)
COLOR_BORDER = (255, 255, 255)

# ===== VIDEO EXPORT SETTINGS =====
EXPORT_VIDEO = True
OUTPUT_VIDEO_PATH = "follower_battle_royale.mp4"
VIDEO_CODEC = "libx264"
VIDEO_FPS = 30  # Export FPS (can be lower than game FPS for smaller file)

# ===== INSTAGRAM API SETTINGS =====
# Set these values if you have Instagram Graph API access
# Leave empty to run in offline mode with random colored avatars
INSTAGRAM_ACCESS_TOKEN = ""  # Your Instagram Graph API access token
INSTAGRAM_USER_ID = ""       # Your Instagram user ID
USE_OFFLINE_MODE = True      # Set to False to attempt API fetching

# ===== RANDOM AVATAR COLORS (for offline mode) =====
RANDOM_COLORS = [
    (255, 100, 100), (100, 255, 100), (100, 100, 255),
    (255, 255, 100), (255, 100, 255), (100, 255, 255),
    (255, 150, 100), (150, 255, 100), (100, 150, 255),
    (255, 100, 150), (100, 255, 150), (150, 100, 255),
]
