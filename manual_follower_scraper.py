"""
Manual Instagram Follower Scraper
Login with burner account, YOU manually scroll, script reads what's loaded
No automation limits - you control everything
"""

import time
import json
import pickle
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Configuration
TARGET_USERNAME = "followerbattlegrounds"  # Account to scrape followers from
BURNER_USERNAME = ""  # Your burner account (will be saved after first login)
COOKIE_FILE = "burner_instagram_cookies.pkl"


def setup_browser():
    """Setup Chrome browser"""
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
    """Save browser cookies"""
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
    """Load cookies from file"""
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
        print(f"[ERROR] Failed to load cookies: {e}")
        return False


def manual_login(driver):
    """Manual login with burner account"""
    print("\n" + "="*60)
    print("  MANUAL LOGIN WITH BURNER ACCOUNT")
    print("="*60)
    print()
    print("The Instagram login page will open in Chrome.")
    print()
    print("INSTRUCTIONS:")
    print("1. Login with your BURNER account credentials")
    print("2. Complete any 2FA if required")
    print("3. Click through any popups/notifications")
    print("4. Once you see the Instagram home feed, come back here")
    print()
    input("Press Enter to open Instagram login page...")

    driver.get("https://www.instagram.com/accounts/login/")
    time.sleep(3)

    print()
    print("=" * 60)
    print("WAITING FOR YOU TO LOGIN...")
    print("=" * 60)
    print()
    print("Please login in the Chrome window with your burner account.")
    print("After you login successfully and see your home feed,")
    print("come back here and press Enter.")
    print()

    input("Press Enter AFTER you have successfully logged in... ")

    # Save cookies
    print("[SAVING] Saving session cookies...")
    if save_cookies(driver):
        print("[OK] Session saved! Next time you won't need to login manually.")

    return True


def open_followers_dialog(driver, target_username):
    """Open the followers dialog"""
    print(f"\n[INFO] Opening profile: @{target_username}...")
    driver.get(f"https://www.instagram.com/{target_username}/")
    time.sleep(4)

    # Close any popups
    try:
        buttons = driver.find_elements(By.TAG_NAME, "button")
        for b in buttons:
            if any(t in b.text for t in ["Not Now", "Cancel", "Close"]):
                try:
                    b.click()
                    time.sleep(1)
                except:
                    pass
    except:
        pass

    print("[INFO] Opening Followers dialog...")

    # Click followers link
    followers_button = driver.find_element(By.PARTIAL_LINK_TEXT, "followers")

    for attempt in range(5):
        try:
            try:
                followers_button.click()
            except:
                driver.execute_script("arguments[0].click();", followers_button)
            time.sleep(2)
            break
        except Exception as e:
            print(f"[WARN] Click blocked (attempt {attempt+1}/5). Retrying...")
            time.sleep(1)

    print("[INFO] Waiting for followers dialog...")
    time.sleep(3)

    # Find the dialog
    dialogs = driver.find_elements(By.XPATH, "//div[@role='dialog']")
    if not dialogs:
        raise Exception("[ERROR] Followers dialog did not appear")

    dialog = dialogs[0]

    # Check for promotional popup and close it
    try:
        buttons_in_dialog = driver.find_elements(By.XPATH, "//div[@role='dialog']//div[@role='button']")
        if len(buttons_in_dialog) > 0:
            for btn in buttons_in_dialog[:3]:
                try:
                    inner_html = btn.get_attribute("innerHTML")
                    if "svg" in inner_html.lower() and "close" in inner_html.lower():
                        print("[INFO] Closing promotional popup...")
                        try:
                            btn.click()
                        except:
                            driver.execute_script("arguments[0].click();", btn)
                        time.sleep(2)

                        # Re-open followers dialog
                        print("[INFO] Re-opening followers dialog...")
                        followers_button = driver.find_element(By.PARTIAL_LINK_TEXT, "followers")
                        try:
                            followers_button.click()
                        except:
                            driver.execute_script("arguments[0].click();", followers_button)
                        time.sleep(3)

                        dialogs = driver.find_elements(By.XPATH, "//div[@role='dialog']")
                        if dialogs:
                            dialog = dialogs[0]
                        break
                except:
                    continue
    except:
        pass

    # Find scrollable panel
    print("[INFO] Locating scrollable followers list...")
    time.sleep(2)

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
        raise Exception("[ERROR] Could not locate scrollable followers panel")

    print("[OK] Followers scroll panel found!")
    return scroll_panel


