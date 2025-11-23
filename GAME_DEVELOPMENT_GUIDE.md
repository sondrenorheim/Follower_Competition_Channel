# Follower Competition Channel - Game Development Guide

This guide explains how to create new games for the Follower Competition Channel project. The project features social media followers (from Instagram/TikTok) competing in various game modes, with results exported as vertical videos for social media.

## Project Overview

### Purpose
Create engaging competition videos where followers battle each other in different game modes. Each game:
- Imports followers from Instagram/TikTok CSV files
- Renders a game simulation at 540x960 (9:16 vertical format)
- Awards points based on placement (100 for 1st, descending)
- Tracks all-time statistics across games
- Exports to video when `config.EXPORT_VIDEO = True`

### Existing Games
1. **Battle Royale** (`battle_royale/`) - Shrinking circle elimination
2. **Fighter Arena** (`fighter_arena/`) - Combat in a rectangular arena
3. **Obstacle Course** (`obstacle_course/`) - Horizontal race with obstacles

---

## Standard Layout (MUST follow for all games)

All games must use this consistent visual layout:

```
┌─────────────────────────────────────┐
│         [GAME TITLE] (56pt)         │  <- Y = 60
│  "Making my followers battle..."    │  <- Y = 100 (32pt)
├─────────────────────────────────────┤
│                                     │  <- Y = 160 (GAME_AREA_TOP)
│                                     │
│           MAIN GAME AREA            │  <- 500px wide, centered
│         (where action happens)      │  <- Full simulation height
│                                     │
│                                     │
├─────────────────────────────────────┤  <- Y = 860 (GAME_AREA_BOTTOM)
│      "Day X: XX followers"          │  <- Y = 890 (36pt)
└─────────────────────────────────────┘
         540px wide, 960px tall
```

### Key Dimensions
```python
SCREEN_WIDTH = 540
SCREEN_HEIGHT = 960
DEFAULT_GAME_WIDTH = 500      # Same as obstacle course track width
DEFAULT_GAME_HEIGHT = 700     # Vertical game area
GAME_AREA_LEFT = 20           # (540 - 500) / 2
GAME_AREA_TOP = 160           # Below title/subtitle
GAME_AREA_BOTTOM = 860        # GAME_AREA_TOP + DEFAULT_GAME_HEIGHT
```

---

## Template Files (in `shared/`)

### 1. GameTemplate (`shared/game_template.py`)

The main game orchestrator. Handles:
- Pygame initialization
- Follower import from Instagram/TikTok
- Game loop with phases (intro → countdown → playing → finished)
- Scoring and statistics
- Video export

**Key methods to override:**
```python
class MyGame(GameTemplate):
    GAME_TITLE = "MY GAME"
    PLAYER_LABEL = "players"  # or "racers", "fighters", etc.

    def _init_game_components(self):
        """Initialize arena, renderer, particles, etc."""
        self.arena = MyArena()
        self.renderer = MyRenderer(self.screen)

    def _create_player(self, follower_data, position):
        """Create your player type from follower data."""
        return MyPlayer(follower_data, position)

    def _get_starting_position(self, index, total_players):
        """Calculate starting position for each player."""
        return self.arena.get_random_position(margin=20)

    def update(self, dt):
        """Game logic - movement, collisions, eliminations."""
        for player in self.players:
            player.update(dt, self.arena)
        # Check win conditions, call self.finish_game() when done

    def render(self):
        """Render the game state."""
        self.renderer.render_frame(self.players, game_state)
        pygame.display.flip()
        self.recorder.capture_frame(self.screen)

    def _calculate_bonus_points(self, player):
        """Optional: Add game-specific bonus points."""
        return 0  # e.g., return player.kills * 5
```

### 2. RendererTemplate (`shared/renderer_template.py`)

Handles all visual rendering with consistent UI layout.

