"""
Configuration file for Follower Battle Royale & Fighter Arena
Modify these values to customize game behavior
"""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent


def project_path(*parts: str) -> str:
    """Return an absolute path rooted at the project directory."""
    return str((PROJECT_ROOT.joinpath(*parts)).resolve())

# ===== GAME MODE =====
# Options: "battle_royale", "fighter_arena", "maze_rush", "math_drop", "plinko", "obstacle_course",
#          "snake_escape", "team_battle", "platformer_race", "spleef", "mingle",
#          "heads_or_tails", "wheel_spinner", "lava_platform", "mini_golf",
#          "flappy_followers", "tiny_followers", "jetpack_followers", "doodle_followers", "crossy_followers", "followers_io", "super_follower_bros",
#          "subway_followers", "subway_followers_3d",
#          "beacon_blitz", "lane_rush", "discord_signal", "club_duel", "club_relic",
#          "moon_stack", "ALL"
# When set to "ALL", games will run in the order defined by ALL_GAME_MODES.
# ALL_GAME_MODES = ["obstacle_course", "team_battle", "platformer_race"]
# ALL_GAME_MODES = [ "snake_escape", "team_battle", "platformer_race"]
# ALL_GAME_MODES = [
#     "super_follower_bros_1_1",
#     "super_follower_bros_1_2",
#     "super_follower_bros_1_3",
#     "super_follower_bros_1_4",
#     "super_follower_bros_2_1",
#     "super_follower_bros_2_2",
#     "super_follower_bros_2_3",
#     "super_follower_bros_2_4",
#     "super_follower_bros_3_1",
#     "super_follower_bros_3_2",
#     "super_follower_bros_3_3",
#     "super_follower_bros_3_4",
#     "super_follower_bros_4_1",
#     "super_follower_bros_4_2",
#     "super_follower_bros_4_3",
#     "super_follower_bros_4_4",
#     "super_follower_bros_5_1",
#     "super_follower_bros_5_2",
#     "super_follower_bros_5_3",
#     "super_follower_bros_5_4",
#     "super_follower_bros_6_1",
#     "super_follower_bros_6_2",
#     "super_follower_bros_6_3",
#     "super_follower_bros_6_4",
#     "super_follower_bros_7_1",
#     "super_follower_bros_7_2",
#     "super_follower_bros_7_3",
#     "super_follower_bros_7_4",
#     "super_follower_bros_8_1",
#     "super_follower_bros_8_2",
#     "super_follower_bros_8_3",
#     "super_follower_bros_8_4",
# ]
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
# ALL_GAME_MODES = ["math_drop", "heads_or_tails", "fighter_arena", "maze_rush", "wheel_spinner"] 

ALL_GAME_MODES = ["math_drop", "heads_or_tails", "fighter_arena", "maze_rush", "mini_golf", "snake_escape", "flappy_followers", "discord_signal", "doodle_followers"] 
# ALL_GAME_MODES = ["math_drop", "heads_or_tails", "fighter_arena", "maze_rush", "wheel_spinner", "jetpack_followers", "flappy_followers", "super_follower_bros_1_2", "discord_signal", "doodle_followers", "mini_golf", "snake_escape"] 

# ALL_GAME_MODES = ["beacon_blitz", "lane_rush", "discord_signal", "club_duel", "club_relic",] 
# ALL_GAME_MODES = ["discord_signal"]
NON_SCORING_GAME_TYPES = ["mingle", "lava_platform", "plinko", "moon_stack"]
YOUTUBE_SKIP_GAME_MODES = ["super_follower_bros"]
# Skip including the "Top 10" block in Instagram captions for these game modes.dx
TOP10_SKIP_GAME_MODES = ["super_follower_bros", "super_follower_bros_1_2", "jetpack_followers", "crossy_followers"]

# Test mode - when True, game results won't be saved to the all-time leaderboard
GAME_MODE = "ALL" # Options: "battle_royale", "fighter_arena", "followers_io", "maze_rush", "math_drop", "plinko", "obstacle_course", "snake_escape", "team_battle", "platformer_race", "anime_fighting", "mingle", "heads_or_tails", "wheel_spinner", "lava_platform", "mini_golf", "flappy_followers", "tiny_followers", "jetpack_followers", "doodle_followers", "crossy_followers", "super_follower_bros", "subway_followers", "subway_followers_3d", "beacon_blitz", "lane_rush", "discord_signal", "club_duel", "club_relic", "moon_stack", "ALL"
TEST_MODE = False  # Set to True to enable test mode (won't save results to leaderboard)
EXPORT_VIDEO = True
DAY_NUMBER = 112 # Increment  this each time you record a new video
COMMENT_RESULT_PROMPT_TEXT = 'Comment "RESULT" to see how you did'
WEB_RESULTS_PREVIEW_LIMIT = 200  # Top N results to include in web preview files

DOWNLOAD_PROFILE_PICTURES = True  # Deprecated - use download_all_profile_pics.py instead
LOAD_PROFILE_PICTURES = True  # Set to True to load from avatar_cache/, False to skip entirely (faster testing)
HEADLESS_MODE = False
SHOW_NAMETAGS = False
TEST_MINIMAL_PLAYERS = False # Set True to use test users, False to use real followers
TEST_MINIMAL_PLAYER_COUNT = 10

SUPER_FOLLOWER_BROS_DAY_OFFSET = 71
# Jetpack captions/results can use a mode-specific displayed day like SMB.
# Example with offset 71: actual day 93 -> displayed day 22.
JETPACK_FOLLOWERS_DAY_OFFSET = SUPER_FOLLOWER_BROS_DAY_OFFSET
CROSSY_FOLLOWERS_DAY_OFFSET = JETPACK_FOLLOWERS_DAY_OFFSET

# ===== MEDIA KIT SETTINGS =====
# When MEDIA_KIT_DAILY_VIDEOS_RANGE is None, we compute min/max from recent days.
MEDIA_KIT_DAILY_VIDEOS_RANGE = None
MEDIA_KIT_DAILY_VIDEOS_FALLBACK = (6, 10)
MEDIA_KIT_ENGAGEMENT_GROWTH_PCT = 9600
MEDIA_KIT_REACH = {
    "total_views": 4000000,
    "accounts_reached": 2000000,
    "interactions": 216000,
    "accounts_engaged": 165000,
}
MEDIA_KIT_INSIGHTS = {
    "viral_reach_pct": 79.3,
    "profile_visits": 115000,
    "external_link_taps": 10900,
    "top_reel_views": [179000, 78000, 47000],
}
MEDIA_KIT_DEMOGRAPHICS = {
    "age_distribution": {
        "13-17": 25.5,
        "18-24": 34.1,
        "25-34": 29.7,
        "35-44": 6.4,
        "45+": 4.3,
    },
    "under_35_pct": 89,
    "gender_split": {"male": 81, "female": 19},
    "top_countries": [
        {"name": "United States", "pct": 32.5},
        {"name": "United Kingdom", "pct": 4.6},
        {"name": "Indonesia", "pct": 4.2},
        {"name": "France", "pct": 3.9},
        {"name": "Italy", "pct": 3.7},
    ],
    "countries_reached": 50,
}
MEDIA_KIT_AUDIENCE_INTERESTS = [
    "Gaming",
    "Tech",
    "Entertainment",
    "Memes",
    "Esports",
    "Social Media",
]

# Profile picture settings:
# - DOWNLOAD_PROFILE_PICTURES: Legacy flag for downloading during game run (slow, not recommended)
# - LOAD_PROFILE_PICTURES: Load profile pictures from avatar_cache/ (fast, recommended)
#
# Recommended workflow:
#   1. Run download_all_profile_pics.py once to cache all profile pictures
#   2. Set LOAD_PROFILE_PICTURES = True to use cached images
#   3. Games will load instantly from disk cache


# ===== WEBHOOK SERVICE AUTOSTART =====
# PC runtime should not launch inbound services; webhook/tunnel move to the Mac.
AUTO_START_WEBHOOK_SERVICES = False
WEBHOOK_SERVER_SCRIPT = "instagram_webhook.py"
WEBHOOK_SERVER_PORT = 5000
# Tunnel provider: "cloudflared" (Cloudflare Tunnel) or "ngrok"
TUNNEL_PROVIDER = "cloudflared"

# Cloudflare Tunnel (quick tunnel) settings
# Use full path if cloudflared is not on PATH.
_CLOUDFLARED_LOCAL = Path(project_path("tools", "cloudflared-windows-amd64.exe"))
CLOUDFLARED_PATH = str(_CLOUDFLARED_LOCAL) if _CLOUDFLARED_LOCAL.exists() else "cloudflared"
CLOUDFLARED_URL = f"http://localhost:{WEBHOOK_SERVER_PORT}"
CLOUDFLARED_METRICS_PORT = 49312
CLOUDFLARED_LOG_LEVEL = "info"
CLOUDFLARED_NO_AUTOUPDATE = True
# Optional stability flags for network issues.
# Valid protocols: "", "auto", "quic", "http2"
CLOUDFLARED_PROTOCOL = "http2"
# Valid values: "", "auto", "4", "6"
CLOUDFLARED_EDGE_IP_VERSION = "4"

# Cloudflare Tunnel mode: "quick" or "named"
# - quick: temporary trycloudflare.com URL (changes each restart)
# - named: stable hostname via your Cloudflare account + domain
CLOUDFLARED_TUNNEL_MODE = "named"
# Required for named tunnel mode (set these after running setup_cloudflared_named_tunnel.py)
CLOUDFLARED_TUNNEL_NAME = "fbg-webhook"
# Example: "webhook.yourdomain.com"
CLOUDFLARED_HOSTNAME = "webhook.followerbattlegrounds.com"
# Optional explicit config path (leave empty to use default ~/.cloudflared/config.yml)
CLOUDFLARED_CONFIG_PATH = r"C:\Users\SondreNorheim\.cloudflared\config.yml"

NGROK_HTTP_PORT = 5000
NGROK_API_PORT = 4040
NGROK_PATH = "ngrok"
NGROK_LOG_MODE = "stdout"
WEBHOOK_SERVICE_HEADLESS = True
WEBHOOK_SERVICE_LOG_DIR = "logs/webhook_services"

# ===== DISCORD BOT AUTOSTART =====
# Discord bot also runs on the Mac, not from the PC pipeline.
AUTO_START_DISCORD_BOT = False
DISCORD_BOT_SCRIPT = "discord_bot/bot.py"
DISCORD_BOT_PID_FILE = "discord_bot/discord_bot.pid"
DISCORD_BOT_LOG_DIR = "logs/discord_bot"
DISCORD_BOT_HEADLESS = True

# Minimal test players - when True, use generated test users instead of real followers
 # Number of test users to generate (minimum 100-200 recommended for Battle Royale)
# Control whether stats auto-push is enabled.
AUTO_PUSH_STATS = True
# Control whether video files are included in auto-push (set False to only push stats data)
AUTO_PUSH_INCLUDE_VIDEOS = False
AUTO_PUSH_MERGE_API_GAMES = True
# Keep heavyweight API partitions out of git; push them to R2 instead.
AUTO_PUSH_TRACK_HEAVY_API = False
AUTO_PUSH_SYNC_R2_FROM_LOCAL = True
AUTO_PUSH_SYNC_EVENTS_TO_R2_FROM_LOCAL = True
# Pull Mac-owned follower/webhook state before the next render run starts.
AUTO_PULL_MAC_STATE_BEFORE_RUN = True
# Optional AWS CLI override for Windows or macOS.
AWS_CLI_PATH = ""
# Shared Cloudflare R2 configuration for API/events/state sync.
R2_ENDPOINT = ""
R2_BUCKET = ""
R2_ACCESS_KEY_ID = ""
R2_SECRET_ACCESS_KEY = ""
R2_API_PREFIX = "api"
R2_EVENTS_PREFIX = "events"
R2_STATE_PREFIX = "state/mac"
# ALL-mode push behavior:
# - "final_only": push once after all games are complete.
# - "per_game": push after every game (legacy high-commit mode).
# - "every_n_games": push every AUTO_PUSH_ALL_MODE_BATCH_SIZE games and once at the end.
AUTO_PUSH_ALL_MODE_STRATEGY = "every_n_games"
AUTO_PUSH_ALL_MODE_BATCH_SIZE = 5
# When running GAME_MODE="ALL" with batched pushes, temporarily disable
# per-game push calls inside individual game modules.
AUTO_PUSH_ALL_MODE_SUPPRESS_PER_GAME_PUSH = True

# Simulation-light mode:
# - Skip full history/stat loads and full-file persistence during simulation runs.
# - Still append per-game event backups to backups/game_results/events/.
# - Run a separate rebuild step later to regenerate canonical history/stat files.
SIMULATION_LIGHT_MODE = False
# Auto-enable simulation-light when running `main.py --day-range ...`.
SIMULATION_LIGHT_AUTO_FOR_DAY_RANGE = True
# In simulation-light mode, skip in-memory all-time stats updates to reduce RAM.
SIMULATION_LIGHT_DISABLE_STATS_UPDATES = True

# Local audio controls:
# Keep gameplay audio in exported videos, but mute local live playback while processing.
MUTE_LOCAL_GAME_AUDIO = True
# Mute browser audio in Selenium upload windows.
MUTE_BROWSER_AUDIO_DURING_UPLOADS = True

# Instagram upload framing:
# These game modes should stay in 1:1 (square) in the Instagram crop dialog.
# All other game modes default to 9:16.
INSTAGRAM_SQUARE_ASPECT_GAME_MODES = [
    "fighter_arena",
    "maze_rush",
    "mini_golf",
    "obstacle_course",
    "discord_signal",
    "snake_escape",
    "math_drop",
    "heads_or_tails",
    "side_choice",  # Alias used by some runs for Heads or Tails
]

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
FOLLOWER_RADIUS = 21        # Radius of each follower circle (will be dynamically adjusted) - 1.5x bigger
OBSTACLE_COURSE_FOLLOWER_RADIUS = 21  # Fixed radius for obstacle course racers
FOLLOWER_BORDER_WIDTH = 2   # White border thickness
FOLLOWER_NAME_FONT_SIZE = 12  # Nametag font size for follower usernames
SHOW_FOLLOWER_NAMES = False  # Show usernames below profile pictures during battle

# Profile picture rendering optimization
# Only render profile pictures when radius is large enough to actually see them
# When smaller, use colored circles instead (saves massive rendering overhead with 40k players)
PROFILE_PICTURE_MIN_RADIUS = 8  # Pixels - only render profile pics when radius >= this value

# Club member highlight (glow ring)
CLUB_GLOW_COLOR = (255, 240, 190)
CLUB_GLOW_ALPHA = 180
CLUB_GLOW_LAYERS = 3
CLUB_GLOW_PADDING = 3

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
FOLLOWER_BASE_RADIUS = 18   # Base radius for ~100 final contestants (1.5x bigger: 12 * 1.5 = 18)
FOLLOWER_MIN_RADIUS = 1.5   # No enforced minimum; allows very dense packing (1.5x bigger)
FOLLOWER_MAX_RADIUS = 27    # Maximum radius when only a few players remain (1.5x bigger: 18 * 1.5 = 27)
SCALING_GROWTH_RATE = 0.9   # How quickly players grow as others are eliminated (0.0-1.0) - Increased for faster growth

# ===== BATTLE ROYALE SETTINGS =====
# Set to a fixed radius to disable scaling for Battle Royale (match Meteor Mayhem size).
BATTLE_ROYALE_FIXED_RADIUS = 15
BATTLE_ROYALE_TARGETING_BAND = (0.25, 0.75)
BATTLE_ROYALE_PRESTART_RADIUS_RATIO = 0.85
BATTLE_ROYALE_PRESTART_CENTER_PULL = 0.45

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


