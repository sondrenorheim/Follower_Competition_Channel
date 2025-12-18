# Profile Picture Cache System

This guide explains how to download and cache profile pictures for fast, reliable game performance.

## Overview

The profile picture cache system downloads all follower profile pictures **once** and stores them on disk. Future game runs load instantly from the cache instead of downloading during gameplay.

### Benefits
- ⚡ **Instant loading**: No waiting for downloads during game startup
- 🛡️ **Reliable**: No network failures or rate limiting during games
- 💾 **Efficient**: Pictures downloaded once, used forever
- 🔄 **Resume-friendly**: Can stop and resume downloads anytime

## Quick Start

### 1. Check Current Status

See how many profile pictures are already cached:

```bash
python check_cache_status.py
```

### 2. Download All Profile Pictures

Run the cache builder to download all missing profile pictures:

```bash
python download_all_profile_pics.py
```

This will:
- Download profile pictures for all followers with URLs
- Save them to `avatar_cache/` directory
- Skip already-cached pictures (safe to re-run)
- Show progress and estimated time remaining

**Estimated time**: ~5-15 minutes for 40,000 followers (depends on your internet speed)

### 3. Enable Cache in Games

Make sure these settings are configured in [config.py](config.py):

```python
LOAD_PROFILE_PICTURES = True   # Load from cache
DOWNLOAD_PROFILE_PICTURES = False  # Don't download during game (deprecated)
```

### 4. Run Your Games

Profile pictures will now load instantly from the cache!

## How It Works

### Cache Structure

```
avatar_cache/
├── username1.jpg
├── username2.jpg
├── username3.jpg
└── ...
```

- One JPEG file per follower
- Named by Instagram username
- Optimized quality (85%) for smaller file size
- Typical cache size: ~200-500 MB for 40,000 followers

### Download Process

The `download_all_profile_pics.py` script:

1. **Loads** follower data from `Followers/all_followers_fresh.json`
2. **Checks** which profile pictures are already cached
3. **Downloads** missing pictures with:
   - Browser-like headers to avoid rate limiting
   - Automatic retries on failure
   - Progressive backoff on errors
   - Rate limiting (0.25s between requests)
4. **Saves** images as optimized JPEGs
5. **Reports** progress every 100 downloads

### Game Loading

When you run a game with `LOAD_PROFILE_PICTURES = True`:

1. Game checks `avatar_cache/{username}.jpg` exists
2. If exists: Loads instantly from disk ⚡
3. If missing: Falls back to colored circle (no download)
4. In-memory cache prevents re-loading same image multiple times

## Common Scenarios

### Scenario 1: New Followers Added

When you add new followers to `all_followers_fresh.json`:

```bash
# Check how many are missing
python check_cache_status.py

# Download only the missing ones
python download_all_profile_pics.py
```

The script automatically skips already-cached pictures.

### Scenario 2: Corrupted Cache Files

If some cache files get corrupted:

```bash
# The download script will verify and report issues
python download_all_profile_pics.py
```

Delete corrupted files and re-run to re-download them.

### Scenario 3: Testing Without Pictures

For faster testing, disable profile pictures:

```python
# config.py
LOAD_PROFILE_PICTURES = False  # Use colored circles instead
```

Games will use random colored circles instead of profile pictures.

### Scenario 4: Moving Cache to Different Machine

Copy the entire `avatar_cache/` folder:

```bash
# On machine 1
tar -czf avatar_cache.tar.gz avatar_cache/

# Transfer to machine 2
# Extract
tar -xzf avatar_cache.tar.gz
```

## Troubleshooting

### "No URL available" for many followers

**Cause**: Profile picture URLs haven't been fetched yet.

**Solution**: Run `fetch_profile_pics_no_auth.py` or use Apify to get URLs first:

```bash
python fetch_profile_pics_no_auth.py
```

### Downloads failing with 429 errors (Rate Limited)

**Cause**: Instagram CDN is rate limiting your requests.

**Solutions**:
1. Wait 1-2 hours and retry
2. Use a VPN to change IP address
3. Increase `MIN_DELAY` in `download_all_profile_pics.py`

### Cache using too much disk space

**Current size**: Check with `check_cache_status.py`

**Reduce size**: Lower JPEG quality in `download_all_profile_pics.py`:

```python
# Change quality=85 to quality=70
rgb_img.save(cache_file, 'JPEG', quality=70, optimize=True)
```

Then delete cache and re-download.

### Pictures loading slowly during game

**Check**:
1. `LOAD_PROFILE_PICTURES = True` in config.py
2. Cache files exist in `avatar_cache/`
3. Run `check_cache_status.py` to verify

If cache is complete but still slow, you may have too many followers for your system. Consider:
- Using `FOLLOWER_COUNT = 5000` to limit players
- Disabling pictures for testing: `LOAD_PROFILE_PICTURES = False`

## File Reference

| File | Purpose |
|------|---------|
| `download_all_profile_pics.py` | Main cache builder script |
| `check_cache_status.py` | Check cache coverage and status |
| `avatar_cache/` | Directory containing cached profile pictures |
| `config.py` | Game configuration (LOAD_PROFILE_PICTURES setting) |
| `shared/api.py` | Contains cache loading logic |

## Advanced: Batch Processing

If you have a very large follower count (100k+), you can process in batches:

```python
# Edit download_all_profile_pics.py
# Add a limit in load_followers():
followers = load_followers(FOLLOWER_FILE)[:10000]  # First 10k only
```

Run multiple times with different ranges.

## Configuration Options

In `download_all_profile_pics.py`:

```python
BATCH_SIZE = 100     # How often to save progress
MIN_DELAY = 0.25     # Seconds between downloads
MAX_RETRIES = 5      # Retry attempts for failed downloads
TIMEOUT = 15         # Request timeout in seconds
```

**Adjust these** if you experience rate limiting or timeouts.

## Summary

✅ **Recommended workflow:**
1. Get profile picture URLs (using Apify or `fetch_profile_pics_no_auth.py`)
2. Run `python download_all_profile_pics.py` once
3. Set `LOAD_PROFILE_PICTURES = True` in config.py
4. Run games - instant loading!

🔄 **Maintenance:**
- Re-run download script when adding new followers
- Use `check_cache_status.py` to monitor coverage
- Cache persists forever - download once, use forever!
