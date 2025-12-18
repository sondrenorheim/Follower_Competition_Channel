# Profile Picture Fetching Guide - Authenticated Playwright Method

## Overview
This guide shows you how to safely fetch profile picture URLs for all 39,666 followers using a **burner Instagram account** with the Playwright script.

## ⚠️ Important Safety Notes

### Using a Burner Account
- **DO NOT use your main Instagram account**
- Create a fresh burner account at instagram.com
- Use a temporary email (tempmail.com, guerrillamail.com, etc.)
- No 2FA needed
- Account may get restricted/banned - that's why we use a burner

### Safety Features in the Script
✅ **Ultra-safe delays**: 8-15 seconds between profiles (human-like)
✅ **Session limits**: Stops after 200 profiles (~45 min session)
✅ **Browser restarts**: Restarts Chrome every 40 profiles (avoid patterns)
✅ **Avatar guard**: Detects and rejects burner account's own avatar
✅ **Auto-save**: Saves progress every 25 profiles
✅ **Resumable**: Can stop and resume anytime

## Prerequisites

### 1. Install Playwright
```bash
pip install playwright
playwright install chromium
```

### 2. Create Burner Instagram Account
1. Go to instagram.com
2. Sign up with temporary email
3. Use simple username (e.g., "user12345")
4. Skip all profile setup steps
5. Don't follow anyone (not required)

## How to Use

### Step 1: First Run (Login)
```bash
python fill_profile_pics_system_chrome.py
```

**What happens:**
- Chrome window opens
- Script prompts: "🔐 Please log in in the opened Chrome window"
- You manually log in with your burner account
- Press Enter in terminal when logged in
- Script saves session to `ig_state.json`
- Starts fetching profile pictures

### Step 2: Monitor Progress
You'll see output like:
```
Loaded: 39666 entries
Missing profile_pic_url: 29238
🧍 Detected logged-in avatar URL (will be rejected if returned for others)
➡️  Fetching: username123
✅  Saved avatar URL for: username123
💾  Saved progress to disk (25 updates)
```

### Step 3: Session Stops Automatically
After 200 profiles (~45 minutes), script will stop:
```
⏸️  Session limit reached (200 profiles). Stopping for safety.
✅ Session complete!
📊 Profiles fetched this session: 200/200
💡 To continue, run this script again. It will resume from where it stopped.
```

### Step 4: Resume (Multiple Sessions)
**Wait at least 2-4 hours before next session**, then run again:
```bash
python fill_profile_pics_system_chrome.py
```

Script automatically:
- Skips profiles that already have URLs
- Uses saved session (no login needed)
- Continues from where it stopped

## Timeline Estimate

**With ultra-safe settings:**
- 200 profiles per session
- ~45 minutes per session
- Average 11.5 seconds per profile
- 29,238 missing profiles ÷ 200 = ~146 sessions needed

**Realistic schedule:**
- Run 2-3 sessions per day (wait 2-4 hours between)
- Complete in ~2 months (running casually)
- Or run 5-6 sessions per day (wait 2 hours between)
- Complete in ~3-4 weeks (running aggressively)

## Files Created

1. **ig_state.json** - Your burner account session (don't commit to git)
2. **all_followers_fresh.json** - Updated with profile_pic_url fields
3. **Checkpoints** - Auto-saved every 25 successful fetches

## Troubleshooting

### "Please log in" appears on second run
- Session expired (Instagram logged you out)
- Just log in again manually
- Script will save new session

### Too many failures/rejections
Possible reasons:
- Private profiles (normal - can't access)
- Instagram rate limiting (wait longer between sessions)
- Burner account flagged (create new burner)

### Script crashes
- Progress is auto-saved every 25 profiles
- Just run again - it resumes automatically

### "Rejected (matched your own avatar)"
- Script correctly detected burner's avatar
- This prevents false data
- Working as intended

## Safety Best Practices

1. **Space out sessions**: Wait 2-4 hours between 200-profile batches
2. **Don't run overnight**: Run during day when you can monitor
3. **Watch for rate limits**: If many failures, stop and wait 24h
4. **Use VPN (optional)**: Rotate IP between sessions for extra safety
5. **Expect account loss**: Burner may get banned - that's okay

## After Completion

Once all 29,238 profiles have URLs:

1. **Verify completion:**
   ```bash
   python -c "import json; data = json.load(open('Followers/all_followers_fresh.json')); print(f'{sum(1 for x in data if x.get(\"profile_pic_url\"))} have URLs')"
   ```

2. **Your games will automatically download images:**
   - Games check for `profile_pic_url` in JSON
   - Download to `avatar_cache/` folder
   - Images persist across games

3. **Delete burner artifacts (optional):**
   ```bash
   del ig_state.json
   ```

## Quick Commands

**Start/resume fetching:**
```bash
python fill_profile_pics_system_chrome.py
```

**Check progress:**
```bash
python -c "import json; data = json.load(open('Followers/all_followers_fresh.json')); total = len(data); with_pics = sum(1 for x in data if x.get('profile_pic_url')); print(f'{with_pics}/{total} ({with_pics*100/total:.1f}%) have profile_pic_url')"
```

**Clean up (after done):**
```bash
del ig_state.json
```

## Risk Summary

**With burner account:**
- ✅ Your main account: 0% risk (not involved)
- ⚠️ Burner account: Medium risk (may get restricted/banned)
- ⚠️ IP address: Low risk (use VPN if concerned)

**Without burner account (NOT RECOMMENDED):**
- ❌ Main account: High risk (could get banned)
- ❌ Don't do this

## Questions?

**Q: How long does it take?**
A: ~2 months running casually (2-3 sessions/day), or ~3-4 weeks running aggressively (5-6 sessions/day)

**Q: Can I speed it up?**
A: You could reduce delays, but increases risk. Current settings are ultra-safe.

**Q: What if burner gets banned?**
A: Create new burner account, delete `ig_state.json`, run script again (it resumes)

**Q: Do I need to follow anyone?**
A: No - burner just needs to be logged in

**Q: Can I run multiple burners in parallel?**
A: Technically yes, but complex and higher risk. Stick with one.

**Q: Can I use main account "just this once"?**
A: NO. Use burner only. Main account ban is permanent.