def get_non_ig_variant_video_path(
    game_mode: str = None,
    day_number: int | None = None,
    test_mode: bool = None,
) -> str:
    """
    Build output path for non-Instagram video variants.
    Example: maze_rush_day_102_non_ig_join.mp4
    """
    gm = (game_mode or GAME_MODE) if (game_mode or GAME_MODE) else "battle_royale"
    day = day_number if day_number is not None else DAY_NUMBER
    is_test = TEST_MODE if test_mode is None else test_mode
    suffix = str(globals().get("NON_IG_VARIANT_SUFFIX", "_non_ig_join") or "_non_ig_join")
    day_folder = VIDEO_OUTPUT_BASE / f"Day_{day}"
    day_folder.mkdir(parents=True, exist_ok=True)
    if is_test:
        return str(day_folder / f"{gm}_test_video{suffix}.mp4")
    return str(day_folder / f"{gm}_day_{day}{suffix}.mp4")


OUTPUT_VIDEO_PATH = get_output_video_path()

VIDEO_CODEC = "libx264"
VIDEO_FPS = 30  # Export FPS (can be lower than game FPS for smaller file)

# Dual output variants: base (Instagram) + non-IG JOIN footer variant
NON_IG_VARIANT_ENABLED = True
NON_IG_VARIANT_SUFFIX = "_non_ig_join"
NON_IG_JOIN_FOOTER_TEXT = 'Comment "JOIN" to join future games'
NON_IG_JOIN_FOOTER_ENABLED = True
NON_IG_JOIN_FOOTER_FONT_SIZE = 16
NON_IG_JOIN_FOOTER_BOTTOM_MARGIN = 10
NON_IG_JOIN_FOOTER_BOX_HEIGHT = 56
NON_IG_JOIN_FOOTER_BOX_OPACITY = 0.55
NON_IG_JOIN_FOOTER_PLACEMENT_MODE = "above_result_prompt"  # above_result_prompt | fixed_bottom_margin | auto_best_fit
NON_IG_JOIN_ABOVE_RESULT_LINE_GAP = 15
NON_IG_JOIN_ABOVE_RESULT_FONT_COLOR = "black"
NON_IG_JOIN_ABOVE_RESULT_SHADOW_OPACITY = 0.45
NON_IG_JOIN_FOOTER_FIXED_BOTTOM_MARGIN = 10
NON_IG_JOIN_FOOTER_AUTO_CENTER_X_MIN_PCT = 0.20
NON_IG_JOIN_FOOTER_AUTO_CENTER_X_MAX_PCT = 0.80
NON_IG_JOIN_FOOTER_AUTO_SAMPLE_RATIOS = [0.05, 0.25, 0.5, 0.75, 0.95]
NON_IG_JOIN_FOOTER_AUTO_PIXEL_DIFF_THRESHOLD = 28
NON_IG_JOIN_FOOTER_AUTO_ROW_OCCUPANCY_THRESHOLD = 0.02
NON_IG_JOIN_FOOTER_AUTO_RESERVED_BOTTOM_UI_PX = 180
NON_IG_JOIN_FOOTER_AUTO_MIN_TOP_PX = 1480
NON_IG_JOIN_FOOTER_AUTO_MAX_TOP_PX = 1760
NON_IG_JOIN_FOOTER_AUTO_ROW_GAP_PX = 10
NON_IG_JOIN_FOOTER_AUTO_FALLBACK_BOTTOM_MARGIN = 220
NON_IG_VARIANT_AUTO_ROUTE_PLATFORMS = ["facebook", "tiktok", "youtube", "snapchat", "x", "lemon8", "rednote"]
NON_IG_VARIANT_GENERATE_AFTER_EXPORT = True
NON_IG_VARIANT_GENERATE_ON_UPLOAD_IF_MISSING = False

# Streaming mode - write frames directly to disk (prevents memory errors for long videos)
VIDEO_STREAMING_MODE = True  # True = low memory (unlimited length), False = high quality (limited length)

FOLLOWER_IMPORT_FILE = "Followers/new_followers_fresh.json"
# Per-game import overrides (keys = game_mode). Example: {"mingle": "Followers/discord_followers.json"}
FOLLOWER_IMPORT_FILE_BY_MODE = {
    "mingle": "Followers/discord_followers.json",
    "lava_platform": "Followers/discord_followers.json",
    "plinko": "Followers/discord_followers.json",
    "discord_signal": "Followers/discord_followers.json",
    "subway_followers": "Followers/subway_followers.json",
    "subway_followers_3d": "Followers/subway_followers.json",
    "jetpack_followers": "Followers/club_members_followers.json",
    "crossy_followers": "Followers/club_members_followers.json",
    "super_follower_bros": "Followers/club_members_followers.json",
    "super_follower_bros_1_2": "Followers/club_members_followers.json",
    "club_duel": "Followers/club_members_followers.json",
    "club_relic": "Followers/club_members_followers.json",
}

# ===== MOON STACK OBJECTIVE SETTINGS =====
MOON_STACK_TARGET_KM = 383400
MOON_STACK_VIDEO_DURATION_SECONDS = 45.0
MOON_STACK_KM_TO_WORLD_UNITS = 0.03
MOON_STACK_MAX_VISIBLE_BALLS = 420
MOON_STACK_ALLOW_NETWORK_AVATAR_DOWNLOAD = False
MOON_STACK_AVATAR_TEXTURE_SIZE = 128
MOON_STACK_STATE_FILE = "Followers/moon_stack_state.json"
MOON_STACK_INSTAGRAM_FILE = "Followers/new_followers_fresh.json"
MOON_STACK_DISCORD_FILE = "Followers/discord_followers.json"
MOON_STACK_CLUB_FILE = "Followers/club_members_followers.json"
MOON_STACK_AVATAR_CACHE_DIR = "avatar_cache"
MOON_STACK_TEST_EMPTY = False  # True = load zero users (empty stack) for fast scene testing
MOON_STACK_FOLLOWER_WEIGHT = 1
MOON_STACK_DISCORD_WEIGHT = 10
MOON_STACK_CLUB_WEIGHT = 100
MOON_STACK_FOLLOWER_DIAMETER_MULT = 1.0
MOON_STACK_DISCORD_DIAMETER_MULT = 10.0
MOON_STACK_CLUB_DIAMETER_MULT = 100.0
MOON_STACK_BACKGROUND_COLOR = (0.02, 0.02, 0.05)
MOON_STACK_CAMERA_FOV = 42.0
MOON_STACK_CAMERA_BASE_DISTANCE = 3.0
MOON_STACK_CAMERA_ZOOM_AMPLITUDE = 0.9
MOON_STACK_CAMERA_SIDE_SWAY = 0.5
MOON_STACK_CAMERA_HEIGHT_OFFSET = 0.8
MOON_STACK_CAMERA_LOOK_OFFSET = 0.4
MOON_STACK_EARTH_RADIUS_UNITS = 2.6
MOON_STACK_MOON_RADIUS_UNITS = 1.9
MOON_STACK_TOP_MARKER_RADIUS_UNITS = 0.35
MOON_STACK_TOP_MARKER_OFFSET_UNITS = 0.25
MOON_STACK_TITLE_COLOR = (0.95, 0.95, 1.0, 1.0)
MOON_STACK_TEXT_COLOR = (0.92, 0.94, 1.0, 1.0)

# TikTok followers import file (optional - will be combined with Instagram followers)
TIKTOK_IMPORT_FILE = ""  # Disabled - only using Instagram followers


INSTAGRAM_ACCESS_TOKEN = ""  # Your Instagram Graph API access token
INSTAGRAM_USER_ID = ""       # Your Instagram user ID
FACEBOOK_PAGE_AUTO_UPLOAD = False
FACEBOOK_PAGE_ID = ""
FACEBOOK_PAGE_ACCESS_TOKEN = ""
FACEBOOK_GRAPH_API_VERSION = "v18.0"
FACEBOOK_UPLOAD_ON_IG_FAILURE = False

# Facebook comment automation (JOIN intake + RESULT replies)
FACEBOOK_JOIN_PROMPT_TEXT = 'Comment "JOIN" in order to be added to future games'
FACEBOOK_JOIN_PROMPT_MODE = "both"  # off | title | comment | both
FACEBOOK_JOIN_KEYWORDS = ["join"]
FACEBOOK_RESULT_KEYWORDS = ["result"]
FACEBOOK_UPLOAD_JOIN_COMMENT_ENABLED = True
FACEBOOK_UPLOAD_JOIN_COMMENT_TEXT = 'Comment "JOIN" in order to be added to future games'
FACEBOOK_JOIN_ACK_REPLY_ENABLED = True
FACEBOOK_JOIN_ACK_REPLY_TEXT = "You're in. You'll be added to future games."
FACEBOOK_JOIN_ALREADY_REPLY_TEXT = 'You are already part of the games. Comment "RESULT" to see how you did.'
FACEBOOK_RESULT_FUTURE_GAMES_REPLY_TEXT = (
    "You've been added to the follower list and will be part of future games soon."
)
FACEBOOK_WEBHOOK_SECRETS_FILE = "facebook_page_publish.local.env"
FACEBOOK_ENABLE_JOIN_CAPTURE = True
FACEBOOK_ENABLE_RESULT_REPLIES = True
WEBHOOK_MEDIA_GAME_MAP_PATH = "logs/webhook_services/media_game_mapping.json"
FACEBOOK_MEDIA_GAME_MAP_PATH = "logs/webhook_services/facebook_media_game_mapping.json"
FACEBOOK_PROCESSED_COMMENT_IDS_PATH = "logs/webhook_services/processed_comment_ids.json"

# YouTube comment automation (JOIN intake + RESULT replies)
YOUTUBE_ENABLE_JOIN_CAPTURE = True
YOUTUBE_ENABLE_RESULT_REPLIES = True
YOUTUBE_JOIN_KEYWORDS = ["join"]
YOUTUBE_RESULT_KEYWORDS = ["result"]
YOUTUBE_UPLOAD_JOIN_COMMENT_ENABLED = True
YOUTUBE_UPLOAD_JOIN_COMMENT_TEXT = 'Comment "JOIN" in order to be added to future games'
YOUTUBE_JOIN_ACK_REPLY_ENABLED = True
YOUTUBE_JOIN_ACK_REPLY_TEXT = "You're in. You'll be added to future games."
YOUTUBE_JOIN_ALREADY_REPLY_TEXT = 'You are already part of the games. Comment "RESULT" to see how you did.'
YOUTUBE_RESULT_FUTURE_GAMES_REPLY_TEXT = (
    "You've been added to the follower list and will be part of future games soon."
)
YOUTUBE_COMMENT_POLL_ENABLED = True
YOUTUBE_COMMENT_POLL_INTERVAL_SECONDS = 90
YOUTUBE_COMMENT_POLL_MAX_THREADS = 100
YOUTUBE_ALLOW_INTERACTIVE_AUTH = False
YOUTUBE_CHANNEL_ID = ""
YOUTUBE_CLIENT_SECRET_PATH = "secrets/youtube_client_secret.json"
YOUTUBE_COMMENT_TOKEN_PATH = "secrets/youtube_comment_token.pickle"
YOUTUBE_MEDIA_GAME_MAP_PATH = "logs/webhook_services/youtube_media_game_mapping.json"

# Webhook memory guards (events fallback cache behavior)
WEBHOOK_EVENTS_RECENT_DAYS_WINDOW = 0
WEBHOOK_EVENTS_GAME_CACHE_RECENT_ONLY = True
WEBHOOK_EVENTS_DAY_REFRESH_SECONDS = 60
WEBHOOK_EVENTS_DAY_CACHE_MAX = 256
WEBHOOK_EVENTS_GAME_CACHE_MAX = 0
WEBHOOK_EVENTS_SCAN_MAX_FILES = 0
WEBHOOK_USE_LOCAL_HISTORY = False
WEBHOOK_EVENTS_DIR = project_path("backups", "game_results", "events")
WEBHOOK_LOCAL_HISTORY_MAX_MB = 512
WEBHOOK_LOCAL_HISTORY_ALLOW_HUGE = False
WEBHOOK_EVENTS_FALLBACK = True
WEBHOOK_ISOLATE_RESULT_LOOKUP = True
WEBHOOK_LOOKUP_WORKER_TIMEOUT_SECONDS = 60
WEBHOOK_RESULT_LOOKUP_MAX_CONCURRENCY = 1
WEBHOOK_LOG_FULL_EVENTS = False
WEBHOOK_MAX_CONTENT_LENGTH_MB = 1
WEBHOOK_THREADED = False
WEBHOOK_EVENT_QUEUE_MAX = 2000
WEBHOOK_EVENT_WORKERS = 1

# Snapchat upload automation (Story + Spotlight)
SNAPCHAT_ENABLE = True
SNAPCHAT_AUTO_UPLOAD = False
SNAPCHAT_UPLOAD_ON_IG_FAILURE = False
SNAPCHAT_UPLOADER = "safe"  # "api" or "safe"
SNAPCHAT_COOKIES_FILE = "snapchat_cookies.json"
SNAPCHAT_PROFILE_DIR = "sessions/snapchat_chrome_profile"
SNAPCHAT_HEADLESS = False
SNAPCHAT_SAFE_SPOTLIGHT_ONLY = True
SNAPCHAT_CLIENT_ID = ""
SNAPCHAT_CLIENT_SECRET = ""
SNAPCHAT_REDIRECT_URI = ""
SNAPCHAT_PROFILE_ID = ""
SNAPCHAT_ACCESS_TOKEN_PATH = "secrets/snapchat_access_token.json"
SNAPCHAT_REFRESH_TOKEN_PATH = "secrets/snapchat_refresh_token.json"
SNAPCHAT_SCOPE = "snapchat-profile-api"
SNAPCHAT_API_BASE = "https://businessapi.snapchat.com"
SNAPCHAT_ENABLE_STORY_POST = True
SNAPCHAT_ENABLE_SPOTLIGHT_POST = True
SNAPCHAT_SPOTLIGHT_LOCALE = "en_US"
SNAPCHAT_SPOTLIGHT_SKIP_SAVE_TO_PROFILE = False
SNAPCHAT_USE_NON_IG_VARIANT = True
SNAPCHAT_RETRY_COUNT = 3
SNAPCHAT_TIMEOUT_SECONDS = 120

# X (Twitter) upload automation
X_ENABLE = True
X_AUTO_UPLOAD = True
X_UPLOAD_ON_IG_FAILURE = False
X_CONSUMER_KEY = ""
X_CONSUMER_SECRET = ""
X_ACCESS_TOKEN = ""
X_ACCESS_TOKEN_SECRET = ""
X_API_BASE = "https://api.x.com"
X_UPLOAD_API_URL = "https://upload.twitter.com/1.1/media/upload.json"
X_UPLOADER = "api"  # "api" or "safe"
X_COOKIES_FILE = "x_cookies.json"
X_HEADLESS = False
X_USE_NON_IG_VARIANT = True
X_SAFE_POST_READY_TIMEOUT_SECONDS = 60
X_SAFE_POST_CLICK_ATTEMPTS = 4
X_RETRY_COUNT = 3
X_TIMEOUT_SECONDS = 120

# Lemon8 safe upload automation
LEMON8_ENABLE = True
LEMON8_AUTO_UPLOAD = False
LEMON8_UPLOAD_ON_IG_FAILURE = False
LEMON8_UPLOADER = "safe"  # currently supports "safe"
LEMON8_COOKIES_FILE = "lemon8_cookies.json"
LEMON8_HEADLESS = False
LEMON8_USE_NON_IG_VARIANT = True

# Rednote (Xiaohongshu) safe upload automation
REDNOTE_ENABLE = True
REDNOTE_AUTO_UPLOAD = False
REDNOTE_UPLOAD_ON_IG_FAILURE = False
REDNOTE_UPLOADER = "safe"  # currently supports "safe"
REDNOTE_COOKIES_FILE = "rednote_cookies.json"
REDNOTE_HEADLESS = False
REDNOTE_USE_NON_IG_VARIANT = True

# Account Center export defaults (used by automation)
IG_EXPORT_ACCOUNT_CENTER_URL = "https://accountscenter.instagram.com/"
IG_EXPORT_PROFILE_NAME = "followerbattlegrounds"
IG_EXPORT_INFO_PERMISSIONS_LABEL = "Your information and permissions"
IG_EXPORT_EXPORT_INFO_LABEL = "Export your information"
IG_EXPORT_EXPORT_TO_DEVICE_LABEL = "Export to device"
IG_EXPORT_DATE_RANGE = "All time"
IG_EXPORT_FOLLOWERS_LABEL = "Followers and following"
IG_EXPORT_FORMAT_LABEL = "JSON"
IG_EXPORT_MEDIA_QUALITY_LABEL = "Low"
IG_EXPORT_PASSWORD = ""
IG_EXPORT_WAIT_FOR_READY = True
IG_EXPORT_MAX_WAIT_MINUTES = 90
IG_EXPORT_POLL_INTERVAL_SECONDS = 60
IG_EXPORT_DOWNLOAD_DIR = "Followers/exports"

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

