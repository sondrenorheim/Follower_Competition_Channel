"""
Fetch Profile Pictures Using Selenium (Browser Automation)
Uses a real browser to appear more human-like
No authentication required - works for public profiles
"""

import json
import time
import random
from pathlib import Path
from datetime import datetime
from typing import Optional

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    SELENIUM_AVAILABLE = True
except ImportError:
    print("[!]  Selenium not installed. Install with: pip install selenium")
    SELENIUM_AVAILABLE = False

# Configuration
INPUT_FILE = "Followers\chunks\chunk_1.json"
OUTPUT_FILE = "Followers\chunks\chunk_1_with_pics.json"

# Rate limiting (appear human-like)
MIN_DELAY = 4.0   # Minimum seconds between profiles
MAX_DELAY = 8.0   # Maximum seconds between profiles
BATCH_SIZE = 20   # Save progress every N profiles
PAGE_TIMEOUT = 15 # Seconds to wait for page load


def load_followers(filename):
    """Load follower data from JSON file"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"[LOADED] {len(data):,} followers from {filename}")
            return data
    except FileNotFoundError:
        print(f"[ERROR] File not found: {filename}")
        return []
    except Exception as e:
        print(f"[ERROR] Failed to load {filename}: {e}")
        return []


def save_followers(followers, filename):
    """Save followers to JSON file"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(followers, f, indent=2, ensure_ascii=False)
        print(f"[SAVED] {len(followers):,} followers to {filename}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to save {filename}: {e}")
        return False


def setup_driver():
    """Setup Chrome driver with options to avoid detection"""
    print("[SETUP] Initializing Chrome browser...")

    options = webdriver.ChromeOptions()

    # Anti-detection options
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    # Optional: Run headless (no visible browser)
    # options.add_argument('--headless')

    # Optional: Disable images for faster loading
    prefs = {
        "profile.managed_default_content_settings.images": 2,  # Disable images
        "profile.default_content_setting_values.notifications": 2  # Disable notifications
    }
    options.add_experimental_option("prefs", prefs)

    try:
        driver = webdriver.Chrome(options=options)

        # Override navigator.webdriver flag
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        print("[SETUP] [OK] Browser initialized")
        return driver
    except Exception as e:
        print(f"[SETUP] [X] Failed to initialize browser: {e}")
        print("\nMake sure you have Chrome and ChromeDriver installed:")
        print("  1. Download ChromeDriver: https://chromedriver.chromium.org/")
        print("  2. Add it to your PATH or place in project folder")
        return None


def fetch_profile_pic_url(driver, username: str) -> Optional[str]:
    """
    Fetch profile picture URL using Selenium

    Args:
        driver: Selenium WebDriver instance
        username: Instagram username

    Returns:
        Profile picture URL or None if failed
    """
    try:
        url = f"https://www.instagram.com/{username}/"
        driver.get(url)

        # Wait for page to load
        wait = WebDriverWait(driver, PAGE_TIMEOUT)

        # Try to find profile picture
        # Method 1: Look for meta tag
        try:
            meta_tag = driver.find_element(By.CSS_SELECTOR, 'meta[property="og:image"]')
            pic_url = meta_tag.get_attribute('content')
            if pic_url:
                return pic_url
        except NoSuchElementException:
            pass

        # Method 2: Look for img tag with profile picture
        try:
            img_elements = driver.find_elements(By.TAG_NAME, 'img')
            for img in img_elements:
                alt_text = img.get_attribute('alt')
                if alt_text and 'profile picture' in alt_text.lower():
                    src = img.get_attribute('src')
                    if src:
                        return src
        except NoSuchElementException:
            pass

        return None

    except TimeoutException:
        print(f"      Timeout loading page")
        return None
    except Exception as e:
        print(f"      Error: {type(e).__name__}")
        return None


