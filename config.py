"""
Configuration file for Follower Battle Royale & Fighter Arena
Modify these values to customize game behavior
"""
from pathlib import Path

# ===== GAME MODE =====
# Options: "battle_royale", "fighter_arena", "obstacle_course",
#          "snake_escape", "team_battle", "platformer_race", "spleef", "ALL"
# When set to "ALL", games will run in the order defined by ALL_GAME_MODES.
# ALL_GAME_MODES = ["obstacle_course", "team_battle", "platformer_race"]
# ALL_GAME_MODES = [ "snake_escape", "team_battle", "platformer_race"]

# ===== GAME SETTINGS =====
SCREEN_WIDTH = 540   # Scaled down for better visibility on monitors
SCREEN_HEIGHT = 960  # 9:16 aspect ratio for Instagram Reels / TikTok
FPS = 60
# Set to True to run without display window (faster processing, videos still export)

# Performance optimization: Lower FPS during video export for better performance
# Since video is only 30 FPS, running simulation at 60 FPS wastes CPU
SIMULATION_FPS_DURING_EXPORT = 30  # FPS during video export (should match VIDEO_FPS)

# Time scaling during video export - slows down simulation to give more processing time
# 1.0 = normal speed, 0.5 = half speed (2x more time per frame), 0.25 = quarter speed (4x more time)

# Maximum delta time cap - prevents huge jumps when system lags
MAX_DELTA_TIME = 1.0 / 20.0  # Cap dt at 50ms (20 FPS minimum) to prevent chaos


ALL_GAME_MODES = ["battle_royale", "fighter_arena", "obstacle_course", "snake_escape", "platformer_race","gorillas_vs_followers", "team_battle"]

# Test mode - when True, game results won't be saved to the all-time leaderboard
GAME_MODE = "ALL" # Options: "battle_royale", "fighter_arena", "obstacle_course", "snake_escape", "team_battle", "platformer_race", "ALL"
TEST_MODE = False
EXPORT_VIDEO = True
DAY_NUMBER = 29  # Increment this each time you record a new video

# Profile picture settings:
# - DOWNLOAD_PROFILE_PICTURES: Legacy flag for downloading during game run (slow, not recommended)
# - LOAD_PROFILE_PICTURES: Load profile pictures from avatar_cache/ (fast, recommended)
#
# Recommended workflow:
#   1. Run download_all_profile_pics.py once to cache all profile pictures
#   2. Set LOAD_PROFILE_PICTURES = True to use cached images
#   3. Games will load instantly from disk cache
DOWNLOAD_PROFILE_PICTURES = True  # Deprecated - use download_all_profile_pics.py instead
LOAD_PROFILE_PICTURES = True  # Set to True to load from avatar_cache/, False to skip entirely (faster testing)
HEADLESS_MODE = False
SHOW_NAMETAGS = True

# Minimal test players - when True, use generated test users instead of real followers
TEST_MINIMAL_PLAYERS = False  # Set True to use test users, False to use real followers
TEST_MINIMAL_PLAYER_COUNT = 100  # Number of test users to generate (minimum 100-200 recommended for Battle Royale)
# Control whether stats auto-push after each game (set False to review then push manually)
AUTO_PUSH_STATS = False
# Control whether video files are included in auto-push (set False to only push stats data)
AUTO_PUSH_INCLUDE_VIDEOS = False
TEST_MODE_SPEED_MULTIPLIER = 1  # Speed multiplier when TEST_MODE is True (0.5 = half speed, 1.0 = normal)
 # Increment this each time you record a new video
UPSCALE_VIDEO = True  # Enable upscaling for higher quality video output
UPSCALE_FACTOR = 2.0 
EXPORT_TIME_SCALE = 1  # Run simulation at half speed during export for smoother results

