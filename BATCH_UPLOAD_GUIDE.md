# Batch YouTube Upload Guide

Quick guide for uploading multiple day folders to YouTube with scheduled spacing.

## 🚀 Quick Start

### Upload from Day 13 onwards with 2-hour spacing
```bash
python batch_youtube_upload.py --start-day 13 --spacing-hours 2
```

### Dry run first (recommended!)
```bash
python batch_youtube_upload.py --start-day 13 --spacing-hours 2 --dry-run
```

---

## 📋 Common Commands

### Upload specific range of days
```bash
# Upload Days 13-20 only
python batch_youtube_upload.py --start-day 13 --end-day 20 --spacing-hours 2
```

### Upload as unlisted (visible to anyone with link)
```bash
python batch_youtube_upload.py --start-day 13 --spacing-hours 2 --privacy unlisted
```

### Upload as public (visible in search)
```bash
python batch_youtube_upload.py --start-day 13 --spacing-hours 2 --privacy public
```

### Different spacing intervals
```bash
# 1-hour spacing (tight schedule)
python batch_youtube_upload.py --start-day 13 --spacing-hours 1

# 3-hour spacing (more spread out)
python batch_youtube_upload.py --start-day 13 --spacing-hours 3

# 24-hour spacing (one per day)
python batch_youtube_upload.py --start-day 13 --spacing-hours 24
```

### Continue even if one video fails
```bash
python batch_youtube_upload.py --start-day 13 --spacing-hours 2 --skip-on-error
```

---

## 📊 How It Works

### 1. Finds Day Folders
```
Videos/
├── Day_13/
├── Day_14/
├── Day_15/
└── ...
```

### 2. Detects Game Modes
Automatically detects game mode from filename:
- `team_battle_day_13.mp4` → "team_battle"
- `battle_royale_day_13.mp4` → "battle_royale"
- `fighter_arena_day_13.mp4` → "fighter_arena"

### 3. Schedules Uploads
With `--spacing-hours 2`:
- Video 1: Upload now, publish now (0 hours)
- Video 2: Upload now, publish in 2 hours
- Video 3: Upload now, publish in 4 hours
- Video 4: Upload now, publish in 6 hours
- etc.

### 4. Uploads Sequentially
All videos upload immediately to YouTube, but are scheduled to publish at different times.

---

## 🎯 Example Workflow

### Step 1: Dry Run (Recommended)
```bash
python batch_youtube_upload.py --start-day 13 --spacing-hours 2 --dry-run
```

**Output:**
```
📹 BATCH YOUTUBE UPLOAD WITH SCHEDULING
======================================================================
Start Day: 13
Spacing: 2 hours between videos
Privacy: private
🧪 DRY RUN MODE - No actual uploads will occur
======================================================================

📂 Found 3 day folder(s):
   - Day_13
   - Day_14
   - Day_15

📁 Day_13: Found 3 video(s)
   - battle_royale_day_13.mp4 (battle_royale)
   - fighter_arena_day_13.mp4 (fighter_arena)
   - team_battle_day_13.mp4 (team_battle)

📁 Day_14: Found 3 video(s)
   - battle_royale_day_14.mp4 (battle_royale)
   - fighter_arena_day_14.mp4 (fighter_arena)
   - team_battle_day_14.mp4 (team_battle)

======================================================================
📊 UPLOAD SCHEDULE (6 videos total)
======================================================================
1. battle_royale_day_13.mp4
   Day: 13, Game: battle_royale
   Publish: 2025-12-23 14:00 (0h from now)

2. fighter_arena_day_13.mp4
   Day: 13, Game: fighter_arena
   Publish: 2025-12-23 16:00 (2h from now)

3. team_battle_day_13.mp4
   Day: 13, Game: team_battle
   Publish: 2025-12-23 18:00 (4h from now)

4. battle_royale_day_14.mp4
   Day: 14, Game: battle_royale
   Publish: 2025-12-23 20:00 (6h from now)

5. fighter_arena_day_14.mp4
   Day: 14, Game: fighter_arena
   Publish: 2025-12-23 22:00 (8h from now)

6. team_battle_day_14.mp4
   Day: 14, Game: team_battle
   Publish: 2025-12-24 00:00 (10h from now)
```

### Step 2: Run Actual Upload
```bash
python batch_youtube_upload.py --start-day 13 --spacing-hours 2
```

**Confirmation prompt:**
```
Proceed with uploads? (yes/no):
```

Type `yes` and press Enter to start uploading.

