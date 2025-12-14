"""
Configuration for multiple burner accounts
Edit this file to add your burner accounts, then run the multi-burner scraper
"""

# Account to scrape followers FROM (the target)
TARGET_USERNAME = "followerbattlegrounds"

# List of your burner accounts
# Add as many as you want - script will rotate through them
BURNER_ACCOUNTS = [
    {
        "username": "stinsonoscar2",
        "cookie_file": "instagram_cookies_burner1.pkl",
        "status": "BLOCKED",  # READY, ACTIVE, BLOCKED, COOLDOWN
        "notes": "Used Dec 13, got blocked after 2k followers"
    },
    {
        "username": "stinsonoscar2burner2",
        "cookie_file": "instagram_cookies_burner2.pkl",
        "status": "READY",
        "notes": "Created Dec 13, 2024 - Ready to scrape"
    },
    {
        "username": "burner_account_3",
        "cookie_file": "instagram_cookies_burner3.pkl",
        "status": "NOT_CREATED",
        "notes": "Not created yet - add username when ready"
    },
    # Add more burner accounts here as needed
]

# Search patterns for alphabet scraper
# Start with single letters, expand if needed
SEARCH_PATTERNS = [
    'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm',
    'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z',
    '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
    '_', '.', '-',
]

# Scraping settings
SCRAPING_SETTINGS = {
    # How many search patterns to run per account before switching
    "patterns_per_account": 13,  # ~13 letters per burner = 3 burners for a-z

    # Delay between searches (seconds)
    "search_delay_min": 2,
    "search_delay_max": 4,

    # Delay between switching accounts (seconds)
    "account_switch_delay": 30,

    # Auto-stop after collecting this many unique followers (0 = no limit)
    "target_follower_count": 0,
}


def get_active_burners():
    """Get list of burner accounts that are ready to use"""
    return [b for b in BURNER_ACCOUNTS if b["status"] in ["READY", "ACTIVE"]]


def get_next_burner(current_username=None):
    """Get next available burner account"""
    active = get_active_burners()

    if not active:
        return None

    if current_username is None:
        return active[0]

    # Find current burner and get next one
    for i, burner in enumerate(active):
        if burner["username"] == current_username:
            # Return next burner (wrap around to start)
            next_index = (i + 1) % len(active)
            return active[next_index]

    return active[0]


def mark_burner_blocked(username):
    """Mark a burner account as blocked"""
    for burner in BURNER_ACCOUNTS:
        if burner["username"] == username:
            burner["status"] = "BLOCKED"
            print(f"[WARN] Marked {username} as BLOCKED")
            return True
    return False


def print_burner_status():
    """Print status of all burner accounts"""
    print("\n" + "="*60)
    print("BURNER ACCOUNT STATUS")
    print("="*60)

    for i, burner in enumerate(BURNER_ACCOUNTS, 1):
        status_emoji = {
            "READY": "✅",
            "ACTIVE": "🔄",
            "BLOCKED": "❌",
            "COOLDOWN": "⏸️"
        }.get(burner["status"], "❓")

        print(f"{i}. {status_emoji} {burner['username']}")
        print(f"   Status: {burner['status']}")
        print(f"   Notes: {burner['notes']}")

    active_count = len(get_active_burners())
    print(f"\nActive burners available: {active_count}")
    print("="*60 + "\n")


if __name__ == "__main__":
    print_burner_status()