# ===== ARENA SETTINGS =====
ARENA_CENTER = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
ARENA_INITIAL_RADIUS = 250  # Starting safe zone radius (scaled to match screen size)
ARENA_MIN_RADIUS = 50       # Minimum safe zone radius before game ends
SHRINK_RATE = 0.10          # Pixels per second the zone shrinks (smooth continuous shrinking)
                            # Lower = slower shrink, Higher = faster shrink
                            # Recommended: 0.15-0.3 for slower games, 0.5-1.0 for fast-paced

ARENA_SHAPE = "circle"

# ===== FOLLOWER SETTINGS =====
# Set to an integer to cap followers, or None to use all available from data/API.
FOLLOWER_COUNT = None
FOLLOWER_RADIUS = 14        # Radius of each follower circle (will be dynamically adjusted)
FOLLOWER_BORDER_WIDTH = 2   # White border thickness
FOLLOWER_NAME_FONT_SIZE = 12  # Nametag font size for follower usernames
SHOW_FOLLOWER_NAMES = False  # Show usernames below profile pictures during battle

# Profile picture rendering optimization
# Only render profile pictures when radius is large enough to actually see them
# When smaller, use colored circles instead (saves massive rendering overhead with 40k players)
PROFILE_PICTURE_MIN_RADIUS = 8  # Pixels - only render profile pics when radius >= this value

# ===== NAMETAG DISPLAY SETTINGS =====
# Master toggle for nametag display across all games

# Username truncation (uniform across all games)
NAMETAG_MAX_USERNAME_LENGTH = 12  # Characters to display before truncation

# Scaling games - size-based thresholds (show nametags when players are large enough)
NAMETAG_MIN_RADIUS_BATTLE_ROYALE = 8  # Pixels - show when follower radius >= this value
NAMETAG_MIN_RADIUS_SNAKE_ESCAPE = 12   # Pixels - show when follower radius >= this value

# Scaling games - count-based thresholds (show nametags when player count is low enough)
NAMETAG_MAX_ALIVE_FIGHTER_ARENA = 250  # Show nametags when alive fighters <= this count
NAMETAG_MAX_ALIVE_TEAM_BATTLE = 250     # Show nametags when alive fighters <= this count

# Nametag styling
NAMETAG_FONT_SIZE = 20                    # Font size for nametag text
NAMETAG_TEXT_COLOR = (255, 255, 255)      # White text
NAMETAG_OUTLINE_COLOR = (0, 0, 0)         # Black outline
NAMETAG_OUTLINE_WIDTH = 1                 # Outline thickness in pixels
NAMETAG_VERTICAL_OFFSET = 8               # Pixels below avatar center

# ===== DYNAMIC SCALING SETTINGS =====
USE_DYNAMIC_SCALING = True  # Enable dynamic follower size based on player count
FOLLOWER_BASE_RADIUS = 12   # Base radius for ~100 final contestants (good size)
FOLLOWER_MIN_RADIUS = 1     # No enforced minimum; allows very dense packing
FOLLOWER_MAX_RADIUS = 18    # Maximum radius when only a few players remain
SCALING_GROWTH_RATE = 0.5   # How quickly players grow as others are eliminated (0.0-1.0)

# ===== PERFORMANCE OPTIMIZATION SETTINGS =====
# These settings help Battle Royale handle 100,000+ players
USE_NUMBA_PHYSICS = True            # Use Numba JIT compilation for 10-50x faster physics (requires: pip install numba)
ENABLE_VIEW_FRUSTUM_CULLING = True  # Only render on-screen players (huge performance gain)
ENABLE_UPDATE_THROTTLING = True     # Stagger player updates across frames (for >5000 players)
UPDATE_BATCHES_PER_FRAME = 4        # Divide players into N batches (higher = more batches = smoother but slower updates)
SPATIAL_GRID_CELL_SIZE = None       # Auto-calculated based on FOLLOWER_RADIUS * 4 (None = auto)
DISABLE_PARTICLES_THRESHOLD = 20000  # Disable particle effects when player count exceeds this (0 = never disable)