### Step 3: Monitor Progress
The script shows real-time progress:
```
======================================================================
📹 Upload 1/6: battle_royale_day_13.mp4
======================================================================
🔐 Authenticating with YouTube...
✅ YouTube authentication successful.
🚀 Uploading to YouTube (scheduled 0h from now)...
✅ Uploaded successfully! Video ID: abc123
✅ Upload successful (1/6 completed)

======================================================================
📹 Upload 2/6: fighter_arena_day_13.mp4
======================================================================
...
```

### Step 4: Final Summary
```
======================================================================
📊 BATCH UPLOAD SUMMARY
======================================================================
Total videos: 6
✅ Successful: 6
❌ Failed: 0

🎬 Videos will publish over the next 10 hours
   Check YouTube Studio to manage scheduled videos
======================================================================
```

---

## ⚙️ Options Reference

| Option | Description | Example |
|--------|-------------|---------|
| `--start-day` | Starting day number (required) | `--start-day 13` |
| `--end-day` | Ending day number (optional) | `--end-day 20` |
| `--spacing-hours` | Hours between each video | `--spacing-hours 2` |
| `--privacy` | Privacy status | `--privacy unlisted` |
| `--dry-run` | Preview without uploading | `--dry-run` |
| `--skip-on-error` | Continue if a video fails | `--skip-on-error` |

---

## 💡 Tips

### 1. Always Dry Run First
```bash
python batch_youtube_upload.py --start-day 13 --spacing-hours 2 --dry-run
```
This shows you exactly what will happen without actually uploading.

### 2. Start with Private
```bash
# Default is private (safe)
python batch_youtube_upload.py --start-day 13 --spacing-hours 2
```
You can change to unlisted/public later in YouTube Studio.

### 3. Manage Scheduled Videos
After upload:
1. Go to YouTube Studio → Content
2. Filter by "Scheduled"
3. Edit publish times or metadata before they go live
4. Can manually publish early if desired

### 4. Spacing Strategy
- **1-2 hours:** Good for same-day batch release
- **3-6 hours:** Spread throughout one day
- **12-24 hours:** One per day schedule
- **48+ hours:** Multi-day release schedule

### 5. Handle Failures
If a video fails:
- **Default:** Script stops, fix issue and re-run
- **With `--skip-on-error`:** Continues to next video

---

## 🐛 Troubleshooting

### "No day folders found"
- Check that folders are named `Day_13`, `Day_14`, etc.
- Verify you're in the correct directory
- Try absolute path: `--videos-root "C:\Full\Path\To\Videos"`

### "Could not detect game mode"
Video filenames must contain one of:
- `battle_royale`
- `fighter_arena`
- `team_battle`
- `obstacle_course`
- `platformer_race`
- `snake_escape`
- `spleef`
- `anime_fighting`

### "YouTube upload limit reached"
- YouTube has daily upload quotas
- Wait 24 hours and retry
- Or use `--skip-on-error` to skip failed videos

### "Upload timed out"
- Large videos may take longer
- Check internet connection
- Try uploading manually: `python youtube_uploader.py --video "path/to/video.mp4" --day 13 --game "team_battle"`

---

## 📈 Example Schedules

### Tight Schedule (1-hour spacing)
9 videos = 8 hours total
```bash
python batch_youtube_upload.py --start-day 13 --end-day 15 --spacing-hours 1
```
- 2:00 PM - Video 1
- 3:00 PM - Video 2
- 4:00 PM - Video 3
- ...
- 10:00 PM - Video 9

### Daily Schedule (24-hour spacing)
9 videos = 8 days total
```bash
python batch_youtube_upload.py --start-day 13 --end-day 15 --spacing-hours 24
```
- Day 1 - Video 1
- Day 2 - Video 2
- Day 3 - Video 3
- ...
- Day 9 - Video 9

### Mixed Schedule
Upload Days 13-15 with 2-hour spacing, then Days 16-20 with 6-hour spacing:
```bash
# First batch
python batch_youtube_upload.py --start-day 13 --end-day 15 --spacing-hours 2

# Wait, then second batch (starts where first left off)
python batch_youtube_upload.py --start-day 16 --end-day 20 --spacing-hours 6
```

---

## ✅ Quick Checklist

Before running:
- [ ] Videos exist in `Videos/Day_XX/` folders
- [ ] Filenames contain game mode keywords
- [ ] YouTube credentials are set up
- [ ] Run dry run first to preview schedule
- [ ] Confirm spacing and privacy settings

After running:
- [ ] Check YouTube Studio for scheduled videos
- [ ] Verify titles and descriptions look correct
- [ ] Set custom thumbnails if desired
- [ ] Adjust publish times if needed

---

**Ready to upload?** Start with a dry run:
```bash
python batch_youtube_upload.py --start-day 13 --spacing-hours 2 --dry-run
```
