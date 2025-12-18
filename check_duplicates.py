"""Check for duplicate images in avatar cache"""
import hashlib
from pathlib import Path
from collections import defaultdict

cache_dir = Path("avatar_cache")
hashes = defaultdict(list)

print("Checking for duplicates...")

for jpg_file in cache_dir.glob("*.jpg"):
    # Calculate MD5 hash
    with open(jpg_file, 'rb') as f:
        file_hash = hashlib.md5(f.read()).hexdigest()
    hashes[file_hash].append(jpg_file.name)

# Find duplicates
duplicates = {h: files for h, files in hashes.items() if len(files) > 1}

print(f"\nTotal files: {sum(len(files) for files in hashes.values())}")
print(f"Unique images: {len(hashes)}")
print(f"Duplicate groups: {len(duplicates)}")

if duplicates:
    print("\nDuplicate images found:")
    for file_hash, files in list(duplicates.items())[:10]:
        print(f"\n  Hash {file_hash[:8]}... ({len(files)} copies):")
        for filename in files:
            print(f"    - {filename}")
    if len(duplicates) > 10:
        print(f"\n  ... and {len(duplicates) - 10} more duplicate groups")
else:
    print("\n✅ No duplicates found! All images are unique.")