# Fighter Arena performance mode (skip combat/collisions at huge counts)
FIGHTER_ARENA_SIMPLIFIED_MODE_THRESHOLD = 10000  # Enable simplified mode when alive > this
FIGHTER_ARENA_RANDOM_ELIMINATION_RATE = 0.015    # Fraction of alive eliminated per second in simplified mode
FIGHTER_ARENA_SIMPLIFIED_SPEED_MULTIPLIER = 2.5  # Speed boost for simplified mode movement
FIGHTER_ARENA_SIMPLIFIED_TURN_CHANCE = 0.12      # Direction change chance per frame in simplified mode
FIGHTER_ARENA_DELAY_MUSIC_UNTIL_SPEEDUP_END = False  # Start export music at countdown instead of waiting for speedup to end
FIGHTER_ARENA_LATE_GAME_THRESHOLD = 400
FIGHTER_ARENA_LATE_GAME_ATTACK_DAMAGE = 10
FIGHTER_ARENA_LATE_GAME_HP = 40

# ===== FOLLOWERS.IO SETTINGS =====
FOLLOWERS_IO_ARENA_RECT = FIGHTER_ARENA_RECT
FOLLOWERS_IO_MAX_GAME_TIME = 720.0

FOLLOWERS_IO_INITIAL_MASS = 36.0
FOLLOWERS_IO_MIN_MASS = 8.0
FOLLOWERS_IO_RADIUS_SCALE = 0.62
FOLLOWERS_IO_BASE_SPEED = 6.0
FOLLOWERS_IO_SPEED_EXPONENT = 0.34
FOLLOWERS_IO_MASS_DECAY_RATE = 0.016
FOLLOWERS_IO_FOOD_GAIN_RATE = 0.20
FOLLOWERS_IO_ABSORB_RATIO = 0.90
FOLLOWERS_IO_EAT_RATIO = 1.12

FOLLOWERS_IO_SIMPLIFIED_THRESHOLD = 12000
FOLLOWERS_IO_COLLISION_FULL_THRESHOLD = 6500
FOLLOWERS_IO_TARGET_DETAILED_UPDATES = 16000
FOLLOWERS_IO_RANDOM_CONSUMPTION_RATE = 0.020
FOLLOWERS_IO_RANDOM_CONSUMPTION_MIN = 16
FOLLOWERS_IO_RANDOM_CONSUMPTION_MAX = 1300
FOLLOWERS_IO_MAX_DETAILED_CONSUMPTIONS = 1800

FOLLOWERS_IO_SPLIT_MIN_MASS = 92.0
FOLLOWERS_IO_SPLIT_COOLDOWN = 2.0
FOLLOWERS_IO_SPLIT_BOOST_DURATION = 0.55
FOLLOWERS_IO_SPLIT_BOOST_MULTIPLIER = 1.9
FOLLOWERS_IO_SPLIT_MASS_COST_RATIO = 0.18
FOLLOWERS_IO_SPLIT_CHANCE_PER_SECOND = 0.10

FOLLOWERS_IO_EJECT_MIN_MASS = 64.0
FOLLOWERS_IO_EJECT_MASS_AMOUNT = 2.0
FOLLOWERS_IO_EJECT_CHANCE_PER_SECOND = 0.35
FOLLOWERS_IO_EJECT_SPEED = 7.0

FOLLOWERS_IO_MAX_FOOD_PARTICLES = 3000
FOLLOWERS_IO_FOOD_TTL = 10.0
FOLLOWERS_IO_FOOD_BANK_RELEASE_RATE = 90.0

FOLLOWERS_IO_EXPORT_SPEEDUP_FACTOR = 8.0
FOLLOWERS_IO_EXPORT_SPEEDUP_END_ALIVE = 500

FOLLOWERS_IO_BG_COLOR = (232, 239, 244)
FOLLOWERS_IO_GRID_COLOR = (202, 216, 225)
FOLLOWERS_IO_BORDER_COLOR = (20, 20, 20)
FOLLOWERS_IO_FOOD_COLOR = (115, 168, 121)
FOLLOWERS_IO_GRID_STEP = 32

FOLLOWERS_IO_RENDER_MAX_PLAYERS = 8000
FOLLOWERS_IO_RENDER_MIN_PLAYERS = 1800
FOLLOWERS_IO_RENDER_HIGH_POP_THRESHOLD = 50000
FOLLOWERS_IO_SIMPLE_RENDER_THRESHOLD = 12000
FOLLOWERS_IO_FOOD_DRAW_LIMIT = 1600

FOLLOWERS_IO_DAY_COUNTER_OFFSET = 18
FOLLOWERS_IO_ELIMINATION_TRACK_LIMIT = 400
FOLLOWERS_IO_ELIMINATION_LIST_SIZE = 0
FOLLOWERS_IO_ELIMINATION_TEXT_SIZE = 18
FOLLOWERS_IO_ELIMINATION_NAME_LENGTH = 16
FOLLOWERS_IO_ELIMINATION_LABEL = "Consumed:"
FOLLOWERS_IO_ELIMINATION_LIST_X_OFFSET = 0

# ===== CLUB PANEL SETTINGS =====
CLUB_PANEL_ENABLED = True
CLUB_PANEL_TEXT = "Club members are always visible and have a holy light."
CLUB_PANEL_WIDTH = 160
CLUB_PANEL_PADDING = 6
CLUB_PANEL_ALPHA = 150
CLUB_PANEL_AVATAR_SIZE = 42
CLUB_PANEL_TEXT_SIZE = 16
CLUB_PANEL_SPACING = 8

# ===== MAZE RUSH SETTINGS =====
MAZE_RUSH_CELL_SIZE = 25
MAZE_RUSH_PLAYER_SIZE = 12
MAZE_RUSH_TARGET_SECONDS = 52.5
MAZE_RUSH_SPEED_MULTIPLIER = 1.0
MAZE_RUSH_SPEED_MULTIPLIER_MIN = 0.5
MAZE_RUSH_SPEED_MULTIPLIER_MAX = 1.5
MAZE_RUSH_SPEED_CHANGE_INTERVAL = 2.0
# Maze arena alignment tweak (used to better frame 1:1 Instagram crops).
MAZE_RUSH_ARENA_OFFSET_X = 0
MAZE_RUSH_ARENA_OFFSET_Y = 46
MAZE_RUSH_ARENA_RECT = (
    FIGHTER_ARENA_RECT[0] + MAZE_RUSH_ARENA_OFFSET_X,
    FIGHTER_ARENA_RECT[1] + MAZE_RUSH_ARENA_OFFSET_Y,
    FIGHTER_ARENA_RECT[2],
    FIGHTER_ARENA_RECT[3],
)
# Shared square-profile layout rect for games that should match Maze Rush framing.
FIGHTER_ARENA_MODE_RECT = MAZE_RUSH_ARENA_RECT
SNAKE_ESCAPE_ARENA_RECT = MAZE_RUSH_ARENA_RECT
SIDE_CHOICE_ARENA_RECT = MAZE_RUSH_ARENA_RECT
DISCORD_SIGNAL_ARENA_RECT = MAZE_RUSH_ARENA_RECT
MAZE_RUSH_SHOW_TITLE = True
MAZE_RUSH_SHOW_SUBTITLE = True
SQUARE_ARENA_HEADER_Y_SHIFT = -4
MAZE_RUSH_PROMPT_ABOVE_ARENA_MARGIN = 8
MAZE_RUSH_ENDSCREEN_Y_OFFSET = 24
MAZE_RUSH_WALL_THICKNESS = 3
MAZE_RUSH_WALL_COLOR = (30, 30, 30)
MAZE_RUSH_FLOOR_COLOR = (180, 180, 190)
MAZE_RUSH_BORDER_COLOR = (0, 0, 0)
MAZE_RUSH_START_COLOR = (80, 200, 120)
MAZE_RUSH_EXIT_COLOR = (255, 120, 80)
MAZE_RUSH_MARKER_SCALE = 0.55
MAZE_RUSH_DAY_COUNTER_OFFSET = 14
MAZE_RUSH_DAY_COUNTER_FONT_SIZE = 32
MAZE_RUSH_CLUB_GLOW_COLOR = (255, 240, 190)
MAZE_RUSH_CLUB_GLOW_ALPHA = 180
MAZE_RUSH_CLUB_GLOW_LAYERS = 3
MAZE_RUSH_CLUB_GLOW_PADDING = 3
MAZE_RUSH_CLUB_PANEL_ENABLED = True
MAZE_RUSH_CLUB_PANEL_TEXT = "Club members stay visible and have a holy light."
MAZE_RUSH_CLUB_PANEL_WIDTH = 160
MAZE_RUSH_CLUB_PANEL_HEIGHT = 80
MAZE_RUSH_CLUB_PANEL_PADDING = 6
MAZE_RUSH_CLUB_PANEL_ALPHA = 150
MAZE_RUSH_CLUB_PANEL_AVATAR_SIZE = 42
MAZE_RUSH_CLUB_PANEL_TEXT_SIZE = 16

# ===== FLAPPY FOLLOWERS SETTINGS =====
FLAPPY_PLAYER_X_RATIO = 0.32
FLAPPY_PLAYER_X_VARIANCE = 18.0
FLAPPY_BIRD_SIZE = 30.0
FLAPPY_GRAVITY = 1200.0
FLAPPY_FLAP_VELOCITY = 380.0
FLAPPY_MAX_FALL_SPEED = 520.0
FLAPPY_FLAP_COOLDOWN = 0.18
FLAPPY_REACTION_DISTANCE = 260.0
FLAPPY_FLAP_BUFFER = 8.0
FLAPPY_GAP_BIAS_SCALE = 0.35
FLAPPY_TARGET_JITTER = 0.12
FLAPPY_PANIC_MARGIN = 28.0

FLAPPY_PIPE_WIDTH = 70.0
FLAPPY_PIPE_SPACING = 220.0
FLAPPY_PIPE_START_OFFSET = 120.0
FLAPPY_PIPE_SPEED = 160.0
FLAPPY_SPEED_BOOST = 80.0

FLAPPY_GAP_SIZE = 160.0
FLAPPY_MIN_GAP_SIZE = 110.0
FLAPPY_GAP_SHRINK = 50.0
FLAPPY_GAP_EDGE_PADDING = 12.0
FLAPPY_DIFFICULTY_RAMP = 50.0
FLAPPY_MAX_GAME_TIME = 90.0

# ===== TINY FOLLOWERS SETTINGS =====
TINY_ARENA_RECT = (0, 100, SCREEN_WIDTH, 780)
TINY_PLAYER_SIZE = 30.0
TINY_START_X = 14.0
TINY_START_X_VARIANCE = 6.0

TINY_GRAVITY = 820.0
TINY_DIVE_FORCE = 2100.0
TINY_DIVE_GROUND_BOOST = 980.0
TINY_AIR_FORWARD_ACCEL = 285.0
TINY_PASSIVE_FORWARD_ACCEL = 50.0
TINY_DIVE_AIR_FORWARD_BONUS = 205.0
TINY_DIVE_HOLD_RAMP_RATE = 1.8
TINY_DIVE_HOLD_MAX_MULT = 2.4
TINY_DIVE_HOLD_RELEASE_DECAY = 3.0
TINY_DIVE_HOLD_FALL_BONUS = 420.0
TINY_DIVE_CHARGE_PUMP_BONUS = 1.35
TINY_MAX_FALL_SPEED = 780.0
TINY_MAX_UPWARD_AIR_SPEED = 1100.0
TINY_TOTAL_SPEED_ABS_CAP = 1000.0
TINY_MAX_AIR_SPEED = 620.0
TINY_AIR_SPEED_CAP_SCALE = 1.0
TINY_AIR_SPEED_CAP_DECAY = 0.30
TINY_AIR_SPEED_ABS_CAP = 980.0
TINY_AIR_TOP_MARGIN = 0.0

TINY_MIN_GROUND_SPEED = 150.0
TINY_MAX_GROUND_SPEED = 560.0
TINY_MIN_AIR_SPEED = 115.0
TINY_GROUND_DRAG = 0.12
TINY_GROUND_GRAVITY_SCALE = 0.12
TINY_DOWNHILL_ACCEL_GAIN = 540.0
TINY_DOWNHILL_ACCEL_CURVE = 1.18
TINY_DOWNHILL_DRAG_REDUCTION = 0.55
TINY_DOWNHILL_EXTRA_SPEED_CAP = 280.0
TINY_DOWNHILL_SPEED_ABS_CAP = 980.0
TINY_DOWNHILL_LANDING_MIN_SLOPE = 0.02
TINY_DOWNHILL_LANDING_TRANSFER = 1.0
TINY_DOWNHILL_LANDING_SPEED_CAP = 980.0
TINY_DOWNHILL_MOMENTUM_HOLD_TIME = 1.20
TINY_DOWNHILL_MOMENTUM_DECAY = 95.0
TINY_DOWNHILL_MOMENTUM_ABS_CAP = 980.0
TINY_UPHILL_MISMATCH_CARRY_REDUCTION = 1.0
TINY_UPHILL_CARRY_TRANSFER = 1.0
TINY_JUMP_LANDING_MIN_AIRTIME = 0.30
TINY_LANDING_SLOPE_THRESHOLD = 0.02
TINY_JUMP_DOWNHILL_SPEED_GAIN = 0.32
TINY_JUMP_UPHILL_SPEED_LOSS = 0.56
TINY_MAX_LAUNCH_UP_SPEED = 1100.0
TINY_LAUNCH_CLEARANCE = 1.75
TINY_PERFECT_TAKEOFF_VY = 230.0
TINY_HIT_ANGLE_THRESHOLD = 2.4
TINY_HIT_SPEED_LOSS = 0.56
TINY_UPHILL_MISMATCH_SLOPE = -0.06
TINY_UPHILL_MISMATCH_MIN_DOWN_SPEED = 130.0
TINY_UPHILL_MISMATCH_SPEED_LOSS = 0.92
TINY_UPHILL_MISMATCH_MIN_KEEP = 0.06
TINY_HORIZONTAL_PUMP_GAIN = 0.95
TINY_HORIZONTAL_PUMP_CAP = 700.0
TINY_HORIZONTAL_CHARGE_BONUS = 1.4
TINY_HORIZONTAL_JUMP_BONUS = 1.25
TINY_HORIZONTAL_JUMP_REF_HEIGHT = 220.0
TINY_HORIZONTAL_MISS_PENALTY = 1.2
TINY_HORIZONTAL_UPHILL_PENALTY = 1.45
TINY_HORIZONTAL_MIN_TANGENT = 0.3
TINY_PUMP_MIN_DOWN_SPEED = 135.0
TINY_PUMP_DOWNHILL_SLOPE = 0.03
TINY_PUMP_SPEED_GAIN = 0.70
TINY_PUMP_STREAK_STEP = 1.20
TINY_PUMP_STREAK_MAX = 7.0
TINY_PUMP_STREAK_MULT = 0.24
TINY_PUMP_STREAK_DECAY = 0.40
TINY_PUMP_LAUNCH_BONUS = 1.35
TINY_COAST_SPEED_BLEED = 0.50
TINY_MISSED_PUMP_SPEED_LOSS = 0.40
TINY_MISSED_PUMP_DOWNHILL_SLOPE = 0.035
TINY_MISSED_PUMP_MIN_DOWN_SPEED = 84.0
TINY_VERTICAL_SPEED_REWARD = 1.55
TINY_VERTICAL_SPEED_REWARD_CAP = 380.0
TINY_VERTICAL_REWARD_MIN_HEIGHT = 14.0
TINY_VERTICAL_REWARD_DOWNHILL_BONUS = 0.35
TINY_VERTICAL_SPEED_CAP_BONUS = 300.0
TINY_VERTICAL_SPEED_CAP_GAIN = 1.45
TINY_LAUNCH_BOOST_FACTOR = 0.76
TINY_LAUNCH_BOOST_CAP = 520.0
TINY_CREST_LOOKAHEAD = 42.0
TINY_CREST_DROP_THRESHOLD = 3.5
TINY_LAUNCH_CREST_SLOPE_MIN = -0.45
TINY_LAUNCH_CREST_SLOPE_MAX = 0.08
TINY_LAUNCH_NEAR_SLOPE_MIN = -0.25
TINY_LAUNCH_FAR_SLOPE_MIN = -0.02
TINY_LAUNCH_MAX_RISE_AHEAD = 72.0
TINY_LAUNCH_MIN_RISE_AHEAD = 4.0
TINY_LAUNCH_MIN_FLATTENING = 0.018
TINY_RELEASE_MARGIN = 92.0
TINY_DIVE_HOLD_BIAS = 0.36

