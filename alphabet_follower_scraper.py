"""
Alphabet-Based Instagram Follower Scraper - HYBRID MODE
Uses search feature to bypass scroll limits.

HYBRID APPROACH:
1. First pass: Search all 2-character patterns (aa, ab, ac, ... zz)
2. Track which patterns return LOTS of followers (high-density)
3. Second pass: For high-density patterns, search 3-character variations
4. This gets maximum coverage in minimum time!
"""

import time
import json
import pickle
import random
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Account to scrape followers FROM
TARGET_USERNAME = "followerbattlegrounds"

# Your burner account username (for login verification only)
BURNER_USERNAME = "stinsonoscar22025"

COOKIE_FILE = "instagram_cookies_burner3.pkl"

# HYBRID MODE CONFIGURATION
# If a 2-char pattern returns this many followers, we'll do 3-char deep dive
HIGH_DENSITY_THRESHOLD = 25  # Adjust this based on results

# Search mode
USE_HYBRID_MODE = True  # True = 2-char + selective 3-char, False = just 2-char


def setup_browser():
    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36"
    )

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver


def save_cookies(driver, filepath=COOKIE_FILE):
    try:
        cookies = driver.get_cookies()
        with open(filepath, 'wb') as f:
            pickle.dump(cookies, f)
        print(f"[SAVED] Cookies saved to {filepath}")
        return True
    except Exception as e:
        print(f"[WARN] Failed to save cookies: {e}")
        return False


def load_cookies(driver, filepath=COOKIE_FILE):
    if not Path(filepath).exists():
        print(f"[INFO] No saved cookies found at {filepath}")
        return False

    try:
        with open(filepath, 'rb') as f:
            cookies = pickle.load(f)

        driver.get("https://www.instagram.com/")
        time.sleep(2)

        for cookie in cookies:
            try:
                if 'expiry' in cookie:
                    cookie['expiry'] = int(cookie['expiry'])
                driver.add_cookie(cookie)
            except:
                pass

        print(f"[OK] Cookies loaded from {filepath}")
        return True
    except Exception as e:
        print(f"[WARN] Failed to load cookies: {e}")
        return False


def verify_login(driver):
    try:
        driver.get("https://www.instagram.com/")
        time.sleep(3)

        login_buttons = driver.find_elements(By.XPATH, "//a[@href='/accounts/login/']")
        if login_buttons:
            print("[WARN] Session expired - login required")
            return False

        nav_links = driver.find_elements(By.XPATH, "//nav//a[contains(@href, '/')]")

        if BURNER_USERNAME:
            profile_links = driver.find_elements(By.XPATH, f"//a[contains(@href, '/{BURNER_USERNAME}/')]")
            if profile_links:
                print(f"[OK] Session is valid - logged in as {BURNER_USERNAME}!")
                return True
        elif nav_links:
            print("[OK] Session is valid - already logged in!")
            return True

        print("[WARN] Could not verify session - will attempt login")
        return False

    except Exception as e:
        print(f"[WARN] Error verifying login: {e}")
        return False


def login(driver):
    print("[LOGIN] Attempting to login to Instagram...")

    if load_cookies(driver):
        if verify_login(driver):
            print("[OK] Logged in successfully using saved session!")
            return True

    print("[LOGIN] Saved session unavailable - manual login required")
    print("        (You only need to do this once - cookies will be saved)")

    driver.get("https://www.instagram.com/accounts/login/")
    print("[LOGIN] Waiting for Instagram login page...")
    time.sleep(4)

    try:
        buttons = driver.find_elements(By.TAG_NAME, "button")
        for b in buttons:
            if "Allow" in b.text or "Accept" in b.text:
                b.click()
                print("[INFO] Cookie popup dismissed")
                time.sleep(2)
                break
    except:
        pass

    try:
        continue_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Continue as')]")
        print("[INFO] Instagram shows a 'Continue as' button. Click it manually.")
        input("Press Enter AFTER you clicked it in the browser... ")
        save_cookies(driver)
        return True
    except:
        pass

    try:
        username_field = driver.find_element(By.NAME, "username")
        password_field = driver.find_element(By.NAME, "password")
        print("[INFO] Enter your BURNER ACCOUNT username and password manually.")
        print("[WARN] Do NOT hit Enter. Click the Login button manually.")
    except:
        print("[WARN] Could not detect login fields.")
        print("[INFO] Please complete login manually in the browser window.")
        print("[INFO] Use your BURNER ACCOUNT credentials.")

    input("Press Enter AFTER you have successfully logged in... ")

    print("[SAVING] Saving session cookies for future use...")
    if save_cookies(driver):
        print("[OK] Session saved! Next time you won't need to login manually.")
    else:
        print("[WARN] Failed to save cookies - you may need to login again next time.")

    return True


