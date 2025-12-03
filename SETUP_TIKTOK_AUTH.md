# Setup TikTok Authentication for Follower Battle

The script now uses your existing **TiktokAutoUploader** (cookie-based) which is much more reliable.

## Steps to Setup:

### 1. Navigate to TiktokAutoUploader
```bash
cd C:\Users\SondreNorheim\Documents\Video_Editor_Script\tools\TiktokAutoUploader
```

### 2. Run authentication for your follower battle account
```bash
python cli.py auth -u followerbattlegro
```

Replace `followerbattlegro` with your actual TikTok username for the follower battle account.

This will:
- Open a browser window
- Ask you to log in to TikTok
- Save the authentication cookie to `CookiesDir/tiktok_session-followerbattlegro.cookie`

### 3. Update the username in post_run_publish.py

Edit `post_run_publish.py` line 161 and change:
```python
tiktok_username = "followerbattlegro"  # Your actual TikTok username
```

### 4. Test the upload
```bash
cd C:\Users\SondreNorheim\Documents\Follower_Competition_Channel
python post_run_publish.py --delay-seconds 0
```

## Troubleshooting

**Cookie not found error:**
- Make sure you ran `python cli.py auth -u <username>` successfully
- Check that the cookie file exists in `TiktokAutoUploader/CookiesDir/`
- Verify the username matches exactly (case-sensitive)

**Upload fails:**
- Re-authenticate: `python cli.py auth -u <username>`
- TikTok cookies expire - you may need to re-auth periodically
- Check TikTok hasn't flagged your account

## Current Status

✅ Instagram: Working perfectly with `instagrapi`
❌ TikTok: Needs cookie authentication setup (one-time)

Once setup, both platforms will upload automatically!