TINY_DECISION_INTERVAL_MIN = 0.08
TINY_DECISION_INTERVAL_MAX = 0.18
TINY_LOOKAHEAD_BASE = 138.0
TINY_LOOKAHEAD_TIME = 0.42
TINY_DIVE_ENTER_SLOPE = 0.05
TINY_DIVE_EXIT_SLOPE = -0.012
TINY_AIR_DIVE_VELOCITY = 95.0
TINY_AIR_DIVE_CLEARANCE = 42.0
TINY_AIR_RELEASE_VELOCITY = 34.0
TINY_AIR_RELEASE_CLEARANCE = 14.0

TINY_KEYPOINT_MIN_DX = 170.0
TINY_KEYPOINT_MAX_DX = 280.0
TINY_KEYPOINT_MIN_DY = 45.0
TINY_KEYPOINT_MAX_DY = 105.0
TINY_TERRAIN_SHARPNESS = 0.58
TINY_MIN_HEIGHT_PADDING = 540.0
TINY_MAX_HEIGHT_PADDING = 20.0
TINY_START_HEIGHT_RATIO = 0.90
TINY_ANCHOR_HEIGHT_RATIO = 0.86
TINY_SECOND_ISLAND_START_HEIGHT_RATIO = 0.89
TINY_CLIFF_DROP = 120.0
TINY_FIRST_ISLAND_LENGTH = 10400.0
TINY_ENABLE_ISLAND_GAP = False
TINY_WATER_GAP_WIDTH = 240.0
TINY_SECOND_ISLAND_ENTRY_LENGTH = 210.0
TINY_SECOND_ISLAND_ENTRY_RISE = 64.0
TINY_SECOND_ISLAND_LENGTH = 12800.0
TINY_FINISH_OFFSET = 11800.0
TINY_WATER_FLOOR_OFFSET = 280.0

TINY_MAX_GAME_TIME = 0.0
TINY_FINISH_GRACE_DURATION = 6.0
TINY_DIFFICULTY_RAMP = 55.0
TINY_WATER_ELIMINATION_MARGIN = 120.0
TINY_DISTANCE_SCALE = 0.10

TINY_CAMERA_FOLLOW_RATIO = 0.35
TINY_CAMERA_SMOOTHING = 5.0
TINY_CAMERA_ZOOM_X = 0.66
TINY_CAMERA_ZOOM_Y = 0.66
TINY_CAMERA_HORIZONTAL_ANCHOR = 0.58
TINY_CAMERA_VERTICAL_ANCHOR = 0.92
TINY_CAMERA_LEAD_IN = 60.0
TINY_CAMERA_FINISH_PADDING = 120.0

TINY_TERRAIN_RENDER_STEP = 2
TINY_RENDER_MAX_PLAYERS = 6500
TINY_RENDER_HIGH_POP_THRESHOLD = 25000
TINY_RENDER_MIN_PLAYERS = 1600
TINY_SIMPLE_AVATAR_THRESHOLD = 90000
TINY_VISIBILITY_PADDING_X = 40.0
TINY_VISIBILITY_PADDING_Y = 140.0
TINY_ELIMINATION_TRACK_LIMIT = 400
TINY_HIGH_POP_OPTIMIZATION_THRESHOLD = 25000
TINY_TARGET_DETAILED_UPDATES_PER_FRAME = 14000
TINY_MAX_DECISION_THROTTLE = 3.5

TINY_DAY_COUNTER_OFFSET = 18
TINY_ELIMINATION_LIST_SIZE = 0
TINY_ELIMINATION_TEXT_SIZE = 18
TINY_ELIMINATION_NAME_LENGTH = 16
TINY_ELIMINATION_LABEL = "Splash Out:"
TINY_ELIMINATION_LIST_X_OFFSET = 0

TINY_SKY_TOP_COLOR = (180, 224, 255)
TINY_SKY_BOTTOM_COLOR = (120, 188, 240)
TINY_WATER_COLOR = (72, 164, 224)
TINY_WATER_HIGHLIGHT = (125, 213, 255)
TINY_TERRAIN_COLOR = (96, 189, 86)
TINY_TERRAIN_SHADOW_COLOR = (58, 133, 64)
TINY_TERRAIN_RIDGE_COLOR = (214, 242, 148)
TINY_NOISE_TEXTURE = "assets/tiny_followers/noise.png"
TINY_NOISE_ALPHA = 34

TINY_BACKGROUND_MUSIC_PATH = "assets/Sydney Tour Song adjusted.m4a"

# ===== JETPACK FOLLOWERS SETTINGS =====
JETPACK_ARENA_RECT = FIGHTER_ARENA_RECT
JETPACK_PLAYER_X_RATIO = 0.32
JETPACK_PLAYER_X_VARIANCE = 28.0
JETPACK_PLAYER_SIZE = 30.0
JETPACK_GRAVITY = 1080.0
JETPACK_THRUST = 1820.0
JETPACK_MAX_FALL_SPEED = 520.0
JETPACK_MAX_RISE_SPEED = 560.0
JETPACK_REACTION_DISTANCE = 340.0
JETPACK_REACTION_DISTANCE_SCALE_MIN = 0.58
JETPACK_REACTION_DISTANCE_SCALE_MAX = 0.84
JETPACK_OBSTACLE_LOOKAHEAD_MULT = 1.15
JETPACK_ROCKET_LOOKAHEAD_MULT = 1.05
JETPACK_OBSTACLE_HORIZON_MULT = 1.05
JETPACK_ROCKET_HORIZON_MULT = 1.12
JETPACK_SCORE_HORIZON_MULT = 1.28
JETPACK_AVOID_MARGIN = 14.0
JETPACK_TARGET_JITTER = 14.0
JETPACK_THRUST_BUFFER = 8.0
JETPACK_CONTROL_GAIN = 3.2
JETPACK_CONTROL_DEADBAND = 12.0
JETPACK_BOUNDARY_MARGIN = 36.0
JETPACK_BOUNDARY_SOFT_CAP = 210.0
JETPACK_OBSTACLE_EXTRA_CLEARANCE = 24.0
JETPACK_ROCKET_EVADE_MULTIPLIER = 7.8
JETPACK_LOOKAHEAD_MIN_SPEED = 95.0
JETPACK_HAZARD_ESCAPE_SPEED = 980.0
JETPACK_MAX_CONTROLLED_DESCENT = 240.0
JETPACK_ESCAPE_UP_ACCEL = 3000.0
JETPACK_ESCAPE_DOWN_ACCEL = 1750.0
JETPACK_ESCAPE_INTENT_ATTACK = 5.2
JETPACK_ESCAPE_INTENT_RELEASE = 2.6
JETPACK_ESCAPE_DOWNWARD_BIAS = 1.26
JETPACK_ESCAPE_UP_MAX_VY = 515.0
JETPACK_ESCAPE_DOWN_MAX_VY = 280.0
JETPACK_DOWNWARD_TARGET_PENALTY = 0.038
JETPACK_TARGET_MOVE_PENALTY = 0.012
JETPACK_HOVER_THRUST_BASE = 0.58
JETPACK_HOVER_THRUST_RESPONSE = 6.8
JETPACK_VERTICAL_OSCILLATION_AMPLITUDE = 20.0
JETPACK_VERTICAL_OSCILLATION_SPEED = 1.85
JETPACK_STEER_ASSIST = 0.34
JETPACK_TARGET_SMOOTHING = 5.6
JETPACK_SEPARATION_GAP = 4.6
JETPACK_SEPARATION_STRENGTH = 7.0
JETPACK_SEPARATION_X_RANGE = 6.5
JETPACK_PATH_VARIATION = 3.8
JETPACK_X_SWAY_AMPLITUDE = 34.0
JETPACK_X_SWAY_SPEED = 1.3
JETPACK_X_SWAY_LERP = 6.0
JETPACK_X_SWAY_JITTER = 0.2
JETPACK_CRUISE_WOBBLE_AMPLITUDE = 68.0
JETPACK_CRUISE_WOBBLE_SPEED = 1.1
JETPACK_CRUISE_BIAS_RANGE = 130.0
JETPACK_CRUISE_BIAS_DRIFT_MIN = 10.0
JETPACK_CRUISE_BIAS_DRIFT_MAX = 24.0
JETPACK_CRUISE_BIAS_DRIFT_SPEED_MIN = 0.35
JETPACK_CRUISE_BIAS_DRIFT_SPEED_MAX = 0.85

JETPACK_WORLD_SPEED = 130.0
JETPACK_SPEED_BOOST = 70.0
JETPACK_DIFFICULTY_RAMP = 42.0
# Set <= 0 to disable hard time limit (round ends only when one survivor remains).
JETPACK_MAX_GAME_TIME = 0.0
JETPACK_DISTANCE_SCALE = 0.06
JETPACK_BACKGROUND_SCROLL_FACTOR = 1.2

JETPACK_OBSTACLE_WIDTH = 86.0
JETPACK_OBSTACLE_HEIGHT_MIN = 46.0
JETPACK_OBSTACLE_HEIGHT_MAX = 132.0
JETPACK_OBSTACLE_SPAWN_MIN = 1.25
JETPACK_OBSTACLE_SPAWN_MAX = 2.05
JETPACK_OBSTACLE_SPAWN_OFFSET = 140.0
JETPACK_OBSTACLE_EDGE_PADDING = 18.0
JETPACK_OBSTACLE_HITBOX_INSET_X = 12.0
JETPACK_OBSTACLE_HITBOX_INSET_Y = 14.0
JETPACK_DOUBLE_OBSTACLE_CHANCE = 0.16
JETPACK_OBSTACLE_PAIR_X_GAP = (120.0, 210.0)
JETPACK_OBSTACLE_PAIR_Y_GAP_MAX = 180.0

JETPACK_ROCKET_ENABLED = True
JETPACK_ROCKET_WARMUP_TIME = 36.0
JETPACK_ROCKET_SPAWN_INTERVAL_MIN = 7.0
JETPACK_ROCKET_SPAWN_INTERVAL_MAX = 11.5
JETPACK_ROCKET_SPEED = 230.0
JETPACK_ROCKET_TRACK_SPEED = 132.0
JETPACK_ROCKET_TRACK_STOP_DISTANCE = 80.0
JETPACK_ROCKET_WIDTH = 68.0
JETPACK_ROCKET_HEIGHT = 30.0
JETPACK_ROCKET_SPAWN_OFFSET = 220.0
JETPACK_ROCKET_MAX_AGE = 10.0
JETPACK_ROCKET_WARNING_DISTANCE = 120.0

JETPACK_BG_COLOR = (172, 214, 246)
JETPACK_DAY_COUNTER_OFFSET = 18
JETPACK_ELIMINATION_LIST_SIZE = 0
JETPACK_ELIMINATION_TEXT_SIZE = 18
JETPACK_ELIMINATION_NAME_LENGTH = 16
JETPACK_ELIMINATION_LABEL = "Eliminated:"
JETPACK_ELIMINATION_LIST_X_OFFSET = 0
JETPACK_ELIMINATION_TRACK_LIMIT = 400

JETPACK_ASSET_DIR = "assets/jetpack_followers"
JETPACK_BACKGROUND_IMAGE = "assets/jetpack_followers/BackdropMain.png"
JETPACK_ZAPPER_IMAGES = [
    "assets/jetpack_followers/Zapper1.png",
    "assets/jetpack_followers/Zapper2.png",
    "assets/jetpack_followers/Zapper3.png",
    "assets/jetpack_followers/Zapper4.png",
]
JETPACK_ZAPPER_ANIMATION_FPS = 10.0
JETPACK_ZAPPER_ANIMATION_SPEED_MIN = 0.85
JETPACK_ZAPPER_ANIMATION_SPEED_MAX = 1.2
JETPACK_ROCKET_IMAGE = "assets/jetpack_followers/Rocket.png"
JETPACK_ROCKET_WARNING_IMAGE = "assets/jetpack_followers/RocketWarning.png"
JETPACK_FIRE_IMAGE = "assets/jetpack_followers/FlyFire2.png"
JETPACK_SHOW_THRUST_FIRE = True
JETPACK_BACKGROUND_MUSIC_PATH = "assets/Sydney Tour Song adjusted.m4a"

# ===== CROSSY FOLLOWERS SETTINGS =====
# Full-screen arena, matching Doodle Followers layout.
CROSSY_ARENA_RECT = (0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)
CROSSY_LANE_COUNT = 9
CROSSY_ROW_HEIGHT = 56.0
CROSSY_START_ROW = 8
CROSSY_INITIAL_ROWS = 32
CROSSY_ROWS_AHEAD = 34
CROSSY_ROWS_BEHIND = 10
CROSSY_CAMERA_ROW_OFFSET = 6.0
CROSSY_CAMERA_SMOOTH = 7.0
CROSSY_FALL_BEHIND_ROWS = 4
CROSSY_MAX_GAME_TIME = 85.0
CROSSY_MOVE_COOLDOWN = 0.25
CROSSY_PLAYER_COUNT_MIN = 10
CROSSY_PLAYER_COUNT_MAX = 20
CROSSY_PLAYER_RADIUS = 15.0
CROSSY_PLAYER_SIZE = 30.0

# Enable true 3D Panda renderer that uses Expo-Crossy-Road OBJ assets.
# Set False to use the legacy 2D pygame renderer.
CROSSY_USE_3D_RENDERER = True
CROSSY_3D_CAMERA_POS = (0.0, -2.9, 2.8)
CROSSY_3D_CAMERA_LOOK_AT = (0.0, 0.0, 0.0)
CROSSY_3D_ORTHO_VIEW_HEIGHT = 26.0
CROSSY_3D_WORLD_EASING = 0.03
CROSSY_3D_WORLD_X_MIN = -1.0
CROSSY_3D_WORLD_X_MAX = 1.0
CROSSY_3D_WORLD_BASE_OFFSET = -3.5
CROSSY_3D_ROW_VISUAL_WIDTH = 25.0
CROSSY_3D_AMBIENT_INTENSITY = 1.8
CROSSY_3D_DIRECTIONAL_INTENSITY = 1.0
CROSSY_3D_LIGHT_POS = (20.0, 0.05, 30.0)
CROSSY_3D_END_SCREEN_DURATION = 5.0

CROSSY_BG_COLOR = (164, 197, 226)
CROSSY_DAY_COUNTER_OFFSET = 60
CROSSY_ELIMINATION_LIST_SIZE = 6
CROSSY_ELIMINATION_TEXT_SIZE = 18
CROSSY_ELIMINATION_NAME_LENGTH = 16
CROSSY_ELIMINATION_LABEL = "Eliminated:"
CROSSY_ELIMINATION_LIST_X_OFFSET = 0
CROSSY_ELIMINATION_TRACK_LIMIT = 400

CROSSY_ASSET_DIR = "assets/crossy_followers"
CROSSY_GRASS_LIGHT_TEXTURE = "assets/crossy_followers/grass_light.png"
CROSSY_GRASS_DARK_TEXTURE = "assets/crossy_followers/grass_dark.png"
CROSSY_ROAD_STRIPES_TEXTURE = "assets/crossy_followers/road_stripes.png"
CROSSY_ROAD_BLANK_TEXTURE = "assets/crossy_followers/road_blank.png"
CROSSY_RIVER_TEXTURE = "assets/crossy_followers/river.png"
CROSSY_RAILROAD_TEXTURE = "assets/crossy_followers/railroad.png"