def scrape_followers_with_search(driver, search_pattern):
    """
    Scrape followers using search pattern
    Returns dict of {username: follower_data}
    """
    followers = {}

    print(f"\n[SEARCH] Searching for: '{search_pattern}'")

    # Find search input in the followers dialog
    try:
        search_input = driver.find_element(By.XPATH, "//input[@placeholder='Search']")

        # Clear existing search
        search_input.clear()
        time.sleep(0.5)

        # Type search pattern
        search_input.send_keys(search_pattern)
        time.sleep(2)  # Wait for results to load

    except Exception as e:
        print(f"[WARN] Could not find search input: {e}")
        return followers

    # Find the results container (scrollable area with search results)
    try:
        dialogs = driver.find_elements(By.XPATH, "//div[@role='dialog']")
        if not dialogs:
            print("[WARN] No dialog found")
            return followers

        dialog = dialogs[0]

        # Find scrollable container
        scroll_candidates = dialog.find_elements(By.XPATH, ".//*")
        scroll_panel = None
        max_height = 0

        for el in scroll_candidates:
            try:
                height = driver.execute_script("return arguments[0].scrollHeight;", el)
                visible = driver.execute_script("return arguments[0].clientHeight;", el)
                if height > visible and visible > 0:
                    if height > max_height:
                        max_height = height
                        scroll_panel = el
            except:
                continue

        if scroll_panel is None:
            print("[WARN] Could not find scroll panel for search results")
            return followers

    except Exception as e:
        print(f"[WARN] Error finding scroll panel: {e}")
        return followers

    # Scroll through search results
    retries = 0
    while retries < 15:  # Fewer retries per search since results are smaller
        try:
            # Randomized human-like scrolling
            scroll_distance = random.randint(300, 500)
            driver.execute_script("""
                var element = arguments[0];
                element.scrollBy({top: arguments[1], behavior: 'smooth'});
            """, scroll_panel, scroll_distance)

            delay = random.uniform(1.5, 3.0)  # Faster for search results
            time.sleep(delay)

            # Parse current results
            html = scroll_panel.get_attribute("innerHTML")
            soup = BeautifulSoup(html, "html.parser")

            items = soup.find_all("a", href=True)
            added = 0

            for a in items:
                href = a["href"]
                if href.startswith("/") and href.count("/") == 2:
                    username = href.replace("/", "")
                    if username not in followers:
                        parent = a.find_parent("div").find_parent("div")
                        img = parent.find("img")
                        avatar = img["src"] if (img and "src" in img.attrs) else ""

                        followers[username] = {
                            "username": username,
                            "profile_url": f"https://instagram.com/{username}",
                            "profile_pic_url": avatar,
                        }
                        added += 1

            if added == 0:
                retries += 1
            else:
                retries = 0

        except Exception as e:
            print(f"[WARN] Error during scroll: {e}")
            retries += 1

    print(f"[RESULT] Found {len(followers)} followers for '{search_pattern}'")
    return followers


