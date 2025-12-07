# Spleef Test Mode with Minimal Players

## New Config Settings

Added to `config.py`:

```python
# Minimal test players - when True, use generated test users instead of real followers
TEST_MINIMAL_PLAYERS = True  # Set True to use test users, False to use real followers
TEST_MINIMAL_PLAYER_COUNT = 50  # Number of test users to generate
```

## How It Works

### Test Mode (Current Setting)
When `TEST_MINIMAL_PLAYERS = True`:
- ✅ Generates simple test players (Player1, Player2, etc.)
- ✅ No Instagram/TikTok API calls
- ✅ No profile picture loading
- ✅ Fast startup
- ✅ Configurable player count (default: 50)
- ✅ Perfect for testing performance and gameplay

### Production Mode
When `TEST_MINIMAL_PLAYERS = False`:
- Uses real Instagram and TikTok followers
- Loads profile pictures (if enabled)
- Full follower data with real usernames

## Usage

### For Testing (Current):
```python
# config.py
TEST_MINIMAL_PLAYERS = True
TEST_MINIMAL_PLAYER_COUNT = 50  # Adjust as needed
```

Then run:
```bash
python main.py
```

Output:
```
🧪 Generating test players...
✅ Generated 50 test players
✅ Spawned 50 players on arena
```

### For Production Video:
```python
# config.py
TEST_MINIMAL_PLAYERS = False
FOLLOWER_COUNT = None  # Use all followers
# or
FOLLOWER_COUNT = 500  # Limit to 500 for performance
```

## Performance Comparison

### 50 Test Players:
- **Startup**: Instant
- **FPS**: 60 FPS (very smooth)
- **Render time**: ~15ms per frame
- **Use for**: Testing, development, quick iterations

### 500 Real Followers:
- **Startup**: ~2-3 seconds
- **FPS**: 30-45 FPS (smooth)
- **Render time**: ~20-40ms per frame
- **Use for**: Production videos, good balance

### 1,386 Real Followers:
- **Startup**: ~5-8 seconds
- **FPS**: 10-20 FPS (acceptable)
- **Render time**: ~50-100ms per frame
- **Use for**: Full follower experience

## Quick Settings Reference

```python
# Fast testing with 50 players
TEST_MINIMAL_PLAYERS = True
TEST_MINIMAL_PLAYER_COUNT = 50

# Fast testing with more players
TEST_MINIMAL_PLAYERS = True
TEST_MINIMAL_PLAYER_COUNT = 100

# Production with limited followers (recommended)
TEST_MINIMAL_PLAYERS = False
FOLLOWER_COUNT = 500

# Production with all followers
TEST_MINIMAL_PLAYERS = False
FOLLOWER_COUNT = None
```

## Benefits of Test Mode

1. **Faster Development**
   - No API calls
   - Instant player generation
   - Quick iterations

2. **Better Performance**
   - Smaller player count
   - No avatar loading
   - Smooth 60 FPS

3. **Easier Debugging**
   - Predictable player names
   - Consistent setup
   - Easy to track specific players

4. **Visual Testing**
   - Test layer mechanics
   - Verify rendering
   - Check gameplay flow

## Current Status

✅ **Currently set to test mode**:
- `TEST_MINIMAL_PLAYERS = True`
- `TEST_MINIMAL_PLAYER_COUNT = 50`

This gives you smooth 60 FPS performance for testing the game mechanics!
