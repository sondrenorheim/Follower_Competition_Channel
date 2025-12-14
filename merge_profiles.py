"""
Merge profile pictures from multiple sources
Preserves all profile_pic_urls from all sources
"""
import json

# Load all sources
print("Loading followers_safe_20251213_merged.json...")
with open('followers_safe_20251213_merged.json', 'r', encoding='utf-8') as f:
    safe_followers = json.load(f)

print("Loading Followers/all_followers.json...")
with open('Followers/all_followers.json', 'r', encoding='utf-8') as f:
    current_followers = json.load(f)

# Create merged dict
merged = {}

# First priority: followers_safe (has 10,639 profile pics!)
for f in safe_followers:
    username = f.get('username', '')
    if username:
        merged[username] = f.copy()

# Add new followers from current, preserving any profile pics they might have
for f in current_followers:
    username = f.get('username', '')
    if not username:
        continue

    if username in merged:
        # Follower exists, update profile_pic_url if current has one but merged doesn't
        if f.get('profile_pic_url', '') and not merged[username].get('profile_pic_url', ''):
            merged[username]['profile_pic_url'] = f['profile_pic_url']
    else:
        # New follower not in safe file
        merged[username] = f.copy()

# Convert to sorted list
final = sorted(merged.values(), key=lambda x: x.get('username', '').lower())

# Stats
with_pics = sum(1 for f in final if f.get('profile_pic_url', ''))
without_pics = len(final) - with_pics

print(f"\nMERGE RESULTS:")
print(f"  Total followers: {len(final):,}")
print(f"  With profile pics: {with_pics:,}")
print(f"  Need profile pics: {without_pics:,}")

# Save
with open('Followers/all_followers.json', 'w', encoding='utf-8') as f:
    json.dump(final, f, indent=2, ensure_ascii=False)

print(f"\nSaved to Followers/all_followers.json")