def scrape_all_followers_alphabetically(driver):
    """
    Main scraping function using HYBRID alphabet search

    HYBRID MODE:
    - Pass 1: Search all 2-char patterns (aa-zz)
    - Track which patterns have high density (lots of followers)
    - Pass 2: For high-density patterns, do 3-char deep dive
    """
    print(f"[INFO] Opening profile page for {TARGET_USERNAME}...")
    driver.get(f"https://www.instagram.com/{TARGET_USERNAME}/")
    time.sleep(4)

    # Close popups
    try:
        buttons = driver.find_elements(By.TAG_NAME, "button")
        for b in buttons:
            if any(t in b.text for t in ["Not Now", "Cancel", "Close", "OK"]):
                try:
                    b.click()
                    time.sleep(1)
                except:
                    pass
    except:
        pass

    # Click followers button
    print("[INFO] Opening Followers dialog...")
    followers_button = driver.find_element(By.PARTIAL_LINK_TEXT, "followers")

    for attempt in range(12):
        try:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", followers_button)
            time.sleep(0.5)

            try:
                followers_button.click()
            except:
                driver.execute_script("arguments[0].click();", followers_button)

            time.sleep(3)
            break
        except Exception as e:
            print(f"[WARN] Followers button blocked (attempt {attempt+1}/12). Retrying...")
            time.sleep(1)
            if attempt == 11:
                raise

    print("[INFO] Followers dialog opened!")
    time.sleep(2)

    # PASS 1: 2-Character search
    all_followers = {}
    pattern_density = {}  # Track how many followers each pattern returns

    two_char_patterns = [
        f"{a}{b}" for a in 'abcdefghijklmnopqrstuvwxyz'
        for b in 'abcdefghijklmnopqrstuvwxyz'
    ]

    print(f"\n{'='*70}")
    print(f"PASS 1: 2-CHARACTER SEARCH")
    print(f"Searching {len(two_char_patterns)} patterns (aa-zz)")
    print(f"{'='*70}\n")

    for i, pattern in enumerate(two_char_patterns, start=1):
        print(f"\n[PROGRESS] Pattern {i}/{len(two_char_patterns)}: '{pattern}'")

        pattern_followers = scrape_followers_with_search(driver, pattern)

        # Track density
        pattern_density[pattern] = len(pattern_followers)

        # Merge into all_followers
        new_count = 0
        for username, data in pattern_followers.items():
            if username not in all_followers:
                all_followers[username] = data
                new_count += 1

        print(f"[STATS] Found {len(pattern_followers)} total | {new_count} new unique")
        print(f"[STATS] Total unique followers so far: {len(all_followers)}")

        # Small break between searches
        if i < len(two_char_patterns):
            pause = random.uniform(2, 4)
            print(f"[PAUSE] Waiting {pause:.1f}s before next search...")
            time.sleep(pause)

    print(f"\n{'='*70}")
    print(f"PASS 1 COMPLETE!")
    print(f"Total unique followers from 2-char search: {len(all_followers)}")
    print(f"{'='*70}\n")

    # PASS 2: 3-Character deep dive for high-density patterns
    if USE_HYBRID_MODE:
        high_density_patterns = [
            p for p, count in pattern_density.items()
            if count >= HIGH_DENSITY_THRESHOLD
        ]

        if high_density_patterns:
            print(f"\n{'='*70}")
            print(f"PASS 2: 3-CHARACTER DEEP DIVE")
            print(f"Found {len(high_density_patterns)} high-density patterns (≥{HIGH_DENSITY_THRESHOLD} followers)")
            print(f"Patterns: {', '.join(high_density_patterns[:10])}{'...' if len(high_density_patterns) > 10 else ''}")
            print(f"{'='*70}\n")

            # Generate 3-char patterns for high-density ones
            three_char_patterns = []
            for base_pattern in high_density_patterns:
                for c in 'abcdefghijklmnopqrstuvwxyz':
                    three_char_patterns.append(f"{base_pattern}{c}")

            print(f"[INFO] Will search {len(three_char_patterns)} 3-character patterns")
            print(f"[INFO] Estimated time: {len(three_char_patterns) * 3.5 / 60:.0f} minutes\n")

            pass2_start_count = len(all_followers)

            for i, pattern in enumerate(three_char_patterns, start=1):
                print(f"\n[PROGRESS] 3-Char {i}/{len(three_char_patterns)}: '{pattern}'")

                pattern_followers = scrape_followers_with_search(driver, pattern)

                # Merge into all_followers
                new_count = 0
                for username, data in pattern_followers.items():
                    if username not in all_followers:
                        all_followers[username] = data
                        new_count += 1

                print(f"[STATS] Found {len(pattern_followers)} total | {new_count} new unique")
                print(f"[STATS] Total unique followers: {len(all_followers)}")

                # Small break between searches
                if i < len(three_char_patterns):
                    pause = random.uniform(2, 4)
                    print(f"[PAUSE] Waiting {pause:.1f}s...")
                    time.sleep(pause)

            pass2_added = len(all_followers) - pass2_start_count
            print(f"\n{'='*70}")
            print(f"PASS 2 COMPLETE!")
            print(f"New unique followers from 3-char deep dive: {pass2_added}")
            print(f"{'='*70}\n")
        else:
            print(f"\n[INFO] No high-density patterns found (none had ≥{HIGH_DENSITY_THRESHOLD} followers)")
            print(f"[INFO] Skipping Pass 2\n")

    print(f"\n{'='*70}")
    print(f"HYBRID SCRAPING COMPLETE!")
    print(f"Final unique follower count: {len(all_followers)}")
    print(f"{'='*70}\n")

    return list(all_followers.values())


