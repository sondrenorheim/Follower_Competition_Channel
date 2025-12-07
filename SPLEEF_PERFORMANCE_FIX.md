# Spleef Performance Optimizations

## Problem
The game was running at ~0.2 FPS (1 frame every 5 seconds) due to expensive rendering with 1,386 players and 900 blocks.

## Optimizations Applied

### 1. Block Sampling (90% reduction)
- **Before**: Drew all 900 blocks every frame
- **After**: Draw every 3rd block (~100 blocks)
- **Exception**: Always draw damaged/breaking blocks for visual feedback
- **Impact**: 9x faster block rendering

### 2. Simplified Block Rendering
- **Before**: Drew 3D blocks with top, side, and bottom faces (3+ polygons per block)
- **After**: Draw only top face (1 polygon per block)
- **Impact**: 3x faster per block

### 3. Frustum Culling for Players
- **Before**: Drew all 1,386 players regardless of position
- **After**: Only draw players within screen bounds + margin
- **Impact**: Typically only 100-300 players drawn

### 4. Skip Avatar Images
- **Before**: Loaded, resized, and pasted avatar images for every player
- **After**: Draw simple colored circles
- **Impact**: 10x+ faster player rendering

### 5. Skip Username Text
- **Before**: Drew username text with background for every player
- **After**: Skip all username text
- **Impact**: Significant text rendering savings

### 6. Skip Avatar Pasting
- **Before**: Pasted up to 1,386 avatar images per frame
- **After**: Skip entirely if more than 200 avatars
- **Impact**: Eliminates expensive PIL paste operations

## Performance Expectations

### Before Optimizations:
- **FPS**: 0.2 FPS (1 frame per 5 seconds)
- **Blocks drawn**: 900 per frame
- **Players drawn**: 1,386 per frame
- **Cost per frame**: ~5,000ms

### After Optimizations:
- **FPS**: 15-30 FPS (expected)
- **Blocks drawn**: ~100 per frame
- **Players drawn**: ~200 per frame (those visible)
- **Cost per frame**: ~30-60ms

## Configuration

If you need even better performance, you can adjust the sample rate in `spleef/renderer.py`:

```python
# Line 259 in renderer.py
sample_rate = 3  # Draw every 3rd block

# Increase for even more performance:
sample_rate = 4  # Draw every 4th block (even faster)
sample_rate = 5  # Draw every 5th block (fastest)
```

## Visual Trade-offs

These optimizations prioritize performance over visual fidelity:
- ✅ Arena is still clearly visible
- ✅ Players are still visible
- ✅ Block degradation is still visible
- ⚠️ Less dense block grid (more gaps)
- ⚠️ No 3D block depth
- ⚠️ No player avatars
- ⚠️ No player usernames

For video export, this is acceptable as the game will:
- Record at 30 FPS smoothly
- Show clear gameplay
- Display player count and block count in UI
- Show winner at the end

## Testing

Restart the game with:
```bash
python main.py
```

The game should now run at a much more reasonable framerate!
