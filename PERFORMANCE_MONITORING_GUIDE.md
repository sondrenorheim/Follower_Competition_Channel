# Performance Monitoring Guide

Real-time performance insights for Battle Royale simulation

---

## What It Does

The Performance Monitor tracks and logs detailed metrics about your game's performance in real-time, helping you:
- **Identify bottlenecks** - See which parts of the game are slow
- **Optimize settings** - Tune config for your hardware
- **Track FPS** - Monitor frame rate stability
- **Understand scaling** - See how performance changes with player count

---

## Performance Logs

Every 2 seconds (configurable), you'll see output like this:

```
======================================================================
PERFORMANCE STATS (2.0s interval, 120 frames)
======================================================================
FPS: 58.3 | Frame Time: 17.15ms
  Update: 8.42ms | Physics: 5.31ms | Render: 3.42ms

Detailed Metrics:
  Collision Checks: 1,247/frame
  Players Updated: 1,000/frame
  Players Rendered: 523/frame
  Players Culled: 477/frame
  Culling Efficiency: 47.7% off-screen
======================================================================
```

---

## Understanding the Metrics

### Frame Rate
- **FPS**: Frames per second (average over last 60 frames)
  - Target: 30-60 FPS
  - 60+ FPS: Excellent
  - 30-60 FPS: Good
  - <30 FPS: Needs optimization

- **Frame Time**: Total time per frame in milliseconds
  - Lower is better
  - 16.67ms = 60 FPS
  - 33.33ms = 30 FPS

### Section Timings

**Update** - Player AI and game logic
- Includes: follower updates, target selection, movement
- Typical: 5-15ms for 1,000 players
- High values indicate: Too many players updating, slow AI logic

**Physics** - Collision detection and resolution
- Includes: spatial grid, collision checks, separation force
- Typical: 3-10ms for 1,000 players
- High values indicate: Spatial grid not working, too many collision checks

**Render** - Drawing graphics
- Includes: drawing followers, arena, UI
- Typical: 2-8ms for visible players
- High values indicate: Too many players on screen, slow rendering

### Detailed Metrics

**Collision Checks** - Number of collision detection checks per frame
- With spatial grid: ~1-3 checks per player
- Without spatial grid: ~500 checks per player (O(n²))
- If this is high (>5000 for 1,000 players), spatial grid isn't working

**Players Updated** - Number of players updated this frame
- Without throttling: Same as total player count
- With throttling (>5000 players): 1/4 of total player count
- Example: 10,000 players with 4 batches = 2,500 updated/frame

**Players Rendered** - Number of players actually drawn
- Depends on how many are visible on screen
- Typical: 300-800 for 1,000 players

**Players Culled** - Number of players skipped (off-screen)
- Higher is better (means culling is working!)
- Typical: 40-80% culled for large player counts

**Culling Efficiency** - Percentage of players off-screen
- Higher is better
- 50%+ efficiency is excellent
- If low (<20%), most players are visible (camera zoomed out?)

---

## Configuration

Edit `config.py`:

```python
# Performance monitoring/logging
PERFORMANCE_LOG_INTERVAL = 2.0       # How often to print stats (seconds)
PERFORMANCE_DETAILED_LOGGING = True  # Show detailed metrics
```

### Options:

**Fast logging** (every second):
```python
PERFORMANCE_LOG_INTERVAL = 1.0
```

**Slow logging** (every 5 seconds):
```python
PERFORMANCE_LOG_INTERVAL = 5.0
```

**Disable detailed metrics** (only show FPS and timing):
```python
PERFORMANCE_DETAILED_LOGGING = False
```

---

## Interpreting Results

### Scenario 1: Slow Physics
```
FPS: 25.0 | Frame Time: 40.00ms
  Update: 8.00ms | Physics: 28.00ms | Render: 4.00ms

Detailed Metrics:
  Collision Checks: 125,000/frame  ← PROBLEM!
```

**Problem**: Physics is taking 28ms (70% of frame time)
**Cause**: 125,000 collision checks = spatial grid NOT working (should be ~3,000)
**Solution**: Check if spatial grid is properly initialized