def load_previous_followers():
    """Load all previous follower files and merge them (from any scraper)"""
    import glob

    # Load from BOTH alphabet scraper AND safe scraper files
    alphabet_files = glob.glob("followers_alphabet_*.json")
    safe_files = glob.glob("followers_safe_*.json")
    all_files = alphabet_files + safe_files

    if not all_files:
        print("[INFO] No previous follower files found")
        return {}

    print(f"[INFO] Found {len(all_files)} previous follower file(s)")
    if alphabet_files:
        print(f"       - {len(alphabet_files)} from alphabet scraper")
    if safe_files:
        print(f"       - {len(safe_files)} from safe scraper")

    all_previous = {}
    for file in all_files:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for follower in data:
                    username = follower.get('username')
                    if username and username not in all_previous:
                        all_previous[username] = follower
        except Exception as e:
            print(f"[WARN] Could not load {file}: {e}")

    print(f"[INFO] Loaded {len(all_previous)} unique followers from all previous files")
    return all_previous


def save_file(data):
    filename = f"followers_alphabet_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"[SAVED] Saved to {filename}")


def main():
    driver = setup_browser()

    try:
        login(driver)

        # Load previous followers
        previous_followers = load_previous_followers()

        # Scrape using alphabet search
        new_followers = scrape_all_followers_alphabetically(driver)
        print(f"[SCRAPED] Scraped {len(new_followers)} followers this session")

        # Merge with previous
        merged = previous_followers.copy()
        new_count = 0

        for follower in new_followers:
            username = follower.get('username')
            if username and username not in merged:
                merged[username] = follower
                new_count += 1
            elif username:
                merged[username] = follower

        merged_list = list(merged.values())

        print(f"\n{'='*60}")
        print("FINAL RESULTS")
        print(f"{'='*60}")
        print(f"Previous followers: {len(previous_followers)}")
        print(f"New unique followers: {new_count}")
        print(f"Total followers after merge: {len(merged_list)}")
        print(f"{'='*60}\n")

        # Save
        save_file(merged_list)

        print(f"\n[SUCCESS] Final follower count: {len(merged_list)}")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        input("\nPress Enter to close browser...")
        driver.quit()


if __name__ == "__main__":
    main()
