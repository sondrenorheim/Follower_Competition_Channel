import asyncio
import json
import os
import random
import re
import time
from tqdm import tqdm
from playwright.async_api import async_playwright

# -----------------------
# CONFIG
# -----------------------
INPUT_JSON = r"C:\Users\SondreNorheim\Documents\Follower_Competition_Channel\Followers\all_followers_fresh.json"
STATE_FILE = r"C:\Users\SondreNorheim\Documents\Follower_Competition_Channel\ig_state.json"

# ULTRA-SAFE MODE for burner account (very slow but minimal detection risk)
DELAY_MIN = 8.0             # Minimum 8 seconds between profiles (human-like)
DELAY_MAX = 15.0            # Maximum 15 seconds between profiles (random variation)
TIMEOUT_MS = 30_000

RESTART_EVERY = 40          # restart Chrome every 40 profiles (avoid detection patterns)
WRITE_EVERY = 25            # write JSON every N successful URL fills

# Session limits (run in batches to avoid long sessions)
MAX_PROFILES_PER_SESSION = 200  # Stop after 200 profiles (~45 min session)

# -----------------------
# HELPERS
# -----------------------
def log(msg: str):
    print(msg, flush=True)

def atomic_write_json(path, data, retries=25, delay=0.2):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # Windows can temporarily lock files (VSCode/OneDrive/AV)
    for _ in range(retries):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            time.sleep(delay)
    os.replace(tmp, path)

def normalize_profile_url(item):
    url = (item.get("profile_url") or "").strip()
    if url:
        return url.rstrip("/")
    username = (item.get("username") or "").strip()
    if not username:
        return ""
    return f"https://www.instagram.com/{username}".rstrip("/")

def normalize_pic_url(url: str | None) -> str | None:
    if not url:
        return None
    # Convert escaped slashes if they slipped through
    # (e.g. https:\/\/... or https:\\/\\/)
    url = url.replace("\\/", "/")
    url = url.replace("\\\\/", "/")
    url = url.replace("\\\\", "\\")  # tidy
    return url

def extract_pic_from_html(html: str) -> str | None:
    """
    Try to extract target user's profile picture URL from HTML.
    """
    # Prefer embedded JSON keys
    for key in ("profile_pic_url_hd", "profile_pic_url"):
        m = re.search(rf'"{key}"\s*:\s*"([^"]+)"', html)
        if m:
            val = bytes(m.group(1), "utf-8").decode("unicode_escape")
            return normalize_pic_url(val)

    # Fallback to og:image
    m = re.search(
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        html,
        re.I
    )
    if m:
        return normalize_pic_url(m.group(1))

    return None

def looks_like_bad_pic(url: str) -> bool:
    """
    Catch common non-avatar / placeholder-ish returns.
    This is conservative; adjust if needed.
    """
    u = url.lower()
    # Sometimes "static" placeholders or obviously non-image endpoints show up
    if "static" in u and "instagram" in u and ("sprite" in u or "blank" in u):
        return True
    # Must at least look like an image URL
    if not any(ext in u for ext in (".jpg", ".jpeg", ".png", ".webp")):
        # Some IG URLs may omit extension, but most profile pics have .jpg
        return False
    return False

async def ensure_logged_in(page, context):
    await page.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=TIMEOUT_MS)
    await page.wait_for_timeout(1200)

    if "accounts/login" in page.url.lower():
        log("\n🔐 Please log in in the opened Chrome window.")
        log("When you see your feed, come back here and press Enter.\n")
        input("Press Enter when logged in... ")
        await page.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=TIMEOUT_MS)

    await context.storage_state(path=STATE_FILE)
    log(f"✅ Session saved to {STATE_FILE}")

async def get_own_avatar_url(page) -> str | None:
    """
    Grab the logged-in user's own avatar URL once.
    We then reject any extracted pic URLs that equal this (your reported bug).
    """
    # accounts/edit/ is usually accessible and contains your own profile context
    await page.goto("https://www.instagram.com/accounts/edit/", wait_until="domcontentloaded", timeout=TIMEOUT_MS)
    await page.wait_for_timeout(800)
    html = await page.content()
    pic = extract_pic_from_html(html)
    return normalize_pic_url(pic)

def should_accept_pic(pic_url: str | None, own_avatar_url: str | None) -> bool:
    if not pic_url:
        return False
    if own_avatar_url and pic_url == own_avatar_url:
        return False
    if looks_like_bad_pic(pic_url):
        return False
    return True

