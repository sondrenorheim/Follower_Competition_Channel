import json

# Read the usernames
with open('usernames_to_fetch.txt', 'r', encoding='utf-8') as f:
    usernames = [line.strip() for line in f if line.strip()]

# Convert to Instagram URLs
urls = [f"https://www.instagram.com/{username}/" for username in usernames]

# Save as JSON array for Apify
with open('apify_urls.json', 'w', encoding='utf-8') as f:
    json.dump(urls, f, indent=2)

print(f"Converted {len(urls)} usernames to Instagram URLs")
print(f"Saved to: apify_urls.json")
print(f"\nNow copy the contents of apify_urls.json and paste into Apify's JSON editor")
