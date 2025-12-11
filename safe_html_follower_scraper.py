import time
import json
import pickle
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

USERNAME = "followerbattlegrounds"
COOKIE_FILE = "instagram_session_cookies.pkl"


# -----------------------------
# Browser setup
# -----------------------------
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


# -----------------------------
# Cookie management
# -----------------------------
def save_cookies(driver, filepath=COOKIE_FILE):
    """Save browser cookies to file for session persistence"""
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
    """Load cookies from file and add them to the browser"""
    if not Path(filepath).exists():
        print(f"[INFO] No saved cookies found at {filepath}")
        return False

    try:
        with open(filepath, 'rb') as f:
            cookies = pickle.load(f)

        # Go to Instagram first (cookies need a domain)
        driver.get("https://www.instagram.com/")
        time.sleep(2)

        # Add each cookie
        for cookie in cookies:
            try:
                # Remove 'expiry' if it exists and is not a valid timestamp
                if 'expiry' in cookie:
                    # Selenium expects expiry as an integer, not float
                    cookie['expiry'] = int(cookie['expiry'])
                driver.add_cookie(cookie)
            except Exception as e:
                # Skip problematic cookies
                pass

        print(f"[OK] Cookies loaded from {filepath}")
        return True
    except Exception as e:
        print(f"[WARN] Failed to load cookies: {e}")
        return False


def verify_login(driver):
    """Check if we're logged in by looking for profile button"""
    try:
        # Refresh to apply cookies
        driver.get("https://www.instagram.com/")
        time.sleep(3)

        # Look for profile link or other logged-in indicators
        # Instagram shows profile icon in top right when logged in
        profile_links = driver.find_elements(By.XPATH, f"//a[contains(@href, '/{USERNAME}/')]")
        if profile_links:
            print("[OK] Session is valid - already logged in!")
            return True

        # Alternative check: look for login button (means NOT logged in)
        login_buttons = driver.find_elements(By.XPATH, "//a[@href='/accounts/login/']")
        if login_buttons:
            print("[WARN] Session expired - login required")
            return False

        # If we don't see clear indicators, assume we need to login
        print("[WARN] Could not verify session - will attempt login")
        return False

    except Exception as e:
        print(f"[WARN] Error verifying login: {e}")
        return False


# -----------------------------
# Robust Instagram login with cookie persistence
# -----------------------------
def login(driver):
    """
    Login to Instagram using saved cookies if available,
    otherwise perform manual login and save cookies for future use
    """
    print("[LOGIN] Attempting to login to Instagram...")

    # Try to load existing cookies first
    if load_cookies(driver):
        # Verify the session is still valid
        if verify_login(driver):
            print("[OK] Logged in successfully using saved session!")
            return True

    # If cookies didn't work, do manual login
    print("[LOGIN] Saved session unavailable - manual login required")
    print("        (You only need to do this once - cookies will be saved)")

    driver.get("https://www.instagram.com/accounts/login/")
    print("[LOGIN] Waiting for Instagram login page...")
    time.sleep(4)

    # Close cookie popup if needed
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

    # Case 1: "Continue as <username>"
    try:
        continue_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Continue as')]")
        print("[INFO] Instagram shows a 'Continue as' button. Click it manually.")
        input("Press Enter AFTER you clicked it in the browser... ")
        # Save cookies after successful login
        save_cookies(driver)
        return True
    except:
        pass

    # Case 2: username/password fields
    try:
        username_field = driver.find_element(By.NAME, "username")
        password_field = driver.find_element(By.NAME, "password")
        print("[INFO] Enter your username and password manually.")
        print("[WARN] Do NOT hit Enter. Click the Login button manually.")
    except:
        print("[WARN] Could not detect login fields.")
        print("[INFO] Please complete login manually in the browser window.")

    input("Press Enter AFTER you have successfully logged in... ")

    # Save cookies after successful manual login
    print("[SAVING] Saving session cookies for future use...")
    if save_cookies(driver):
        print("[OK] Session saved! Next time you won't need to login manually.")
    else:
        print("[WARN] Failed to save cookies - you may need to login again next time.")

    return True


