"""
Split usernames into batches optimized for $1.10/1000 pricing
- First batch: $3.49 worth = 3,173 usernames
- Remaining batches: $5.00 worth = 4,545 usernames each
"""

import json

# Load usernames
with open('usernames_to_fetch.txt', 'r', encoding='utf-8') as f:
    usernames = [line.strip() for line in f if line.strip()]

print(f"Total usernames: {len(usernames):,}")

# Batch sizes
FIRST_BATCH_SIZE = 3173  # $3.49 worth
REGULAR_BATCH_SIZE = 4545  # $5.00 worth

batches = []

# First batch (3,173 usernames)
batch_1 = usernames[:FIRST_BATCH_SIZE]
batches.append((1, batch_1, 3.49))

# Remaining batches (4,545 each)
remaining = usernames[FIRST_BATCH_SIZE:]
batch_num = 2

for i in range(0, len(remaining), REGULAR_BATCH_SIZE):
    batch = remaining[i:i + REGULAR_BATCH_SIZE]
    cost = len(batch) * 1.10 / 1000
    batches.append((batch_num, batch, cost))
    batch_num += 1

print(f"\nCreated {len(batches)} batches:")
print()

# Save each batch as Instagram URLs in JSON format
total_cost = 0

for batch_num, batch, cost in batches:
    # Just use plain usernames (no URLs)
    usernames_list = batch

    # Save as JSON
    filename = f"apify_batch_{batch_num}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(usernames_list, f, indent=2)

    total_cost += cost
    print(f"Batch {batch_num}: {len(batch):,} URLs (${cost:.2f}) -> {filename}")

print(f"\nTotal cost: ${total_cost:.2f}")
print(f"Free Apify accounts needed: {len(batches)}")
print(f"\nEach batch file is ready to paste into Apify's JSON editor!")
