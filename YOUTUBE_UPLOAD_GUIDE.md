# YouTube Upload Integration Guide

This guide explains how to upload your Follower Competition videos to YouTube using the same channel as your movie summary videos.

## 🎯 Overview

Your follower battle videos will now upload to:
- **Instagram** (Reels)
- **TikTok** (Short videos)
- **YouTube** (Same channel as "Singing Narrator" movie summaries)

All three platforms share the same YouTube credentials, so there's **no additional authentication needed**!

---

## 📋 Prerequisites

### ✅ Already Configured (from Movie Pipeline)
- ✅ YouTube OAuth credentials: `client_secret_895049337311-*.json`
- ✅ YouTube token: `youtube_token.json`
- ✅ Both files exist and are authenticated for your channel

### 📦 Required Python Packages
```bash
pip install google-api-python-client google-auth-oauthlib google-auth-httplib2
```

---

## 🚀 Quick Start

### 1. Test YouTube Upload (Recommended First Step)

Test with a single video to verify everything works:

```bash
python test_youtube_upload.py --video "Videos/Day_30/team_battle_day_30.mp4" --day 30 --game "team_battle"
```

This will:
- Authenticate with YouTube (may open browser first time)
- Upload the video as **private** (safe for testing)
- Show you the video URL to verify

### 2. Upload All Videos to YouTube

Once testing succeeds, use the main upload workflow:

```bash
# Upload to all platforms (Instagram, TikTok, YouTube)
python post_run_publish.py

# Upload only to YouTube (skip Instagram/TikTok)
python post_run_publish.py --skip-instagram --skip-tiktok

# Upload as unlisted instead of private
python post_run_publish.py --youtube-privacy unlisted

# Schedule YouTube uploads for 24 hours from now
python post_run_publish.py --youtube-schedule-hours 24
```

---

## 🎬 How It Works

### Video Metadata

Each video gets automatically generated metadata:

**Title:**
```
Follower Team Battle - Day 30 | Real Instagram Followers Battle!
```

**Description:**
```
Watch real Instagram followers compete in an epic Team Battle!

🎮 Day 30 of the Follower Competition
👥 Featuring REAL Instagram followers
🏆 Who will win today's battle?

In this video, Instagram followers battle it out in a team battle competition.
Each player represents a real follower from our community!

📊 Check out the full leaderboard and statistics at:
https://www.followerbattlegrounds.com/

Want to see yourself in the next video? Follow us on Instagram @followerbattlegrounds!
```

**Tags:**
```
Team Battle, Team Battle Day 30, Instagram Team Battle, Follower Battle Royale,
Instagram Followers, Follower Challenge, Instagram Game, Social Media Battle, etc.
```

**Category:** Gaming (YouTube Category ID: 20)

---

## ⚙️ Configuration Options

### Privacy Settings

```bash
# Private (default - only you can see)
python post_run_publish.py --youtube-privacy private

# Unlisted (anyone with link can see)
python post_run_publish.py --youtube-privacy unlisted

# Public (appears in search/recommendations)
python post_run_publish.py --youtube-privacy public
```

### Scheduling

```bash
# Upload as private immediately (default)
python post_run_publish.py

# Schedule to publish in 24 hours
python post_run_publish.py --youtube-schedule-hours 24 --youtube-privacy public
```

### Skip YouTube

```bash
# Only upload to Instagram/TikTok (skip YouTube)
python post_run_publish.py --skip-youtube
```

---

## 📁 File Structure

```
Follower_Competition_Channel/
├── youtube_uploader.py              # YouTube upload module
├── test_youtube_upload.py           # Test script
├── post_run_publish.py              # Main upload workflow (updated)
└── Videos/
    └── Day_30/
        ├── team_battle_day_30.mp4
        ├── battle_royale_day_30.mp4
        └── fighter_arena_day_30.mp4
```

---

## 🔐 Authentication

### First-Time Setup

On first run, you'll see:
```
🔐 Launching browser for Google sign-in...
```

1. Browser opens automatically
2. Log into your Google account (the one linked to your YouTube channel)
3. Grant permissions to the app
4. Token is saved and reused for future uploads

### Token Location

The YouTube token is shared with your movie pipeline:
```
C:\Users\SondreNorheim\Documents\Video_Editor_Script\youtube_token.json
```