# -----------------------------
# Scrape followers through scrolling
# -----------------------------
def scrape_followers(driver):
    print("[INFO] Opening profile page...")
    driver.get(f"https://www.instagram.com/{USERNAME}/")
    time.sleep(4)

    # ---------- CLOSE POPUPS ----------
    def close_popups():
        try:
            buttons = driver.find_elements(By.TAG_NAME, "button")
            for b in buttons:
                if any(t in b.text for t in ["Not Now", "Cancel", "Close", "OK", "Allow", "Dismiss"]):
                    try:
                        print(f"[INFO] Closing popup: {b.text}")
                        b.click()
                        time.sleep(1)
                    except:
                        pass
        except:
            pass

    close_popups()

    # ---------- CLICK FOLLOWERS BUTTON ----------
    print("[INFO] Opening Followers dialog...")

    followers_button = driver.find_element(By.PARTIAL_LINK_TEXT, "followers")

    # Retry click until successful (with JavaScript fallback)
    for attempt in range(12):
        try:
            close_popups()

            # Try scrolling element into view first
            try:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", followers_button)
                time.sleep(0.5)
            except:
                pass

            # Try regular click first
            try:
                followers_button.click()
            except:
                # If intercepted, use JavaScript click as fallback
                print(f"[INFO] Regular click blocked, trying JavaScript click...")
                driver.execute_script("arguments[0].click();", followers_button)

            time.sleep(2)
            break
        except Exception as e:
            print(f"[WARN] Followers button blocked (attempt {attempt+1}/12). Retrying...")
            time.sleep(1)
            if attempt == 11:
                raise

    # ---------- WAIT FOR DIALOG ----------
    print("[INFO] Waiting for followers dialog to appear...")
    time.sleep(3)

    dialogs = driver.find_elements(By.XPATH, "//div[@role='dialog']")
    if not dialogs:
        raise Exception("[ERROR] Followers dialog did not appear at all")

    dialog = dialogs[0]

    # ---------- CHECK FOR AND CLOSE PROMOTIONAL POPUP ----------
    print("[DEBUG] Checking for promotional popup...")
    time.sleep(2)

    try:
        # Find all buttons in the dialog
        buttons_in_dialog = driver.find_elements(By.XPATH, "//div[@role='dialog']//div[@role='button']")
        print(f"[DEBUG] Found {len(buttons_in_dialog)} buttons in dialog")

        # Check if first button is a close button (contains SVG with "close")
        if len(buttons_in_dialog) > 0:
            for idx, btn in enumerate(buttons_in_dialog[:3]):
                try:
                    inner_html = btn.get_attribute("innerHTML")
                    has_svg = "svg" in inner_html.lower()
                    has_close = "close" in inner_html.lower()

                    if has_svg and has_close:
                        print(f"[INFO] Found promotional popup close button, clicking to dismiss...")
                        try:
                            btn.click()
                        except:
                            driver.execute_script("arguments[0].click();", btn)

                        time.sleep(2)
                        print("[OK] Closed promotional popup")

                        # After closing promo, the dialog closes too!
                        # We need to re-open the followers dialog
                        print("[INFO] Re-opening followers dialog...")

                        # Re-find and click followers button
                        followers_button = driver.find_element(By.PARTIAL_LINK_TEXT, "followers")
                        try:
                            followers_button.click()
                        except:
                            driver.execute_script("arguments[0].click();", followers_button)

                        time.sleep(3)
                        print("[OK] Followers dialog re-opened")

                        # Re-find the dialog
                        dialogs = driver.find_elements(By.XPATH, "//div[@role='dialog']")
                        if dialogs:
                            dialog = dialogs[0]

                        break
                except:
                    continue

    except Exception as e:
        print(f"[DEBUG] No promo popup or couldn't handle it: {e}")

    # ---------- FIND TRUE SCROLLABLE ELEMENT ----------
    print("[INFO] Locating scrollable followers list container...")
    time.sleep(2)

    scroll_candidates = dialog.find_elements(By.XPATH, ".//*")

    scroll_panel = None
    max_height = 0

    for el in scroll_candidates:
        try:
            height = driver.execute_script("return arguments[0].scrollHeight;", el)
            visible = driver.execute_script("return arguments[0].clientHeight;", el)

            # A scrollable list has scrollHeight > clientHeight
            if height > visible and visible > 0:
                if height > max_height:
                    max_height = height
                    scroll_panel = el
        except:
            continue

    if scroll_panel is None:
        raise Exception("[ERROR] Could not locate scrollable followers panel")

    print("[OK] Followers scroll panel found!")

    # ---------- START SCROLLING ----------
    print("[SCROLL] Scrolling follower list safely...")

    followers = {}
    retries = 0
    stale_retries = 0

    def refind_scroll_panel():
        """Re-find the scroll panel if it becomes stale"""
        dialogs = driver.find_elements(By.XPATH, "//div[@role='dialog']")
        if not dialogs:
            return None

        dialog = dialogs[0]
        scroll_candidates = dialog.find_elements(By.XPATH, ".//*")

        panel = None
        max_h = 0

        for el in scroll_candidates:
            try:
                h = driver.execute_script("return arguments[0].scrollHeight;", el)
                v = driver.execute_script("return arguments[0].clientHeight;", el)
                if h > v and v > 0 and h > max_h:
                    max_h = h
                    panel = el
            except:
                continue

        return panel

    while True:
        try:
            # Get current scroll position and height for debugging
            scroll_top = driver.execute_script("return arguments[0].scrollTop;", scroll_panel)
            scroll_height = driver.execute_script("return arguments[0].scrollHeight;", scroll_panel)
            client_height = driver.execute_script("return arguments[0].clientHeight;", scroll_panel)

            # Scroll by JavaScript - use smooth incremental scroll to trigger lazy loading
            # Instead of jumping to the bottom, scroll incrementally
            driver.execute_script("""
                var element = arguments[0];
                element.scrollBy({top: 1000, behavior: 'smooth'});
            """, scroll_panel)
            time.sleep(2)  # Increased wait time for Instagram to load more content

            # Check if scroll position changed
            new_scroll_top = driver.execute_script("return arguments[0].scrollTop;", scroll_panel)

            # Debug output every 10 iterations
            if len(followers) % 120 == 0 or retries > 0:
                print(f"[DEBUG] Scroll: top={new_scroll_top}, height={scroll_height}, client={client_height}")

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
                print(f"[WAIT] No new followers loaded (retry {retries}/25)...")
                if retries > 25:
                    print("[INFO] End of follower list reached.")
                    break
            else:
                retries = 0  # Reset retries on success
                stale_retries = 0  # Reset stale retries on success

            print(f"[STATS] Total collected: {len(followers)}")

        except Exception as e:
            # Handle stale element reference
            if "stale element" in str(e).lower():
                stale_retries += 1
                print(f"[WARN] Scroll panel became stale, re-finding... (attempt {stale_retries}/5)")

                if stale_retries > 5:
                    print("[ERROR] Too many stale element errors, stopping.")
                    break

                # Re-find the scroll panel
                scroll_panel = refind_scroll_panel()
                if scroll_panel is None:
                    print("[ERROR] Could not re-find scroll panel")
                    break

                print("[OK] Scroll panel re-found, continuing...")
                time.sleep(2)
                continue
            else:
                # Other error, re-raise
                raise

    return list(followers.values())




