# How to Get Fresh TikTok Session ID

The TikTok upload failed because the session might be expired. Here's how to get a fresh sessionid:

## Method 1: Browser Developer Tools (Easiest)

1. Open Chrome/Edge browser
2. Go to https://www.tiktok.com and log in to your account
3. Press F12 to open Developer Tools
4. Go to the "Application" tab (or "Storage" in Firefox)
5. In the left sidebar, expand "Cookies" and click on "https://www.tiktok.com"
6. Find the cookie named `sessionid`
7. Copy the value (it's a long string)
8. Update your `tiktok_follower_account_sessionid.json` file:
   ```json
   {
     "sessionid": "paste-your-copied-sessionid-here"
   }
   ```

## Method 2: Use Browser Extension

1. Install "EditThisCookie" Chrome extension
2. Go to https://www.tiktok.com (logged in)
3. Click the extension icon
4. Find `sessionid` cookie
5. Copy the value

## Common Issues

- **Session expires quickly**: TikTok sessions expire faster than Instagram
- **Multiple failed uploads**: TikTok may rate limit you - wait 1-2 hours
- **Video in drafts**: Check your TikTok drafts - the video might be uploaded but not published

## Alternative: Manual Upload

If the API keeps failing, you can:
1. Download the video from `Videos/Day_12/battle_royale_day_12.mp4`
2. Upload manually through TikTok app/website
3. Use the same caption from the script
