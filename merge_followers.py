"""
Merge two follower files to create a complete list
"""
import json
from datetime import datetime

# Load both files
with open('followers_safe_20251207.json', 'r', encoding='utf-8') as f:
    prev_followers = json.load(f)

with open('followers_safe_20251208.json', 'r', encoding='utf-8') as f:
    new_followers = json.load(f)

print(f"Previous file (Dec 7): {len(prev_followers)} followers")
print(f"New file (Dec 8): {len(new_followers)} followers")

# Create a dict with username as key for deduplication
all_followers = {}

# Add all previous followers
for follower in prev_followers:
    username = follower['username']
    all_followers[username] = follower

print(f"\nAfter adding previous followers: {len(all_followers)}")

# Add new followers (will overwrite if username exists - gets latest profile pic URL)
new_count = 0
for follower in new_followers:
    username = follower['username']
    if username not in all_followers:
        new_count += 1
    all_followers[username] = follower

print(f"New followers found: {new_count}")
print(f"Total unique followers: {len(all_followers)}")

# Convert back to list
merged_list = list(all_followers.values())

# Save merged file
output_file = f"followers_safe_{datetime.now().strftime('%Y%m%d')}.json"
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(merged_list, f, indent=2)

print(f"\n✅ Saved merged file: {output_file}")
print(f"   Total followers: {len(merged_list)}")