CROSSY_CAR_SPRITES = [
    "blue_car",
    "green_car",
    "orange_car",
    "police_car",
    "purple_car",
    "red_truck",
    "blue_truck",
    "taxi",
]
CROSSY_LOG_SPRITES = ["log0", "log1", "log2", "log3"]
CROSSY_TREE_SPRITES = ["tree0", "tree1", "tree2", "tree3"]
CROSSY_BOULDER_SPRITES = ["boulder0", "boulder1"]

# ===== DOODLE FOLLOWERS SETTINGS =====
# Full-screen arena for Doodle Followers (no boxed playfield).
DOODLE_ARENA_RECT = (0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)
# Keep camera centering consistent with the previous arena height (500 + 100).
DOODLE_CAMERA_VIEW_HEIGHT = FIGHTER_ARENA_RECT[3] + 100

DOODLE_PLAYER_RADIUS = 16.0
DOODLE_PLAYER_SIZE = 32.0
DOODLE_GRAVITY = 1200.0
DOODLE_MAX_FALL_SPEED = 900.0
DOODLE_JUMP_VELOCITY = -620.0
DOODLE_SPRING_VELOCITY = -900.0
DOODLE_TRAMPOLINE_VELOCITY = -1100.0
DOODLE_MOVE_SPEED = 160.0
DOODLE_MOVE_SMOOTH = 8.0
DOODLE_AI_RETARGET_MIN = 0.18
DOODLE_AI_RETARGET_MAX = 0.5
DOODLE_AIM_MIN = 40.0
DOODLE_AIM_MAX = 220.0
DOODLE_HORIZONTAL_REACH_FACTOR = 1.15
DOODLE_FALL_LOOKAHEAD_MIN = 8.0
DOODLE_FALL_LOOKAHEAD_MAX = 260.0
DOODLE_AIM_ERROR_RANGE = 0.08
DOODLE_AI_VERTICAL_WEIGHT = 0.35
DOODLE_PLATFORM_PENALTY_BREAKABLE = 0.18
DOODLE_PLATFORM_PENALTY_MOVING = 0.1
DOODLE_PLATFORM_PENALTY_TRAMPOLINE = 0.08
DOODLE_PANIC_SPEED_MULTIPLIER = 1.45
DOODLE_PANIC_FALL_SPEED = 320.0
DOODLE_MOVE_GAIN_BASE = 3.0
DOODLE_MOVE_GAIN_BOOST = 3.0
DOODLE_MOVE_GAIN_DISTANCE = 180.0
DOODLE_MOVE_SMOOTH_BOOST = 6.0
DOODLE_MOVE_SMOOTH_DISTANCE = 180.0
DOODLE_JUMP_HEIGHT_FACTOR = 0.75
DOODLE_REACH_SAFETY = 0.85
DOODLE_TARGET_SPREAD = 0.25
DOODLE_JUMP_TARGET_REACH_SAFETY = 0.5
DOODLE_JUMP_CROSS_SCREEN_SPEED = 520.0
DOODLE_JUMP_GAIN_MULTIPLIER = 1.8
DOODLE_JUMP_SMOOTH_MULTIPLIER = 1.4
DOODLE_HORIZ_ACCEL = 900.0
DOODLE_HORIZ_ACCEL_JUMP = 1200.0
DOODLE_APEX_X_RATIO = 0.5
DOODLE_LANDING_BRAKE_FACTOR = 4.0
DOODLE_LANDING_BRAKE_LOOKAHEAD = 140.0
DOODLE_LANDING_BRAKE_MIN_VX = 40.0
DOODLE_HORIZONTAL_JITTER = 0.22
DOODLE_HORIZONTAL_WOBBLE_SPEED = 1.8
DOODLE_JUMP_HEIGHT_VARIANCE = 0.12
DOODLE_JITTER_HEIGHT_RAMP = 2000.0
DOODLE_JITTER_MAX_MULT = 1.35
DOODLE_LEADER_AIRTIME_SLOW = 1.15
DOODLE_EXPORT_TIME_SCALE = 0.4

DOODLE_PLATFORM_WIDTH = 90.0
DOODLE_PLATFORM_HEIGHT = 16.0
DOODLE_START_PLATFORM_MARGIN = 6.0
DOODLE_PLATFORM_SPACING_MIN = 55.0
DOODLE_PLATFORM_SPACING_MAX = 95.0
DOODLE_PLATFORM_SPACING_RAMP = 0.6
DOODLE_EARLY_DENSITY_HEIGHT = 1200.0
DOODLE_EARLY_SPACING_SCALE = 0.7
DOODLE_SAFE_GAP_RATIO = 0.85
DOODLE_PLATFORM_EDGE_PADDING = 30.0
DOODLE_MOVING_PLATFORM_CHANCE = 0.18
DOODLE_BREAK_PLATFORM_CHANCE = 0.0
DOODLE_TRAMPOLINE_CHANCE = 0.06
DOODLE_SPRING_CHANCE = 0.25
DOODLE_MOVING_PLATFORM_SPEED = 50.0
DOODLE_BREAK_DELAY = 0.1

DOODLE_MONSTER_CHANCE = 0.08
DOODLE_MAX_MONSTERS = 8
DOODLE_MONSTER_SPEED = 40.0
DOODLE_MONSTER_WIDTH = 36.0
DOODLE_MONSTER_HEIGHT = 34.0

DOODLE_CAMERA_FOLLOW_RATIO = 0.42
DOODLE_CAMERA_SMOOTH = 10.0
DOODLE_CAMERA_MAX_SPEED = 700.0
DOODLE_DIFFICULTY_HEIGHT = 2200.0
DOODLE_FALL_MARGIN = 0.0
DOODLE_OFFSCREEN_MARGIN = 0.0
DOODLE_DISABLE_BOOSTERS_HEIGHT = 10000.0
DOODLE_SOFTLOCK_TIMEOUT = 4.0
DOODLE_SOFTLOCK_PROGRESS_DELTA = 40.0
DOODLE_RESCUE_GAP_RATIO = 0.6

DOODLE_BG_COLOR = (248, 243, 224)
DOODLE_GRID_COLOR = (220, 210, 190)
DOODLE_GRID_SIZE = 40
DOODLE_GRID_SUBDIV = 20

DOODLE_PLATFORM_COLOR = (86, 185, 106)
DOODLE_PLATFORM_SHADOW = (60, 150, 80)
DOODLE_PLATFORM_HIGHLIGHT = (110, 210, 130)
DOODLE_PLATFORM_BORDER = (30, 80, 50)
DOODLE_MOVING_PLATFORM_COLOR = (70, 150, 210)
DOODLE_BREAK_PLATFORM_COLOR = (186, 120, 60)
DOODLE_TRAMPOLINE_COLOR = (220, 70, 70)
DOODLE_SPRING_COLOR = (40, 40, 40)
DOODLE_SPRING_HIGHLIGHT = (220, 220, 220)
DOODLE_MONSTER_COLOR = (90, 160, 200)
DOODLE_MONSTER_BORDER = (30, 60, 90)
DOODLE_MONSTER_EYE = (255, 255, 255)

DOODLE_DAY_COUNTER_OFFSET = 60
DOODLE_ELIMINATION_LIST_SIZE = 6
DOODLE_ELIMINATION_TEXT_SIZE = 18
DOODLE_ELIMINATION_NAME_LENGTH = 16
DOODLE_ELIMINATION_LABEL = "Eliminated:"
DOODLE_ELIMINATION_LIST_X_OFFSET = 0

# ===== SUPER FOLLOWER BROS SETTINGS =====
SUPER_FOLLOWER_BROS_ARENA_RECT = FIGHTER_ARENA_RECT
SUPER_FOLLOWER_BROS_TILE_SIZE = 16
SUPER_FOLLOWER_BROS_ROWS = 30
SUPER_FOLLOWER_BROS_COLS = 224
SUPER_FOLLOWER_BROS_PLAYER_RADIUS = 8.0
SUPER_FOLLOWER_BROS_PLAYER_SIZE = 16.0
SUPER_FOLLOWER_BROS_PLAYER_MATCH_TILESET = True
SUPER_FOLLOWER_BROS_BIG_SIZE_MULTIPLIER = 1.5
SUPER_FOLLOWER_BROS_GRAVITY = 1200.0
SUPER_FOLLOWER_BROS_MAX_FALL_SPEED = 900.0
SUPER_FOLLOWER_BROS_JUMP_VELOCITY = -460.0
SUPER_FOLLOWER_BROS_JUMP_HEIGHT = 172.0
SUPER_FOLLOWER_BROS_JUMP_VARIANCE = 0.08
SUPER_FOLLOWER_BROS_JUMP_COOLDOWN = 0.18
SUPER_FOLLOWER_BROS_RUN_SPEED = 140.0
SUPER_FOLLOWER_BROS_RUN_SPEED_VARIANCE = 20.0
SUPER_FOLLOWER_BROS_LOOKAHEAD = 28.0
SUPER_FOLLOWER_BROS_RANDOM_JUMP_CHANCE = 0.04
SUPER_FOLLOWER_BROS_STUCK_TIMEOUT = 1.35
SUPER_FOLLOWER_BROS_STUCK_PROGRESS_RATIO = 0.35
SUPER_FOLLOWER_BROS_STUCK_BACKTRACK_TIME = (0.45, 1.1)
SUPER_FOLLOWER_BROS_STUCK_SPEED_MULTIPLIER = 1.1
SUPER_FOLLOWER_BROS_STUCK_JUMP_COOLDOWN_MULTIPLIER = 0.65
SUPER_FOLLOWER_BROS_STUCK_JUMP_BOOST = 1.08
SUPER_FOLLOWER_BROS_STUCK_WALL_LOOKAHEAD = 24.0
SUPER_FOLLOWER_BROS_STUCK_REVERSE_BIAS = 0.8
SUPER_FOLLOWER_BROS_STUCK_BACKTRACK_MIN_DISTANCE = 170.0
SUPER_FOLLOWER_BROS_STUCK_BLOCKED_EXTRA_DISTANCE = 120.0
SUPER_FOLLOWER_BROS_STUCK_BACKTRACK_HARD_MAX_DISTANCE = 420.0
SUPER_FOLLOWER_BROS_STUCK_BACKTRACK_MAX_TIME = 3.0
SUPER_FOLLOWER_BROS_ITEM_SEEK_CHANCE = 0.35
SUPER_FOLLOWER_BROS_ITEM_SEEK_RANGE = 280.0
SUPER_FOLLOWER_BROS_ITEM_SEEK_BACKTRACK = 24.0
SUPER_FOLLOWER_BROS_ITEM_SEEK_INTERVAL = 0.35
SUPER_FOLLOWER_BROS_ITEM_SEEK_TOLERANCE = 6.0
SUPER_FOLLOWER_BROS_ITEM_SEEK_MAX_ADJUST = 0.6
SUPER_FOLLOWER_BROS_ITEM_SEEK_DROP = 40.0
SUPER_FOLLOWER_BROS_TIME_LIMIT = 400
SUPER_FOLLOWER_BROS_WORLD_LABEL = "1-1"
SUPER_FOLLOWER_BROS_CAMERA_RATIO = 0.35
SUPER_FOLLOWER_BROS_CAMERA_SMOOTH = 8.0
SUPER_FOLLOWER_BROS_START_X = 64.0
SUPER_FOLLOWER_BROS_CAMERA_START_X = 64.0
SUPER_FOLLOWER_BROS_START_Y = 420.0
SUPER_FOLLOWER_BROS_1_2_CAMERA_RATIO = 0.5
SUPER_FOLLOWER_BROS_1_2_CAMERA_START_X = 0.0
SUPER_FOLLOWER_BROS_1_2_CAMERA_ALLOW_BACKTRACK = True
SUPER_FOLLOWER_BROS_1_2_RESPAWN_Y_MARGIN = 80.0
SUPER_FOLLOWER_BROS_1_2_CAMERA_LEADER_MIN_Y = -96.0
SUPER_FOLLOWER_BROS_1_2_CAMERA_LEADER_MAX_Y = 24.0

SUPER_FOLLOWER_BROS_BG_COLOR = (92, 148, 252)
SUPER_FOLLOWER_BROS_GROUND_COLOR = (228, 130, 35)
SUPER_FOLLOWER_BROS_BRICK_COLOR = (200, 92, 32)
SUPER_FOLLOWER_BROS_QUESTION_COLOR = (240, 168, 48)
SUPER_FOLLOWER_BROS_PIPE_COLOR = (0, 168, 0)
SUPER_FOLLOWER_BROS_FLAG_COLOR = (248, 216, 48)
SUPER_FOLLOWER_BROS_FLAG_POLE_COLOR = (245, 245, 245)
SUPER_FOLLOWER_BROS_FLAG_WIDTH = 18.0
SUPER_FOLLOWER_BROS_FLAG_HEIGHT = 170.0
SUPER_FOLLOWER_BROS_FLAG_POLE_WIDTH = 4.0
SUPER_FOLLOWER_BROS_DAY_COUNTER_OFFSET = 18
SUPER_FOLLOWER_BROS_ARENA_BORDER = False
SUPER_FOLLOWER_BROS_BLOCK_BORDER = (60, 36, 18)
SUPER_FOLLOWER_BROS_BLOCK_BUMP_HEIGHT = 6.0
SUPER_FOLLOWER_BROS_BLOCK_BUMP_TIME = 0.16
SUPER_FOLLOWER_BROS_RENDER_MARGIN = 140
SUPER_FOLLOWER_BROS_DESPAWN_MARGIN = 220
SUPER_FOLLOWER_BROS_ENEMY_SIZE = 18.0
SUPER_FOLLOWER_BROS_ENEMY_SPEED = 60.0
SUPER_FOLLOWER_BROS_ENEMY_GRAVITY = 1200.0
SUPER_FOLLOWER_BROS_ENEMY_MAX_FALL_SPEED = 900.0
SUPER_FOLLOWER_BROS_ENEMY_SPAWN_LEAD = 200.0
SUPER_FOLLOWER_BROS_ENEMY_SPAWN_SPACING = 42.0
SUPER_FOLLOWER_BROS_ENEMY_COLOR = (168, 80, 32)
SUPER_FOLLOWER_BROS_KOOPA_COLOR = (40, 148, 72)
SUPER_FOLLOWER_BROS_ENEMY_OUTLINE = (70, 35, 15)
SUPER_FOLLOWER_BROS_ENEMY_EYE_COLOR = (245, 245, 245)
SUPER_FOLLOWER_BROS_ENEMY_PUPIL_COLOR = (30, 30, 30)
SUPER_FOLLOWER_BROS_KOOPA_SPEED_MULTIPLIER = 1.15
SUPER_FOLLOWER_BROS_KOOPA_SIZE_MULTIPLIER = 1.1
SUPER_FOLLOWER_BROS_SPRITE_SCALE = 2.5
SUPER_FOLLOWER_BROS_ENEMY_SHEET_PATH = "assets/super_follower_bros/smb_enemies_sheet.png"
SUPER_FOLLOWER_BROS_ENEMY_ANIM_TIME = 0.125
SUPER_FOLLOWER_BROS_ENEMY_RESPAWN_TIME = 10.0
SUPER_FOLLOWER_BROS_SHELL_SPEED = 220.0
SUPER_FOLLOWER_BROS_STOMP_BOUNCE = 0.6
SUPER_FOLLOWER_BROS_STOMP_ZONE = 0.7
SUPER_FOLLOWER_BROS_TILESET_PATH = "assets/super_follower_bros/tile_set.png"
SUPER_FOLLOWER_BROS_ITEM_OBJECTS_PATH = "assets/super_follower_bros/item_objects.png"
SUPER_FOLLOWER_BROS_TILESET_SCALE = 2.69
SUPER_FOLLOWER_BROS_ITEM_SCALE = 2.5
# Level 1-2 uses a baked background whose vertical origin differs from level-space.
# This offset (in design-space pixels) aligns colliders/blocks with visible tiles.
SUPER_FOLLOWER_BROS_1_2_VERTICAL_OFFSET = 0
# Final render shift for World 1-2 to place the arena content slightly lower.
SUPER_FOLLOWER_BROS_1_2_RENDER_Y_OFFSET = 14
SUPER_FOLLOWER_BROS_QUESTION_ANIM_TIME = 0.125
SUPER_FOLLOWER_BROS_SHOW_BLOCK_COINS = True
SUPER_FOLLOWER_BROS_COIN_ANIM_TIME = 0.08
SUPER_FOLLOWER_BROS_COIN_FLOAT_OFFSET = 0.2
SUPER_FOLLOWER_BROS_COIN_POP_TIME = 0.4
SUPER_FOLLOWER_BROS_POWERUP_RESPAWN_TIME = 20.0
SUPER_FOLLOWER_BROS_POWERUP_REVEAL_TIME = 0.6
SUPER_FOLLOWER_BROS_MUSHROOM_ALTERNATE_FIRE = True
SUPER_FOLLOWER_BROS_FIREFLOWER_ANIM_TIME = 0.03
SUPER_FOLLOWER_BROS_STAR_ANIM_TIME = 0.03
SUPER_FOLLOWER_BROS_STAR_DURATION = 10.0
SUPER_FOLLOWER_BROS_HURT_INVINCIBLE_TIME = 1.0
SUPER_FOLLOWER_BROS_FIRE_COOLDOWN = 0.7
SUPER_FOLLOWER_BROS_FIRE_RANGE = 260.0
SUPER_FOLLOWER_BROS_FIRE_CHANCE = 0.35
SUPER_FOLLOWER_BROS_FIRE_VERTICAL_TOLERANCE = 60.0
SUPER_FOLLOWER_BROS_FIREBALL_SPEED = 240.0
SUPER_FOLLOWER_BROS_FIREBALL_GRAVITY = 1200.0
SUPER_FOLLOWER_BROS_FIREBALL_BOUNCE = 320.0
SUPER_FOLLOWER_BROS_FIREBALL_LIFETIME = 6.0
SUPER_FOLLOWER_BROS_FIREBALL_ANIM_TIME = 0.12
SUPER_FOLLOWER_BROS_MINIMAP_ENABLED = True
SUPER_FOLLOWER_BROS_MINIMAP_SIZE = (220, 70)
SUPER_FOLLOWER_BROS_MINIMAP_PADDING = 12
SUPER_FOLLOWER_BROS_MINIMAP_BG = (0, 0, 0, 120)
SUPER_FOLLOWER_BROS_MINIMAP_BORDER = (40, 40, 40)
SUPER_FOLLOWER_BROS_MINIMAP_VIEWPORT = (255, 255, 255, 80)
SUPER_FOLLOWER_BROS_MINIMAP_DOT_RADIUS = 2
SUPER_FOLLOWER_BROS_MINIMAP_MAX_DOTS = 2000
SUPER_FOLLOWER_BROS_MINIMAP_ALIVE_COLOR = (80, 200, 120)
SUPER_FOLLOWER_BROS_MINIMAP_DEAD_COLOR = (200, 80, 80)
SUPER_FOLLOWER_BROS_MINIMAP_AVATAR_SIZE = 16
SUPER_FOLLOWER_BROS_MINIMAP_AVATAR_OFFSET = 14
SUPER_FOLLOWER_BROS_MINIMAP_AVATAR_MAX = 200
SUPER_FOLLOWER_BROS_SUBTITLE_BELOW_MINIMAP_OFFSET = 34