**Key methods to override:**
```python
class MyRenderer(RendererTemplate):
    GAME_TITLE = "MY GAME"
    PLAYER_LABEL = "players"

    def _draw_game_area(self, players, game_state):
        """Draw your arena/track/background."""
        # Draw within self.game_left, self.game_top,
        #            self.game_right, self.game_bottom
        pass

    def _draw_players(self, players):
        """Draw all players."""
        for player in players:
            if player.alive:
                self._draw_player_avatar(player)

    def _draw_game_ui(self, players, game_state):
        """Draw game-specific UI (health bars, progress, etc.)."""
        pass
```

**Built-in features (automatic):**
- Title and subtitle rendering
- Day counter
- End-game leaderboards with winner spotlight
- Avatar caching for performance

### 3. ArenaTemplate (`shared/arena_template.py`)

Defines the game area boundaries.

**Configuration:**
```python
class MyArena(ArenaTemplate):
    WIDTH = 500               # Game area width
    HEIGHT = 700              # Game area height
    SHAPE = ArenaShape.RECTANGLE  # or CIRCLE, HEXAGON, OCTAGON
    SHRINKS = False           # Set True for battle royale style
    SHRINK_RATE = 0.1         # Pixels per second
    MIN_SIZE = 50             # Minimum before game ends
```

**Key methods:**
```python
arena.is_inside(x, y, radius)           # Check if position is valid
arena.clamp_position(x, y, radius)      # Keep entity inside
arena.get_distance_to_edge(x, y)        # Distance to nearest wall
arena.get_random_position(margin)       # Random valid position
arena.update(dt)                        # Update shrinking, etc.
```

### 4. EntityTemplate (`shared/entity_template.py`)

Base class for players/followers.

**Attributes:**
```python
entity.username          # Display name from Instagram/TikTok
entity.color             # RGB tuple for avatar
entity.avatar_image      # PIL Image (profile picture, if available)
entity.x, entity.y       # Position
entity.vx, entity.vy     # Velocity
entity.radius            # Collision radius (config.FOLLOWER_RADIUS)
entity.alive             # Is still in game
entity.placement         # Final placement for scoring
entity.alpha             # Transparency (for fade effects)
```

**Key methods:**
```python
entity.update(dt, arena, all_players)   # Override for behavior
entity.eliminate(placement)              # Mark as eliminated
entity.collides_with(other)             # Collision check
entity.push_apart(other, force)         # Collision response
entity.distance_to(other)               # Distance calculation
entity.get_survival_time()              # For statistics
```

**MovingEntity subclass:**
Pre-built entity with random AI movement - good starting point.

---

## Scoring System

All games use the same base scoring formula:

```python
points = ((total_participants - placement + 1) / total_participants) * 100
```

Examples (100 players):
- 1st place: 100 points
- 10th place: 91 points
- 50th place: 51 points
- 100th place: 1 point

**Adding bonus points:**
Override `_calculate_bonus_points(player)` in your game class:
```python
def _calculate_bonus_points(self, player):
    bonus = 0
    if hasattr(player, 'kills'):
        bonus += player.kills * 2  # 2 points per kill
    if hasattr(player, 'finished') and player.finished:
        bonus += 10  # Completion bonus
    return bonus
```

---

## Follower Import

Followers are imported via `InstagramAPI` from CSV files:

```python
# In config.py
FOLLOWER_IMPORT_FILE = "path/to/instagram_followers.csv"
TIKTOK_IMPORT_FILE = "path/to/tiktok_followers.csv"  # Optional
DOWNLOAD_PROFILE_PICTURES = True  # Load real profile pics
```

CSV format (auto-detected columns):
```csv
username,profile_pic_url
cooluser123,https://...
another_user,https://...
```

The API handles:
- Merging Instagram + TikTok followers
- Downloading profile pictures (if enabled)
- Generating placeholder names in offline mode

---

## Video Export

When `config.EXPORT_VIDEO = True`:

1. Frames are captured during `self.recorder.capture_frame(screen)`
2. Green screen countdown overlay is applied during export
3. Background music is mixed in
4. Video is upscaled (default 2x: 540x960 → 1080x1920)
5. Exported as MP4 with H.264 codec

**Key config settings:**
```python
EXPORT_VIDEO = True
UPSCALE_VIDEO = True
UPSCALE_FACTOR = 2.0      # 1080p output
VIDEO_FPS = 30
DAY_NUMBER = 1            # For filename and display
```

---

## Game Phases

All games follow this phase structure:

1. **Intro** (optional): Show day announcement
2. **Countdown**: "3, 2, 1, GO!" with video overlay
   - Background music starts at low volume
   - Players visible but not moving
3. **Playing**: Main game loop
   - Music at full volume
   - All game mechanics active
4. **Finished**: Show results
   - Winner spotlight with pulsing effect
   - Two leaderboards: Current Game + All-Time
   - Semi-transparent black overlay
   - Auto-closes after 5 seconds

---

## Creating a New Game: Step-by-Step

### 1. Create folder structure
```
my_new_game/
├── __init__.py
├── game.py          # Copy from game_template.py
├── renderer.py      # Copy from renderer_template.py
├── arena.py         # Copy from arena_template.py
├── player.py        # Copy from entity_template.py
```

### 2. Define your arena (`arena.py`)
```python
from shared import ArenaTemplate, ArenaShape

class MyArena(ArenaTemplate):
    WIDTH = 500
    HEIGHT = 600
    SHAPE = ArenaShape.CIRCLE
    SHRINKS = True
    SHRINK_RATE = 0.2
```

### 3. Define your player (`player.py`)
```python
from shared import EntityTemplate

class MyPlayer(EntityTemplate):
    def _init_entity(self, follower_data):
        self.score = 0
        self.power_ups = []

    def update(self, dt, arena, all_players):
        if not self.alive:
            self.update_fade()
            return

        # Your movement/behavior logic
        self.apply_velocity(dt)
        self.apply_friction()

        # Keep inside arena
        if not arena.is_inside(self.x, self.y, self.radius):
            self.eliminate()
```

### 4. Define your renderer (`renderer.py`)
```python
from shared import RendererTemplate

class MyRenderer(RendererTemplate):
    GAME_TITLE = "MY NEW GAME"
    PLAYER_LABEL = "contestants"

    def _draw_game_area(self, players, game_state):
        # Draw arena background
        self.arena.fill(self.screen, (200, 200, 200))
        self.arena.draw_boundary(self.screen, (100, 100, 100), 3)

    def _draw_players(self, players):
        for player in players:
            if player.alive or player.is_fading():
                self._draw_player_avatar(player)
```

### 5. Create your game (`game.py`)
```python
from shared import GameTemplate
from .arena import MyArena
from .renderer import MyRenderer
from .player import MyPlayer

class MyNewGame(GameTemplate):
    GAME_TITLE = "MY NEW GAME"
    PLAYER_LABEL = "contestants"

    def _init_game_components(self):
        self.arena = MyArena()
        self.renderer = MyRenderer(self.screen)

    def _create_player(self, follower_data, position):
        return MyPlayer(follower_data, position)

    def update(self, dt):
        if self.game_over:
            return

        self.arena.update(dt)

        for player in self.players:
            player.update(dt, self.arena, self.players)

        # Check for winner
        alive = [p for p in self.players if p.alive]
        if len(alive) <= 1:
            sorted_players = sorted(self.players,
                key=lambda p: (not p.alive, -p.get_survival_time()))
            self.finish_game(sorted_players)

    def render(self):
        game_state = {
            'phase': self.phase,
            'alive_count': sum(1 for p in self.players if p.alive),
            'show_leaderboards': self.show_leaderboards,
            'current_game_leaderboard': self.current_game_leaderboard,
            'all_time_leaderboard': self.all_time_leaderboard,
            'winner': self.winner,
        }
        self.renderer.render_frame(self.players, game_state)
        pygame.display.flip()
        self.recorder.capture_frame(self.screen)
```

