"""
Quick Baseline Setup
Helps you create your baseline follower file with profile pictures
Uses the mixed approach for best results
"""

import json
import subprocess
import time
from pathlib import Path
from datetime import datetime

INPUT_FILE = "followers_safe_20251213_merged.json"
OUTPUT_FILE = "followers_baseline_with_pics.json"


def count_followers_with_pics(filename):
    """Count how many followers have profile pic URLs"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)

        total = len(data)
        with_pics = sum(1 for item in data if item.get('profile_pic_url', '').strip())
        without_pics = total - with_pics

        return total, with_pics, without_pics
    except FileNotFoundError:
        return 0, 0, 0


def main():
    print("\n" + "="*60)
    print("  BASELINE SETUP - PROFILE PICTURE FETCHER")
    print("="*60)
    print()
    print("This will create your baseline follower file with profile pics.")
    print("You only need to do this ONCE, then use incremental updates.")
    print()

    # Check current status
    print("Checking current status...")
    total, with_pics, without_pics = count_followers_with_pics(INPUT_FILE)

    if total == 0:
        print(f"❌ Input file not found: {INPUT_FILE}")
        print("   Please create your follower list first.")
        return

    print(f"\n📊 Current Status:")
    print(f"   Total followers: {total:,}")
    print(f"   ✅ With profile pics: {with_pics:,} ({with_pics/total*100:.1f}%)")
    print(f"   ❌ Without profile pics: {without_pics:,} ({without_pics/total*100:.1f}%)")
    print()

    if without_pics == 0:
        print("✅ All followers already have profile pictures!")
        response = input("Copy to baseline file anyway? (y/n): ")
        if response.lower() == 'y':
            import shutil
            shutil.copy(INPUT_FILE, OUTPUT_FILE)
            print(f"✅ Copied to {OUTPUT_FILE}")
        return

    # Calculate time estimates
    fast_hours = without_pics * 3 / 3600
    slow_hours = without_pics * 6 / 3600

    print("⏱️  Time Estimates:")
    print(f"   Fast method (requests): ~{fast_hours:.1f} hours")
    print(f"   Slow method (selenium): ~{slow_hours:.1f} hours")
    print()

    # Recommend strategy
    print("📋 Recommended Strategy:")
    print()
    print("   OPTION 1: Fast Method (Recommended)")
    print("   • Uses lightweight requests")
    print("   • May get blocked after 500-1000 profiles")
    print("   • Can resume with Selenium if blocked")
    print()
    print("   OPTION 2: Slow But Reliable")
    print("   • Uses Selenium browser automation")
    print("   • More reliable, less likely to block")
    print("   • Takes longer")
    print()
    print("   OPTION 3: Mixed Approach (Best)")
    print("   • Start with fast method")
    print("   • Switch to Selenium if/when blocked")
    print("   • Run overnight")
    print()

    print("Which method do you want to use?")
    print("1. Fast method (requests)")
    print("2. Slow method (Selenium)")
    print("3. Exit (I'll do it manually)")
    print()

    choice = input("Enter choice (1/2/3): ").strip()

    if choice == "1":
        print("\n🚀 Starting fast method...")
        print("   Press Ctrl+C to stop anytime (progress auto-saves)")
        print()
        time.sleep(2)

        # Update the script's config
        with open("fetch_profile_pics_no_auth.py", 'r', encoding='utf-8') as f:
            content = f.read()

        content = content.replace(
            'INPUT_FILE = "followers_safe_20251213_merged.json"',
            f'INPUT_FILE = "{INPUT_FILE}"'
        )
        content = content.replace(
            'OUTPUT_FILE = f"followers_with_pics_{datetime.now().strftime(\'%Y%m%d_%H%M\')}.json"',
            f'OUTPUT_FILE = "{OUTPUT_FILE}"'
        )

        with open("fetch_profile_pics_no_auth.py", 'w', encoding='utf-8') as f:
            f.write(content)

        subprocess.run(["python", "fetch_profile_pics_no_auth.py"])

    elif choice == "2":
        print("\n🌐 Starting Selenium method...")
        print("   Chrome browser will open")
        print("   Press Ctrl+C to stop anytime (progress auto-saves)")
        print()
        time.sleep(2)

        # Update the script's config
        with open("fetch_profile_pics_selenium.py", 'r', encoding='utf-8') as f:
            content = f.read()

        content = content.replace(
            'INPUT_FILE = "followers_safe_20251213_merged.json"',
            f'INPUT_FILE = "{INPUT_FILE}"'
        )
        content = content.replace(
            'OUTPUT_FILE = f"followers_with_pics_{datetime.now().strftime(\'%Y%m%d_%H%M\')}.json"',
            f'OUTPUT_FILE = "{OUTPUT_FILE}"'
        )

        with open("fetch_profile_pics_selenium.py", 'w', encoding='utf-8') as f:
            f.write(content)

        subprocess.run(["python", "fetch_profile_pics_selenium.py"])

    else:
        print("\nℹ️  Manual Setup Instructions:")
        print()
        print("1. Edit fetch_profile_pics_no_auth.py:")
        print(f'   INPUT_FILE = "{INPUT_FILE}"')
        print(f'   OUTPUT_FILE = "{OUTPUT_FILE}"')
        print()
        print("2. Run:")
        print("   python fetch_profile_pics_no_auth.py")
        print()
        print("3. If blocked, switch to:")
        print("   python fetch_profile_pics_selenium.py")
        print()

    # Check final status
    print("\n" + "="*60)
    total, with_pics, without_pics = count_followers_with_pics(OUTPUT_FILE)

    if total > 0:
        print(f"✅ Baseline file created: {OUTPUT_FILE}")
        print(f"   Total: {total:,} followers")
        print(f"   With pics: {with_pics:,} ({with_pics/total*100:.1f}%)")

        if without_pics > 0:
            print(f"\n⚠️  Still missing {without_pics:,} profile pictures")
            print("   Run the script again to continue fetching")

    print("="*60)


if __name__ == "__main__":
    main()