FLAPPY_X_SWAY_AMPLITUDE = 45.0
FLAPPY_X_SWAY_SPEED = 1.4
FLAPPY_X_SWAY_LERP = 6.0
FLAPPY_X_SWAY_JITTER = 0.25

FLAPPY_ELIMINATION_LIST_SIZE = 0
FLAPPY_ELIMINATION_TEXT_SIZE = 18
FLAPPY_ELIMINATION_NAME_LENGTH = 16
FLAPPY_ELIMINATION_LABEL = "Eliminated:"
FLAPPY_ELIMINATION_LIST_X_OFFSET = 0

FLAPPY_BG_COLOR = (172, 214, 246)
FLAPPY_PIPE_COLOR = (70, 180, 90)
FLAPPY_PIPE_BORDER_COLOR = (30, 120, 50)
FLAPPY_PIPE_HIGHLIGHT_COLOR = (110, 210, 120)
FLAPPY_DAY_COUNTER_OFFSET = 18

# ===== SUBWAY FOLLOWERS SETTINGS =====
SUBWAY_LANE_COUNT = 3
SUBWAY_LANE_PADDING = 24
SUBWAY_LANE_GAP = 6
SUBWAY_PLAYER_SIZE = 30.0
SUBWAY_MOVE_SPEED = 160.0
SUBWAY_VERTICAL_SPEED = 120.0
SUBWAY_LANE_CHANGE_SPEED = 220.0
SUBWAY_LANE_CHANGE_COOLDOWN = 0.35
SUBWAY_REACTION_DISTANCE = 210.0
SUBWAY_SAFE_DISTANCE = 120.0
SUBWAY_DECISION_INTERVAL_RANGE = (0.25, 0.6)
SUBWAY_RUNNER_Y_RANGE = (0.6, 0.9)
SUBWAY_MAX_GAME_TIME = 90.0
SUBWAY_BASE_SPEED = 180.0
SUBWAY_SPEED_BOOST = 120.0
SUBWAY_DIFFICULTY_RAMP = 55.0
SUBWAY_SPAWN_INTERVAL_MIN = 0.45
SUBWAY_SPAWN_INTERVAL_MAX = 0.9
SUBWAY_OBSTACLE_GAP_MIN = 140.0
SUBWAY_TRAIN_DOUBLE_CHANCE = 0.25
SUBWAY_TRAIN_LATERAL_CHANCE = 0.35
SUBWAY_TRAIN_LATERAL_SPEED = 180.0
SUBWAY_TRAIN_HEIGHT = 160.0
SUBWAY_BARRIER_HEIGHT = 42.0
SUBWAY_POLE_HEIGHT = 70.0
SUBWAY_WALL_HEIGHT = 90.0
SUBWAY_BG_COLOR = (34, 36, 44)
SUBWAY_TRACK_COLOR = (48, 50, 58)
SUBWAY_LANE_LINE_COLOR = (90, 92, 100)
SUBWAY_RAIL_COLOR = (120, 120, 130)
SUBWAY_TRAIN_COLOR = (180, 60, 60)
SUBWAY_TRAIN_OUTLINE = (40, 40, 40)
SUBWAY_TRAIN_ACCENT = (240, 210, 110)
SUBWAY_BARRIER_COLOR = (200, 120, 50)
SUBWAY_BARRIER_OUTLINE = (60, 40, 20)
SUBWAY_BARRIER_ACCENT = (250, 210, 140)
SUBWAY_POLE_COLOR = (80, 110, 170)
SUBWAY_POLE_OUTLINE = (20, 30, 50)
SUBWAY_POLE_ACCENT = (220, 230, 245)
SUBWAY_WALL_COLOR = (70, 75, 90)
SUBWAY_WALL_OUTLINE = (25, 25, 30)
SUBWAY_WALL_ACCENT = (120, 130, 150)
SUBWAY_DAY_COUNTER_OFFSET = 18

# ===== SUBWAY FOLLOWERS 3D SETTINGS =====
SUBWAY_3D_TRACK_WIDTH = 10.0
SUBWAY_3D_TRACK_SEGMENT_LENGTH = 12.0
SUBWAY_3D_TRACK_SEGMENT_COUNT = 8
SUBWAY_3D_LANE_PADDING = 0.6
SUBWAY_3D_LANE_GAP = 0.15
SUBWAY_3D_ROAD_THICKNESS = 0.15
SUBWAY_3D_TRACK_COLOR = (0.12, 0.12, 0.16)
SUBWAY_3D_ROAD_COLOR = (0.12, 0.12, 0.16)
SUBWAY_3D_ROAD_TEXTURE = "assets/subway_followers_3d/textures/asphalt.png"
SUBWAY_3D_ROAD_TEXTURE_SCALE = (1.35, 2.2)
SUBWAY_3D_ROAD_SPECULAR = (0.35, 0.35, 0.38)
SUBWAY_3D_ROAD_SHININESS = 48.0
SUBWAY_3D_ROAD_OVERLAP = 0.35
SUBWAY_3D_EDGE_LINE_COLOR = (0.95, 0.95, 0.95)
SUBWAY_3D_LANE_LINE_COLOR = (0.95, 0.86, 0.2)
SUBWAY_3D_LANE_DASH_COLOR = (0.95, 0.86, 0.2)
SUBWAY_3D_LANE_DASH_LENGTH = 2.2
SUBWAY_3D_LANE_DASH_GAP = 1.4
SUBWAY_3D_LANE_DASH_WIDTH = 0.18
SUBWAY_3D_LANE_DASH_THICKNESS = 0.03
SUBWAY_3D_CURB_WIDTH = 0.5
SUBWAY_3D_CURB_HEIGHT = 0.18
SUBWAY_3D_CURB_COLOR = (0.82, 0.82, 0.86)
SUBWAY_3D_SAND_WIDTH = 4.0
SUBWAY_3D_SAND_HEIGHT = 0.08
SUBWAY_3D_SAND_COLOR = (0.78, 0.64, 0.4)
SUBWAY_3D_PALM_TRUNK_COLOR = (0.6, 0.38, 0.2)
SUBWAY_3D_PALM_LEAF_COLOR = (0.28, 0.78, 0.28)
SUBWAY_3D_PALM_HEIGHT = 2.8
SUBWAY_3D_PALM_LEAF_SIZE = 1.3
SUBWAY_3D_PALM_PER_SEGMENT = 1
SUBWAY_3D_SKY_TOP_COLOR = (0.32, 0.63, 0.92)
SUBWAY_3D_SKY_BOTTOM_COLOR = (0.72, 0.86, 0.98)
SUBWAY_3D_CLOUD_TEXTURE = "assets/subway_followers_3d/textures/clouds.png"
SUBWAY_3D_CLOUD_SPEED = 0.006
SUBWAY_3D_CITY_COLOR = (0.5, 0.7, 0.95)
SUBWAY_3D_CITY_ACCENT = (0.4, 0.6, 0.85)
SUBWAY_3D_CITY_NEAR_COLOR = (0.42, 0.62, 0.9)
SUBWAY_3D_CITY_NEAR_ACCENT = (0.32, 0.5, 0.78)
SUBWAY_3D_CITY_PARALLAX_FAR = 0.008
SUBWAY_3D_CITY_PARALLAX_NEAR = 0.014
SUBWAY_3D_BACKDROP_WIDTH = 120.0
SUBWAY_3D_BACKDROP_HEIGHT = 70.0
SUBWAY_3D_BACKDROP_Y = 160.0
SUBWAY_3D_BASE_SPEED = 18.0
SUBWAY_3D_SPEED_BOOST = 12.0
SUBWAY_3D_MAX_GAME_TIME = 90.0
SUBWAY_3D_OBSTACLE_GAP_MIN = 12.0
SUBWAY_3D_SPAWN_Y = 80.0
SUBWAY_3D_DESPAWN_Y = -10.0
SUBWAY_3D_TRACK_RECYCLE_Y = -5.0
SUBWAY_3D_RUNNER_Y = 6.0
SUBWAY_3D_RUNNER_Y_JITTER = 1.0
SUBWAY_3D_RUNNER_RADIUS = 0.35
SUBWAY_3D_RUNNER_DEPTH = 0.5
SUBWAY_3D_RUNNER_HEIGHT = 1.5
SUBWAY_3D_AVATAR_SIZE = 1.1
SUBWAY_3D_REACTION_DISTANCE = 12.0
SUBWAY_3D_LANE_CHANGE_SPEED = 6.0
SUBWAY_3D_LANE_CHANGE_COOLDOWN = 0.35
SUBWAY_3D_TRAIN_HEIGHT = 3.2
SUBWAY_3D_BARRIER_HEIGHT = 1.2
SUBWAY_3D_POLE_HEIGHT = 1.8
SUBWAY_3D_WALL_HEIGHT = 1.5
SUBWAY_3D_JUMP_HEIGHT = 1.6
SUBWAY_3D_JUMP_GRAVITY = 9.2
SUBWAY_3D_ROLL_DURATION = 0.6
SUBWAY_3D_ROLL_HEIGHT = 0.7
SUBWAY_3D_MODEL_TRAIN = "assets/subway_followers_3d/models/train.bam"
SUBWAY_3D_MODEL_BARRIER = "assets/subway_followers_3d/models/barrier.bam"
SUBWAY_3D_MODEL_TUNNEL = "assets/subway_followers_3d/models/tunnel.bam"
SUBWAY_3D_TEXTURE_TRAIN = ""
SUBWAY_3D_TEXTURE_BARRIER = ""
SUBWAY_3D_TEXTURE_TUNNEL = ""
SUBWAY_3D_TINT_MODELS = False
SUBWAY_3D_TRAIN_COLOR = (0.2, 0.7, 0.95)
SUBWAY_3D_BARRIER_COLOR = (0.95, 0.25, 0.25)
SUBWAY_3D_POLE_COLOR = (0.6, 0.7, 0.85)
SUBWAY_3D_WALL_COLOR = (0.28, 0.32, 0.4)
SUBWAY_3D_CAMERA_POS = (0, -18, 8)
SUBWAY_3D_CAMERA_LOOK_AT = (0, 20, 3)
SUBWAY_3D_END_SCREEN_DURATION = 5.0

# ===== MINI GOLF SETTINGS =====
MINIGOLF_CELL_SIZE = 120
MINIGOLF_PLAYER_SIZE = 30
MINIGOLF_WALL_THICKNESS = 10
MINIGOLF_WALL_COLOR = (30, 30, 30)
MINIGOLF_FLOOR_COLOR = (180, 180, 190)
MINIGOLF_BORDER_COLOR = (0, 0, 0)
MINIGOLF_START_COLOR = (80, 200, 120)
MINIGOLF_HOLE_COLOR = (40, 40, 40)
MINIGOLF_START_MARKER_SCALE = 0.55
MINIGOLF_DAY_COUNTER_OFFSET = 14
MINIGOLF_HOLE_RADIUS = 15.0

MINIGOLF_TOTAL_ROUNDS = 3
MINIGOLF_MAX_SHOTS = 4
MINIGOLF_SHOT_DELAY = 0.5
MINIGOLF_ROUND_INTERMISSION = 0.75

MINIGOLF_FRICTION = 0.975
MINIGOLF_STOP_SPEED = 6.0
MINIGOLF_MIN_SHOT_POWER = 140.0
MINIGOLF_MAX_SHOT_POWER = 900.0
MINIGOLF_POWER_SCALE = 4.6
MINIGOLF_LOOKAHEAD_CELLS = 7
MINIGOLF_DIRECTION_RANDOMNESS_DEG = 20.0
MINIGOLF_DIRECTION_CANDIDATES = 18
MINIGOLF_DIRECTION_PROBE_CELLS = 7
MINIGOLF_BOUNCE_CANDIDATES = 4
MINIGOLF_BOUNCE_LOOKAHEAD_CELLS = 12
MINIGOLF_BOUNCE_WALL_SCAN_RADIUS = 2
MINIGOLF_SHOT_SIM_STEPS = 60
MINIGOLF_SHOT_SIM_TIME = 8
MINIGOLF_SHOT_SIM_MAX_BOUNCES = 8
MINIGOLF_POWER_RANDOMNESS = 0.24
MINIGOLF_MISTAKE_CHANCE = 0.08
MINIGOLF_POWER_CANDIDATES = 5
MINIGOLF_POWER_SAMPLES = 9
MINIGOLF_POWER_RANGE = 0.0
MINIGOLF_GLOBAL_ANGLE_SAMPLES = 60
MINIGOLF_REFINE_ANGLE_SAMPLES = 11
MINIGOLF_REFINE_ANGLE_SPREAD_DEG = 22.0
MINIGOLF_REFINE_POWER_SAMPLES = 7
MINIGOLF_USE_NUMBA = True
MINIGOLF_FINISHER_LIST_SIZE = 0
MINIGOLF_FINISHER_TEXT_SIZE = 18
MINIGOLF_FINISHER_NAME_LENGTH = 16
MINIGOLF_FINISHER_LABEL = "In hole:"
MINIGOLF_FINISHER_LIST_X_OFFSET = 0
MINIGOLF_ELIMINATION_TEXT = "Make it to the hole in 4 shots or get eliminated"
MINIGOLF_SHOT_LEADERBOARD_SIZE = 0
MINIGOLF_SHOT_LEADERBOARD_CACHE_SIZE = 30
MINIGOLF_SHOT_LEADERBOARD_TEXT_SIZE = 18
MINIGOLF_SHOT_LEADERBOARD_NAME_LENGTH = 16
MINIGOLF_SHOT_LEADERBOARD_LABEL = "Shot leaders:"
MINIGOLF_SHOT_LEADERBOARD_X_OFFSET = 80
MINIGOLF_LEADER_HIGHLIGHT_COUNT = 10
MINIGOLF_LEADER_HIGHLIGHT_START_ROUND = 2
MINIGOLF_LEADER_HIGHLIGHT_COLOR = (255, 210, 90)
MINIGOLF_LEADER_HIGHLIGHT_THICKNESS = 3
MINIGOLF_LEADER_HIGHLIGHT_PADDING = 4.0
MINIGOLF_LEADER_LABEL_TEXT_SIZE = 16
MINIGOLF_LEADER_LABEL_COLOR = (255, 255, 255)
MINIGOLF_LEADER_LABEL_OFFSET = 6

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
    "hp": 30,           # Number of attack points it can survive (2 hits to kill at 15 attack)
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
    "push_force": 24.0,           # Force applied during collisions
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