def continuous_scrape(driver, scroll_panel):
    """
    Continuously scrape followers while user manually scrolls
    No automatic scrolling - user controls everything
    """
    print("\n" + "="*60)
    print("  MANUAL SCRAPING MODE")
    print("="*60)
    print()
    print("INSTRUCTIONS:")
    print("1. Go to the Chrome window with the Instagram follower popup")
    print("2. MANUALLY SCROLL DOWN the follower list at your own pace")
    print("3. The script will continuously read whatever is loaded")
    print("4. Scroll slowly to let Instagram load more followers")
    print("5. When you're satisfied (or can't scroll anymore):")
    print("   - Come back to this terminal")
    print("   - Press CTRL+C to stop scraping")
    print()
    print("=" * 60)
    print("SCRAPING STARTED - YOU CONTROL THE SCROLLING")
    print("=" * 60)
    print()
    print("Status updates every 5 seconds...")
    print("Press CTRL+C when done scraping")
    print()

    followers = {}
    last_count = 0
    last_update = time.time()

    try:
        while True:
            try:
                # Read current HTML
                html = scroll_panel.get_attribute("innerHTML")
                soup = BeautifulSoup(html, "html.parser")

                # Find all follower links
                items = soup.find_all("a", href=True)

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

                # Print status update every 5 seconds
                current_time = time.time()
                if current_time - last_update >= 5.0:
                    new_since_last = len(followers) - last_count
                    print(f"[SCRAPING] Total: {len(followers):,} followers "
                          f"(+{new_since_last} in last 5 sec) - Keep scrolling manually!")
                    last_count = len(followers)
                    last_update = current_time

                # Small delay to not hammer the browser
                time.sleep(0.5)

            except Exception as e:
                # Ignore errors and keep trying
                time.sleep(1)
                continue

    except KeyboardInterrupt:
        print("\n\n[STOPPED] Manual scraping stopped by user!")
        print(f"[FINAL] Scraped {len(followers):,} followers")
        return followers


def load_previous_followers(filename="followers_safe.json"):
    """Load previously scraped followers"""
    if Path(filename).exists():
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"[LOADED] {len(data)} previous followers from {filename}")
            return {item['username']: item for item in data}
    else:
        print(f"[INFO] No previous follower file found")
        return {}


def merge_and_save_followers(old_followers, new_followers):
    """Merge and save followers"""
    print("\n[MERGE] Merging follower data...")

    merged = old_followers.copy()
    new_count = 0

    for username, data in new_followers.items():
        if username not in merged:
            new_count += 1
        merged[username] = data

    print(f"[MERGE] Previous followers: {len(old_followers):,}")
    print(f"[MERGE] New unique followers: {new_count:,}")
    print(f"[MERGE] Total followers after merge: {len(merged):,}")

    # Save to file
    date_str = datetime.now().strftime("%Y%m%d")
    filename = f"followers_safe_{date_str}.json"

    follower_list = list(merged.values())

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(follower_list, f, indent=2, ensure_ascii=False)

    print(f"[SAVED] Saved to {filename}")
    print(f"\n[SUCCESS] Final follower count: {len(merged):,}")

    return merged


def main():
    """Main execution"""
    print("\n" + "="*60)
    print("  MANUAL INSTAGRAM FOLLOWER SCRAPER")
    print("  (YOU scroll, script reads)")
    print("="*60)
    print()

    driver = setup_browser()

    try:
        # Try to load existing session
        cookies_loaded = load_cookies(driver)

        if not cookies_loaded:
            # Need to login manually
            manual_login(driver)

        # Refresh Instagram to apply cookies
        print("[INFO] Loading Instagram with saved session...")
        driver.get("https://www.instagram.com/")
        time.sleep(3)

        # Open followers dialog
        scroll_panel = open_followers_dialog(driver, TARGET_USERNAME)

        # Load previous followers
        previous_followers = load_previous_followers()

        # Start manual scraping
        new_followers = continuous_scrape(driver, scroll_panel)

        if not new_followers:
            print("\n[ERROR] No followers scraped.")
            return

        # Merge and save
        merge_and_save_followers(previous_followers, new_followers)

    except KeyboardInterrupt:
        print("\n\n[STOPPED] Scraping interrupted by user.")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n[INFO] Closing browser in 5 seconds...")
        time.sleep(5)
        driver.quit()
        print("[OK] Browser closed.")


if __name__ == "__main__":
    main()
