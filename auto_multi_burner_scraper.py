"""
Automated Multi-Burner Instagram Scraper
Automatically rotates through all available burner accounts
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
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Import burner config
from multi_burner_config import (
    TARGET_USERNAME,
    BURNER_ACCOUNTS,
    SEARCH_PATTERNS,
    SCRAPING_SETTINGS,
    get_active_burners,
    print_burner_status
)


class MultiBurnerScraper:
    def __init__(self):
        self.driver = None
        self.current_burner = None
        self.all_followers = {}

    def setup_browser(self):
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
        self.driver = webdriver.Chrome(service=service, options=options)

    def save_cookies(self, cookie_file):
        """Save browser cookies"""
        try:
            cookies = self.driver.get_cookies()
            with open(cookie_file, 'wb') as f:
                pickle.dump(cookies, f)
            print(f"[SAVED] Cookies saved to {cookie_file}")
            return True
        except Exception as e:
            print(f"[WARN] Failed to save cookies: {e}")
            return False

    def load_cookies(self, cookie_file):
        """Load cookies from file"""
        if not Path(cookie_file).exists():
            print(f"[INFO] No saved cookies found at {cookie_file}")
            return False

        try:
            with open(cookie_file, 'rb') as f:
                cookies = pickle.load(f)

            self.driver.get("https://www.instagram.com/")
            time.sleep(2)

            for cookie in cookies:
                try:
                    if 'expiry' in cookie:
                        cookie['expiry'] = int(cookie['expiry'])
                    self.driver.add_cookie(cookie)
                except:
                    pass

            print(f"[OK] Cookies loaded from {cookie_file}")
            return True
        except Exception as e:
            print(f"[WARN] Failed to load cookies: {e}")
            return False

    def verify_login(self, username):
        """Check if logged in"""
        try:
            self.driver.get("https://www.instagram.com/")
            time.sleep(3)

            login_buttons = self.driver.find_elements(By.XPATH, "//a[@href='/accounts/login/']")
            if login_buttons:
                return False

            if username:
                profile_links = self.driver.find_elements(By.XPATH, f"//a[contains(@href, '/{username}/')]")
                if profile_links:
                    print(f"[OK] Logged in as {username}!")
                    return True

            return False
        except Exception as e:
            print(f"[WARN] Error verifying login: {e}")
            return False

    def login(self, burner):
        """Login with burner account"""
        print(f"\n[LOGIN] Logging in as {burner['username']}...")

        if self.load_cookies(burner['cookie_file']):
            if self.verify_login(burner['username']):
                return True

        print("[LOGIN] Manual login required")
        self.driver.get("https://www.instagram.com/accounts/login/")
        time.sleep(4)

        # Close popups
        try:
            buttons = self.driver.find_elements(By.TAG_NAME, "button")
            for b in buttons:
                if "Allow" in b.text or "Accept" in b.text:
                    b.click()
                    time.sleep(2)
                    break
        except:
            pass

        print(f"\n{'='*60}")
        print(f"LOGIN REQUIRED FOR: {burner['username']}")
        print(f"{'='*60}")
        print("Please login manually in the browser window.")
        print("Use these credentials:")
        print(f"  Username: {burner['username']}")
        print(f"  Password: [check your burner_accounts.txt file]")
        print("\nDo NOT press Enter in the terminal - click Login in browser!")
        print(f"{'='*60}\n")

        input("Press Enter AFTER you are logged in... ")

        self.save_cookies(burner['cookie_file'])
        return True

    def open_followers_dialog(self):
        """Open followers dialog for target account"""
        print(f"\n[INFO] Opening {TARGET_USERNAME} profile...")
        self.driver.get(f"https://www.instagram.com/{TARGET_USERNAME}/")
        time.sleep(4)

        # Close popups
        try:
            buttons = self.driver.find_elements(By.TAG_NAME, "button")
            for b in buttons:
                if any(t in b.text for t in ["Not Now", "Cancel", "Close"]):
                    try:
                        b.click()
                        time.sleep(1)
                    except:
                        pass
        except:
            pass

        # Click followers
        print("[INFO] Opening Followers dialog...")
        followers_button = self.driver.find_element(By.PARTIAL_LINK_TEXT, "followers")

        for attempt in range(12):
            try:
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", followers_button)
                time.sleep(0.5)
                try:
                    followers_button.click()
                except:
                    self.driver.execute_script("arguments[0].click();", followers_button)
                time.sleep(3)
                break
            except:
                time.sleep(1)
                if attempt == 11:
                    raise Exception("Could not open followers dialog")

        time.sleep(2)
        print("[OK] Followers dialog opened!")

    def scrape_search_pattern(self, pattern):
        """Scrape followers for a single search pattern"""
        followers = {}

        print(f"[SEARCH] Searching for: '{pattern}'")

        try:
            # Find search input
            search_input = self.driver.find_element(By.XPATH, "//input[@placeholder='Search']")
            search_input.clear()
            time.sleep(0.5)
            search_input.send_keys(pattern)
            time.sleep(2)
        except Exception as e:
            print(f"[WARN] Could not search: {e}")
            return followers

        # Find scroll panel
        try:
            dialogs = self.driver.find_elements(By.XPATH, "//div[@role='dialog']")
            if not dialogs:
                return followers

            dialog = dialogs[0]
            scroll_candidates = dialog.find_elements(By.XPATH, ".//*")
            scroll_panel = None
            max_height = 0

            for el in scroll_candidates:
                try:
                    height = self.driver.execute_script("return arguments[0].scrollHeight;", el)
                    visible = self.driver.execute_script("return arguments[0].clientHeight;", el)
                    if height > visible and visible > 0 and height > max_height:
                        max_height = height
                        scroll_panel = el
                except:
                    continue

            if not scroll_panel:
                return followers

        except:
            return followers

        # Scroll through results
        retries = 0
        while retries < 15:
            try:
                scroll_distance = random.randint(300, 500)
                self.driver.execute_script("""
                    var element = arguments[0];
                    element.scrollBy({top: arguments[1], behavior: 'smooth'});
                """, scroll_panel, scroll_distance)

                delay = random.uniform(1.5, 3.0)
                time.sleep(delay)

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

            except:
                retries += 1

        print(f"[RESULT] Found {len(followers)} followers for '{pattern}'")
        return followers

    def scrape_with_burner(self, burner, patterns_to_scrape):
        """Scrape using a single burner account"""
        print(f"\n{'='*60}")
        print(f"SCRAPING WITH: {burner['username']}")
        print(f"Patterns to scrape: {len(patterns_to_scrape)}")
        print(f"{'='*60}\n")

        # Login
        if not self.login(burner):
            print(f"[ERROR] Failed to login with {burner['username']}")
            return 0

        # Open followers dialog
        try:
            self.open_followers_dialog()
        except Exception as e:
            print(f"[ERROR] Failed to open followers dialog: {e}")
            return 0

        # Scrape each pattern
        new_followers_count = 0

        for i, pattern in enumerate(patterns_to_scrape, start=1):
            print(f"\n[PROGRESS] Pattern {i}/{len(patterns_to_scrape)} for {burner['username']}")

            pattern_followers = self.scrape_search_pattern(pattern)

            # Merge
            new_count = 0
            for username, data in pattern_followers.items():
                if username not in self.all_followers:
                    self.all_followers[username] = data
                    new_count += 1
                    new_followers_count += 1

            print(f"[STATS] New unique from this search: {new_count}")
            print(f"[STATS] Total unique followers: {len(self.all_followers)}")

            # Pause between searches
            if i < len(patterns_to_scrape):
                pause = random.uniform(2, 4)
                time.sleep(pause)

        print(f"\n[DONE] {burner['username']} scraped {new_followers_count} new unique followers")
        return new_followers_count

    def load_previous_followers(self):
        """Load all previous follower files"""
        import glob

        alphabet_files = glob.glob("followers_alphabet_*.json")
        safe_files = glob.glob("followers_safe_*.json")
        all_files = alphabet_files + safe_files

        if not all_files:
            print("[INFO] No previous follower files found")
            return

        print(f"[INFO] Loading {len(all_files)} previous file(s)...")

        for file in all_files:
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for follower in data:
                        username = follower.get('username')
                        if username and username not in self.all_followers:
                            self.all_followers[username] = follower
            except:
                pass

        print(f"[OK] Loaded {len(self.all_followers)} unique followers from previous files")

    def save_results(self):
        """Save final results"""
        filename = f"followers_multi_burner_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        followers_list = list(self.all_followers.values())

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(followers_list, f, indent=2)

        print(f"\n[SAVED] {filename}")
        print(f"[SUCCESS] Total followers: {len(followers_list)}")

    def run(self):
        """Main scraping orchestration"""
        print("\n" + "="*60)
        print("AUTOMATED MULTI-BURNER SCRAPER")
        print("="*60 + "\n")

        # Show burner status
        print_burner_status()

        # Get active burners
        active_burners = get_active_burners()

        if not active_burners:
            print("❌ No active burners available!")
            print("Edit multi_burner_config.py and set status to 'READY'")
            return

        print(f"✅ Found {len(active_burners)} active burner(s)\n")

        # Load previous followers
        self.load_previous_followers()
        starting_count = len(self.all_followers)

        # Setup browser
        self.setup_browser()

        try:
            # Divide patterns among burners
            patterns_per_burner = SCRAPING_SETTINGS['patterns_per_burner']

            for i, burner in enumerate(active_burners):
                # Calculate which patterns this burner should scrape
                start_idx = i * patterns_per_burner
                end_idx = min(start_idx + patterns_per_burner, len(SEARCH_PATTERNS))

                if start_idx >= len(SEARCH_PATTERNS):
                    break

                patterns_to_scrape = SEARCH_PATTERNS[start_idx:end_idx]

                # Scrape with this burner
                new_count = self.scrape_with_burner(burner, patterns_to_scrape)

                # If more burners available, wait before switching
                if i < len(active_burners) - 1:
                    delay = SCRAPING_SETTINGS['account_switch_delay']
                    print(f"\n[PAUSE] Waiting {delay}s before switching to next burner...")
                    time.sleep(delay)

            # Save final results
            self.save_results()

            # Summary
            print(f"\n{'='*60}")
            print("FINAL SUMMARY")
            print(f"{'='*60}")
            print(f"Starting followers: {starting_count}")
            print(f"New followers scraped: {len(self.all_followers) - starting_count}")
            print(f"Total unique followers: {len(self.all_followers)}")
            print(f"Burners used: {len(active_burners)}")
            print(f"{'='*60}\n")

        except Exception as e:
            print(f"\n[ERROR] {e}")
            import traceback
            traceback.print_exc()
        finally:
            input("\nPress Enter to close browser...")
            if self.driver:
                self.driver.quit()


def main():
    scraper = MultiBurnerScraper()
    scraper.run()


if __name__ == "__main__":
    main()