# ===== PLATFORMER RACE SETTINGS =====
# Platformer-specific player size (50% of default FOLLOWER_RADIUS)
PLATFORMER_RACER_RADIUS = FOLLOWER_RADIUS * 0.5  # 50% smaller than other games

# ===== OBSTACLE COURSE SETTINGS =====
# Course dimensions
OBSTACLE_COURSE_LENGTH = 18000     # Total course length in pixels (doubled)
OBSTACLE_COURSE_WIDTH = 500        # Track width in pixels
OBSTACLE_COURSE_VISIBILITY_MARGIN = 100

# Rendering performance knobs (visual-only; no gameplay impact)
OBSTACLE_COURSE_DENSITY_RENDER_ENABLED = True
OBSTACLE_COURSE_DENSITY_RENDER_THRESHOLD = 2500
OBSTACLE_COURSE_RENDER_CELL_SIZE = 18
OBSTACLE_COURSE_RENDER_MAX_PER_CELL = 1

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
METEOR_SPAWN_INTERVAL_MIN = (0.7, 1.2)  # Fastest spawn interval at peak intensity
METEOR_SPAWN_RAMP_DURATION = 60.0       # Seconds to reach peak intensity
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
# Gorilla variants with different rarities and stats
GORILLA_VARIANTS = {
    "brown": {
        "weight": 44.9,  # 44.9% spawn chance
        "color": (101, 67, 33),  # Medium brown
        "hp": 8000,
        "speed": 1,
        "attack": 30,
        "attack_speed": 15,  # 3 attacks per second (value / 10)
        "knockback_distance": 55,
        "regeneration": 0
    },
    "black": {
        "weight": 30.0,  # 30% spawn chance
        "color": (30, 20, 10),  # Nearly black
        "hp": 8000,
        "speed": 1,
        "attack": 30,
        "attack_speed": 10,  # 2 attacks per second (value / 10)
        "knockback_distance": 65,
        "regeneration": 0
    },
    "white": {
        "weight": 20.0,  # 20% spawn chance
        "color": (220, 220, 220),  # White
        "hp": 10000,
        "speed": 1,
        "attack": 15,
        "attack_speed": 5,  # 3 attacks per second (value / 10)
        "knockback_distance": 55,
        "regeneration": 0
    },
    "red": {
        "weight": 5.0,  # 5% spawn chance
        "color": (200, 30, 30),  # Red
        "hp": 3000,
        "speed": 6,
        "attack": 40,
        "attack_speed": 20,  # 6 attacks per second (value / 10)
        "knockback_distance": 55,
        "regeneration": 0
    },
    "golden": {
        "weight": 0.1,  # 0.1% spawn chance (ultra rare!)
        "color": (255, 215, 0),  # Golden
        "hp": 50000,
        "speed": 1,
        "attack": 40,
        "attack_speed": 65,  # 6 attacks per second (value / 10)
        "knockback_distance": 100,
        "regeneration": 0
    }
} 

# Default gorilla stats (fallback if GORILLA_VARIANTS not used)
GORILLA_STATS = {
    "hp": 17000,
    "speed": 1,
    "attack": 30,
    "attack_speed": 30,
    "knockback_distance": 55,
    "regeneration": 0
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

# Gorilla colors (legacy - now using colors from GORILLA_VARIANTS)
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
    "attack_speed": 25  # Attacks per second = value / 10 (3 attacks/sec)
}

# Arena dimensions (extended height)
# Format: (x, y, width, height)
GORILLAS_ARENA_RECT = (40, 180, SCREEN_WIDTH - 80, SCREEN_HEIGHT - 190)

# Kill bonus points
TEAM_BATTLE_KILL_BONUS = 1  # Points per kill

# ===== MINGLE SETTINGS =====
MINGLE_ROOM_COUNT = 20
MINGLE_ROOM_COLORS = [
    (220, 60, 60),   # Red
    (240, 140, 60),  # Orange
    (245, 220, 80),  # Yellow
    (170, 220, 80),  # Lime
    (80, 200, 110),  # Green
    (70, 190, 180),  # Teal
    (80, 200, 230),  # Cyan
    (80, 120, 220),  # Blue
    (100, 90, 200),  # Indigo
    (160, 90, 200),  # Purple
]
MINGLE_PLATFORM_RADIUS = 140
MINGLE_ROOM_SIZE = 32
MINGLE_ROOM_WIDTH = 52
MINGLE_ROOM_HEIGHT = 48
MINGLE_ROOM_RING_PADDING = 0
MINGLE_ROOM_ENTRY_RADIUS = 18
MINGLE_ROOM_PACKING_FACTOR = 0.75
MINGLE_MIN_RADIUS = 1.0
MINGLE_TOTAL_ROUNDS = 5
MINGLE_TARGET_FINALISTS = 1

MINGLE_MAX_ROOM_SIZE = 5
MINGLE_GROUP_SIZES = [2, 3, 4, 5]
MINGLE_ROOM_PUSH_FORCE = 3.0
MINGLE_ROOM_PUSH_MARGIN = 10.0
MINGLE_ENTRY_COLLISION_SCALE = 0.6
MINGLE_ENTRY_COLLISION_MARGIN = 8.0
MINGLE_INTERMISSION_SONG_PATH = "mingle_song.m4a"
MINGLE_INTERMISSION_VOLUME = 0.85
MINGLE_SCRAMBLE_SONG_PATH = project_path("Minute to Win It - Dramatic Game Music - Dan.mp3")
MINGLE_SCRAMBLE_SONG_VOLUME = 0.85
MINGLE_MIX_DURATION = 6.0
MINGLE_SCRAMBLE_DURATION = 10.0
MINGLE_RESOLVE_DURATION = 2.0

MINGLE_MIX_SPEED = 40.0
MINGLE_SCRAMBLE_SPEED = 75.0
MINGLE_WANDER_JITTER = 0.15
MINGLE_PLATFORM_SPIN_SPEED = 0.9
MINGLE_PLATFORM_ROTATION_SPEED = 0.6

# ===== PLINKO SETTINGS =====
PLINKO_STAGE_COUNT = 3
PLINKO_TRIANGLE_MODE = True
PLINKO_PEG_ROWS = 14
PLINKO_PEG_MAX_PER_ROW = 14
PLINKO_PLAYER_RADIUS = 9
PLINKO_GRAVITY = 160.0
PLINKO_MAX_FALL_SPEED = 130.0
PLINKO_ROW_SPACING = 24.0
PLINKO_BIAS_STRENGTH = 1.4
PLINKO_DRIFT_DAMPING = 0.18
PLINKO_WALL_BOUNCE = 0.5
PLINKO_MAX_HORIZONTAL_SPEED = 260.0
PLINKO_SKILL_MIN = 0.35
PLINKO_SKILL_MAX = 1.0
PLINKO_PEG_BOUNCE = 0.65
PLINKO_PEG_JITTER = 0.12
PLINKO_PEG_HITBOX_SCALE = 1.25
PLINKO_MAX_UPWARD_SPEED = 140.0
PLINKO_MIN_FALL_SPEED = 15.0
PLINKO_PEG_SLIDE_SPEED = 20.0
PLINKO_PEG_STICK_SPEED = 12.0
PLINKO_PEG_STICK_NUDGE = 0.35
PLINKO_PEG_TOP_NORMAL_THRESHOLD = 0.75
PLINKO_PEG_TOP_ESCAPE_IMPULSE = 65.0
PLINKO_PEG_CENTER_ESCAPE_BIAS = 0.18
PLINKO_SPAWN_JITTER = 10.0
PLINKO_SPAWN_SPREAD_X = 40.0
PLINKO_ADVANCE_OUTER_COUNT = 1
PLINKO_STALL_TIME = 0.8
PLINKO_STALL_MIN_MOVE = 0.6
PLINKO_STALL_PROGRESS_TIME = 0.7
PLINKO_STALL_PROGRESS_EPSILON = 1.2
PLINKO_STALL_NUDGE_SPEED = 30.0
PLINKO_STALL_NUDGE_X = 40.0
PLINKO_STALL_ESCAPE_DROP = 14.0
PLINKO_STALL_ESCAPE_X = 12.0
PLINKO_STALL_ESCAPE_VY = 45.0
PLINKO_STALL_CENTER_PUSH = 70.0
PLINKO_ROUND_TIME_LIMIT = 40.0

PLINKO_SIDE_PADDING = 4
PLINKO_STAGE_TOP_PADDING = 8
PLINKO_STAGE_BOTTOM_PADDING = 18
PLINKO_PEG_RADIUS = 2
PLINKO_PEG_COLUMNS = 10

PLINKO_HOLE_COUNT = 11
PLINKO_HOLE_WIDTH = 100
PLINKO_HOLE_HEIGHT = 18
PLINKO_HOLE_GAP = 2

PLINKO_BG = (36, 34, 76)
PLINKO_TEXT_COLOR = (245, 245, 255)
PLINKO_BOARD_FILL = (42, 40, 86)
PLINKO_BOARD_BORDER = (70, 70, 110)
PLINKO_PEG_COLOR = (245, 245, 255)
PLINKO_HOLE_COLOR = (120, 60, 60)
PLINKO_HOLE_BORDER = (20, 15, 30)
PLINKO_HOLE_COLORS = []
PLINKO_HOLE_OUTER_COLOR = (70, 180, 90)
PLINKO_HOLE_INNER_COLOR = (140, 140, 150)
PLINKO_SAFE_HOLE_COLOR = (70, 180, 90)
PLINKO_ELIM_HOLE_COLOR = (140, 140, 150)
PLINKO_HOLE_COUNT_SIZE = 16
PLINKO_HOLE_COUNT_COLOR = (20, 10, 10)
PLINKO_HOLE_COUNT_OFFSET = 6
PLINKO_HOLE_LABELS = []
PLINKO_STAGE_COLORS = [(130, 170, 220), (140, 210, 160), (230, 190, 90), (210, 120, 140)]
PLINKO_DAY_COUNTER_OFFSET = 30
PLINKO_HOLE_LABEL_SIZE = 16
PLINKO_HOLE_COUNT_BELOW_OFFSET = 8
PLINKO_ELIMINATION_LIST_SIZE = 6
PLINKO_ELIMINATION_TEXT_SIZE = 18
PLINKO_ELIMINATION_NAME_LENGTH = 16
PLINKO_ELIMINATION_LABEL = "Eliminated:"
PLINKO_ELIMINATION_LIST_X_OFFSET = 0

# ===== LAVA PLATFORM SETTINGS =====
LAVA_PLATFORM_INITIAL_RADIUS = 120    # Starting platform radius (pixels)
LAVA_PLATFORM_MIN_RADIUS = 40         # Minimum platform radius
LAVA_PLATFORM_SHRINK_RATE = 15        # Radius decrease per round (pixels)

LAVA_PLATFORM_INITIAL_TIME = 8.0      # Starting scramble time (seconds)
LAVA_PLATFORM_MIN_TIME = 3.0          # Minimum scramble time
LAVA_PLATFORM_TIME_DECREASE = 0.5     # Time decrease per round (seconds)

LAVA_PLATFORM_WAITING_DURATION = 2.0  # Time to show platform before scramble
LAVA_PLATFORM_LAVA_DURATION = 2.0     # Lava animation duration
LAVA_PLATFORM_RESOLVE_DURATION = 1.5  # Pause between rounds

LAVA_PLATFORM_MAX_ROUNDS = 10         # Maximum rounds before ending
LAVA_PLATFORM_TARGET_FINALISTS = 1    # End when this many remain

LAVA_PLATFORM_MOVE_SPEED = 40.0       # Base player movement speed (reduced for more tension)
LAVA_PLATFORM_PANIC_SPEED = 65.0      # Speed when time is low (reduced)
LAVA_PLATFORM_PANIC_THRESHOLD = 3.0   # Seconds remaining to trigger panic
LAVA_PLATFORM_WANDER_SPEED = 18.0     # Speed during waiting phase (reduced)
LAVA_PLATFORM_WANDER_JITTER = 0.2     # Movement randomness

LAVA_PLATFORM_ARENA_SIZE = 460        # Square arena side length (pixels)
LAVA_PLATFORM_PLATFORM_MARGIN = 30    # Min distance from arena edge to platform center
LAVA_PLATFORM_PLAYER_RADIUS = 13      # Fixed player radius (pixels)

# Obstacle settings
LAVA_PLATFORM_MIN_OBSTACLES = 3       # Minimum obstacles per round
LAVA_PLATFORM_MAX_OBSTACLES = 6       # Maximum obstacles per round
LAVA_PLATFORM_OBSTACLE_MIN_SIZE = 30  # Minimum obstacle dimension (pixels)
LAVA_PLATFORM_OBSTACLE_MAX_SIZE = 60  # Maximum obstacle dimension (pixels)
LAVA_PLATFORM_MAX_ACTIVE_PLAYERS = 200  # Max players allowed in arena per round part

# ===== SIDE CHOICE SETTINGS =====
SIDE_CHOICE_ARENA_SIZE = 500
SIDE_CHOICE_ORIENTATION = "vertical"  # "vertical" = left/right, "horizontal" = top/bottom
SIDE_CHOICE_PLAYER_RADIUS = 15
SIDE_CHOICE_SELECTION_DURATION = 6.0
SIDE_CHOICE_RESULT_DURATION = 2.0
SIDE_CHOICE_MOVE_SPEED = 80.0
SIDE_CHOICE_TURN_RATE = 0.18
SIDE_CHOICE_DIRECTION_JITTER = 0.2
SIDE_CHOICE_WANDER_SPEED = 35.0
SIDE_CHOICE_WANDER_INTERVAL = (0.8, 1.6)
SIDE_CHOICE_TARGET_REFRESH = (0.6, 1.4)
SIDE_CHOICE_FALL_SPEED = 260.0
SIDE_CHOICE_DAY_COUNTER_OFFSET = 14
SIDE_CHOICE_STATUS_PANEL_OFFSET = 24
SIDE_CHOICE_STATUS_PANEL_WIDTH = 200
SIDE_CHOICE_STATUS_TEXT_SIZE = 36
SIDE_CHOICE_STATUS_TEXT_OFFSET = 18
SIDE_CHOICE_SHOW_NAMES_MAX = 1000
SIDE_CHOICE_NAME_FONT_SIZE = 16
SIDE_CHOICE_NAME_OFFSET = 18
SIDE_CHOICE_COIN_FLIP_DURATION = 1.2
SIDE_CHOICE_COIN_FLIP_TURNS = 8
SIDE_CHOICE_COIN_RADIUS = 26
SIDE_CHOICE_COIN_OFFSET = 32
SIDE_CHOICE_COIN_COLOR = (240, 200, 80)
SIDE_CHOICE_COIN_EDGE_COLOR = (120, 90, 30)
SIDE_CHOICE_COIN_TEXT_COLOR = (40, 30, 10)
SIDE_CHOICE_COIN_TEXT_SIZE = 26
SIDE_CHOICE_COIN_INNER_COLOR = (255, 225, 140)
SIDE_CHOICE_COIN_RIM_COLOR = (180, 120, 40)
SIDE_CHOICE_COIN_SHINE_COLOR = (255, 250, 220)
SIDE_CHOICE_COIN_SHADOW_ALPHA = 120
SIDE_CHOICE_COIN_SHADOW_OFFSET = 10
SIDE_CHOICE_COIN_BOB = 12.0
SIDE_CHOICE_COIN_TRAIL_COUNT = 2
SIDE_CHOICE_COIN_TRAIL_ALPHA = 80
SIDE_CHOICE_COIN_EDGE_WIDTH = 2
SIDE_CHOICE_COIN_FACE_SCALE = 0.9
SIDE_CHOICE_LEFT_COLOR = (190, 200, 210)
SIDE_CHOICE_RIGHT_COLOR = (210, 190, 200)
SIDE_CHOICE_OPEN_COLOR = (45, 45, 50)
SIDE_CHOICE_BORDER_COLOR = (0, 0, 0)
SIDE_CHOICE_SPLIT_LINE_COLOR = (40, 40, 40)