def fetch_all_profile_pictures(followers):
    """
    Fetch profile picture URLs for all followers using Selenium

    Args:
        followers: List of follower dictionaries

    Returns:
        Updated followers list with profile_pic_url populated
    """
    if not SELENIUM_AVAILABLE:
        print("[ERROR] Selenium is required. Install with: pip install selenium")
        return followers

    print("\n" + "="*60)
    print("  PROFILE PICTURE FETCHER (Selenium Browser)")
    print("="*60)
    print()
    print("[i]  This method:")
    print("   • Uses a real Chrome browser")
    print("   • Works for PUBLIC profiles only")
    print("   • More reliable than direct requests")
    print("   • Slower but less likely to be blocked")
    print()

    # Setup browser
    driver = setup_driver()
    if not driver:
        return followers

    try:
        # Stats
        total = len(followers)
        success_count = 0
        fail_count = 0
        skip_count = 0

        # Process each follower
        for i, follower in enumerate(followers, 1):
            username = follower.get('username', '')
            current_url = follower.get('profile_pic_url', '')

            # Skip if already has profile pic URL
            if current_url and current_url.strip():
                skip_count += 1
                if i % 100 == 0:
                    print(f"[{i}/{total}] Skipped {username} (already has URL)")
                continue

            print(f"[{i}/{total}] Fetching: {username:20s}", end=' ')

            # Fetch profile pic URL
            pic_url = fetch_profile_pic_url(driver, username)

            if pic_url:
                follower['profile_pic_url'] = pic_url
                success_count += 1
                print(f"[OK]")
            else:
                fail_count += 1
                print(f"[X]")

            # Human-like delay
            if i < total:
                delay = random.uniform(MIN_DELAY, MAX_DELAY)
                time.sleep(delay)

            # Save progress every BATCH_SIZE profiles
            if i % BATCH_SIZE == 0:
                print(f"\n[CHECKPOINT] Saving progress... ({i}/{total} processed)")
                save_followers(followers, OUTPUT_FILE)
                print()

        # Final summary
        print("\n" + "="*60)
        print("  FETCH COMPLETE")
        print("="*60)
        print(f"Total followers: {total:,}")
        print(f"[OK] Successfully fetched: {success_count:,}")
        print(f"[>>]  Skipped (already had URL): {skip_count:,}")
        print(f"[X] Failed: {fail_count:,}")
        print(f"[FILE] Output file: {OUTPUT_FILE}")
        print("="*60)
        print()

    finally:
        # Always close browser
        print("[CLEANUP] Closing browser...")
        driver.quit()

    return followers


def main():
    """Main execution"""
    # Check dependencies
    if not SELENIUM_AVAILABLE:
        print("\n[X] Missing required package!")
        print("Install with: pip install selenium")
        return

    # Load existing followers
    followers = load_followers(INPUT_FILE)
    if not followers:
        return

    print(f"\n[!]  IMPORTANT NOTES:")
    print(f"   • This will take ~{len(followers) * 6 / 3600:.1f} hours for {len(followers):,} followers")
    print(f"   • A Chrome browser window will open")
    print(f"   • Only PUBLIC profiles will work")
    print(f"   • Progress auto-saves every {BATCH_SIZE} profiles")
    print(f"   • You can stop (Ctrl+C) and resume anytime")
    print()

    # Auto-start for parallel execution (no user prompt needed)
    print("Starting fetch (parallel worker mode)...")

    # Fetch profile pictures
    updated_followers = fetch_all_profile_pictures(followers)

    # Save final results
    save_followers(updated_followers, OUTPUT_FILE)

    print("\n[OK] Profile picture URLs have been fetched!")
    print(f"[FILE] Output saved to: {OUTPUT_FILE}")
    print()
    print("Next steps:")
    print(f"1. Set DOWNLOAD_PROFILE_PICTURES = True in config.py")
    print(f"2. Set FOLLOWER_IMPORT_FILE = '{OUTPUT_FILE}' in config.py")
    print(f"3. Run your game - pictures will download from cached URLs")
    print()


if __name__ == "__main__":
    main()
