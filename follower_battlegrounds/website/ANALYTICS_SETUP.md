# Setting Up Website Analytics

## Google Analytics Setup Instructions

Follow these steps to track visitor statistics on your website:

### 1. Create a Google Analytics Account

1. Go to [https://analytics.google.com/](https://analytics.google.com/)
2. Sign in with your Google account
3. Click "Start measuring" or "Admin" (if you already have an account)

### 2. Create a Property

1. Click "Create Property"
2. Enter property name: "The Follower Battles"
3. Select your timezone and currency
4. Click "Next"

### 3. Set Up Data Stream

1. Select "Web" as the platform
2. Enter your website URL (e.g., `https://yourwebsite.com`)
3. Enter stream name: "The Follower Battles Website"
4. Click "Create stream"

### 4. Get Your Measurement ID

1. After creating the stream, you'll see a **Measurement ID** (looks like `G-XXXXXXXXXX`)
2. Copy this ID

### 5. Add the ID to Your Website

1. Open `website/index.html`
2. Find the two instances of `G-XXXXXXXXXX` (lines 13 and 18)
3. Replace both with your actual Measurement ID
4. Save the file

Example:
```html
<!-- Before -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"></script>
<script>
  gtag('config', 'G-XXXXXXXXXX');
</script>

<!-- After (with your real ID) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-ABC123DEF4"></script>
<script>
  gtag('config', 'G-ABC123DEF4');
</script>
```

### 6. Deploy and Verify

1. Deploy your website with the updated code
2. Visit your website
3. In Google Analytics, go to "Reports" → "Realtime" to see visitors in real-time
4. You should see yourself as an active user

## What You Can Track

Once set up, Google Analytics will show you:

- **Visitor Count**: Total number of visitors (daily, weekly, monthly)
- **Page Views**: How many times each page is viewed
- **User Behavior**: Which pages are most popular
- **Traffic Sources**: Where visitors come from (direct, social media, search, etc.)
- **Device Types**: Desktop, mobile, tablet breakdown
- **Geographic Data**: Countries and cities of your visitors
- **Session Duration**: How long visitors stay on your site
- **Bounce Rate**: Percentage of single-page visits

## Viewing Your Analytics

Access your analytics dashboard at: [https://analytics.google.com/](https://analytics.google.com/)

### Key Reports:
- **Realtime**: See current visitors right now
- **Acquisition**: How users find your site
- **Engagement**: Which pages they visit
- **Demographics**: Age, gender, interests
- **Technology**: Browsers, devices, operating systems

## Alternative: Simple Self-Hosted Analytics

If you prefer not to use Google Analytics, you can also set up a simple self-hosted solution using tools like:
- **Plausible**: Privacy-focused, lightweight
- **Umami**: Simple, fast, open-source
- **Matomo**: Feature-rich, self-hosted

These alternatives require more setup but give you full control over your data.
