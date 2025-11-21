"""
Configuration file for Follower Battle Royale & Fighter Arena
Modify these values to customize game behavior
"""

# ===== GAME MODE =====
# Options: "battle_royale" or "fighter_arena"

# GAME_MODE = "battle_royale"
# ===== GAME SETTINGS =====
SCREEN_WIDTH = 540   # Scaled down for better visibility on monitors
SCREEN_HEIGHT = 960  # 9:16 aspect ratio for Instagram Reels / TikTok
FPS = 60




# Test mode - when True, game results won't be saved to the all-time leaderboard
GAME_MODE = "fighter_arena"
TEST_MODE = True
EXPORT_VIDEO = True
DAY_NUMBER = 1  # Increment this each time you record a new video
DOWNLOAD_PROFILE_PICTURES = True
UPSCALE_VIDEO = True  # Enable upscaling for higher quality video output
UPSCALE_FACTOR = 2.0 

# ===== ARENA SETTINGS =====
ARENA_CENTER = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
ARENA_INITIAL_RADIUS = 250  # Starting safe zone radius (scaled to match screen size)
ARENA_MIN_RADIUS = 50       # Minimum safe zone radius before game ends

# Continuous shrinking settings
SHRINK_RATE = 0.10          # Pixels per second the zone shrinks (smooth continuous shrinking)
                            # Lower = slower shrink, Higher = faster shrink
                            # Recommended: 0.15-0.3 for slower games, 0.5-1.0 for fast-paced

# Arena shape - Options: "circle", "square", "hexagon", "octagon"
ARENA_SHAPE = "circle"

# ===== FOLLOWER SETTINGS =====
FOLLOWER_COUNT = 500        # Number of followers (can be 500-1000)
FOLLOWER_RADIUS = 14        # Radius of each follower circle (will be dynamically adjusted)
FOLLOWER_BORDER_WIDTH = 2   # White border thickness
FOLLOWER_NAME_FONT_SIZE = 16  # Increased from 12 for better readability
SHOW_FOLLOWER_NAMES = False  # Show usernames below profile pictures during battle

# ===== DYNAMIC SCALING SETTINGS =====
USE_DYNAMIC_SCALING = True  # Enable dynamic follower size based on player count
FOLLOWER_BASE_RADIUS = 14   # Base radius for ~100 final contestants (good size)
FOLLOWER_MIN_RADIUS = 6     # Minimum radius for very large player counts (100K+)
FOLLOWER_MAX_RADIUS = 20    # Maximum radius when only a few players remain
SCALING_GROWTH_RATE = 0.5   # How quickly players grow as others are eliminated (0.0-1.0)

# ===== PHYSICS SETTINGS =====
BASE_SPEED = 2.0            # Base movement speed (pixels per frame) - reduced for slower pace
FRICTION = 0.95             # Friction multiplier (lower = more friction)
PUSH_FORCE = 8.0            # Force applied during collisions
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
COLOR_BORDER = (255, 255, 255)

# ===== VIDEO EXPORT SETTINGS =====

# Determine output video filename based on test mode
if TEST_MODE:
    OUTPUT_VIDEO_PATH = "follower_battle_royale_test_video.mp4"
else:
    OUTPUT_VIDEO_PATH = f"follower_battle_royale_day_{DAY_NUMBER}.mp4"

VIDEO_CODEC = "libx264"
VIDEO_FPS = 30  # Export FPS (can be lower than game FPS for smaller file)

# Video upscaling settings
# Game renders at SCREEN_WIDTH x SCREEN_HEIGHT, but exports at higher resolution
 # Multiplier for output resolution (2.0 = 1080x1920 from 540x960)
# With UPSCALE_FACTOR = 2.0: 540x960 -> 1080x1920 (1080p vertical HD)
# With UPSCALE_FACTOR = 3.0: 540x960 -> 1620x2880 (1620p vertical)

# ===== INSTAGRAM DATA SETTINGS =====

