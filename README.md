# 🎮 Follower Battle Royale

A Python-based Battle Royale simulation using Pygame that pits Instagram followers against each other in a shrinking arena. Watch as followers compete, collide, and get eliminated until only one remains!

## ✨ Features

- **Instagram Integration**: Fetch real followers and profile images via Instagram Graph API
- **Offline Mode**: Run without API credentials using colorful placeholder avatars
- **Physics Simulation**: Realistic movement, collision detection, and push mechanics
- **Shrinking Safe Zone**: Circular arena that shrinks every 3 seconds
- **Smart AI**: Followers target nearest opponents and try to push them toward the edge
- **Live Scoreboard**: Real-time statistics and player count
- **Top 10 Marquee**: Special animation when 10 survivors remain
- **Victory Podium**: Animated podium showing the final winners
- **Video Export**: Automatically exports the entire battle to MP4

## 📋 Requirements

- Python 3.10 or higher
- FFmpeg (for video export)

## 🚀 Installation

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Install FFmpeg

**Ubuntu/Debian:**
```bash
sudo apt-get install ffmpeg
```

**macOS (using Homebrew):**
```bash
brew install ffmpeg
```

**Windows:**
Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH

## 🎯 Usage

### Quick Start (Offline Mode)

Run the game without Instagram API credentials:

```bash
python main.py
```

This will generate 500 placeholder followers with random colored avatars.

### Option 1: Import Your Own Followers (✅ RECOMMENDED - Safe & Legal!)

**Use Instagram's official "Download Your Data" feature:**

1. **Request your Instagram data:**
   - Instagram App → Settings → Security → Download Data
   - Or visit: instagram.com/download/request
   - Wait 24-48 hours for email with download link

2. **Download and extract** the ZIP file

3. **Find `followers.json`** in the extracted folder (usually in `followers_and_following/`)

4. **Edit `config.py`:**
   ```python
   FOLLOWER_IMPORT_FILE = "path/to/followers.json"
   ```

5. **Run the game:**
   ```bash
   python main.py
   ```

**Or create your own custom list:**

See `examples/` folder for CSV, JSON, and TXT templates. You can create a simple file:

```csv
username
friend1
friend2
follower3
```

Then set `FOLLOWER_IMPORT_FILE = "my_followers.csv"` in config.py

**Note:** Imported followers will have colored circle avatars (usernames only, no profile pictures).

### Option 2: Using Instagram Graph API (Safe, Official)

1. Get Instagram Graph API credentials:
   - Create a Facebook Developer account
   - Create an app and get an access token
   - Get your Instagram User ID

2. Edit `config.py`:
   ```python
   INSTAGRAM_ACCESS_TOKEN = "your_access_token_here"
   INSTAGRAM_USER_ID = "your_user_id_here"
   USE_OFFLINE_MODE = False
   ```

3. Run the game:
   ```bash
   python main.py
   ```

### Option 3: Using Web Scraper (⚠️ Violates Instagram ToS - Not Recommended)

**WARNING:** This can get your account banned! Use at your own risk.

1. Edit `config.py`:
   ```python
   USE_INSTALOADER_SCRAPER = True
   INSTAGRAM_USERNAME = "your_username"
   INSTAGRAM_PASSWORD = "your_password"
   USE_OFFLINE_MODE = False
   ```

2. Run the game:
   ```bash
   python main.py
   ```

**📖 For detailed scraping instructions, security warnings, and troubleshooting, see [SCRAPING_GUIDE.md](SCRAPING_GUIDE.md)**

## ⚙️ Configuration

All game settings can be modified in `config.py`:

### Game Settings
- `FOLLOWER_COUNT`: Number of followers (500-1000)
- `FPS`: Game framerate (default: 60)
- `SCREEN_WIDTH/HEIGHT`: Display resolution (default: 1080x1080)

### Arena Settings
- `ARENA_INITIAL_RADIUS`: Starting safe zone size (default: 500px)
- `ARENA_MIN_RADIUS`: Minimum zone size (default: 100px)
- `SHRINK_INTERVAL`: Time between shrinks (default: 3 seconds)
- `SHRINK_PERCENTAGE`: How much to shrink (default: 2%)

### Physics Settings
- `BASE_SPEED`: Movement speed (default: 2.0)
- `FRICTION`: Movement friction (default: 0.95)
- `PUSH_FORCE`: Collision push force (default: 5.0)
- `BUMP_COOLDOWN`: Cooldown between collisions (default: 0.5s)
- `MOVEMENT_RANDOMNESS`: AI randomness (default: 0.3)

### Video Export Settings
- `EXPORT_VIDEO`: Enable/disable video export (default: True)
- `OUTPUT_VIDEO_PATH`: Output file path (default: "follower_battle_royale.mp4")
- `VIDEO_FPS`: Export framerate (default: 30)

## 🎨 Customization Guide

### Modify Game Rules

**Change zone shrinking speed:**
```python
# In config.py
SHRINK_INTERVAL = 2.0  # Shrink every 2 seconds (faster)
SHRINK_PERCENTAGE = 0.03  # Shrink by 3% (more aggressive)
```

