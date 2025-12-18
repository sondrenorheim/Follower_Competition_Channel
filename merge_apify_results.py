"""
Merge Apify Results with Existing Follower Data
Safely updates profile_pic_url fields without overwriting existing data
"""
import json
import os
from datetime import datetime

# Configuration
FOLLOWERS_FILE = "Followers/all_followers_fresh.json"
APIFY_RESULTS_FILE = "apify_results.json"
BACKUP_FILE = f"Followers/all_followers_fresh_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"


def load_json(filepath):
    """Load JSON file with error handling"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✅ Loaded {len(data):,} entries from {filepath}")
        return data
    except FileNotFoundError:
        print(f"❌ File not found: {filepath}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in {filepath}: {e}")
        return None
    except Exception as e:
        print(f"❌ Error loading {filepath}: {e}")
        return None


def save_json(filepath, data):
    """Save JSON file with atomic write"""
    try:
        # Write to temp file first
        temp_file = filepath + ".tmp"
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # Replace original with temp
        os.replace(temp_file, filepath)
        print(f"✅ Saved {len(data):,} entries to {filepath}")
        return True
    except Exception as e:
        print(f"❌ Error saving {filepath}: {e}")
        return False


def normalize_url(url):
    """Normalize profile picture URL for comparison"""
    if not url:
        return None

    # Remove query parameters for comparison
    url = url.split('?')[0]

    # Basic validation - must be HTTPS image URL
    if not url.startswith('https://'):
        return None
    if not any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
        return None

    return url


def main():
    print("=" * 70)
    print("  MERGE APIFY RESULTS WITH EXISTING FOLLOWER DATA")
    print("=" * 70)
    print()

    # Step 1: Load existing follower data
    print("Step 1: Loading existing follower data...")
    followers = load_json(FOLLOWERS_FILE)
    if followers is None:
        return

    # Step 2: Create backup
    print(f"\nStep 2: Creating backup...")
    if save_json(BACKUP_FILE, followers):
        print(f"   Backup saved to: {BACKUP_FILE}")
    else:
        print("   ⚠️  Backup failed, but continuing...")

    # Step 3: Load Apify results
    print(f"\nStep 3: Loading Apify results...")
    apify_data = load_json(APIFY_RESULTS_FILE)
    if apify_data is None:
        print("\n❌ Could not load Apify results. Please ensure:")
        print(f"   1. You've downloaded results from Apify")
        print(f"   2. Saved them as: {APIFY_RESULTS_FILE}")
        print(f"   3. File is in the same directory as this script")
        return

    # Step 4: Build username -> profile_pic_url mapping from Apify
    print(f"\nStep 4: Building profile picture mapping...")
    apify_map = {}
    skipped_count = 0

    for item in apify_data:
        username = item.get('username')

        # Try multiple possible field names from Apify
        pic_url = (
            item.get('profilePicUrlHD') or
            item.get('profilePicUrl') or
            item.get('profile_pic_url_hd') or
            item.get('profile_pic_url')
        )

        # Normalize and validate URL
        pic_url = normalize_url(pic_url)

        if username and pic_url:
            apify_map[username] = pic_url
        else:
            skipped_count += 1

    print(f"   ✅ Valid profile pictures: {len(apify_map):,}")
    print(f"   ⏭️  Skipped (invalid/missing): {skipped_count:,}")

    # Step 5: Count current state
    print(f"\nStep 5: Analyzing current state...")
    before_count = sum(1 for f in followers if f.get('profile_pic_url'))
    missing_count = len(followers) - before_count
    print(f"   Current with profile pics: {before_count:,}")
    print(f"   Current missing pics: {missing_count:,}")

    # Step 6: Update followers with Apify data
    print(f"\nStep 6: Merging Apify data...")
    updated_count = 0
    already_had_count = 0
    not_in_apify_count = 0

    for follower in followers:
        username = follower.get('username')
        current_url = follower.get('profile_pic_url', '').strip()

        # Skip if already has valid URL
        if current_url and current_url.startswith('https://'):
            already_had_count += 1
            continue

        # Try to get URL from Apify results
        if username in apify_map:
            follower['profile_pic_url'] = apify_map[username]
            updated_count += 1
        else:
            not_in_apify_count += 1

    # Step 7: Save updated data
    print(f"\nStep 7: Saving updated follower data...")
    if not save_json(FOLLOWERS_FILE, followers):
        print("\n❌ Failed to save updated data!")
        print(f"   Your backup is safe at: {BACKUP_FILE}")
        return

    # Final summary
    after_count = sum(1 for f in followers if f.get('profile_pic_url'))
    coverage_percent = (after_count / len(followers)) * 100

    print("\n" + "=" * 70)
    print("  MERGE COMPLETE!")
    print("=" * 70)
    print(f"\nResults:")
    print(f"  Total followers: {len(followers):,}")
    print(f"  Before merge: {before_count:,} had profile pics")
    print(f"  After merge:  {after_count:,} have profile pics")
    print(f"  Newly added:  {updated_count:,} profile pics")
    print(f"  Coverage:     {coverage_percent:.1f}%")
    print()
    print(f"  Already had URL: {already_had_count:,}")
    print(f"  Not in Apify:    {not_in_apify_count:,}")
    print()
    print(f"Files:")
    print(f"  Updated: {FOLLOWERS_FILE}")
    print(f"  Backup:  {BACKUP_FILE}")
    print("=" * 70)
    print()

    # Success message
    if updated_count > 0:
        print("✅ Successfully merged Apify results!")
        print()
        print("Next steps:")
        print("  1. Your games will automatically use these profile pictures")
        print("  2. Pictures will be downloaded to avatar_cache/ folder")
        print("  3. No further action needed!")
    else:
        print("⚠️  No new profile pictures were added.")
        print()
        print("Possible reasons:")
        print("  1. All followers already had profile picture URLs")
        print("  2. Apify usernames don't match your follower usernames")
        print("  3. Apify results file format is different than expected")
        print()
        print("Check that apify_results.json has fields like:")
        print("  - 'username' (must match your follower usernames)")
        print("  - 'profilePicUrl' or 'profilePicUrlHD' (must be valid HTTPS URLs)")


if __name__ == "__main__":
    main()