# ===== MATH DROP SETTINGS =====
MATH_DROP_ARENA_RECT = MAZE_RUSH_ARENA_RECT
MATH_DROP_PLAYER_RADIUS = 15
MATH_DROP_SELECTION_DURATION = 7.0
MATH_DROP_RESULT_DURATION = 2.0
MATH_DROP_REVEAL_DURATION = 1.2
MATH_DROP_MOVE_SPEED = 130.0
MATH_DROP_TURN_RATE = 0.24
MATH_DROP_DIRECTION_JITTER = 0.12
MATH_DROP_WANDER_SPEED = 35.0
MATH_DROP_WANDER_INTERVAL = (0.8, 1.6)
MATH_DROP_TARGET_REFRESH = (0.5, 1.0)
MATH_DROP_FALL_SPEED = 260.0
MATH_DROP_DAY_COUNTER_OFFSET = 14
MATH_DROP_STATUS_PANEL_OFFSET = 24
MATH_DROP_STATUS_PANEL_WIDTH = 200
MATH_DROP_STATUS_TEXT_SIZE = 34
MATH_DROP_STATUS_TEXT_OFFSET = 18
MATH_DROP_SHOW_NAMES_MAX = 0
MATH_DROP_NAME_FONT_SIZE = 16
MATH_DROP_NAME_OFFSET = 18
MATH_DROP_EQUATION_TEXT_SIZE = 72
MATH_DROP_ANSWER_TEXT_SIZE = 72
MATH_DROP_EQUATION_OFFSET = 28
MATH_DROP_SQUARE_MARGIN = 14
MATH_DROP_SQUARE_GAP = 10
MATH_DROP_UPPER_BG = (205, 208, 216)
MATH_DROP_LOWER_BG = (190, 190, 200)
MATH_DROP_SQUARE_COLOR = (240, 240, 245)
MATH_DROP_SQUARE_OPEN_COLOR = (55, 55, 65)
MATH_DROP_SQUARE_BORDER_COLOR = (0, 0, 0)
MATH_DROP_SQUARE_TEXT_COLOR = (20, 20, 20)
MATH_DROP_SQUARE_OPEN_TEXT_COLOR = (235, 235, 235)
MATH_DROP_ANSWER_OUTLINE_WIDTH = 2
MATH_DROP_ANSWER_OUTLINE_COLOR = None  # Auto-picks black/white by text brightness.
MATH_DROP_EQUATION_OUTLINE_WIDTH = 3
MATH_DROP_EQUATION_OUTLINE_COLOR = None  # Auto-picks black/white by text brightness.
MATH_DROP_CORRECT_COLOR = (170, 220, 170)
MATH_DROP_SPLIT_LINE_COLOR = (40, 40, 40)
MATH_DROP_ZONE_LINE_COLOR = (150, 150, 160)
MATH_DROP_BORDER_COLOR = (0, 0, 0)
MATH_DROP_TELEPORT_FLASH_DURATION = 0.35
MATH_DROP_TELEPORT_FLASH_ALPHA = 140
MATH_DROP_TELEPORT_TEXT = "Teleporting..."
MATH_DROP_TELEPORT_TEXT_SIZE = 30
MATH_DROP_TELEPORT_TEXT_COLOR = (30, 30, 30)
MATH_DROP_OPERAND_MIN = 1
MATH_DROP_OPERAND_MAX = 20
MATH_DROP_OPERATORS = ["+", "-", "*"]
MATH_DROP_ALLOW_NEGATIVE = False
MATH_DROP_RESULT_MIN = 0
MATH_DROP_RESULT_MAX = 99
MATH_DROP_CORRECT_PROB_BY_ROUND = [0.99, 0.85, 0.75, 0.65, 0.55, 0.45, 0.35, 0.33, 0.33, 0.33]
MATH_DROP_CORRECT_PROB_FLOOR = 0.33

# ===== WHEEL SPINNER SETTINGS =====
WHEEL_SPINNER_ARENA_WIDTH = 500
WHEEL_SPINNER_ARENA_HEIGHT = 700
WHEEL_SPINNER_RADIUS = 220
WHEEL_SPINNER_CENTER_Y_OFFSET = 0
WHEEL_SPINNER_START_ANGLE = 0.0
WHEEL_SPINNER_WINDUP_DURATION = 0.9
WHEEL_SPINNER_SPIN_DURATION = 5.5
WHEEL_SPINNER_RESULT_DURATION = 2.6
WHEEL_SPINNER_WINDUP_ANGLE_DEG = 18.0
WHEEL_SPINNER_SPIN_TURNS_MIN = 4
WHEEL_SPINNER_SPIN_TURNS_MAX = 7
WHEEL_SPINNER_SPIN_EASE_POWER = 8.0
WHEEL_SPINNER_TAIL_FRACTION = 0.0
WHEEL_SPINNER_TAIL_POWER = 4.0
WHEEL_SPINNER_OPTION_TEXT_SIZE = 26
WHEEL_SPINNER_INDICATOR_TEXT_SIZE = 32
WHEEL_SPINNER_STATUS_TEXT_SIZE = 28
WHEEL_SPINNER_STATUS_PANEL_WIDTH = 240
WHEEL_SPINNER_STATUS_PANEL_OFFSET = 16
WHEEL_SPINNER_INDICATOR_OFFSET = 10
WHEEL_SPINNER_SELECTED_TEXT_SIZE = 28
WHEEL_SPINNER_SELECTED_OFFSET = 36
WHEEL_SPINNER_SELECTED_MAX_SHOWN = 10
WHEEL_SPINNER_SELECTED_COLOR = (255, 230, 160)
WHEEL_SPINNER_SELECTED_PANEL_ALPHA = 160
WHEEL_SPINNER_SELECTED_PANEL_BG = (28, 28, 36)
WHEEL_SPINNER_SELECTED_PANEL_BORDER = (80, 80, 95)
WHEEL_SPINNER_SELECTED_PANEL_RADIUS = 12
WHEEL_SPINNER_SELECTED_PANEL_PADDING = 12
WHEEL_SPINNER_SELECTED_PANEL_GAP = 8
WHEEL_SPINNER_BADGE_TEXT_SIZE = 26
WHEEL_SPINNER_BADGE_BG = (235, 235, 245)
WHEEL_SPINNER_BADGE_BORDER = (120, 120, 140)
WHEEL_SPINNER_BADGE_TEXT = (30, 30, 40)
WHEEL_SPINNER_BADGE_RADIUS = 8
WHEEL_SPINNER_BADGE_PADDING = 6
WHEEL_SPINNER_POINTER_PANEL_BG = (28, 28, 36)
WHEEL_SPINNER_POINTER_PANEL_BORDER = (80, 80, 95)
WHEEL_SPINNER_POINTER_PANEL_ALPHA = 180
WHEEL_SPINNER_POINTER_PANEL_RADIUS = 10
WHEEL_SPINNER_POINTER_PANEL_PADDING = 10
WHEEL_SPINNER_POINTER_GAP = 8
WHEEL_SPINNER_POINTER_WIDTH = 32
WHEEL_SPINNER_POINTER_HEIGHT = 22
WHEEL_SPINNER_POINTER_COLOR = (20, 20, 20)
WHEEL_SPINNER_POINTER_OUTLINE = (240, 240, 240)
WHEEL_SPINNER_BORDER_COLOR = (0, 0, 0)
WHEEL_SPINNER_DIVIDER_COLOR = (30, 30, 30)
WHEEL_SPINNER_SEGMENT_COLORS = [
    (255, 92, 92),
    (255, 153, 51),
    (255, 221, 51),
    (120, 230, 80),
    (60, 200, 120),
    (0, 200, 190),
    (0, 190, 255),
    (70, 140, 255),
    (120, 110, 255),
    (180, 90, 255),
    (255, 90, 210),
    (255, 120, 170),
]
WHEEL_SPINNER_LIGHT_ANGLE_DEG = -55.0
WHEEL_SPINNER_RIM_THICKNESS = 18
WHEEL_SPINNER_BEVEL_DEPTH = 14
WHEEL_SPINNER_RIM_COLOR = (54, 54, 64)
WHEEL_SPINNER_RIM_HIGHLIGHT = (255, 255, 255)
WHEEL_SPINNER_RIM_SHADOW = (25, 25, 30)
WHEEL_SPINNER_FACE_BORDER = (20, 20, 20)
WHEEL_SPINNER_FACE_BORDER_WIDTH = 0
WHEEL_SPINNER_FACE_INNER_RING = (250, 250, 255)
WHEEL_SPINNER_FACE_INNER_RING_SHADOW = (120, 120, 135)
WHEEL_SPINNER_FACE_INNER_RING_WIDTH = 0
WHEEL_SPINNER_FACE_GLOW = (255, 255, 255)
WHEEL_SPINNER_HUB_RADIUS = 26
WHEEL_SPINNER_HUB_COLOR = (235, 235, 240)
WHEEL_SPINNER_HUB_RING_COLOR = (70, 70, 80)
WHEEL_SPINNER_HUB_GLINT_COLOR = (255, 255, 255)
WHEEL_SPINNER_SHADOW_ALPHA = 0
WHEEL_SPINNER_SHADOW_OFFSET = 18
WHEEL_SPINNER_SHADOW_SCALE = 0.65
WHEEL_SPINNER_SHOW_BACKDROP = False
WHEEL_SPINNER_SHOW_FACE_OVERLAYS = False
WHEEL_SPINNER_SHOW_RIM_HIGHLIGHTS = False
WHEEL_SPINNER_LABEL_COLOR = (20, 20, 20)
WHEEL_SPINNER_LABEL_SHADOW_ALPHA = 0
WHEEL_SPINNER_LABEL_SHADOW_OFFSET = 2
WHEEL_SPINNER_LABEL_RADIUS_FACTOR = 0.86
WHEEL_SPINNER_LABEL_OUTLINE_COLOR = (245, 245, 245)
WHEEL_SPINNER_LABEL_OUTLINE_WIDTH = 0

# ===== BEACON BLITZ SETTINGS =====
BEACON_BLITZ_RUSH_DURATION = 8.0
BEACON_BLITZ_PULSE_DURATION = 1.5
BEACON_BLITZ_SURVIVAL_RATIO = 0.55
BEACON_BLITZ_MOVE_SPEED = 80.0
BEACON_BLITZ_TURN_RATE = 0.2
BEACON_BLITZ_JITTER = 0.2
BEACON_BLITZ_TARGET_RADIUS = 60.0
BEACON_BLITZ_BEACON_RADIUS = 16
BEACON_BLITZ_FADE_DURATION = 0.6
BEACON_BLITZ_DAY_COUNTER_OFFSET = 16
BEACON_BLITZ_THROTTLE_THRESHOLD = 12000

# ===== LANE RUSH SETTINGS =====
LANE_RUSH_LANES = 6
LANE_RUSH_ROUND_DURATION = 7.0
LANE_RUSH_SURVIVAL_RATIO = 0.65
LANE_RUSH_BASE_SPEED = 0.12
LANE_RUSH_BOOST_SPEED = 0.06
LANE_RUSH_SPEED_VARIANCE = 0.015
LANE_RUSH_BOOST_LANES = 2
LANE_RUSH_FADE_DURATION = 0.6
LANE_RUSH_DAY_COUNTER_OFFSET = 16

# ===== DISCORD SIGNAL SETTINGS =====
DISCORD_SIGNAL_ROUND_DURATION = 7.0
DISCORD_SIGNAL_SPIN_DURATION = 2.4
DISCORD_SIGNAL_SPIN_STEP = 0.18
DISCORD_SIGNAL_RADIUS_MULT = 1.08
DISCORD_SIGNAL_SURVIVAL_RATIO = 0.55
DISCORD_SIGNAL_SAFE_BIAS = 0.4
DISCORD_SIGNAL_MOVE_SPEED = 90.0
DISCORD_SIGNAL_TURN_RATE = 0.2
DISCORD_SIGNAL_JITTER = 0.2
DISCORD_SIGNAL_FADE_DURATION = 0.6
DISCORD_SIGNAL_DAY_COUNTER_OFFSET = 14
DISCORD_SIGNAL_SHOW_NAMES_MAX = 300

# ===== CLUB DUEL SETTINGS =====
CLUB_DUEL_APPROACH_DURATION = 4.0
CLUB_DUEL_RESOLVE_DURATION = 2.0
CLUB_DUEL_MOVE_SPEED = 110.0
CLUB_DUEL_TURN_RATE = 0.25
CLUB_DUEL_RING_RADIUS = FIGHTER_ARENA_RECT[3] * 0.32
CLUB_DUEL_PAIR_OFFSET = 18.0
CLUB_DUEL_FADE_DURATION = 0.8
CLUB_DUEL_DAY_COUNTER_OFFSET = 16

# ===== CLUB RELIC SETTINGS =====
CLUB_RELIC_ROUND_DURATION = 6.0
CLUB_RELIC_SURVIVAL_RATIO = 0.6
CLUB_RELIC_MOVE_SPEED = 100.0
CLUB_RELIC_TURN_RATE = 0.25
CLUB_RELIC_RELIC_SPEED = 60.0
CLUB_RELIC_RELIC_RADIUS = 16
CLUB_RELIC_FADE_DURATION = 0.8
CLUB_RELIC_DAY_COUNTER_OFFSET = 16

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

# ===== ANIME FIGHTING SETTINGS =====
# Tournament settings
ANIME_FIGHTING_BRACKET_SIZE = 16         # Number of fighters in tournament (power of 2: 8, 16, 32)
ANIME_FIGHTING_MATCH_TIME_LIMIT = 60     # Seconds per 1v1 match

# Combat tuning
ANIME_FIGHTING_FPS_MULTIPLIER = 1.12     # Faster than real-time for anime pace
ANIME_FIGHTING_HITSTOP_ENABLED = True    # Enable freeze frames on hit
ANIME_FIGHTING_ZOOM_PUNCH_ENABLED = True # Enable dynamic zoom on impacts
ANIME_FIGHTING_SCREEN_SHAKE_ENABLED = True  # Enable screen shake effects

# Visual effects
ANIME_FIGHTING_MAX_PARTICLES = 1400      # Maximum particle count (only 2 fighters)
ANIME_FIGHTING_AFTERIMAGE_ENABLED = True # Enable motion trail effects

# Arena dimensions (for 540x960 screen)
ANIME_FIGHTING_ARENA_MARGIN = 20         # Margin from screen edges
ANIME_FIGHTING_ARENA_Y_OFFSET = 120      # Vertical offset below title area
ANIME_FIGHTING_ARENA_WIDTH = 500         # Arena width
ANIME_FIGHTING_ARENA_HEIGHT = 500        # Arena height
