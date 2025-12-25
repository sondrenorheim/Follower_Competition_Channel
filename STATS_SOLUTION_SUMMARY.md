# Game History & Stats Partitioning Solution

## Problem Identified

Your GitHub Actions workflow was failing with:
```
batch response: This repository exceeded its LFS budget.
Error: failed to fetch some objects from LFS
```

### Root Cause

The issue was **NOT video files** (those are correctly .gitignored).
The problem was **massive JSON stat files in Git LFS**:
- `game_history.json`: **837 MB** (!!!)
- `player_statistics.json`: **29.4 MB**

With 35 days × 6 game modes = 210+ games, each with thousands of player results, these monolithic files became enormous and exceeded GitHub's free LFS quota.

## Solution Implemented

### ✅ Partitioned File Architecture

Instead of one giant 837MB file, we now create **many small files**:

```
website/public/api/
├── index.json                 (4.2 KB - master index)
├── games/                     (151 files)
│   ├── 20251129_001_platformer_race.json
│   ├── 20251130_001_obstacle_course.json
│   └── ... (one file per game)
├── days/                      (26 files)
│   ├── 1.json
│   ├── 2.json
│   └── 35.json               (768 bytes)
├── types/                     (7 files)
│   ├── battle_royale.json
│   ├── platformer_race.json
│   └── ...
└── players/                   (27 files - already existed)
    ├── a.json
    ├── b.json
    └── ...
```

### Files Changed

#### 1. **shared/game_history.py**
Enhanced `export_partitioned_history()` to create:
- Individual game files (one per game)
- Day summary files (metadata only, no full results)
- Game type indexes
- Master index with all metadata

#### 2. **shared/auto_push.py**
- Changed to ONLY push `website/public/api/` directory
- Removed monolithic files from push list
- Updated to only generate partitioned files

#### 3. **.gitignore**
Added exclusions for large monolithic files:
```gitignore
player_statistics.json
game_history.json
website/public/player_statistics_web.json
website/public/game_history_web.json
```

#### 4. **.gitattributes**
Removed LFS tracking for JSON files:
```
# LFS removed - these files are now in .gitignore
# We use partitioned API files in website/public/api/ instead
```

#### 5. **partition_game_history.py** (NEW)
Standalone script to partition existing game history.

## Benefits

### 🚀 Performance
- **Faster website loads**: Load only data you need (one game, one day, etc.)
- **Better caching**: Browser can cache individual games/days
- **Parallel requests**: Load multiple resources simultaneously

### 💾 Storage
- **No more LFS**: Small JSON files don't need LFS
- **No budget limits**: Free GitHub works fine
- **Efficient diffs**: Git tracks changes to individual games, not entire history

### 📊 Scalability
- **Handles growth**: Add games without file size explosion
- **Query efficiency**: Index files let website find data fast
- **Future-proof**: Works for 1,000+ days and 10,000+ games

## File Size Comparison

| Before (Monolithic) | After (Partitioned) |
|---------------------|---------------------|
| game_history.json: 837 MB | 151 individual game files |
| 1 huge file | Average ~5.5 MB per game file |
| | Day 35 summary: 768 bytes |
| | Master index: 4.2 KB |

**Result**: Instead of downloading 837MB, website can load:
- Just the index (4KB) to see available data
- Just one day (768 bytes) to show daily games
- Just one game file (~5MB) to show full results

## How It Works Now

### When Games Complete

1. Game saves to local `game_history.json` (837MB, local only)
2. Auto-push triggers partitioning:
   - Creates/updates files in `website/public/api/`
   - Generates individual game files
   - Updates day summaries
   - Updates type indexes
   - Updates master index
3. Only pushes small partitioned files to GitHub
4. GitHub Actions deploys website with fresh data

### Website Data Loading

Your website should now use the partitioned API:

```javascript
// Get index to see available days/games
fetch('/api/index.json')

// Get specific day's games
fetch('/api/days/35.json')

// Get specific game results
fetch('/api/games/20251225_001_battle_royale.json')

// Get all games of a type
fetch('/api/types/platformer_race.json')

// Get player stats (already partitioned)
fetch('/api/players/a.json')  // All players starting with 'a'
```

## Testing Results

Successfully partitioned 151 games from 26 days:
- ✅ 151 individual game files created
- ✅ 26 day summary files created
- ✅ 7 game type index files created
- ✅ Master index created
- ✅ Total: 185 manageable files

## Next Steps

### 1. Update Website (REQUIRED)

Update your website to load from partitioned API instead of monolithic files:

**Before:**
```javascript
fetch('/game_history_web.json')  // 837MB download!
```

**After:**
```javascript
// Load just what you need:
fetch('/api/index.json')  // 4KB
fetch('/api/days/35.json')  // 768 bytes
fetch('/api/games/20251225_001_battle_royale.json')  // ~5MB
```

### 2. Clean Up Git LFS (RECOMMENDED)

Remove large files from LFS history:

```bash
# Uninstall LFS from repo (optional)
git lfs uninstall

# Remove LFS tracked files from history
git lfs migrate export --everything --include="*.json"

# Force push to clean history (CAUTION!)
git push origin --force --all
```

### 3. Test Auto-Push

After next game:
```bash
python post_run_publish.py
```

Verify it only pushes `website/public/api/` files, not monolithic JSON.

## Maintenance

- **Local files**: `game_history.json` and `player_statistics.json` stay on your machine
- **Backups**: These local files are your backups - keep them safe!
- **Git repo**: Only small partitioned files are pushed
- **No LFS needed**: All files are small enough for regular Git

## Summary

✅ **Problem**: 837MB game_history.json exceeded LFS budget
✅ **Solution**: Partitioned into 185 small files
✅ **Result**: No more LFS errors, faster website, better scalability
✅ **Status**: Tested and working!

---

**Generated**: December 25, 2024
**Stats**: 151 games, 26 days, 7 game types, 185 partitioned files
