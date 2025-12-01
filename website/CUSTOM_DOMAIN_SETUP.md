# Custom Domain Setup Guide

## Setting up www.followerbattleground.com

### Step 1: Configure DNS Records (at your domain registrar)

You need to add DNS records where you purchased `followerbattleground.com`. The exact steps vary by registrar (GoDaddy, Namecheap, Google Domains, etc.), but you'll need to add these records:

**Option A: Using CNAME (Recommended)**
```
Type: CNAME
Name: www
Value: <your-github-username>.github.io
TTL: 3600 (or default)
```

**Option B: Using A Records (for apex domain)**
If you want both `followerbattlegrounds.com` AND `www.followerbattlegrounds.com`:

```
Type: A
Name: @
Value: 185.199.108.153
TTL: 3600

Type: A
Name: @
Value: 185.199.109.153
TTL: 3600

Type: A
Name: @
Value: 185.199.110.153
TTL: 3600

Type: A
Name: @
Value: 185.199.111.153
TTL: 3600

Type: CNAME
Name: www
Value: <your-github-username>.github.io
TTL: 3600
```

### Step 2: Configure GitHub Pages

1. Push your code to GitHub:
   ```bash
   git add .
   git commit -m "Configure custom domain www.followerbattlegrounds.com"
   git push
   ```

2. Go to your GitHub repository settings:
   - Navigate to **Settings** → **Pages**
   - Under "Source", select **GitHub Actions**
   - Under "Custom domain", enter: `www.followerbattlegrounds.com`
   - Check the box "Enforce HTTPS" (wait for DNS to propagate first)
   - Click **Save**

### Step 3: Wait for DNS Propagation

DNS changes can take 24-48 hours to propagate fully, but often work within minutes to a few hours.

You can check DNS propagation at: https://www.whatsmydns.net/

### Step 4: Verify It Works

Once DNS has propagated:
1. Visit `http://www.followerbattlegrounds.com`
2. GitHub will automatically redirect to HTTPS
3. Your website should load!

### Step 5: Test Deployment

When you run a game, the auto-push system will:
1. Update `player_statistics.json` and `game_history.json`
2. Commit and push to GitHub
3. Trigger GitHub Actions to rebuild and deploy
4. Your website updates automatically at `www.followerbattlegrounds.com`

## Troubleshooting

**"Domain does not resolve" error:**
- Wait longer for DNS to propagate
- Double-check your DNS records
- Make sure you're using the correct GitHub username

**HTTPS not working:**
- GitHub needs DNS to be working first before it can issue SSL certificate
- This can take a few hours after DNS propagates
- Once working, check "Enforce HTTPS" in settings

**404 errors:**
- Make sure the CNAME file exists in `website/public/CNAME`
- Verify GitHub Actions workflow completed successfully
- Check repository Settings → Pages shows your custom domain

## Files Already Configured

✅ `website/public/CNAME` - Contains `www.followerbattlegrounds.com`
✅ `website/vite.config.js` - Base path set to `/` for custom domain
✅ `website/src/App.jsx` - Router basename removed
✅ `website/src/utils/dataLoader.js` - Data path updated for custom domain
✅ `.github/workflows/deploy-stats.yml` - GitHub Actions deployment ready

All code is ready - you just need to configure DNS and GitHub Pages settings!
