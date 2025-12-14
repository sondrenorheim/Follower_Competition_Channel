"""
Test if multiple scraping sessions give us new followers
Tracks progress across multiple runs
"""

import json
import glob
from datetime import datetime

def analyze_scraping_progress():
    """Analyze follower files to see if we're getting new unique followers"""

    # Find all follower files sorted by date
    files = sorted(glob.glob("followers_safe_*.json"))

    if len(files) < 2:
        print("Need at least 2 scraping sessions to compare!")
        print(f"Found {len(files)} file(s): {files}")
        return

    print("="*60)
    print("SCRAPING PROGRESS ANALYSIS")
    print("="*60)
    print()

    all_time_followers = {}

    for i, file in enumerate(files, start=1):
        with open(file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Count new unique followers in this file
        new_count = 0
        for follower in data:
            username = follower.get('username')
            if username and username not in all_time_followers:
                all_time_followers[username] = True
                new_count += 1

        total_in_file = len(data)
        total_unique = len(all_time_followers)

        print(f"Session {i}: {file}")
        print(f"  Total in file: {total_in_file}")
        print(f"  New unique: {new_count}")
        print(f"  Cumulative unique: {total_unique}")

        if i > 1:
            # Calculate effectiveness
            if new_count < 100:
                print(f"  ⚠️  WARNING: Only {new_count} new followers - hitting same users!")
            elif new_count < 500:
                print(f"  ⚠️  CAUTION: {new_count} new followers - diminishing returns")
            else:
                print(f"  ✅ GOOD: {new_count} new followers - making progress!")

        print()

    print("="*60)
    print("CONCLUSION:")
    print("="*60)

    if len(files) >= 3:
        # Check last two sessions
        with open(files[-2], 'r') as f:
            prev_data = json.load(f)
        with open(files[-1], 'r') as f:
            curr_data = json.load(f)

        prev_usernames = {f.get('username') for f in prev_data}
        curr_usernames = {f.get('username') for f in curr_data}

        overlap = prev_usernames & curr_usernames
        overlap_pct = (len(overlap) / len(curr_usernames)) * 100

        print(f"Last two sessions overlap: {overlap_pct:.1f}%")
        print()

        if overlap_pct > 90:
            print("❌ HIGH OVERLAP - You're scraping the same followers repeatedly!")
            print("   Recommendation: Try a different burner account")
        elif overlap_pct > 70:
            print("⚠️  MODERATE OVERLAP - Some new followers but hitting limits")
            print("   Recommendation: Use multiple burner accounts")
        else:
            print("✅ LOW OVERLAP - Good progress, keep scraping!")

    print()
    print(f"Total unique followers collected: {len(all_time_followers)}")
    print("="*60)

if __name__ == "__main__":
    analyze_scraping_progress()