# Performance monitoring/logging
PERFORMANCE_LOG_INTERVAL = 2.0       # How often to print performance stats (in seconds)
PERFORMANCE_DETAILED_LOGGING = True  # Show detailed metrics (collision checks, culling, etc.)

# ===== PHYSICS SETTINGS =====
BASE_SPEED = 2.5            # Base movement speed (pixels per frame) - reduced for slower pace
FRICTION = 0.85             # Friction multiplier (lower = more friction)
PUSH_FORCE = 6.0            # Force applied during collisions
BUMP_COOLDOWN = 0.5         # Cooldown between bumps (seconds) - reduced for more frequent collisions
COLLISION_DISTANCE = FOLLOWER_RADIUS * 2  # Distance for collision detection
MOVEMENT_RANDOMNESS = 0.1   # Randomness factor for natural movement (0-1)

# ===== ELIMINATION SETTINGS =====
FADE_DURATION = 0.5         # Duration of elimination fade animation (seconds)
TOP_SURVIVORS_COUNT = 10    # When to show "Top 10 Survivors" marquee

# ===== UI SETTINGS =====
SCOREBOARD_WIDTH = SCREEN_WIDTH - 40  # Full width with 20px padding on each side
SCOREBOARD_X = 20  # Left padding
SCOREBOARD_Y = SCREEN_HEIGHT - 160  # Positioned near bottom of screen
SCOREBOARD_FONT_SIZE = 28  # Increased from 24 for better readability
SCOREBOARD_BG_COLOR = (0, 0, 0, 180)  # Semi-transparent black

# ===== COLORS =====
COLOR_BACKGROUND = (201, 198, 201)     # Light gray (#c9c6c9)
COLOR_ARENA = (201, 198, 201)          # Same as background
COLOR_SAFE_ZONE = (201, 198, 201)      # Same as background (no border)
COLOR_DANGER_ZONE = (255, 20, 20)      # Sharp red
COLOR_TEXT = (0, 0, 0)                 # Black text
COLOR_BORDER = (0, 0, 0)  # Black outline for fighters


VIDEO_OUTPUT_BASE = Path("Videos")

def get_output_video_path(game_mode: str = None, day_number: int = None, test_mode: bool = None) -> str:
    """
    Build output video filename based on game mode, day number, and test flag.
    Example: team_battle_day_10.mp4 or snake_escape_test_video.mp4
    """
    gm = (game_mode or GAME_MODE) if (game_mode or GAME_MODE) else "battle_royale"
    day = day_number if day_number is not None else DAY_NUMBER
    is_test = TEST_MODE if test_mode is None else test_mode
    # Organize by day folder: VIDEO_OUTPUT_BASE/Day_<N>/filename.mp4
    day_folder = VIDEO_OUTPUT_BASE / f"Day_{day}"
    day_folder.mkdir(parents=True, exist_ok=True)
    if is_test:
        return str(day_folder / f"{gm}_test_video.mp4")
    return str(day_folder / f"{gm}_day_{day}.mp4")

OUTPUT_VIDEO_PATH = get_output_video_path()

VIDEO_CODEC = "libx264"
VIDEO_FPS = 30  # Export FPS (can be lower than game FPS for smaller file)


FOLLOWER_IMPORT_FILE = "Followers/all_followers_fresh.json"

# TikTok followers import file (optional - will be combined with Instagram followers)
TIKTOK_IMPORT_FILE = ""  # Disabled - only using Instagram followers


INSTAGRAM_ACCESS_TOKEN = ""  # Your Instagram Graph API access token
INSTAGRAM_USER_ID = ""       # Your Instagram user ID


USE_INSTALOADER_SCRAPER = False  # Set to True to enable web scraping
INSTAGRAM_USERNAME = ""          # Your Instagram username (for scraping)
INSTAGRAM_PASSWORD = ""          # Your Instagram password (for scraping)
INSTAGRAM_TARGET_USERNAME = ""   # Target account to scrape followers from (leave empty to use your own)

