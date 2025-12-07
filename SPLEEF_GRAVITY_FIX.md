# Spleef Gravity/Positioning Fix

## Problem

Players appeared to be positioned on the **edge/side** of the platform instead of on top of blocks. The gravity seemed to push them "sideways" across the platform, destroying many blocks instead of just one underneath them.

### Root Cause

**File:** `spleef/physics.py` line 147 (old version)

The `snap_to_surface()` function was snapping players to the **layer origin Y coordinate** instead of the **block surface Y coordinate**.

```python
# OLD CODE (WRONG):
def snap_to_surface(self, player, arena):
    layer_y = arena.get_layer_y_position(player.current_layer)  # e.g., 200
    player.y = layer_y  # Snaps to layer origin!
    player.vy = 0
```

### Why This Caused the Problem

1. **Layer origin** (`layer_y`): The top-left corner of the layer grid (e.g., 200, 400, 600)
2. **Block centers**: Offset from origin by `(grid_x * 32 + 16, grid_y * 32 + 16)`
   - Example: Block at grid (0,0) has center at (216, 216), not (200, 200)
3. **Players snapped to 200**: They were placed at the layer's edge, not on block centers
4. **Result**: Players appeared to be on the corner/edge of the platform

### Visual Explanation

```
Layer origin at Y=200
│
▼
┌─────────────────────────────  ← Layer edge (where players were)
│  Block (0,0)   Block (1,0)
│  Center: 216   Center: 248
│
│  Block (0,1)   Block (1,1)
│  Center: 248   Center: 280
```

Players were being snapped to Y=200 (edge), but they should be at Y=216, 248, etc. (block centers).

## The Fix

**File:** `spleef/physics.py` lines 138-159

```python
def snap_to_surface(self, player, arena: SpleefArena):
    """
    Snap player to the surface of their current layer
    Players should be ON TOP of blocks, not at the layer origin
    """
    layer = arena.get_layer(player.current_layer)
    if layer:
        # Get the block beneath the player
        block = layer.get_block_at_world_pos(player.x, player.y)
        if block:
            # Snap to the center Y of the block (where player should stand)
            _, block_center_y = layer.grid_to_world(block.grid_x, block.grid_y)
            player.y = block_center_y  # ← Now uses block center!
        else:
            # Fallback: use layer origin (shouldn't happen if block exists)
            layer_y = arena.get_layer_y_position(player.current_layer)
            player.y = layer_y
    player.vy = 0
```

### What Changed

1. **Get the block beneath player**: `layer.get_block_at_world_pos(player.x, player.y)`
2. **Get block's center position**: `layer.grid_to_world(block.grid_x, block.grid_y)`
3. **Snap to block center Y**: `player.y = block_center_y`

Now players snap to the actual surface of the blocks they're standing on!

## Expected Results

### Before Fix:
- ❌ Players positioned at layer edge (Y=200)
- ❌ Players appear to slide sideways
- ❌ Gravity pulls them diagonally across platform
- ❌ Multiple blocks destroyed in a line
- ❌ Confusing visual perspective

### After Fix:
- ✅ Players positioned on block centers (Y=216, 248, etc.)
- ✅ Players stand on top of blocks correctly
- ✅ Gravity pulls players straight down
- ✅ One block breaks beneath each player
- ✅ Clear, intuitive gameplay

## Visual Comparison

### Before (Edge Positioning):
```
        Player ●  ← At Y=200 (edge)
       ╱╱╱╱╱╱╱
      ┌─────────  ← Platform edge
      │ Block    │  ← Block center at Y=216
      └─────────
```
Player falls diagonally across the edge

### After (Block Center Positioning):
```
          ●  ← At Y=216 (block center)
        ┌───┐
        │ █ │  ← Standing ON the block
        └───┘
```
Player falls straight down through the block

## Testing

### 1. Start Game
```bash
python main.py
```

### 2. Observe Initial State
- ✅ All players positioned on top of blocks
- ✅ Players distributed across the platform surface
- ✅ No players on edges or corners

### 3. Watch Gameplay
- ✅ Players move across blocks smoothly
- ✅ Blocks crack beneath players
- ✅ One block breaks per player standing on it
- ✅ Players fall straight down through broken blocks
- ✅ No diagonal sliding or edge behavior

### 4. Check Block Destruction Pattern
- ✅ Blocks break in a natural pattern
- ✅ Not a straight line across the platform
- ✅ Each player destroys their own column of blocks

## Performance Impact

✅ **NO performance impact** - Same number of operations, just using correct Y coordinates

## Related Fixes

This fix works together with the previous spawn position fix:

1. **Spawn fix** (`arena.py:159`): Players spawn at correct block centers initially
2. **Snap fix** (`physics.py:153`): Players stay at block centers when standing on them

Both fixes ensure players are always positioned on block surfaces, not layer edges.

## Status

✅ **FIXED AND READY TO TEST**

The "sideways gravity" issue should now be completely resolved!
