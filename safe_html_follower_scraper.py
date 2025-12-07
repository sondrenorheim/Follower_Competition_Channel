import time
import json
from datetime import datetime
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

USERNAME = "followerbattlegrounds"


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
# Robust Instagram login
# -----------------------------
def login(driver):
    driver.get("https://www.instagram.com/accounts/login/")
    print("🔐 Waiting for Instagram login page...")
    time.sleep(4)

    # Close cookie popup if needed
    try:
        buttons = driver.find_elements(By.TAG_NAME, "button")
        for b in buttons:
            if "Allow" in b.text or "Accept" in b.text:
                b.click()
                print("🍪 Cookie popup dismissed")
                time.sleep(2)
                break
    except:
        pass

    # Case 1: "Continue as <username>"
    try:
        continue_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Continue as')]")
        print("➡ Instagram shows a 'Continue as' button. Click it manually.")
        input("Press Enter AFTER you clicked it in the browser... ")
        return
    except:
        pass

    # Case 2: username/password fields
    try:
        username_field = driver.find_element(By.NAME, "username")
        password_field = driver.find_element(By.NAME, "password")
        print("➡ Enter your username and password manually.")
        print("⚠ Do NOT hit Enter. Click the Login button manually.")
    except:
        print("⚠ Could not detect login fields.")
        print("➡ Please complete login manually in the browser window.")

    input("Press Enter AFTER you have successfully logged in... ")


# -----------------------------
# Scrape followers through scrolling
# -----------------------------
def scrape_followers(driver):
    print("📄 Opening profile page...")
    driver.get(f"https://www.instagram.com/{USERNAME}/")
    time.sleep(4)

    # ---------- CLOSE POPUPS ----------
    def close_popups():
        try:
            buttons = driver.find_elements(By.TAG_NAME, "button")
            for b in buttons:
                if any(t in b.text for t in ["Not Now", "Cancel", "Close", "OK", "Allow"]):
                    try:
                        print(f"🛑 Closing popup: {b.text}")
                        b.click()
                        time.sleep(1)
                    except:
                        pass
        except:
            pass

    close_popups()

    # ---------- CLICK FOLLOWERS BUTTON ----------
    print("📁 Opening Followers dialog...")

    followers_button = driver.find_element(By.PARTIAL_LINK_TEXT, "followers")

    # Retry click until successful
    for attempt in range(12):
        try:
            close_popups()
            followers_button.click()
            time.sleep(2)
            break
        except Exception:
            print(f"⚠ Followers button blocked (attempt {attempt+1}/12). Retrying...")
            time.sleep(1)
            if attempt == 11:
                raise

    # ---------- WAIT FOR DIALOG ----------
    print("🔍 Waiting for followers dialog to appear...")
    time.sleep(3)

    dialogs = driver.find_elements(By.XPATH, "//div[@role='dialog']")
    if not dialogs:
        raise Exception("❌ Followers dialog did not appear at all")

    dialog = dialogs[0]

    # ---------- FIND TRUE SCROLLABLE ELEMENT ----------
    print("📐 Locating scrollable followers list container...")

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
        raise Exception("❌ Could not locate scrollable followers panel")

    print("✅ Followers scroll panel found!")

    # ---------- START SCROLLING ----------
    print("👀 Scrolling follower list safely...")

    followers = {}
    retries = 0

    while True:
        # Scroll by JavaScript instead of send_keys
        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", scroll_panel)
        time.sleep(1.5)

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
            print(f"⏳ No new followers loaded (retry {retries}/25)...")
            if retries > 25:
                print("📌 End of follower list reached.")
                break

        print(f"📊 Total collected: {len(followers)}")

    return list(followers.values())




# -----------------------------
# Save output to JSON
# -----------------------------
def save_file(data):
    filename = f"followers_safe_{datetime.now().strftime('%Y%m%d')}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"💾 Saved to {filename}")


# -----------------------------
# Main
# -----------------------------
def main():
    driver = setup_browser()
    login(driver)
    followers = scrape_followers(driver)
    print(f"🎉 Finished! Total followers scraped: {len(followers)}")
    save_file(followers)
    driver.quit()


if __name__ == "__main__":
    main()