# Option 1: Import from File (✅ BEST - Safe, Legal, Recommended!)
# Use Instagram's "Download Your Data" feature to get followers.json
# Or use a Chrome extension like "IG Exporter & Scraper" for instant export
# Or create your own CSV/JSON/TXT file with usernames
FOLLOWER_IMPORT_FILE = "C:\\Users\\SondreNorheim\\Downloads\\followerbattlegrounds_Followers.csv"  

# Download real profile pictures from CSV (if profile_pic_url column exists)
# Set to True to download real Instagram profile pictures (takes longer, uses bandwidth)
# Set to False to use colored circle avatars (faster, recommended)
# Option 2: Official Instagram Graph API (Safe, requires business account)
# Requires: Instagram Business account + Facebook Developer account
INSTAGRAM_ACCESS_TOKEN = ""  # Your Instagram Graph API access token
INSTAGRAM_USER_ID = ""       # Your Instagram user ID

# Option 3: Web Scraping with Instaloader (⚠️ VIOLATES INSTAGRAM ToS!)
# WARNING: This can get your account banned! Use a burner account if possible.
# Requires: Regular Instagram account credentials
USE_INSTALOADER_SCRAPER = False  # Set to True to enable web scraping
INSTAGRAM_USERNAME = ""          # Your Instagram username (for scraping)
INSTAGRAM_PASSWORD = ""          # Your Instagram password (for scraping)
INSTAGRAM_TARGET_USERNAME = ""   # Target account to scrape followers from (leave empty to use your own)

# Option 4: Offline Mode (Safe, generates random followers)
USE_OFFLINE_MODE = True      # Set to False to attempt API/scraper fetching

# ===== RANDOM AVATAR COLORS (for offline mode) =====
RANDOM_COLORS = [
    (255, 100, 100), (100, 255, 100), (100, 100, 255),
    (255, 255, 100), (255, 100, 255), (100, 255, 255),
    (255, 150, 100), (150, 255, 100), (100, 150, 255),
    (255, 100, 150), (100, 255, 150), (150, 100, 255),
]


# ===== DYNAMIC RADIUS CALCULATION =====
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
    # For 100 players: use base radius (14px)
    # For more players: scale down proportionally
    # For fewer players: can start slightly larger
    if total_players <= 100:
        start_radius = FOLLOWER_BASE_RADIUS
    else:
        # Scale down for large player counts
        # 1000 players → ~8px, 10000 → ~6.5px, 100000 → ~6px
        scale_factor = math.sqrt(100.0 / total_players)
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

    # Step 4: Clamp to min/max bounds
    current_radius = max(FOLLOWER_MIN_RADIUS, min(FOLLOWER_MAX_RADIUS, current_radius))

    return current_radius


# ===== FIGHTER ARENA SETTINGS =====
# Rectangle arena boundaries (x, y, width, height)
# Height similar to Battle Royale circle diameter (500px = 2 * 250 radius)
FIGHTER_ARENA_RECT = (20, 180, SCREEN_WIDTH - 40, 500)

# Default fighter stats (must sum to 100)
FIGHTER_DEFAULT_STATS = {
    "hp": 40,           # Number of attack points it can survive
    "speed": 10,        # Pixels moved every 2 frames
    "attack": 10,       # HP damage dealt per hit
    "regeneration": 5,  # HP regenerated per second (divided by 2 in code = 2.5 actual)
    "knockback": 15,    # Push distance = knockback / 3 pixels, stun = knockback * 1 frames
    "attack_speed": 20  # Attacks per second = value / 10 (default: 2 attacks/sec)
}

# Stat boosts for specific usernames
# Format: {"username": {"stat_name": bonus_points, ...}, ...}
# Example: {"cooluser": {"attack": 10}, "tankuser": {"hp": 20, "speed": -5}}
FIGHTER_STAT_BOOSTS = {
    # Add usernames here to give them boosted stats
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
