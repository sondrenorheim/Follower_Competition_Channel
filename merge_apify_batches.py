"""
Merge multiple Apify result files into one master file
Then update all_followers_fresh.json with profile pic URLs
"""

import json
import glob
from pathlib import Path
from datetime import datetime

def load_apify_results(pattern=r"C:\Users\SondreNorheim\Downloads\dataset_instagram-profile-scraper-bio-posts_*.json"):
    """Load all Apify result files from Downloads"""
    files = glob.glob(pattern)

    if not files:
        print(f"No files found matching pattern: {pattern}")
        return []

    all_results = []

    for file in sorted(files):
        print(f"Loading {Path(file).name}...", end=' ')
        with open(file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            all_results.extend(data)
            print(f"({len(data):,} profiles)")

    return all_results

def extract_profile_pics(apify_results):
    """Extract username -> profile_pic_url mapping from Apify results"""
    profile_pics = {}

    for item in apify_results:
        # Apify returns different structures - handle all
        username = item.get('username') or item.get('ownerUsername')
        pic_url = (item.get('hdProfilePicUrl') or
                   item.get('profile_pic_url') or
                   item.get('profilePicUrl'))

        if username and pic_url:
            profile_pics[username] = pic_url

    return profile_pics

def update_followers_with_pics(profile_pics, followers_file="Followers/all_followers_fresh.json"):
    """Update all_followers_fresh.json with new profile pic URLs"""

    # Load existing followers
    print(f"\nLoading {followers_file}...")
    with open(followers_file, 'r', encoding='utf-8') as f:
        followers = json.load(f)

    print(f"Loaded {len(followers):,} followers")

    # Backup first
    backup_file = followers_file.replace('.json', f'_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
    with open(backup_file, 'w', encoding='utf-8') as f:
        json.dump(followers, f, indent=2, ensure_ascii=False)
    print(f"Backup created: {backup_file}")

    # Update profile pics
    updated_count = 0
    not_found_count = 0

    for follower in followers:
        username = follower.get('username')
        if username in profile_pics:
            follower['profile_pic_url'] = profile_pics[username]
            updated_count += 1
        else:
            not_found_count += 1

    # Save updated file
    with open(followers_file, 'w', encoding='utf-8') as f:
        json.dump(followers, f, indent=2, ensure_ascii=False)

    print(f"\nUpdated {followers_file}")
    print(f"  Updated: {updated_count:,} profiles")
    print(f"  Not found: {not_found_count:,} profiles")

    return followers

def main():
    """Main execution"""
    print("\n" + "="*60)
    print("  APIFY BATCH MERGER")
    print("="*60)
    print()

    # Load all Apify results
    print("Step 1: Loading Apify result files...")
    apify_results = load_apify_results()

    if not apify_results:
        print("\nNo results found. Exiting.")
        return

    print(f"\nTotal profiles from Apify: {len(apify_results):,}")

    # Extract profile pic URLs
    print("\nStep 2: Extracting profile picture URLs...")
    profile_pics = extract_profile_pics(apify_results)
    print(f"Extracted {len(profile_pics):,} profile pic URLs")

    # Update followers file
    print("\nStep 3: Updating all_followers_fresh.json...")
    update_followers_with_pics(profile_pics)

    print("\n" + "="*60)
    print("  MERGE COMPLETE!")
    print("="*60)
    print("\nYour all_followers_fresh.json now has updated profile pics!")
    print()

if __name__ == "__main__":
    main()
