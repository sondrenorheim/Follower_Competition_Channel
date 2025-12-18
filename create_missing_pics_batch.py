"""
Create Apify batches for followers missing profile pics
"""

import json

# Load all followers
with open('Followers/all_followers_fresh.json', 'r', encoding='utf-8') as f:
    followers = json.load(f)

print(f"Total followers: {len(followers):,}")

# Find usernames without profile pics
missing_pics = []

for follower in followers:
    username = follower.get('username', '')
    pic_url = follower.get('profile_pic_url', '')

    # No profile pic or placeholder
    if not pic_url or pic_url.startswith('http://via.placeholder.com'):
        missing_pics.append(username)

print(f"Missing profile pics: {len(missing_pics):,}")

# Save as single file first
with open('usernames_to_fetch.txt', 'w', encoding='utf-8') as f:
    for username in missing_pics:
        f.write(f"{username}\n")

print(f"Saved to: usernames_to_fetch.txt")

# Now create batches
FIRST_BATCH_SIZE = 3173  # $3.49 worth
REGULAR_BATCH_SIZE = 4545  # $5.00 worth

batches = []

# First batch
if len(missing_pics) > 0:
    batch_1 = missing_pics[:FIRST_BATCH_SIZE]
    batches.append((1, batch_1, min(len(batch_1) * 1.10 / 1000, 3.49)))

    # Remaining batches
    remaining = missing_pics[FIRST_BATCH_SIZE:]
    batch_num = 2

    for i in range(0, len(remaining), REGULAR_BATCH_SIZE):
        batch = remaining[i:i + REGULAR_BATCH_SIZE]
        cost = len(batch) * 1.10 / 1000
        batches.append((batch_num, batch, cost))
        batch_num += 1

print(f"\nCreating {len(batches)} batches:")
print()

# Save each batch
total_cost = 0

for batch_num, batch, cost in batches:
    filename = f"apify_batch_{batch_num}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(batch, f, indent=2)

    total_cost += cost
    print(f"Batch {batch_num}: {len(batch):,} usernames (${cost:.2f}) -> {filename}")

print(f"\nTotal cost: ${total_cost:.2f}")
print(f"Free Apify accounts needed: {len(batches)}")
