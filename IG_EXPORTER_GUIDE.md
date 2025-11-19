# Using IG Exporter Chrome Extension

This guide shows you how to use the **IG Exporter & Scraper** Chrome extension to quickly export your Instagram followers for the game.

## ⚡ Quick Method (5 minutes)

Instead of waiting 24-48 hours for Instagram's Data Download, you can use a Chrome extension for instant export.

### Extension Information

**Name:** IG Exporter & Scraper: Export Instagram Followers & Following data to list
**Link:** [Chrome Web Store](https://chrome.google.com/webstore/search/ig%20exporter)
**Export Limit:** Up to 50,000 followers
**Formats:** CSV and Excel
**Risk Level:** 🟡 Low-Medium (uses your browser session, some account risk)

## 📋 Step-by-Step Instructions

### Step 1: Install Extension

1. Open Chrome browser
2. Go to Chrome Web Store
3. Search for "IG Exporter & Scraper" or "IG Follower Export Tool"
4. Click "Add to Chrome"
5. Click "Add extension"

### Step 2: Export Your Followers

1. **Go to Instagram** (instagram.com) and log in
2. **Click the extension icon** in Chrome toolbar
3. **Click "Export Instagram Data"**
4. **Enter your Instagram username** or profile URL
5. **Select "Followers"** (not following)
6. **Click "Start Export"**
7. **Wait** while it exports (with cooldown periods every 50 followers)
8. **Download CSV** when complete

**Time estimate:** ~5-15 minutes for 500 followers (10 second cooldown every 50 users)

### Step 3: Save the CSV File

The extension will download a file like:
- `instagram_followers.csv`
- `followers_export.csv`
- Or similar name

**Save it to your game folder** (same folder as `main.py`)

### Step 4: Configure the Game

Edit `config.py`:

```python
# Set the path to your exported CSV file
FOLLOWER_IMPORT_FILE = "instagram_followers.csv"

# Choose: Real profile pictures or colored circles
DOWNLOAD_PROFILE_PICTURES = False  # Set to True for real pics (slower)
```

**About profile pictures:**
- `False` (default): Colored circles - **Fast, recommended**
- `True`: Downloads real Instagram profile pics - **Slow** (~500ms per follower)

### Step 5: Run the Game

```bash
python main.py
```

The game will automatically:
1. Detect the semicolon-delimited CSV format
2. Import all usernames
3. Optionally download profile pictures (if enabled)
4. Start the battle royale!

## 📊 CSV Format Details

The extension exports CSV with these columns:
```
followed_by_viewer;full_name;id;is_verified;profile_pic_url;requested_by_viewer;username
```

Our import code automatically:
- ✅ Detects semicolon delimiter (`;`)
- ✅ Finds the `username` column
- ✅ Finds the `profile_pic_url` column
- ✅ Strips quotes from values
- ✅ Handles the format perfectly!

## 🎨 Profile Picture Options

### Option A: Colored Circles (Recommended ✅)

```python
DOWNLOAD_PROFILE_PICTURES = False
```

**What you get:**
- Real usernames from your followers
- Colorful circle avatars (randomly generated)
- **Fast loading** (instant)
- Zero additional bandwidth

**Best for:** Most users, 500+ followers, quick gameplay

### Option B: Real Profile Pictures

```python
DOWNLOAD_PROFILE_PICTURES = True
```

**What you get:**
- Real usernames from your followers
- Real Instagram profile pictures
- **Slow loading** (~500ms per follower = 4+ minutes for 500 followers)
- Downloads images from Instagram

**Best for:** Small follower counts (<100), when you really want real pics

**Note:** Even with real profile pictures, they'll be scaled down to 64x64 pixels in the game, so colored circles often look better!

## ⚠️ Safety Considerations

**Risk Level:** 🟡 Low-Medium

**What's safe:**
- Extension doesn't ask for your password
- Uses your existing browser session
- Doesn't access DMs, posts, or private data

**What's risky:**
- Instagram may detect automated follower list access
- Possible temporary action block (24-48 hours)
- Small chance of account flag

**Recommendation:**
- ✅ Use on a regular account (low risk)
- ✅ Don't run multiple times per day
- ❌ Don't use on a brand/business account you can't risk
- ✅ Wait between exports (24+ hours)

## 🆚 Comparison: Extension vs Official Download

| Feature | Chrome Extension | Instagram Data Download |
|---------|-----------------|------------------------|
| **Speed** | ⚡ 5-15 minutes | 🐌 24-48 hours |
| **Safety** | 🟡 Low-Medium risk | ✅ Zero risk |
| **Profile pics** | ✅ URLs included | ❌ Not included |
| **Setup** | 🟢 Easy (install extension) | 🟢 Easy (request download) |
| **Legal** | 🟡 Gray area | ✅ Official feature |
| **Max followers** | 50,000 | Unlimited |

## 🐛 Troubleshooting

### Issue: "Rate limit error"

**Solution:**
- Increase cooldown in extension settings (try 20-30 seconds)
- Wait 24 hours and try again
- Export in smaller batches

### Issue: "Import failed: No followers found"

**Solution:**
- Make sure the CSV file is in the game folder
- Check the file path in `config.py` is correct
- Open the CSV file to verify it has data

### Issue: "CSV has wrong format"

**Solution:**
- The extension might use different column names
- Open `modules/api.py` and check line 398 for accepted column names
- Or send me the first few lines of your CSV and I can update the parser

## ✅ Expected Output

When you run the game with the imported followers:

```
============================================================
  FOLLOWER BATTLE ROYALE
============================================================

🎮 Initializing game components...
✅ Game initialized successfully!

👥 Setting up 500 followers...
✅ Importing followers from file: instagram_followers.csv
✅ Successfully imported 500 followers

✅ 500 followers spawned in arena

🎮 Starting game loop...
```

If profile picture download is enabled:
```
✅ Importing followers from file: instagram_followers.csv
   Downloading profile pictures... (this may take a few minutes)
   Downloaded 50/500...
   Downloaded 100/500...
   ...
✅ Successfully imported 500 followers with profile pictures
```

## 🎯 Final Tips

1. **Start with colored circles** - Try `DOWNLOAD_PROFILE_PICTURES = False` first
2. **Export during off-peak hours** - Less likely to hit rate limits
3. **Wait between exports** - Don't export multiple times per day
4. **Check the CSV first** - Open it to make sure data exported correctly
5. **Backup the CSV** - Save it so you don't need to export again

---

**Ready to battle? Export your followers and let the games begin! 🎮**
