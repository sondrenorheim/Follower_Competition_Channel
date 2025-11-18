# 🚨 INSTAGRAM SCRAPING GUIDE

## ⚠️ CRITICAL WARNING

**Web scraping Instagram violates their Terms of Service and can result in:**

- ❌ **Account suspension or permanent ban**
- ❌ **IP address blocking**
- ❌ **Legal action from Meta/Instagram**
- ❌ **Loss of all your Instagram data**

**USE AT YOUR OWN RISK!** We strongly recommend:
1. Using **offline mode** (default, safe)
2. Using the **official Instagram Graph API** if you have business account access
3. Only scraping if absolutely necessary, and **use a burner account**

---

## 📋 Prerequisites for Scraping

Before attempting to scrape Instagram followers:

1. **Instagram Account** (preferably a throwaway/burner account)
2. **Disable Two-Factor Authentication** (scraping doesn't support 2FA)
3. **Python 3.10+** with Instaloader installed
4. **Stable internet connection**
5. **Patience** (scraping is slow to avoid detection)

---

## 🔧 Setup Instructions

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

This will install `instaloader>=4.10.0` along with other dependencies.

### Step 2: Configure Credentials

Edit `config.py` and set the following:

```python
# Enable scraper mode
USE_INSTALOADER_SCRAPER = True

# Your Instagram credentials
INSTAGRAM_USERNAME = "your_username"      # Your Instagram username
INSTAGRAM_PASSWORD = "your_password"      # Your Instagram password

# Target account (optional)
INSTAGRAM_TARGET_USERNAME = ""            # Leave empty to scrape YOUR followers
                                          # Or set to another username to scrape theirs

# Disable offline mode
USE_OFFLINE_MODE = False
```

### Step 3: Important Security Notes

**🔒 Keep Your Credentials Safe:**
- Never commit `config.py` with real credentials to Git
- Consider using environment variables instead:

```python
import os
INSTAGRAM_USERNAME = os.getenv("INSTA_USER", "")
INSTAGRAM_PASSWORD = os.getenv("INSTA_PASS", "")
```

Then run:
```bash
export INSTA_USER="your_username"
export INSTA_PASS="your_password"
python main.py
```

### Step 4: Run the Game

```bash
python main.py
```

---

## 📊 What to Expect

### First Run (With Password)

```
⚠️  Using INSTALOADER SCRAPER (violates Instagram ToS)
Initializing Instaloader...
Logging in as @your_username...
✅ Login successful, session saved
Fetching profile for @your_username...
Found @your_username: Your Name
Total followers: 1250
Fetching up to 500 followers (this may take a while)...
   Scraped 50/500 followers...
   Scraped 100/500 followers...
   ...
✅ Successfully scraped 500 followers
```

**Time Estimate:** ~5-10 minutes for 500 followers (includes 0.5s delay per follower to avoid rate limiting)

### Subsequent Runs (Cached Session)

```
⚠️  Using INSTALOADER SCRAPER (violates Instagram ToS)
Initializing Instaloader...
Logging in as @your_username...
✅ Loaded existing session
...
```

**Faster:** No login required, session is reused from `.instaloader_session_your_username` file.

---

## 🐛 Common Issues & Solutions

### Issue 1: Two-Factor Authentication Required

```
❌ Two-factor authentication required!
   Please disable 2FA temporarily or handle it manually
```

**Solution:** Disable 2FA on your Instagram account:
1. Instagram App → Settings → Security → Two-Factor Authentication → Turn Off

### Issue 2: Bad Credentials

```
❌ Invalid username or password
```

**Solution:**
- Double-check your username and password in `config.py`
- Make sure there are no extra spaces
- Try logging in via Instagram app/web first to ensure credentials work

### Issue 3: Login Required / Session Expired

```
❌ Login required but session expired
```

**Solution:**
- Delete the session file: `rm .instaloader_session_*`
- Re-run the script to create a new session

### Issue 4: Rate Limiting / Temporary Block

```
❌ Error fetching followers: Too many requests
```

**Solution:**
- **Wait 24-48 hours** before trying again
- Instagram has detected unusual activity
- This is exactly why scraping is risky!

### Issue 5: Account Suspended

```
❌ Login failed: Challenge required
```

**Solution:**
- Instagram flagged your account
- You may need to verify via email/phone
- **This is why we recommend burner accounts!**

---

## 🎯 Best Practices

If you absolutely must scrape:

1. **Use a Burner Account**
   - Create a throwaway Instagram account
   - Don't use your main account!

2. **Scrape Infrequently**
   - Don't run the scraper multiple times per day
   - Wait at least 24 hours between runs

3. **Limit the Count**
   - Start with small numbers (50-100 followers)
   - Don't try to scrape thousands at once

4. **Increase Delays**
   - Edit `modules/api.py` line 268:
   ```python
   time.sleep(2.0)  # Increase from 0.5s to 2s for safety
   ```

5. **Use During Off-Peak Hours**
   - Scrape during night hours in your timezone
   - Less likely to trigger Instagram's anti-bot systems

6. **Monitor for Warnings**
   - If Instagram sends you any warnings, **STOP IMMEDIATELY**
   - Switch to offline mode

---

## 🔄 Switching Back to Safe Mode

If you encounter issues or want to stop scraping:

```python
# In config.py
USE_INSTALOADER_SCRAPER = False  # Disable scraper
USE_OFFLINE_MODE = True          # Enable safe offline mode
```

Then run normally:
```bash
python main.py
```

---

## 📝 Session File Management

Instaloader creates session files to cache your login:

- **File:** `.instaloader_session_your_username`
- **Purpose:** Avoid logging in every time (less suspicious)
- **Delete if:** Login issues, account changes, or switching accounts

```bash
# List session files
ls -la .instaloader_session_*

# Delete all sessions
rm .instaloader_session_*
```

---

## 🆚 Scraper vs Official API vs Offline Mode

| Feature | Official API | Web Scraper | Offline Mode |
|---------|-------------|-------------|--------------|
| **Safety** | ✅ Safe | ❌ Account risk | ✅ Completely safe |
| **Setup Difficulty** | 🟡 Complex | 🟢 Easy | 🟢 None |
| **Speed** | ⚡ Fast | 🐌 Slow | ⚡ Instant |
| **Real Followers** | ✅ Yes | ✅ Yes | ❌ Generated |
| **Profile Pictures** | ✅ Yes | ✅ Yes | ⚫ Colored circles |
| **Account Required** | Business | Regular | None |
| **ToS Violation** | ❌ No | ✅ YES | ❌ No |
| **Recommendation** | ⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐⭐⭐ |

---

## 💡 Recommended Approach

**For most users:** Just use offline mode! It's:
- ✅ **Safe** - No account risk
- ✅ **Fast** - Instant startup
- ✅ **Fun** - Creates creative usernames
- ✅ **Legal** - No ToS violations

The game is designed to work perfectly without real followers!

---

## 📧 Support

If you have issues:
1. Check the error messages carefully
2. Review this guide
3. Try offline mode first
4. Consider if scraping is really necessary

**Remember:** We are NOT responsible for any consequences of using the scraper feature. You accept all risks by using it.
