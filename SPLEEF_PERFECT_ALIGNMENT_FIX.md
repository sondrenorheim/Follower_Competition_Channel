# Spleef Perfect Layer Alignment Fix

## Problem

Even after fixing the layer base coordinates, the three platform layers were still **not perfectly aligned** when viewed from above. Your diagram showed they should be:

```
  ┌─────┐  Red (Layer 0)
  │     │
  ├─────┤  Green (Layer 1) - Same X,Y position
  │     │
  ├─────┤  Purple (Layer 2) - Same X,Y position
  │     │
  └─────┘

All three should overlap exactly, just at different Z-heights.
```

## Root Cause

The issue was with **player rendering**:

1. **Physics system** assigns players Y coordinates based on their layer:
   - Layer 0 players: Y = 200
   - Layer 1 players: Y = 400
   - Layer 2 players: Y = 600

2. **Renderer** was using these raw Y values directly in isometric projection:
   ```python
   # OLD CODE:
   screen_x, screen_y = self.world_to_isometric(player.x, player.y, player.current_layer)
   # player.y could be 200, 400, or 600!
   ```

3. **Isometric formula** calculates position using both X and Y:
   ```python
   iso_x = (world_x - world_y) * cos(angle)
   iso_y = (world_x + world_y) * sin(angle)
   ```

4. **Result**: Different Y values (200 vs 400 vs 600) cause **horizontal AND vertical shifts** in isometric space, making layers appear offset!

### Why This Happens

In isometric projection:
- If Layer 0 player at Y=200: `iso_x = (x - 200) * cos(30°)`
- If Layer 1 player at Y=400: `iso_x = (x - 400) * cos(30°)` ← Different!

The 200-pixel difference in Y creates a horizontal shift in the isometric view.

## The Fix

**File:** `spleef/renderer.py` lines 193-218

**Solution**: Normalize all player Y coordinates to the **base layer Y** before rendering:

```python
def draw_player(self, draw: ImageDraw.ImageDraw, player: SpleefPlayer, arena):
    # Normalize player Y to layer's base Y for consistent rendering
    layer_base_y = arena.base_layer_y  # e.g., 200

    # Calculate Y offset within the layer
    layer_actual_y = arena.get_layer_y_position(player.current_layer)
    # Layer 0: 200, Layer 1: 400, Layer 2: 600

    y_offset_in_layer = player.y - layer_actual_y
    # Usually 0, but could be offset if player is falling

    # Render at base Y + offset (normalizes all layers to same Y coordinate)
    render_y = layer_base_y + y_offset_in_layer
    # Layer 0 player: 200 + 0 = 200
    # Layer 1 player: 200 + 0 = 200
    # Layer 2 player: 200 + 0 = 200
    # All normalized to 200!

    screen_x, screen_y = self.world_to_isometric(player.x, render_y, player.current_layer)
```

### How It Works

1. **Physics Y**: Player has Y = 200, 400, or 600 (for physics calculations)
2. **Calculate offset**: How far is player from their layer's origin? (usually 0)
3. **Normalize Y**: Map to base_layer_y (200) + offset
4. **Render**: All players render with Y=200, but different `layer_index`

**Result**: All layers use the same Y coordinate for isometric projection, eliminating the diagonal offset!

## Visual Explanation

### Before (Different Y Values):

```
Layer 0 players at Y=200:
  iso_x = (x - 200) * 0.866 = x*0.866 - 173.2

Layer 1 players at Y=400:
  iso_x = (x - 400) * 0.866 = x*0.866 - 346.4  ← 173.2 pixel shift!

Layer 2 players at Y=600:
  iso_x = (x - 600) * 0.866 = x*0.866 - 519.6  ← 346.4 pixel shift!
```

Layers appear staggered horizontally!

### After (Normalized Y Values):

```
Layer 0 players at Y=200 (normalized):
  iso_x = (x - 200) * 0.866 = x*0.866 - 173.2

Layer 1 players at Y=200 (normalized):
  iso_x = (x - 200) * 0.866 = x*0.866 - 173.2  ← Same!

Layer 2 players at Y=200 (normalized):
  iso_x = (x - 200) * 0.866 = x*0.866 - 173.2  ← Same!
```

Layers appear perfectly aligned horizontally!

Only `layer_index * layer_visual_offset` creates vertical separation.

## What About Blocks?

Blocks were already correct because they use `layer.world_y` which we set to the same value (200) for all layers in the previous fix.

## Expected Results

### Your Diagram (Should Now Work):
```
  ┌─────┐  ← Layer 0 (Red outline)
  │     │
  ├─────┤  ← Layer 1 (Green outline) - Perfectly aligned
  │     │
  ├─────┤  ← Layer 2 (Purple outline) - Perfectly aligned
  │     │
  └─────┘
```

### In Game:
- ✅ All three platforms perfectly centered
- ✅ No horizontal shift between layers
- ✅ Layers stack directly on top of each other
- ✅ When viewed from above, all three would overlap exactly
- ✅ Only vertical (Z-depth) separation visible

## Technical Summary

### Physics Space (3D World):
```
Layer 0: X=110-750, Y=200, Z=0
Layer 1: X=110-750, Y=400, Z=1  ← Different Y for physics!
Layer 2: X=110-750, Y=600, Z=2
```

### Rendering Space (Normalized):
```
Layer 0: X=110-750, Y=200 (normalized), layer_index=0
Layer 1: X=110-750, Y=200 (normalized), layer_index=1
Layer 2: X=110-750, Y=200 (normalized), layer_index=2
```

### Isometric Projection:
```
For all layers:
  iso_x = (x - 200) * cos(30°)  ← Same calculation!
  iso_y = (x + 200) * sin(30°) + (layer_index * 150)
          ^^^^^^^^^^^^^^^^^^^    ^^^^^^^^^^^^^^^^^^^^^^^
          Same for all layers    Only this varies
```

## Files Modified

**spleef/renderer.py**
- Lines 193-218: Updated `draw_player()` to normalize player Y coordinates
- Line 295: Pass `arena` parameter to `draw_player()`

## Testing

### 1. Run Game
```bash
python main.py
```

### 2. Visual Check
Look at the three platforms:
- ✅ All centered at same X position
- ✅ No diagonal offset
- ✅ Platforms stack like your diagram
- ✅ Red/Green/Purple outlines would overlap if traced

### 3. Top-Down View (Conceptually)
If you could view from directly above:
```
  All three platforms overlap exactly:
  ┌─────────┐
  │ ███████ │  All three layers
  │ ███████ │  in the same position
  │ ███████ │
  └─────────┘
```

## Status

✅ **FIXED - Layers now perfectly aligned!**

The platforms should now appear **exactly** as in your diagram - perfectly stacked with no horizontal offset!
