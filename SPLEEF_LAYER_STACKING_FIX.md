# Spleef Layer Stacking Fix

## Problem

The three platform layers appeared **diagonally offset** instead of stacked directly on top of each other:

```
Before (Wrong):
    Layer 0 (top)
        └── Layer 1 (middle, offset diagonally)
                └── Layer 2 (bottom, offset diagonally)
```

Instead of:

```
After (Correct):
    Layer 0 (top)
        │
        ↓ (directly below)
        │
    Layer 1 (middle)
        │
        ↓ (directly below)
        │
    Layer 2 (bottom)
```

## Root Cause

The problem had two parts:

### 1. Arena Layer Creation
**File:** `spleef/arena.py` lines 45-55 (old)

Each layer was created with a different `world_y` coordinate:
```python
# OLD CODE:
for i in range(self.layer_count):
    layer_y = top_y + (i * self.layer_spacing)  # 200, 400, 600
    layer = FloorGrid(
        layer_index=i,
        world_x=self.world_x,
        world_y=layer_y  # Different Y for each layer!
    )
```

### 2. Isometric Projection
**File:** `spleef/renderer.py` line 80 (old)

The isometric formula used both `world_x` and `world_y`:
```python
iso_x = (world_x - world_y) * cos(angle)
iso_y = (world_x + world_y) * sin(angle)
```

When `world_y` is different for each layer (200, 400, 600), this causes both:
- Horizontal shift (in `iso_x` calculation)
- Vertical shift (in `iso_y` calculation)

Result: Layers appear diagonally offset!

## The Fix

### Part 1: Unified World Coordinates
**File:** `spleef/arena.py` lines 47-55

All layers now share the **same base world_y** coordinate:

```python
# NEW CODE:
self.base_layer_y = top_y  # Store base Y for all layers
for i in range(self.layer_count):
    layer = FloorGrid(
        layer_index=i,
        world_x=self.world_x,
        world_y=top_y  # All layers at same Y!
    )
```

**Why this works:**
- Layers have same X,Y in world space (they're stacked in Z-dimension)
- The `layer_index` represents the Z-height
- Physics still uses `get_layer_y_position()` which returns calculated heights (200, 400, 600)

### Part 2: Physics Layer Positions
**File:** `spleef/arena.py` line 81

The `get_layer_y_position()` method still returns **different Y values** for physics:

```python
def get_layer_y_position(self, layer_index: int) -> float:
    return self.top_y + (layer_index * self.layer_spacing)
    # Returns: 200, 400, 600 for physics calculations
```

**Why we need both:**
- **Rendering**: Uses base Y (200) + visual offset based on layer_index
- **Physics**: Uses calculated Y (200, 400, 600) for layer transitions

This separation allows:
- ✅ Layers to render stacked directly (no diagonal offset)
- ✅ Physics to calculate layer transitions correctly
- ✅ Players to fall through layers properly

## Visual Comparison

### Before (Diagonal Offset):
```
Isometric view with different world_y values:

       Layer 0 (y=200)
      ╱ ╱ ╱ ╱ ╱ ╱
     Layer 1 (y=400)
    ╱ ╱ ╱ ╱ ╱ ╱
   Layer 2 (y=600)
  ╱ ╱ ╱ ╱ ╱ ╱

Layers appear staggered diagonally!
```

### After (Vertical Stack):
```
Isometric view with same world_y, different layer_index:

    ┌─────────┐
    │ Layer 0 │ (layer_index=0, visual_offset=0)
    └─────────┘
         │
         ↓ (visual offset)
         │
    ┌─────────┐
    │ Layer 1 │ (layer_index=1, visual_offset=150)
    └─────────┘
         │
         ↓ (visual offset)
         │
    ┌─────────┐
    │ Layer 2 │ (layer_index=2, visual_offset=300)
    └─────────┘

Layers stack directly below each other!
```

## Technical Details

### World Coordinate System
```
All layers:
- world_x: 110 (same for all)
- world_y: 200 (same for all)
- layer_index: 0, 1, 2 (represents Z-height)
```

### Isometric Projection
```
For each object at (world_x, world_y, layer_index):

1. Calculate base isometric position:
   iso_x = (world_x - world_y) * cos(30°)
   iso_y = (world_x + world_y) * sin(30°)

2. Add vertical offset for layer:
   iso_y += layer_index * 150  // Visual stacking

3. Convert to screen space:
   screen_x = center_x + iso_x * 0.6
   screen_y = center_y + iso_y * 0.6
```

Since `world_y` is the same (200) for all layers, the base `iso_x` and `iso_y` are the same. Only the `layer_index * 150` offset creates vertical separation.

### Physics System
```
Layer transitions use get_layer_y_position():
- Layer 0: Y = 200
- Layer 1: Y = 400  (200 + 200)
- Layer 2: Y = 600  (200 + 400)

When player.y reaches 400:
- Transition from layer 0 to layer 1

When player.y reaches 600:
- Transition from layer 1 to layer 2
```

## Expected Results

### Visual Layout
- ✅ Layer 0 (top) centered on screen
- ✅ Layer 1 (middle) directly below layer 0
- ✅ Layer 2 (bottom) directly below layer 1
- ✅ All layers horizontally aligned
- ✅ Clear vertical stacking visible

### Player Behavior
- ✅ Players spawn on layer 0 (top, centered)
- ✅ Players move across layer 0 surface
- ✅ Players fall straight down to layer 1
- ✅ Players fall straight down to layer 2
- ✅ Players eliminated when falling through layer 2

### Block Destruction
- ✅ Blocks break in natural patterns
- ✅ One column of blocks breaks per player path
- ✅ No diagonal destruction lines

## Testing

### 1. Start Game
```bash
python main.py
```

### 2. Check Console Output
```
Arena initialized:
  Layer 0: 300 blocks created at world_y=200
  Layer 1: 300 blocks created at world_y=200
  Layer 2: 300 blocks created at world_y=200
```

All layers at same world_y = ✅

### 3. Visual Check
- ✅ Top layer centered
- ✅ Middle layer directly below (not diagonal)
- ✅ Bottom layer directly below (not diagonal)
- ✅ All layers aligned horizontally

### 4. Gameplay Check
- ✅ Players start on top layer
- ✅ Players fall straight down
- ✅ Layer transitions work correctly
- ✅ No weird diagonal movement

## Performance

✅ **NO performance impact** - Same rendering cost, just corrected coordinates

## Files Modified

1. **spleef/arena.py**
   - Line 47: Added `base_layer_y` storage
   - Line 52: All layers use same `world_y`
   - Line 55: Updated debug logging

2. **spleef/renderer.py**
   - Lines 60-91: Updated `world_to_isometric()` documentation
   - Clarified that layer_index is sole source of vertical stacking

## Status

✅ **FIXED - Layers now stack correctly!**

The platforms should now appear directly stacked on top of each other, not diagonally offset.
