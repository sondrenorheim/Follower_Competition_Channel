# Apify Instagram Profile Picture Fetching Guide

## Overview
Use Apify's Instagram Profile Scraper to fetch profile picture URLs for 29,239 followers.

**Estimated Cost:** $7-15 (includes $5 free credits)
**Time:** 2-4 hours (automated, no manual work)
**Risk:** Zero (Apify uses their infrastructure, not your IP or account)

---

## Step 1: Sign Up for Apify

1. Go to https://apify.com
2. Click "Start for free"
3. Sign up with email
4. Verify email
5. Add payment method (won't charge unless you exceed $5 free credits)

---

## Step 2: Find Instagram Profile Scraper

1. Once logged in, go to: https://apify.com/apify/instagram-profile-scraper
2. Or search "Instagram Profile Scraper" in Apify Store
3. Click "Try for free"

---

## Step 3: Configure the Scraper

### Input Settings:

**1. Direct URLs** (Tab)
- Click "Upload file"
- Upload `usernames_to_fetch.txt` (created in your project folder)
- OR manually paste usernames (one per line)

**2. Results limit**
- Set to: `30000` (more than needed, to ensure all complete)

**3. Scrape type**
- Select: **"Profile"**

**4. Output**
- Format: **JSON**
- Keep all default settings

### Advanced Settings (optional):
- Proxy: Leave as default (residential proxies)
- Max concurrency: 10-20 (default is fine)

---

## Step 4: Run the Scraper

1. Review settings
2. Click **"Start"** button (bottom right)
3. Scraper will show:
   - Status (Running/Succeeded)
   - Progress (X/29,239 profiles scraped)
   - Estimated cost (updates in real-time)
   - Estimated time remaining

**Expected:**
- Duration: 2-4 hours
- Cost: $7-15 (depending on private profiles, retries)

---

## Step 5: Monitor Progress

1. Dashboard shows live updates
2. You can:
   - Close browser (it runs in cloud)
   - Check back later
   - Receive email when done

**Don't worry if some profiles fail:**
- Private profiles will fail (expected)
- Deleted accounts will fail (expected)
- You'll still get 70-80% success rate

---

## Step 6: Download Results

Once complete:

1. Click **"Export"** button
2. Select format: **JSON**
3. Download to your computer
4. Save as: `apify_results.json`

---

## Step 7: Merge Results with Your Data

I'll create a Python script to merge Apify's results with your existing `all_followers_fresh.json`.

Run this script after downloading Apify results:

```python
# merge_apify_results.py
import json

# Load your existing follower data
with open('Followers/all_followers_fresh.json', 'r', encoding='utf-8') as f:
    followers = json.load(f)

# Load Apify results
with open('apify_results.json', 'r', encoding='utf-8') as f:
    apify_data = json.load(f)

# Create username -> profile_pic_url mapping from Apify
apify_map = {}
for item in apify_data:
    username = item.get('username')
    pic_url = item.get('profilePicUrl') or item.get('profilePicUrlHD')
    if username and pic_url:
        apify_map[username] = pic_url

# Update your follower data
updated_count = 0
for follower in followers:
    username = follower.get('username')
    # Only update if currently missing AND Apify has it
    if username in apify_map and not follower.get('profile_pic_url'):
        follower['profile_pic_url'] = apify_map[username]
        updated_count += 1

# Save updated data
with open('Followers/all_followers_fresh.json', 'w', encoding='utf-8') as f:
    json.dump(followers, f, indent=2, ensure_ascii=False)

print(f"✅ Updated {updated_count} profiles with Apify data")
print(f"📁 Saved to Followers/all_followers_fresh.json")
```

---

## Step 8: Run Merge Script

```bash
python merge_apify_results.py
```

Expected output:
```
✅ Updated 20,000-25,000 profiles with Apify data
📁 Saved to Followers/all_followers_fresh.json
```

(Some will fail due to private profiles)

---

## Pricing Breakdown

### What you pay for:
- **Compute units** (processing time)
- **Proxy usage** (residential IPs)
- **Storage** (minimal)

### Estimated costs:
- 29,239 profiles × $0.0003 = ~$8.77
- Minus $5 free credits = **~$3.77 actual cost**

### If it costs more than expected:
- Many private profiles = more retries = higher cost
- You can set a **maximum run time** to cap costs
- Set budget limit in Apify settings

---

## Troubleshooting

### "Scraper failed immediately"
- Check username file format (one per line, plain text)
- Try with just 10 usernames first to test

### "Some profiles returned no data"
- Normal! Private profiles can't be scraped
- Expected success rate: 70-80%

### "Cost is higher than estimated"
- Private profiles cause retries
- Set max run time to 4 hours to cap costs

### "Want to cancel mid-run"
- Click "Abort" button in dashboard
- You only pay for what completed
- Results are still downloadable

---

## Final Verification

After merging, check your coverage:

```bash
python -c "import json; data = json.load(open('Followers/all_followers_fresh.json')); with_pics = sum(1 for f in data if f.get('profile_pic_url')); print(f'{with_pics}/39666 ({with_pics*100/39666:.1f}%) have profile pictures')"
```

Expected result:
```
30,000-35,000/39666 (75-88%) have profile pictures
```

---

## Advantages of Apify

✅ **No account risk** - Uses Apify's infrastructure, not yours
✅ **No IP blocks** - Residential proxy rotation built-in
✅ **Scalable** - Handles 29k profiles easily
✅ **Reliable** - Industry-standard tool used by companies
✅ **Fast** - 2-4 hours vs weeks of manual work
✅ **Cheap** - ~$4 after free credits

---

## Support

If you need help:
- Apify documentation: https://docs.apify.com
- Apify Discord: https://discord.gg/jyEM2PRvMU
- Or message me in this chat!

---

## Alternative: Apify API (Advanced)

If you're comfortable with Python, you can use Apify API to automate everything:

```python
from apify_client import ApifyClient

client = ApifyClient('YOUR_API_TOKEN')

run = client.actor('apify/instagram-profile-scraper').call(
    run_input={
        'usernames': ['username1', 'username2', ...],
        'resultsLimit': 30000
    }
)

# Automatically download results
results = client.dataset(run['defaultDatasetId']).list_items().items
```

Let me know if you want me to set this up!
