"""
Multi-Burner Account Scraper
Automatically rotates through multiple burner accounts to scrape more followers
"""

import os
import sys

# Check burner account status first
from multi_burner_config import (
    get_active_burners,
    print_burner_status,
    SCRAPING_SETTINGS
)

def main():
    print("\n" + "="*60)
    print("MULTI-BURNER INSTAGRAM SCRAPER")
    print("="*60)

    # Show burner status
    print_burner_status()

    # Check if we have any active burners
    active_burners = get_active_burners()

    if not active_burners:
        print("❌ ERROR: No active burner accounts available!")
        print("\n📋 TODO:")
        print("1. Create new Instagram burner accounts")
        print("2. Edit multi_burner_config.py and add them")
        print("3. Set their status to 'READY'")
        print("4. Run this script again")
        return

    print(f"\n✅ Found {len(active_burners)} active burner account(s)")
    print("\n📋 Scraping Plan:")
    print(f"   - Rotating through {len(active_burners)} burner account(s)")
    print(f"   - ~{SCRAPING_SETTINGS['patterns_per_account']} searches per account")
    print(f"   - Expected total: ~{len(active_burners) * SCRAPING_SETTINGS['patterns_per_account'] * 200:,} followers")

    print("\n" + "="*60)

    choice = input("\n▶ Start scraping with multiple burners? (y/n): ").lower()

    if choice != 'y':
        print("\nCancelled. No changes made.")
        return

    print("\n" + "="*60)
    print("STARTING MULTI-BURNER SCRAPING")
    print("="*60 + "\n")

    # For now, just run the alphabet scraper with the first burner
    # You would run it multiple times with different burners, or modify
    # alphabet_follower_scraper.py to accept burner config as parameter

    print("\n📝 NEXT STEPS (Manual for now):")
    print("\nFor each burner account, run:")

    for i, burner in enumerate(active_burners, 1):
        print(f"\n{i}. Edit alphabet_follower_scraper.py:")
        print(f"   BURNER_USERNAME = \"{burner['username']}\"")
        print(f"   COOKIE_FILE = \"{burner['cookie_file']}\"")
        print(f"\n   Then run: python alphabet_follower_scraper.py")
        print(f"   (Will auto-merge with previous results!)")

    print("\n" + "="*60)
    print("\n💡 TIP: Each burner will add ~3,000-5,000 unique followers")
    print(f"   With {len(active_burners)} burners = ~{len(active_burners) * 4000:,} total followers!")
    print("\n" + "="*60)


if __name__ == "__main__":
    main()