USE_OFFLINE_MODE = False      # Set to False to attempt API/scraper fetching (or use import file)

RANDOM_COLORS = [
    (255, 100, 100), (100, 255, 100), (100, 100, 255),
    (255, 255, 100), (255, 100, 255), (100, 255, 255),
    (255, 150, 100), (150, 255, 100), (100, 150, 255),
    (255, 100, 150), (100, 255, 150), (150, 100, 255),
]


def calculate_dynamic_follower_radius(total_players, alive_count, safe_zone_radius, initial_zone_radius):
    """
    Calculate dynamic follower radius based on player count and game progression

    Args:
        total_players: Total number of players at game start
        alive_count: Current number of alive players
        safe_zone_radius: Current safe zone radius
        initial_zone_radius: Initial safe zone radius at game start

    Returns:
        float: Calculated follower radius
    """
    import math

    if not USE_DYNAMIC_SCALING:
        return FOLLOWER_BASE_RADIUS

    # Step 1: Calculate starting radius based on total player count
    # For 100 players: use base radius (12px)
    # For more players: scale down proportionally
    # For fewer players: can start slightly larger
    if total_players <= 100:
        start_radius = FOLLOWER_BASE_RADIUS
    else:
        # Scale down for large player counts (less aggressive for moderate counts)
        # 500 players → ~11px, 1000 players → ~9px, 10000 → ~6.5px
        scale_factor = math.pow(100.0 / total_players, 0.6)  # Less aggressive (was 0.5)
        start_radius = max(FOLLOWER_MIN_RADIUS, FOLLOWER_BASE_RADIUS * scale_factor)

    # Step 2: Calculate growth based on elimination progress
    # As players are eliminated, remaining players should grow
    elimination_progress = 1.0 - (alive_count / total_players)

    # Apply growth rate (0.0 = no growth, 1.0 = full growth)
    growth_amount = elimination_progress * SCALING_GROWTH_RATE

    # Calculate target radius: grow towards max radius as game progresses
    radius_range = FOLLOWER_MAX_RADIUS - start_radius
    current_radius = start_radius + (radius_range * growth_amount)

    # Step 3: Constrain by available space in safe zone
    # Don't make followers so big they can't fit in the zone
    zone_ratio = safe_zone_radius / initial_zone_radius

    # If zone is small, cap the radius to prevent overcrowding
    if alive_count > 10:  # Only apply constraint when many players remain
        max_safe_radius = (safe_zone_radius * 0.8) / math.sqrt(alive_count / 2.0)
        current_radius = min(current_radius, max_safe_radius)

    # Step 4: Clamp to max bound only (allow very small radii when crowded)
    current_radius = max(FOLLOWER_MIN_RADIUS, min(FOLLOWER_MAX_RADIUS, current_radius))

    return current_radius


# ===== FIGHTER ARENA SETTINGS =====
# Rectangle arena boundaries (x, y, width, height)
# Height similar to Battle Royale circle diameter (500px = 2 * 250 radius)
FIGHTER_ARENA_RECT = (40, 180, SCREEN_WIDTH - 80, 500)

# Default fighter stats (must sum to 100)
FIGHTER_DEFAULT_STATS = {
    "hp": 40,           # Number of attack points it can survive
    "speed": 5,        # Pixels moved every 2 frames
    "attack": 20,        # HP damage dealt per hit (halved from 10)
    "regeneration": 0,  # HP regenerated per second (divided by 2 in code = 2.5 actual)
    "knockback": 3,    # Push distance = knockback / 3 pixels, stun = knockback * 1 frames
    "attack_speed": 30  # Attacks per second = value / 10 (default: 2 attacks/sec)
}

