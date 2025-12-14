# Daily Video Production Workflow
**Fast profile picture updates for new followers**

---

## Overview

This workflow lets you:
- ✅ Scrape new followers daily
- ✅ Only fetch profile pics for NEW followers (5-10 minutes)
- ✅ Merge with existing followers
- ✅ Run game with updated list
- ✅ No need to re-fetch 12,000+ existing followers

---

## One-Time Setup (Do Once)

### Step 1: Create Your Baseline File

This is your "master" file with all existing followers and their profile pictures.

**Option A: If you don't have profile pics yet**
```bash
# This will take ~15 hours for 12,000 followers
# Run overnight or in batches over several days
python fetch_profile_pics_no_auth.py
```

Edit the script first:
```python
INPUT_FILE = "followers_safe_20251213_merged.json"
OUTPUT_FILE = "followers_baseline_with_pics.json"
```

**Option B: If you already have some profile pics**
```bash
# Use your existing file as baseline
copy followers_safe_20251213_merged.json followers_baseline_with_pics.json
```

---

## Daily Workflow (Each Day)

### Morning: Scrape New Followers

**Option 1: Use existing scrapers**
```bash
# If you have working scraper
python safe_html_follower_scraper.py

# Or alphabet scraper (if not flagged)
python alphabet_follower_scraper.py
```

**Option 2: Manual scrape**
- Use burner account
- Export to: `followers_today.json`

### Afternoon: Update Profile Pictures (5-10 minutes)

**Edit `incremental_profile_pic_update.py` first:**
```python
BASELINE_FILE = "followers_baseline_with_pics.json"  # Your master file
NEW_FOLLOWERS_FILE = "followers_today.json"          # Today's scrape
OUTPUT_FILE = f"followers_updated_{datetime.now().strftime('%Y%m%d')}.json"
```

**Run the incremental update:**
```bash
python incremental_profile_pic_update.py
```

**What it does:**
1. Compares today's list vs. baseline
2. Finds NEW followers (e.g., 50 new today)
3. Fetches profile pics ONLY for those 50 (takes ~3 minutes)
4. Merges everything into updated file
5. Saves as `followers_updated_YYYYMMDD.json`

### Evening: Run Your Game

**Update config.py:**
```python
FOLLOWER_IMPORT_FILE = "followers_updated_20251213.json"  # Today's file
DOWNLOAD_PROFILE_PICTURES = True
TEST_MODE = False
EXPORT_VIDEO = True
```

**Run the game:**
```bash
python main.py
```

### Night: Update Baseline (Optional)

After successful video:
```bash
# Make today's file the new baseline
copy followers_updated_20251213.json followers_baseline_with_pics.json
```

---

## Example Timeline

**Day 1 (Initial Setup)**
- 9:00 AM - Start baseline profile pic fetch (12,000 followers)
- Let run in background all day/night
- Takes ~15 hours

**Day 2 (First Daily Update)**
- 9:00 AM - Scrape new followers (50 new followers found)
- 9:05 AM - Run incremental update (fetches 50 profile pics in 3 minutes)
- 9:10 AM - Have complete updated list ready
- 10:00 AM - Run game simulation
- 12:00 PM - Export and upload video
- ✅ Done for the day!

**Day 3+ (Normal Daily Routine)**
- 9:00 AM - Scrape new followers (~50-100 new)
- 9:05 AM - Incremental update (3-5 minutes)
- 9:10 AM - Run game
- ✅ Repeat forever

---

## Typical Numbers

| Followers | First Time | Daily Update |
|-----------|------------|--------------|
| 100 new | ~5 min | ~5 min |
| 500 new | ~25 min | ~25 min |
| 1,000 new | ~50 min | ~50 min |
| 12,000 (baseline) | ~15 hours | N/A (one time) |

**Most days:** 50-100 new followers = 3-5 minutes

---

## Pro Tips

### 1. Run Baseline in Batches
If 15 hours is too long, split into batches:

```bash
# Day 1: First 2,000
python fetch_profile_pics_no_auth.py
# Stop after 2,000, continue tomorrow

# Day 2: Resume (script auto-skips completed ones)
python fetch_profile_pics_no_auth.py
```

### 2. Selenium for Baseline (More Reliable)
```bash
# For one-time baseline, use Selenium (more reliable but slower)
python fetch_profile_pics_selenium.py
```

### 3. Mixed Approach for Baseline
```bash
# Use fast method until blocked
python fetch_profile_pics_no_auth.py
# When blocked, switch to Selenium for remaining
python fetch_profile_pics_selenium.py
```

### 4. Pre-fetch During Off Hours
Run baseline fetch overnight when you're not using the computer

### 5. Weekly Full Refresh
Once a week, re-fetch all profile pics to catch updated avatars:
```bash
# Update everyone's profile pic
python fetch_profile_pics_no_auth.py
```

---

## File Organization

Suggested folder structure:
```
followers_baseline_with_pics.json      # Master file (updated weekly)
followers_safe_20251213.json           # Daily scrapes (raw)
followers_updated_20251213.json        # Daily final (scrape + pics)
followers_updated_20251214.json        # Next day
followers_updated_20251215.json        # Next day
...
```

---

## Automation Script (Optional)

Want to automate the whole daily workflow? See `daily_automation_loop.py`

Or create a simple batch file:

**`daily_update.bat`:**
```batch
@echo off
echo Starting daily follower update...

REM Step 1: Scrape new followers
python safe_html_follower_scraper.py

REM Step 2: Update profile pictures for new followers
python incremental_profile_pic_update.py

REM Step 3: Run game
python main.py

echo Daily update complete!
pause
```

---

## Troubleshooting

**"No new followers found"**
- Check that NEW_FOLLOWERS_FILE is different from BASELINE_FILE
- Verify scraper actually got new data

**"Rate limited during incremental update"**
- Only 50-100 new followers, should be fine
- If blocked, wait 30 min and retry
- Increase MIN_DELAY to 4.0 seconds

**"Baseline taking too long"**
- Run in batches over multiple days
- Switch to Selenium for better reliability
- Use Selenium overnight (20 hours)

**"Profile pics not showing in game"**
- Set DOWNLOAD_PROFILE_PICTURES = True
- Set LOAD_PROFILE_PICTURES = True
- Check avatar_cache/ folder exists

---

## Summary

✅ **One-time:** Fetch baseline 12,000 followers (15 hours)
✅ **Daily:** Scrape new followers (5 min)
✅ **Daily:** Incremental update (3-5 min)
✅ **Daily:** Run game (as normal)

**Total daily time:** ~10 minutes for follower updates!