### 6. Add to main.py
```python
elif config.GAME_MODE == "my_new_game":
    from my_new_game import MyNewGame
    game = MyNewGame()
    game.run()
```

---

## Best Practices

### Performance
- Use `entity.surface_needs_update` flag to cache surfaces
- Batch similar draw calls together
- Use `arena.is_inside()` before detailed collision checks

### Consistency
- Always use the standard layout (title, game area, day counter)
- Use `config.FOLLOWER_RADIUS` for entity sizes
- Use `config.COLOR_*` for standard colors

### Statistics
- Call `self.finish_game(sorted_players)` to save stats
- Player `.placement` is auto-assigned based on list order
- Stats persist in `player_statistics.json`

### Video Export
- Always call `self.recorder.capture_frame(self.screen)` in render
- The countdown overlay is added automatically during export
- Green screen keying is handled by the recorder

---

## File Reference

```
shared/
├── __init__.py              # Exports all shared modules
├── api.py                   # InstagramAPI - follower import
├── scoring.py               # ScoringSystem - point calculation
├── statistics.py            # PlayerStatistics - persistent storage
├── recorder.py              # VideoRecorder - video export
├── particles.py             # ParticleSystem - visual effects
├── physics.py               # PhysicsEngine - collision detection
├── sound_manager.py         # SoundManager - audio playback
├── audio_logger.py          # AudioLogger - event tracking
├── game_template.py         # GameTemplate - base game class
├── renderer_template.py     # RendererTemplate - base renderer
├── arena_template.py        # ArenaTemplate - game area
└── entity_template.py       # EntityTemplate - player base

config.py                    # All configuration settings
main.py                      # Entry point, game mode selection
player_statistics.json       # Persistent player data
```

---

## Common Patterns

### Elimination with Particles
```python
from shared import ParticleSystem

self.particles = ParticleSystem()

# On elimination:
self.particles.emit_explosion(player.x, player.y, player.color)

# In update:
self.particles.update(dt)

# In render:
self.particles.render(self.screen)
```

### Collision Response
```python
for i, p1 in enumerate(self.players):
    for p2 in self.players[i+1:]:
        if p1.alive and p2.alive and p1.collides_with(p2):
            p1.push_apart(p2, force=config.PUSH_FORCE)
```

### Camera/Scrolling (like obstacle course)
```python
class MyCamera:
    def __init__(self):
        self.x = 0
        self.y = 0

    def world_to_screen(self, pos):
        return (pos[0] - self.x, pos[1] - self.y)

    def follow(self, target_x, target_y):
        self.x = target_x - config.SCREEN_WIDTH // 2
        self.y = target_y - config.SCREEN_HEIGHT // 2
```

---

## Quick Reference Card

| What | Where | Key Method/Attribute |
|------|-------|---------------------|
| Import followers | `GameTemplate.setup_players()` | `self.api.fetch_followers()` |
| Game area bounds | `ArenaTemplate` | `.is_inside()`, `.clamp_position()` |
| Player position | `EntityTemplate` | `.x`, `.y`, `.vx`, `.vy` |
| Eliminate player | `EntityTemplate` | `.eliminate(placement)` |
| End game | `GameTemplate` | `.finish_game(sorted_players)` |
| Save stats | `GameTemplate` | Auto-called by `finish_game()` |
| Export video | `GameTemplate` | Auto-called in `cleanup()` |
| Draw title | `RendererTemplate` | Auto-called in `render_frame()` |
| Draw leaderboards | `RendererTemplate` | Auto when `show_leaderboards=True` |
| Bonus points | `GameTemplate` | Override `_calculate_bonus_points()` |

---

*Last updated: Game Development Guide v1.0*