# Stat boosts for specific usernames
# Format: {"username": {"stat_name": bonus_points, ...}, ...}
# Example: {"cooluser": {"attack": 10}, "tankuser": {"hp": 20, "speed": -5}}
FIGHTER_STAT_BOOSTS = {
    # Add usernames here to give them boosted stats
}

# ===== TEAM BATTLE SETTINGS =====
# Team battle uses separate stats from fighter arena
TEAM_BATTLE_DEFAULT_STATS = {
    "hp": 40,           # Number of attack points it can survive
    "speed": 5,         # Pixels moved every 2 frames
    "attack": 15,      # HP damage dealt per hit
    "regeneration": 0,  # HP regenerated per second (divided by 2 in code = 2.5 actual)
    "knockback": 3,     # Push distance = knockback / 3 pixels, stun = knockback * 1 frames
    "attack_speed": 30  # Attacks per second = value / 10 (default: 3 attacks/sec)
}

# Stat boosts for team battle (separate from fighter arena)
TEAM_BATTLE_STAT_BOOSTS = {
    # Add usernames here to give them boosted stats in team battle
}

# ===== BATTLE ROYALE FOLLOWER STATS =====
# Battle royale follower physics stats
BATTLE_ROYALE_DEFAULT_STATS = {
    "base_speed": 4.0,           # Movement speed (pixels per frame)
    "friction": 0.75,            # Velocity decay multiplier (0-1)
    "push_force": 16.0,           # Force applied during collisions
    "bump_cooldown": 0.5,        # Cooldown between bumps (seconds)
    "movement_randomness": 0.2   # Movement direction randomness (0-1)
}

# Fighter arena colors
COLOR_FIGHTER_ARENA = (180, 180, 190)  # Slightly darker gray for arena floor
COLOR_HP_BAR_BG = (60, 60, 60)         # Dark gray HP bar background
COLOR_HP_BAR_FULL = (50, 200, 50)      # Green when HP is high
COLOR_HP_BAR_MID = (255, 165, 0)       # Orange when HP is medium
COLOR_HP_BAR_LOW = (255, 50, 50)       # Red when HP is low

# Combat settings
FIGHTER_ATTACK_RANGE = FOLLOWER_RADIUS * 2.5  # Distance to land an attack
FIGHTER_HP_BAR_WIDTH = 30             # Width of HP bar above fighters
FIGHTER_HP_BAR_HEIGHT = 4             # Height of HP bar

# ===== OBSTACLE COURSE SETTINGS =====
# Course dimensions
OBSTACLE_COURSE_LENGTH = 18000     # Total course length in pixels (doubled)
OBSTACLE_COURSE_WIDTH = 500        # Track width in pixels

# Track generation settings - simple horizontal race with gentle vertical waves
COURSE_SEGMENT_LENGTH = 300        # Distance between waypoints (pixels)
COURSE_VERTICAL_WAVE_MIN = 30      # Minimum vertical shift between waypoints
COURSE_VERTICAL_WAVE_MAX = 100     # Maximum vertical shift between waypoints

# Course colors
COLOR_OBSTACLE_COURSE_TRACK = (180, 180, 190)  # Track surface color
OBSTACLE_COURSE_BARRIER_COLOR = (100, 100, 100)  # Track edge barriers
COLOR_WAYPOINT_MARKER = (100, 200, 255)  # Waypoint visualization color

# Racer grab mechanic
RACER_GRAB_RANGE = 30              # pixels - distance to grab another racer
RACER_GRAB_COOLDOWN = 2.0          # seconds - cooldown between grabs
RACER_GRAB_THROW_POWER = 15        # pixels/frame - how far target gets thrown

# Finish line settings
FINISH_GRACE_PERIOD = 5.0          # seconds - time after first finisher for others to finish

# Racer default stats (must sum to 30)
RACER_DEFAULT_STATS = {
    "speed": 10,        # Movement speed
    "agility": 10,      # Obstacle avoidance, turn speed
    "intelligence": 10  # Pathfinding quality, grab decisions
}