# -----------------------------
# Load previous followers
# -----------------------------
def load_previous_followers():
    """Load all previous follower files and merge them"""
    import glob

    # Find all previous follower files
    files = glob.glob("followers_safe_*.json")

    if not files:
        print("[INFO] No previous follower files found")
        return {}

    print(f"[INFO] Found {len(files)} previous follower file(s)")

    # Merge all previous followers
    all_previous = {}
    for file in files:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for follower in data:
                    username = follower.get('username')
                    if username and username not in all_previous:
                        all_previous[username] = follower
        except Exception as e:
            print(f"[WARN] Could not load {file}: {e}")

    print(f"[INFO] Loaded {len(all_previous)} unique followers from previous files")
    return all_previous


# -----------------------------
# Save output to JSON
# -----------------------------
def save_file(data):
    filename = f"followers_safe_{datetime.now().strftime('%Y%m%d')}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"[SAVED] Saved to {filename}")


# -----------------------------
# Main
# -----------------------------
def main():
    driver = setup_browser()
    login(driver)

    # Load previous followers first
    previous_followers = load_previous_followers()

    # Scrape new followers
    new_followers = scrape_followers(driver)
    print(f"[SCRAPED] Scraped {len(new_followers)} followers this session")

    # Merge with previous followers
    merged = previous_followers.copy()
    new_count = 0

    for follower in new_followers:
        username = follower.get('username')
        if username and username not in merged:
            merged[username] = follower
            new_count += 1
        elif username:
            # Update existing follower info (in case profile pic changed, etc.)
            merged[username] = follower

    # Convert dict back to list
    merged_list = list(merged.values())

    print(f"[MERGE] Previous followers: {len(previous_followers)}")
    print(f"[MERGE] New unique followers: {new_count}")
    print(f"[MERGE] Total followers after merge: {len(merged_list)}")

    # Save merged list
    save_file(merged_list)

    print(f"\n[SUCCESS] Final follower count: {len(merged_list)}")

    driver.quit()


if __name__ == "__main__":
    main()
