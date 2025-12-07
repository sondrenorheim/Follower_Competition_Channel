# Safe Instagram Reel Upload Guide

## Why This is Safer than instagrapi

- ✅ Uses **real browser** (Selenium) - looks exactly like human behavior
- ✅ Uses your **actual login session** - no API violations
- ✅ **Random delays** between actions - mimics human typing/clicking
- ✅ **Much lower risk** of account restrictions
- ✅ Same approach as your safe follower scraper

## Setup (One-Time)

### 1. Install Selenium

```bash
pip install selenium
```

### 2. Install Chrome WebDriver

Download ChromeDriver that matches your Chrome version:
- Go to: https://chromedriver.chromium.org/downloads
- Or use: `pip install webdriver-manager` (auto-downloads correct version)

Alternatively, if you have Chrome installed, selenium should work automatically with newer versions.

### 3. Save Your Instagram Session (First Time Only)

```bash
python safe_instagram_uploader.py --save-cookies
```

**What happens:**
1. Browser window opens to Instagram
2. **You manually log in** (type username/password)
3. Complete any 2FA if asked
4. Wait until you see your Instagram feed
5. Go back to terminal and press Enter
6. Your session is saved to `instagram_cookies.json`

**This saves your login session** so you don't need to log in every time!

## Usage - Upload Videos

### Single Video Upload

```bash
python safe_instagram_uploader.py --video "path/to/video.mp4" --caption "My caption here"
```

### Upload Multiple Videos with Delays

```bash
# Upload video 1
python safe_instagram_uploader.py --video "video1.mp4" --caption "Day 1"

# Wait 4 hours (14400 seconds)
timeout 14400

# Upload video 2
python safe_instagram_uploader.py --video "video2.mp4" --caption "Day 2"
```

### Example with Your Game Videos

```bash
python safe_instagram_uploader.py \
  --video "Videos/Day_14/battle_royale_day_14.mp4" \
  --caption "Day 14 of making my followers battle! Follow to enter 🥊"
```

## Integration with post_run_publish.py

I can also integrate this into your `post_run_publish.py` script to automatically use the safe uploader instead of instagrapi.

**Would you like me to:**
1. Update `post_run_publish.py` to use the safe Selenium uploader?
2. Create a batch upload script that handles all your game videos with delays?

## Troubleshooting

### "Cookie file not found"
Run `--save-cookies` first to save your login session.

### "Cookies expired"
Cookies expire after ~30 days. Just run `--save-cookies` again to refresh.

### "Could not find file upload input"
Instagram might have changed their UI. Let me know and I can update the script.

### Chrome driver issues
Make sure ChromeDriver version matches your Chrome version, or use:
```bash
pip install webdriver-manager
```

## Safety Tips

- ✅ **Add random delays** between uploads (4-6 hours recommended)
- ✅ **Don't upload too many** videos in one day (2-3 max)
- ✅ **Vary your captions** - don't use identical text
- ✅ **Use --headless** flag to run without opening browser window

## Advanced Usage

### Run in Background (Headless Mode)

```bash
python safe_instagram_uploader.py --video "video.mp4" --caption "Caption" --headless
```

Browser runs invisibly in the background!

### Custom Cookie File Location

```bash
python safe_instagram_uploader.py --save-cookies --cookies-file "my_session.json"
python safe_instagram_uploader.py --video "video.mp4" --cookies-file "my_session.json"
```

## Comparison: Old vs New Method

### Old Way (instagrapi - RISKY)
```python
from instagrapi import Client
cl = Client()
cl.load_settings("session.json")
cl.clip_upload("video.mp4", caption="...")  # ⚠️ Uses unofficial API
```

### New Way (Selenium - SAFE)
```bash
python safe_instagram_uploader.py --video "video.mp4" --caption "..."
# ✅ Uses real browser, looks exactly like human
```

## Next Steps

1. Run `--save-cookies` to set up your session
2. Test with a single video upload
3. If it works, we can integrate into your automation workflow!