# Stat boosts for specific usernames
# Format: {"username": {"stat_name": bonus_points, ...}, ...}
RACER_STAT_BOOSTS = {
    # Add usernames here to give them boosted stats
}

# ===== SNAKE ESCAPE SETTINGS =====
# Snake settings
SNAKE_COUNT = 2                          # Number of snakes in the game
SNAKE_INITIAL_SPEED = BASE_SPEED * 1.25  # Snake starts ~25% faster than followers
SNAKE_MAX_SPEED_MULTIPLIER = 2.0         # Maximum speed multiplier (at end of game)

# Follower flee behavior
SNAKE_FLEE_DISTANCE = 150    # Distance at which followers start fleeing from snake
SNAKE_PANIC_DISTANCE = 80    # Distance at which followers enter panic mode (max speed flee)

# Snake escape follower physics stats
SNAKE_ESCAPE_DEFAULT_STATS = {
    "base_speed": 2.0,           # Movement speed (pixels per frame)
    "friction": 0.75,            # Velocity decay multiplier (0-1)
    "bump_cooldown": 0.5,        # Cooldown between bumps (seconds)
    "movement_randomness": 0.1   # Movement direction randomness (0-1)
}

# ===== METEOR MAYHEM SETTINGS =====
METEOR_ZONE_INITIAL_RADIUS = 240     # Safe zone radius at start
METEOR_ZONE_MIN_RADIUS = 90          # Minimum radius after shrinking
METEOR_ZONE_SHRINK_RATE = 4.0        # Pixels per second shrink
METEOR_SPAWN_INTERVAL = (1.4, 2.4)   # Seconds between meteor spawns (min, max)
METEOR_FALL_SPEED = (380.0, 520.0)   # Speed range for meteors (pixels/sec)
METEOR_RADIUS = (10, 16)             # Visual radius range
METEOR_IMPACT_RADIUS = (60, 90)      # Damage radius range (larger for stronger visuals)
METEOR_PLAYER_SPEED = 110.0          # Player move speed (pixels/sec)
METEOR_PLAYER_JITTER = 0.35          # Randomness factor to movement
METEOR_PUSH_FORCE = 8.0              # Bump strength between players
METEOR_MAX_PLAY_AREA = 500           # Play area diameter (for clamping)
METEOR_BG_COLOR = (18, 20, 34)       # Dark background
METEOR_ZONE_COLOR = (70, 80, 140)    # Safe zone outline
METEOR_COLOR = (255, 120, 70)        # Meteor color
METEOR_IMPACT_COLOR = (255, 200, 120) # Impact ring color
METEOR_PLAYER_COLORS = [
    (90, 200, 255),
    (255, 140, 200),
    (140, 255, 160),
    (255, 220, 100),
    (200, 150, 255),
    (255, 170, 120),
]

# ===== TEAM BATTLE SETTINGS =====
# Team colors (RGB) - used for team rings around fighters
TEAM_BATTLE_COLORS = {
    "red": (220, 50, 50),
    "blue": (50, 100, 220),
    "green": (50, 180, 50),
    "yellow": (220, 200, 50),
}

# Team placement base scores
TEAM_PLACEMENT_SCORES = {
    4: 25,   # First team eliminated (4th place)
    3: 50,   # Second team eliminated (3rd place)
    2: 75,   # Lost finals (2nd place)
    1: 75,   # Won finals (1st place) - individual ranking adds 0-25 more
}

