# Instaloader Follower Scraper Instructions

## What This Does

This new scraper uses **Instaloader** to fetch ALL your Instagram followers using Instagram's official API pagination. Unlike the browser-based scraper, this method:

✅ **Gets ALL followers** (no popup limits)
✅ **Handles pagination automatically** (no manual scrolling)
✅ **Faster** (direct API calls instead of browser automation)
✅ **Session persistence** (login once, use forever)
✅ **Rate limit handling** (automatically paces requests)

## Setup (One-Time)

### Step 1: Install Instaloader

Run the installation script:
```bash
setup_instaloader.bat
```

Or manually install:
```bash
pip install instaloader
```

### Step 2: Prepare Your Burner Account

You'll need a burner Instagram account to login with:
- ⚠️ **Don't use your main account** (to avoid bans)
- Use a throwaway account
- **Disable 2-factor authentication** on the burner account (Instaloader doesn't support 2FA)

## Usage

### Run the Scraper

```bash
python instaloader_follower_scraper.py
```

### First-Time Login

On first run, you'll be prompted:
```
Instagram Username: [enter your burner account username]
Instagram Password: [enter your burner account password]
```

The session will be saved to `instaloader_session` file. You won't need to login again.

### What Happens

1. **Loads previous followers** from `followers_safe.json`
2. **Fetches ALL followers** from your account using Instaloader
3. **Shows progress** every 100 followers with ETA
4. **Merges** new followers with previous data
5. **Saves** to `followers_safe_YYYYMMDD.json`

### Example Output

```
============================================================
  INSTAGRAM FOLLOWER SCRAPER (Instaloader)
============================================================

[LOADED] 8,188 previous followers from followers_safe.json

============================================================
  SCRAPING FOLLOWERS: @followerbattlegrounds
============================================================

[INFO] Loading saved session...
[OK] Session loaded successfully!

[INFO] Fetching profile: @followerbattlegrounds...
[INFO] Total followers reported by Instagram: 11,234
[INFO] Starting to fetch follower list...

[PROGRESS] 100/11,234 followers (0.9%) - Rate: 15.2/sec - ETA: 12.2 min
[PROGRESS] 200/11,234 followers (1.8%) - Rate: 16.1/sec - ETA: 11.4 min
...
[PROGRESS] 11,200/11,234 followers (99.7%) - Rate: 14.8/sec - ETA: 0.1 min

[SUCCESS] Scraped 11,234 followers!
[TIME] Total time: 12.6 minutes

[MERGE] Previous followers: 8,188
[MERGE] New unique followers: 3,046
[MERGE] Total followers after merge: 11,234

[SAVED] Saved to followers_safe_20251212.json
[SUCCESS] Final follower count: 11,234
```

## Configuration

Edit `instaloader_follower_scraper.py` to change:

```python
TARGET_USERNAME = "followerbattlegrounds"  # Account to scrape
LOGIN_USERNAME = ""  # Your burner account (auto-saved after first login)
SESSION_FILE = "instaloader_session"  # Session file location
```

## Output Format

Same format as the original scraper:
```json
[
  {
    "username": "user123",
    "profile_url": "https://instagram.com/user123",
    "profile_pic_url": "https://..."
  }
]
```

## Troubleshooting

### "Login required but session expired"

Session expired. Delete `instaloader_session` file and run again to re-login.

### "Two-factor authentication is enabled"

Disable 2FA on your burner account temporarily.

### "Instagram may be rate limiting"

Instagram has rate limits (~200 requests/hour). Wait 1-2 hours and try again.

### "Profile does not exist"

Check that `TARGET_USERNAME` is spelled correctly.

## Comparison: Old vs New Scraper

| Feature | Browser Scraper | Instaloader |
|---------|----------------|-------------|
| **All followers** | ❌ Popup limit (~60-100) | ✅ Gets all followers |
| **Speed** | 🐌 Slow (scrolling) | ⚡ Fast (API calls) |
| **Reliability** | ⚠️ Popup breaks | ✅ Stable API |
| **Manual work** | 🖱️ Watch browser | 🤖 Fully automated |
| **Session** | 🍪 Cookies expire | 💾 Saved session |
| **Rate limits** | ⚠️ Can trigger bans | ✅ Auto-paced |

## Recommendation

**Use Instaloader scraper** (`instaloader_follower_scraper.py`) as your primary method going forward. Keep the browser scraper (`safe_html_follower_scraper.py`) as a backup.

## Legal & Safety

⚠️ **Disclaimer**: Automated Instagram scraping may violate Instagram's Terms of Service. Use responsibly:
- Use a burner account (not your main)
- Don't scrape too frequently (once per day max)
- Instagram may ban the account if overused
- This is for personal/educational use only

---

**Questions?** Check the script comments or ask for help!
