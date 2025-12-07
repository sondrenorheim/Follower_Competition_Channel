# Spleef Layer Depth Order Fix

## Problem

The layers were aligned correctly, but appearing in the **wrong visual order**:
- **Top layer** (where players start) was rendering at the **bottom** of the screen
- **Bottom layer** was rendering at the **top** of the screen

This made it look like players were starting at the bottom instead of the top!

## Root Cause

**File:** `spleef/renderer.py` line 272 (old)

The depth sorting was backwards:

```python
# OLD CODE:
depth = (layer_index * 10000) + block.grid_x + block.grid_y
```

**Depth values:**
- Layer 0 (top): depth = 0-19 → drawn FIRST (in back) ❌
- Layer 1 (middle): depth = 10000-10019 → drawn second
- Layer 2 (bottom): depth = 20000-20019 → drawn LAST (in front) ❌

**Problem:**
- Lower depth = drawn first = further back in the scene
- Higher depth = drawn last = closer to viewer

But we were giving **layer 0 the lowest depth**, making it appear in the back!

## The Fix

**File:** `spleef/renderer.py` lines 269-277

**Invert the layer index** for depth calculation:

```python
# NEW CODE:
# Invert layer depth: top layer (0) gets highest depth (drawn last/in front)
inverted_layer = (len(arena.layers) - 1 - layer_index)
depth = (inverted_layer * 10000) + block.grid_x + block.grid_y
```

**New depth values:**
- Layer 0 (top): inverted_layer = 2 → depth = 20000-20019 → drawn LAST (in front) ✅
- Layer 1 (middle): inverted_layer = 1 → depth = 10000-10019 → drawn second ✅
- Layer 2 (bottom): inverted_layer = 0 → depth = 0-19 → drawn FIRST (in back) ✅

## Visual Explanation

### Drawing Order (Front to Back):

```
Painter's Algorithm (back to front):

1. Draw layer 2 (bottom, depth=0) first
   ┌─────────┐
   │ Layer 2 │ (darkest, in back)
   └─────────┘

2. Draw layer 1 (middle, depth=10000) on top
   ┌─────────┐
   │ Layer 1 │ (medium, in middle)
   └─────────┘
         ↑
   Covers layer 2

3. Draw layer 0 (top, depth=20000) last
   ┌─────────┐
   │ Layer 0 │ (brightest, in front)
   └─────────┘
         ↑
   Covers layer 1
```

### Isometric View

```
Before (Wrong):
     Layer 2 (in front) ← Looks like top layer!
         ↓
     Layer 1 (middle)
         ↓
     Layer 0 (in back) ← Looks like bottom layer!

After (Correct):
     Layer 0 (in front) ← Looks like top layer! ✅
         ↓
     Layer 1 (middle)
         ↓
     Layer 2 (in back) ← Looks like bottom layer! ✅
```

## Expected Results

### Visual Layout
- ✅ **Top layer** (brightest) appears at the **top** of the screen
- ✅ **Middle layer** (medium brightness) appears in the **middle**
- ✅ **Bottom layer** (darkest) appears at the **bottom**
- ✅ **Players** appear on the **top** layer initially
- ✅ Natural perspective: top → middle → bottom

### Gameplay Flow
1. Players start on **top layer** (now at top of screen)
2. Blocks break beneath them
3. Players **fall down** to middle layer
4. More blocks break
5. Players **fall down** to bottom layer
6. Players fall through bottom → eliminated

The visual flow now matches the logical flow!

## Technical Details

### Depth Calculation

```python
For 3 layers (layer_count = 3):

Layer 0 (top):
  inverted_layer = 3 - 1 - 0 = 2
  depth = 2 * 10000 + grid_x + grid_y
  depth range: 20000-20019

Layer 1 (middle):
  inverted_layer = 3 - 1 - 1 = 1
  depth = 1 * 10000 + grid_x + grid_y
  depth range: 10000-10019

Layer 2 (bottom):
  inverted_layer = 3 - 1 - 2 = 0
  depth = 0 * 10000 + grid_x + grid_y
  depth range: 0-19
```

### Render Queue Sorting

```python
render_queue.sort(key=lambda x: x[1])
# Sorts by depth (ascending)
# Lower depth = drawn first = further back
# Higher depth = drawn last = closer to viewer
```

## Why This Matters

In isometric games, the **visual top** of stacked platforms should be the **top layer** where gameplay starts. Players expect:

1. Start at the **top** (visually and logically)
2. Fall **downward** (visually and logically)
3. Eliminated at the **bottom** (visually and logically)

The old ordering was confusing because players appeared to start at the visual bottom and fall upward!

## Files Modified

**spleef/renderer.py**
- Lines 269-277: Added layer depth inversion
- Inverts `layer_index` before calculating depth
- Ensures correct visual ordering

## Testing

### 1. Run Game
```bash
python main.py
```

### 2. Visual Check
- ✅ Brightest layer (top) at **top** of screen
- ✅ Medium layer in **middle**
- ✅ Darkest layer (bottom) at **bottom** of screen
- ✅ Players start at **top**

### 3. Gameplay Check
- ✅ Players fall **downward** on screen
- ✅ Layer transitions feel natural
- ✅ Elimination makes visual sense (falling off bottom)

## Status

✅ **FIXED - Layers now in correct visual order!**

The top layer (where players start) should now appear at the **top** of the screen, matching both the logical game flow and player expectations!