**Increase aggression:**
```python
# In config.py
PUSH_FORCE = 8.0  # Stronger collisions
BASE_SPEED = 3.0  # Faster movement
BUMP_COOLDOWN = 0.3  # More frequent bumps
```

**Make it chaotic:**
```python
# In config.py
FOLLOWER_COUNT = 1000  # More followers
MOVEMENT_RANDOMNESS = 0.6  # More erratic movement
FRICTION = 0.98  # Less friction (more sliding)
```

### Modify Visuals

**Change colors in `config.py`:**
```python
COLOR_BACKGROUND = (20, 20, 30)  # Dark blue background
COLOR_SAFE_ZONE = (50, 150, 50)  # Green safe zone
COLOR_DANGER_ZONE = (200, 50, 50)  # Red danger zone
```

**Adjust follower appearance:**
```python
FOLLOWER_RADIUS = 40  # Bigger followers
FOLLOWER_BORDER_WIDTH = 5  # Thicker borders
```

## 📁 Project Structure

```
Follower_Competition_Channel/
├── main.py              # Main game loop and orchestration
├── config.py            # All configuration settings
├── requirements.txt     # Python dependencies
├── README.md           # This file
├── modules/            # Game modules
│   ├── __init__.py     # Module exports
│   ├── api.py          # Instagram API integration
│   ├── arena.py        # Arena and safe zone logic
│   ├── follower.py     # Follower character class
│   ├── physics.py      # Physics engine
│   ├── renderer.py     # Rendering and UI
│   └── recorder.py     # Video recording and export
└── assets/             # Assets directory (for future use)
```

## 🎮 How It Works

### Game Flow

1. **Setup**: Followers are fetched from Instagram API or generated as placeholders
2. **Spawn**: Followers are placed randomly within the arena
3. **Battle**: Followers move toward nearest opponents and try to push them
4. **Shrink**: Every 3 seconds, the safe zone shrinks by 2%
5. **Elimination**: Followers outside the safe zone are eliminated
6. **Victory**: Last survivor wins, podium animation plays
7. **Export**: Game is saved as an MP4 video

### Physics System

- **Movement**: Followers move at constant speed toward their target
- **Collision**: When followers collide, they push each other apart
- **Push Bonus**: Moving toward a target during collision increases push force
- **Friction**: Velocity gradually decreases to simulate friction
- **Randomness**: Movement has slight randomness for natural behavior

### AI Behavior

Each follower:
1. Finds the nearest alive opponent
2. Moves toward them
3. On collision, pushes them away
4. The push naturally moves opponents toward the edge
5. Repeats until eliminated or wins

## 🐛 Troubleshooting

### Video Export Fails

**Error**: "MoviePy error" or "ffmpeg not found"

**Solution**: Install ffmpeg and ensure it's in your PATH
```bash
# Test if ffmpeg is installed
ffmpeg -version
```

### Low Performance

**Solution**: Reduce follower count or disable video export
```python
# In config.py
FOLLOWER_COUNT = 250  # Fewer followers
EXPORT_VIDEO = False  # Disable recording
```

### API Connection Issues

**Solution**: Run in offline mode
```python
# In config.py
USE_OFFLINE_MODE = True
```

## 📊 Output

After the game completes, you'll see:

```
============================================================
  GAME STATISTICS
============================================================
Total Followers: 500
Total Eliminations: 499
Zone Shrinks: 45
Collision Checks: 1234567
Collisions Detected: 8901
Video Frames Captured: 1800
Video Duration: 60.0s
============================================================

📹 Exporting video with 1800 frames...
✅ Video exported successfully!
   File: follower_battle_royale.mp4
   Duration: 60.0s
   Frames: 1800
   FPS: 30
```

## 🎬 Example Output

The game generates an MP4 video showing:
- All followers battling in real-time
- Safe zone shrinking with visual indicators
- Live scoreboard with statistics
- "Top 10 Survivors" marquee animation
- Victory podium with top 3 winners

## 🔧 Advanced Modifications

### Add New Elimination Rules

Edit `modules/follower.py`, method `check_safe_zone()`:
```python
# Example: Eliminate followers that move too slowly
if follower.vx**2 + follower.vy**2 < 0.1:  # Too slow
    follower.eliminate()
```

### Change Arena Shape

Edit `modules/arena.py` to implement different arena shapes (square, hexagon, etc.)

### Custom Targeting Strategy

Edit `modules/follower.py`, method `_choose_target()`:
```python
# Example: Target weakest (closest to edge) instead of nearest
weakest = max(alive_followers,
              key=lambda f: self.arena.get_distance_from_center(f.x, f.y))
self.target_follower = weakest
```

## 📝 License

This project is open source and available for educational purposes.

## 🤝 Contributing

Feel free to fork, modify, and create your own variations!

## 📧 Support

For issues or questions, please check:
- Configuration settings in `config.py`
- Module documentation in each `.py` file
- This README for common solutions

---

**Enjoy the battle! May the best follower win! 🏆**