This means **no duplicate authentication** - if you're already uploading movies, you're already authenticated!

---

## 📊 Upload Workflow Example

```bash
# Complete workflow with all platforms
python post_run_publish.py \
    --youtube-privacy unlisted \
    --youtube-schedule-hours 0 \
    --delay-seconds 14400
```

This will:
1. Push stats to GitHub
2. Upload each video to:
   - Instagram (as Reel)
   - TikTok (with cookie-based auth)
   - YouTube (as unlisted video)
3. Wait 4 hours (with ±20% randomization) between each set of uploads

---

## 🎮 Supported Game Modes

The uploader recognizes these game modes:
- `battle_royale` → "Battle Royale"
- `fighter_arena` → "Fighter Arena"
- `team_battle` → "Team Battle"
- `obstacle_course` → "Obstacle Course"
- `platformer_race` → "Platformer Race"
- `snake_escape` → "Snake Escape"
- `spleef` → "Spleef"
- `anime_fighting` → "Anime Fighting"

Titles and tags are automatically customized per game mode.

---

## 🐛 Troubleshooting

### "YouTube upload limit reached"
- YouTube has daily upload quotas
- Videos are skipped gracefully and can be retried tomorrow
- The script continues with other uploads

### "Token file corrupted"
- Delete: `C:\Users\SondreNorheim\Documents\Video_Editor_Script\youtube_token.json`
- Re-run the script - browser will open for re-authentication

### "Video not found"
- Check that videos exist in `Videos/Day_XX/` folders
- Verify file paths match the config.py settings

### "Authentication failed"
- Ensure client secret file exists:
  ```
  C:\Users\SondreNorheim\Downloads\client_secret_895049337311-*.json
  ```
- Check that you're logged into the correct Google account

---

## 💡 Tips

### Testing First
Always test with a single video before batch uploading:
```bash
python test_youtube_upload.py --video "Videos/Day_30/team_battle_day_30.mp4" --day 30 --game team_battle
```

### Privacy Strategy
1. Start with `--youtube-privacy private` (safe default)
2. Review uploads on YouTube dashboard
3. Manually publish or set to unlisted/public as needed

### Scheduling Strategy
- Use `--youtube-schedule-hours 24` for daily content calendars
- Videos stay private until scheduled publish time
- You can edit metadata before they go live

### Custom Titles/Descriptions
For manual uploads with custom metadata:
```bash
python youtube_uploader.py \
    --video "Videos/Day_30/team_battle_day_30.mp4" \
    --day 30 \
    --game team_battle \
    --custom-title "Epic Team Battle - Day 30 Finals!" \
    --custom-description "The most intense battle yet..." \
    --privacy unlisted
```

---

## 🔗 Integration with Existing Workflow

The YouTube uploader integrates seamlessly with your current automation:

1. **Game Generation** (`main.py` with `GAME_MODE = "ALL"`)
   - Generates videos for all game modes
   - Saves to `Videos/Day_XX/`

2. **Stats Push + Upload** (`post_run_publish.py`)
   - Pushes stats to GitHub
   - Uploads to Instagram, TikTok, **and now YouTube**
   - 4-hour delays between uploads (with randomization)

3. **Same YouTube Channel**
   - Uses identical credentials as movie pipeline
   - Videos appear on "The Singing Narrator" channel
   - Can be organized into separate playlists

---

## 📈 Next Steps

1. **Test the upload:**
   ```bash
   python test_youtube_upload.py --video "Videos/Day_30/team_battle_day_30.mp4" --day 30 --game team_battle
   ```

2. **Verify on YouTube:**
   - Check your channel's Videos tab
   - Look for the uploaded video (private)
   - Confirm title, description, tags look correct

3. **Enable in main workflow:**
   - Uncomment the upload section in `post_run_publish.py` (lines 365-410)
   - Run full automation with YouTube included

4. **Create playlists (optional):**
   - "Follower Battle Royale"
   - "Team Battle Series"
   - "Fighter Arena Highlights"

---

## 📞 Support

If you encounter issues:
1. Check the error messages carefully
2. Verify all credentials are in place
3. Test with a single video first
4. Check YouTube dashboard for upload status

---

**✅ You're all set!** Your follower battle videos will now reach audiences on Instagram, TikTok, AND YouTube! 🎉