# ===== GORILLAS VS FOLLOWERS SETTINGS =====
# Gorilla stats (boss enemy)
GORILLA_STATS = {
    "hp": 15000,
    "speed": 1,
    "attack": 30,
    "attack_speed": 20,  # Attacks per second = value / 10 (2 attacks/sec)
    "knockback_distance": 55,
    "regeneration": 0  # No regeneration for gorillas
}
GORILLA_ATTACK_SPLASH_RADIUS = 21  # Full-damage radius around primary target (pixels)
GORILLA_ATTACK_SPLASH_FALLOFF_RADIUS = 30  # Outer radius for half damage (pixels)
GORILLA_ATTACK_KNOCKBACK = 60      # Knockback applied to players hit by gorilla attacks (pixels)
GORILLA_GATE_OPEN_DURATION = 2.0   # Seconds for the mid-gate to fully open after countdown
GORILLA_SPLASH_BASE_PLAYER_RADIUS = 14  # Base follower radius used to scale gorilla splash radii

# Gorilla visual settings
GORILLA_SIZE_MULTIPLIER = 3.0  # 3x follower size
GORILLA_ARM_LENGTH_MULTIPLIER = 1.2  # Arm length relative to body radius
GORILLA_ARM_WIDTH_MULTIPLIER = 0.4   # Arm width relative to body radius
GORILLA_ARM_SWING_AMPLITUDE = 30     # Degrees of arm swing
GORILLA_ARM_SWING_PERIOD = 2.0       # Seconds per full arm swing cycle

# Gorilla colors (brown/black variations)
GORILLA_COLORS = [
    (101, 67, 33),   # Medium brown
    (40, 26, 13),    # Dark brown
    (139, 90, 43),   # Light brown
    (30, 20, 10)     # Nearly black
]

# Gorilla HP bar settings
GORILLA_HP_BAR_WIDTH = 60
GORILLA_HP_BAR_HEIGHT = 6

# Follower stats for gorillas mode (NO boosts, default fighter stats)
GORILLAS_MODE_FOLLOWER_STATS = {
    "hp": 40,
    "speed": 5,
    "attack": 7.5,
    "regeneration": 0,  # No regeneration
    "knockback": 3,
    "attack_speed": 30  # Attacks per second = value / 10 (3 attacks/sec)
}

# Arena dimensions (extended height)
# Format: (x, y, width, height)
GORILLAS_ARENA_RECT = (40, 180, SCREEN_WIDTH - 80, SCREEN_HEIGHT - 190)

# Kill bonus points
TEAM_BATTLE_KILL_BONUS = 1  # Points per kill

# ===== SPLEEF SETTINGS =====
# Arena dimensions
SPLEEF_GRID_WIDTH = 23           # Blocks wide (adjusted for 15px blocks: 23×15=345px, close to original 350px)
SPLEEF_GRID_HEIGHT = 23          # Blocks tall (same as width for perfect square)
SPLEEF_BLOCK_SIZE = 15           # Pixels per block (increased from 10 for better visibility)
SPLEEF_LAYER_COUNT = 8           # Number of floor layers
SPLEEF_LAYER_SPACING = 150        # Vertical spacing between layers (increased to make bottom layer reach screen bottom)

# Block degradation timing (total: 1.0 second from step to break)
SPLEEF_CRACK_DURATION = 0.2      # Time in CRACKED state (seconds)
SPLEEF_BREAK_DURATION = 0.3      # Time in BREAKING state (seconds)
SPLEEF_FALL_DURATION = 0.5       # Time falling through broken block (seconds)
# Hits-to-break scaling (baseline 4 hits at 400 players; +1 hit per 100 players above 400)
SPLEEF_BASE_HITS_PER_BLOCK = 4
SPLEEF_HITS_SCALE_BASE_PLAYERS = 400
SPLEEF_HITS_PER_100_PLAYERS = 1  # Keep at 1 to match “+1 hit per +100 players”

# Physics
SPLEEF_MOVE_SPEED = 100.0        # Player movement speed (reduced from 150)
SPLEEF_GRAVITY = 140.0           # Gravity acceleration (adjusted for 1 second fall time with 70px effective distance: 60px spacing + 10px margin)
SPLEEF_FALL_SPEED_MAX = 600.0    # Maximum falling speed (reduced from 800)