# -----------------------
# MAIN
# -----------------------
async def main():
    with open(INPUT_JSON, encoding="utf-8") as f:
        data = json.load(f)

    missing = [i for i, x in enumerate(data) if not (x.get("profile_pic_url") or "").strip()]
    log(f"Loaded: {len(data)} entries")
    log(f"Missing profile_pic_url: {len(missing)}")

    async with async_playwright() as p:
        start = 0
        dirty = 0  # successful fills since last disk write
        profiles_fetched_this_session = 0  # Track session length

        while start < len(missing) and profiles_fetched_this_session < MAX_PROFILES_PER_SESSION:
            batch = missing[start:start + RESTART_EVERY]
            start += RESTART_EVERY

            browser = await p.chromium.launch(
                channel="chrome",   # system-installed Chrome
                headless=False,
                args=["--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage"],
            )

            context_kwargs = {
                "viewport": {"width": 1200, "height": 900},
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140 Safari/537.36",
            }
            if os.path.exists(STATE_FILE):
                context_kwargs["storage_state"] = STATE_FILE

            context = await browser.new_context(**context_kwargs)
            page = await context.new_page()

            await ensure_logged_in(page, context)

            # 🔥 NEW: detect your own avatar and use it as a guard
            own_avatar_url = await get_own_avatar_url(page)
            if own_avatar_url:
                log("🧍 Detected logged-in avatar URL (will be rejected if returned for others).")
            else:
                log("⚠️ Could not detect logged-in avatar URL. (Guard disabled)")

            for idx in tqdm(batch, desc="Filling profile_pic_url (URL-only, guarded)"):
                # Check session limit
                if profiles_fetched_this_session >= MAX_PROFILES_PER_SESSION:
                    log(f"\n⏸️  Session limit reached ({MAX_PROFILES_PER_SESSION} profiles). Stopping for safety.")
                    break

                item = data[idx]
                username = (item.get("username") or "").strip()
                profile_url = normalize_profile_url(item)

                if not username or not profile_url:
                    continue

                profiles_fetched_this_session += 1

                try:
                    log(f"➡️  Fetching: {username}")

                    await page.goto(profile_url, wait_until="domcontentloaded", timeout=TIMEOUT_MS)
                    await page.wait_for_timeout(650)

                    html = await page.content()
                    pic = extract_pic_from_html(html)

                    # ✅ Guard against “viewer avatar”
                    if should_accept_pic(pic, own_avatar_url):
                        item["profile_pic_url"] = pic
                        dirty += 1
                        log(f"✅  Saved avatar URL for: {username}")

                        if dirty >= WRITE_EVERY:
                            atomic_write_json(INPUT_JSON, data)
                            log(f"💾  Saved progress to disk ({WRITE_EVERY} updates)")
                            dirty = 0
                    else:
                        # Important: do NOT write anything if we suspect it’s your own avatar / bad
                        if pic and own_avatar_url and pic == own_avatar_url:
                            log(f"🚫  Rejected (matched your own avatar): {username}")
                        elif pic:
                            log(f"⚠️  Rejected (suspicious/placeholder): {username}")
                        else:
                            log(f"⚠️  No avatar found for: {username}")

                    # clear memory between profiles
                    await page.goto("about:blank", wait_until="domcontentloaded")

                except KeyboardInterrupt:
                    log("\n🛑 Stopped by user. Saving progress...\n")
                    if dirty:
                        atomic_write_json(INPUT_JSON, data)
                        log("💾  Saved final progress to disk")
                    await browser.close()
                    return

                except Exception as e:
                    log(f"❌  Error fetching {username}: {e}")

                finally:
                    await asyncio.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

            # flush at end of batch
            if dirty:
                atomic_write_json(INPUT_JSON, data)
                log("💾  Saved end-of-batch progress to disk")
                dirty = 0

            await browser.close()

            # Check if we hit session limit
            if profiles_fetched_this_session >= MAX_PROFILES_PER_SESSION:
                break

    log(f"\n✅ Session complete!")
    log(f"📊 Profiles fetched this session: {profiles_fetched_this_session}/{MAX_PROFILES_PER_SESSION}")
    log(f"📁 JSON updated: {INPUT_JSON}")
    log(f"\n💡 To continue, run this script again. It will resume from where it stopped.")

if __name__ == "__main__":
    asyncio.run(main())
