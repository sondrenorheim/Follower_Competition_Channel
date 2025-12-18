"""
Create a batch with ONLY the 1,611 new followers added today
"""

import json

# Load current followers
with open('Followers/all_followers_fresh.json', 'r', encoding='utf-8') as f:
    current_followers = json.load(f)

# Load the backup from before we added new followers
with open('Followers/all_followers_fresh_backup_20251218_001144.json', 'r', encoding='utf-8') as f:
    old_followers = json.load(f)

# Create set of old usernames
old_usernames = {f['username'] for f in old_followers}

# Find only NEW usernames
new_followers = []
for follower in current_followers:
    username = follower['username']
    if username not in old_usernames:
        new_followers.append(username)

print(f"Total current followers: {len(current_followers):,}")
print(f"Old followers: {len(old_followers):,}")
print(f"NEW followers: {len(new_followers):,}")

# Save as batch
with open('apify_batch_new_only.json', 'w', encoding='utf-8') as f:
    json.dump(new_followers, f, indent=2)

cost = len(new_followers) * 1.10 / 1000

print(f"\nSaved {len(new_followers):,} new followers to: apify_batch_new_only.json")
print(f"Cost: ${cost:.2f}")