# Rendering (isometric 2.5D view)
SPLEEF_ISO_ANGLE = 15            # Isometric projection angle (degrees) - decreased for lower, more horizontal view
SPLEEF_LAYER_VISUAL_OFFSET = 100  # Visual depth between layers (balanced to fill screen without cutting off bottom)

# Layer colors (RGB) - distinct high-saturation hues for each platform
SPLEEF_LAYER_COLORS = {
    0: (100, 200, 255),  # Layer 0 - bright cyan/sky blue
    1: (255, 150, 100),  # Layer 1 - vibrant orange
    2: (200, 100, 255),  # Layer 2 - bright purple
    3: (100, 255, 150),  # Layer 3 - bright mint green
    4: (255, 100, 150),  # Layer 4 - hot pink
    5: (255, 255, 100),  # Layer 5 - bright yellow
    6: (100, 255, 255),  # Layer 6 - bright aqua
    7: (255, 100, 255),  # Layer 7 - bright magenta
    8: (150, 255, 100),  # Layer 8 - lime green
    9: (255, 200, 100),  # Layer 9 - golden yellow
}

# Scoring
SPLEEF_POINTS_PER_BLOCK_BROKEN = 5  # Bonus points for each block broken

# Layer visibility settings
SPLEEF_USE_LAYER_TRANSPARENCY = True   # Enable progressive layer transparency
SPLEEF_LAYER_MIN_OPACITY = 80          # Min alpha for sparse upper layers (0-255)
SPLEEF_LAYER_MAX_OPACITY = 255         # Max alpha (fully opaque)

# Layer indicator panel (side panel showing player distribution)
SPLEEF_SHOW_LAYER_PANEL = True         # Enable layer indicator panel
SPLEEF_LAYER_PANEL_X = 420             # X position (move left to avoid overlap)
SPLEEF_LAYER_PANEL_Y = 50              # Y position (higher on screen)
SPLEEF_LAYER_PANEL_WIDTH = 70          # Panel width
SPLEEF_LAYER_PANEL_BAR_HEIGHT = 8      # Height of each layer bar
SPLEEF_LAYER_PANEL_SPACING = 3         # Spacing between bars
SPLEEF_OUTER_WALL_BUFFER = 4.0         # Inward buffer (pixels) for invisible wall on outer ring to keep avatars off the edge

# ===== INSTAGRAM STORY SETTINGS =====
ENABLE_STORY_POSTING = True              # Master toggle for story posting
STORY_DELAY_HOURS = 2                    # Hours to wait after uploads complete
STORY_OUTPUT_DIR = Path("stories")       # Story images directory
STORY_IMAGE_SIZE = (1080, 1920)          # 9:16 aspect ratio (width, height)

# Link sticker settings
STORY_WEBSITE_URL = "https://www.followerbattlegrounds.com/"  # Website link for story
STORY_LINK_TEXT = "Check Out Your Results"                     # Text displayed on link sticker

# Story template colors
STORY_BG_COLOR_TOP = (26, 26, 46)        # Dark blue (#1a1a2e) - top of gradient
STORY_BG_COLOR_BOTTOM = (22, 33, 62)     # Purple (#16213e) - bottom of gradient
STORY_TEXT_COLOR = (255, 255, 255)       # White text
STORY_ACCENT_COLOR = (255, 215, 0)       # Gold for points/1st place (#FFD700)
STORY_SILVER_COLOR = (192, 192, 192)     # Silver for 2nd place
STORY_BRONZE_COLOR = (205, 127, 50)      # Bronze for 3rd place (#CD7F32)

# Avatar styling
STORY_AVATAR_SIZE_1ST = 200              # 1st place avatar diameter (pixels)
STORY_AVATAR_SIZE_2_3 = 140              # 2nd/3rd place avatar diameter (pixels)
STORY_AVATAR_BORDER = 6                  # Border width (pixels)
AVATAR_CACHE_DIR = Path("avatar_cache")  # Avatar cache directory location
