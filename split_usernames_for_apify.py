"""
Split usernames into batches for multiple free Apify accounts
Each batch = ~1,666 usernames (uses $5 free credit per account)
"""

import json

# Load usernames
with open('usernames_to_fetch.txt', 'r', encoding='utf-8') as f:
    usernames = [line.strip() for line in f if line.strip()]

print(f"Total usernames: {len(usernames):,}")

# Split into batches of 1,666 (safe for $5 credit)
BATCH_SIZE = 1666
batches = []

for i in range(0, len(usernames), BATCH_SIZE):
    batch = usernames[i:i + BATCH_SIZE]
    batches.append(batch)

print(f"Split into {len(batches)} batches")

# Save each batch as Instagram URLs in JSON format
for batch_num, batch in enumerate(batches, 1):
    # Convert to Instagram URLs
    urls = [f"https://www.instagram.com/{username}/" for username in batch]

    # Save as JSON
    filename = f"apify_batch_{batch_num}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(urls, f, indent=2)

    print(f"Batch {batch_num}: {len(batch):,} URLs -> {filename}")

print(f"\n✓ Created {len(batches)} batch files")
print(f"\nNow create {len(batches)} free Apify accounts and run one batch per account!")