---

### Scenario 2: Slow Updates
```
FPS: 20.0 | Frame Time: 50.00ms
  Update: 42.00ms | Physics: 3.00ms | Render: 5.00ms

Detailed Metrics:
  Players Updated: 10,000/frame  ← PROBLEM!
```

**Problem**: Update is taking 42ms (84% of frame time)
**Cause**: Updating all 10,000 players every frame
**Solution**: Enable update throttling in config:
```python
ENABLE_UPDATE_THROTTLING = True
UPDATE_BATCHES_PER_FRAME = 4  # Update 2,500 players/frame instead
```

---

### Scenario 3: Slow Rendering
```
FPS: 35.0 | Frame Time: 28.50ms
  Update: 5.00ms | Physics: 4.00ms | Render: 19.50ms

Detailed Metrics:
  Players Rendered: 8,500/frame
  Players Culled: 0/frame  ← PROBLEM!
  Culling Efficiency: 0.0% off-screen
```

**Problem**: Rendering 8,500 players every frame, no culling
**Cause**: View frustum culling not enabled or not working
**Solution**: Enable culling in config:
```python
ENABLE_VIEW_FRUSTUM_CULLING = True
```

---

### Scenario 4: Optimal Performance
```
FPS: 58.3 | Frame Time: 17.15ms
  Update: 8.42ms | Physics: 5.31ms | Render: 3.42ms

Detailed Metrics:
  Collision Checks: 1,247/frame  ✓
  Players Updated: 250/frame  ✓ (1,000 total, 4 batches)
  Players Rendered: 523/frame  ✓
  Players Culled: 477/frame  ✓
  Culling Efficiency: 47.7% off-screen  ✓
```

**Result**: Everything working optimally!
- FPS near 60
- All sections balanced
- Spatial grid working (low collision checks)
- Update throttling active (only 250/frame)
- View frustum culling working (47.7% culled)

---

## Performance Targets by Player Count

| Player Count | Target FPS | Expected Frame Time | Notes |
|--------------|------------|---------------------|-------|
| 100 | 60 | ~16ms | No optimizations needed |
| 1,000 | 50-60 | ~17-20ms | All optimizations on |
| 5,000 | 40-50 | ~20-25ms | Update throttling active |
| 10,000 | 30-40 | ~25-33ms | Higher batch count helps |
| 50,000 | 20-30 | ~33-50ms | May need hardware upgrade |
| 100,000 | 15-25 | ~40-66ms | Requires powerful CPU |

---

## Troubleshooting

### FPS drops over time
**Symptom**: Starts at 60 FPS, drops to 20 FPS after 30 seconds
**Cause**: Memory leak or accumulating objects
**Check**:
- Particle count growing?
- Elimination fade animations not clearing?

### Stuttering / Inconsistent FPS
**Symptom**: FPS jumps between 60 and 30 constantly
**Cause**: Background processes or update throttling mismatch
**Solution**:
- Close other applications
- Adjust `UPDATE_BATCHES_PER_FRAME` to 2 or 8

### High collision checks despite spatial grid
**Symptom**: Collision checks = player_count × player_count
**Cause**: Spatial grid not being built or used
**Solution**:
- Verify physics engine is using `_build_spatial_grid()`
- Check that spatial grid cell size is reasonable

---

## Advanced: Exporting Performance Data

The PerformanceMonitor can be extended to export data for analysis:

```python
# In your code:
perf_summary = game.perf_monitor.get_summary()
# Returns: {
#   "fps": 58.3,
#   "avg_frame_time": 17.15,
#   "avg_update_time": 8.42,
#   "avg_physics_time": 5.31,
#   "avg_render_time": 3.42,
#   "total_frames": 3500
# }
```

---

## Summary

✅ **Real-time insights** - See performance metrics every 2 seconds
✅ **Identify bottlenecks** - Know which section is slow
✅ **Validate optimizations** - Confirm spatial grid, culling, etc. are working
✅ **Tune settings** - Adjust config based on actual performance

**Run Battle Royale and watch the performance logs to understand your game's behavior!**
