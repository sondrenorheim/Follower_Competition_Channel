# instagram_webhook.py
# Flask server to handle Instagram webhook events for automated DM responses.
#
# Setup:
# 1. pip install flask requests python-dotenv
# 2. Copy .env.example to .env and fill in your credentials
# 3. Run: python instagram_webhook.py
# 4. In another terminal: ngrok http 5000
# 5. Copy ngrok HTTPS URL to Meta webhook config
# 6. Use VERIFY_TOKEN below as the verify token in Meta

from flask import Flask, request, jsonify
import requests
import json
import os
import sys
import re
from pathlib import Path
from dotenv import load_dotenv

# Ensure UTF-8 output for logs on Windows (prevents emoji crashes)
if os.name == "nt":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        try:
            import codecs
            sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
            sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")
        except Exception:
            pass

# Load environment variables from .env file (always relative to this file)
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

app = Flask(__name__)

# ============== CONFIGURATION ==============
# Choose any secret string - use this same value in Meta's webhook config
VERIFY_TOKEN = "FBG_WEBHOOK_SECRET_2026"

# Control debug/reloader (useful for headless/background runs)
WEBHOOK_DEBUG = os.getenv("WEBHOOK_DEBUG", "1").strip().lower() not in ("0", "false", "no")
WEBHOOK_USE_RELOADER = os.getenv("WEBHOOK_USE_RELOADER", "1").strip().lower() not in ("0", "false", "no")

# These are loaded from .env file (never commit real values!)
INSTAGRAM_ACCESS_TOKEN_APP = os.getenv("INSTAGRAM_ACCESS_TOKEN_APP", "YOUR_ACCESS_TOKEN_HERE")
INSTAGRAM_ACCOUNT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID", "YOUR_ACCOUNT_ID_HERE")

# Keywords that trigger auto-reply (case insensitive)
TRIGGER_KEYWORDS = [
    "result",
]

RESULTS_FOOTER = "To see other results like your monthly ranking check out the link in bio"

GAME_MODE_ALIASES = {
    "battle royale": "battle_royale",
    "battle_royale": "battle_royale",
    "fighter arena": "fighter_arena",
    "fighter_arena": "fighter_arena",
    "obstacle course": "obstacle_course",
    "obstacle_course": "obstacle_course",
    "snake escape": "snake_escape",
    "snake_escape": "snake_escape",
    "team battle": "team_battle",
    "team_battle": "team_battle",
    "platformer race": "platformer_race",
    "platformer_race": "platformer_race",
    "spleef": "spleef",
    "mingle": "mingle",
    "heads or tails": "heads_or_tails",
    "head or tails": "heads_or_tails",
    "heads/tails": "heads_or_tails",
    "heads_or_tails": "heads_or_tails",
    "wheel spinner": "wheel_spinner",
    "wheel_spinner": "wheel_spinner",
    "gorillas vs followers": "gorillas_vs_followers",
    "gorilla vs followers": "gorillas_vs_followers",
    "gorillas_vs_followers": "gorillas_vs_followers",
    "meteor mayhem": "meteor_mayhem",
    "meteor_mayhem": "meteor_mayhem",
    "anime fighting": "anime_fighting",
    "anime_fighting": "anime_fighting",
}

GAME_DISPLAY_NAMES = {
    "battle_royale": "Battle Royale",
    "fighter_arena": "Fighter Arena",
    "obstacle_course": "Obstacle Course",
    "snake_escape": "Snake Escape",
    "team_battle": "Team Battle",
    "platformer_race": "Platformer Race",
    "spleef": "Spleef",
    "mingle": "Mingle",
    "heads_or_tails": "Heads or Tails",
    "wheel_spinner": "Wheel Spinner",
    "gorillas_vs_followers": "Gorillas vs Followers",
    "meteor_mayhem": "Meteor Mayhem",
    "anime_fighting": "Anime Fighting",
}

DATA_ROOT = BASE_DIR / "website" / "public" / "api"
REQUEST_TIMEOUT_SECONDS = 20

# ============== WEBHOOK ENDPOINTS ==============

@app.route('/webhook', methods=['GET'])
def verify_webhook():
    """Handle Meta's webhook verification request"""
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    print(f"Verification request - Mode: {mode}, Token: {token}")

    if mode == 'subscribe' and token == VERIFY_TOKEN:
        print("Webhook verified successfully!")
        return challenge, 200
    else:
        print(f"Verification failed. Expected token: {VERIFY_TOKEN}, Got: {token}")
        return 'Forbidden', 403


@app.route('/webhook', methods=['POST'])
def handle_webhook():
    """Handle incoming webhook events (comments, mentions, etc.)"""
    data = request.get_json() or {}
    print("\n" + "=" * 50)
    print("Received webhook event:")
    print(json.dumps(data, indent=2))
    print("=" * 50 + "\n")

    try:
        # Process each entry in the webhook payload
        for entry in data.get('entry', []):
            # Handle comment events
            for change in entry.get('changes', []):
                field = change.get('field')
                value = change.get('value', {})

                if field == 'comments':
                    handle_comment(value)
                elif field == 'mentions':
                    handle_mention(value)
                elif field == 'messages':
                    handle_message(value)

    except Exception as e:
        print(f"Error processing webhook: {e}")

    return jsonify({'status': 'ok'}), 200


# ============== EVENT HANDLERS ==============

def handle_comment(comment_data):
    """Process a new comment and potentially post an auto-reply"""
    comment_text = comment_data.get('text')
    comment_id = comment_data.get('id')
    commenter_id = comment_data.get('from', {}).get('id')
    commenter_username = comment_data.get('from', {}).get('username', 'Unknown')

    if commenter_id and str(commenter_id) == str(INSTAGRAM_ACCOUNT_ID):
        print("Skipping comment from our own account")
        return

    if not comment_text and comment_id:
        comment_text = fetch_comment_text(comment_id)

    comment_text_lower = (comment_text or "").lower()
    print(f"New comment from @{commenter_username}: {comment_text_lower}")

    if not comment_id:
        print("Missing comment id - reply skipped")
        return

    # Check if comment contains trigger keyword
    if any(keyword.lower() in comment_text_lower for keyword in TRIGGER_KEYWORDS):
        print(f"Trigger keyword detected. Replying to @{commenter_username}")
        message = build_results_message(comment_data)
        reply_to_comment(comment_id, message)
    else:
        print("No trigger keyword found in comment")


def handle_mention(mention_data):
    """Process when someone mentions the account"""
    print(f"New mention: {mention_data}")


def handle_message(message_data):
    """Process incoming DMs (for future use)"""
    print(f"New message: {message_data}")


# ============== RESULTS LOGIC ==============

def normalize_game_mode(raw_value):
    if not raw_value:
        return None
    candidate = raw_value.strip().lower()
    if candidate in GAME_MODE_ALIASES:
        return GAME_MODE_ALIASES[candidate]
    candidate = candidate.replace("_", " ").replace("-", " ")
    candidate = re.sub(r"\s+", " ", candidate).strip()
    if candidate in GAME_MODE_ALIASES:
        return GAME_MODE_ALIASES[candidate]
    underscored = candidate.replace(" ", "_")
    if underscored in GAME_MODE_ALIASES:
        return GAME_MODE_ALIASES[underscored]
    if underscored in GAME_DISPLAY_NAMES:
        return underscored
    return None


def parse_game_info(caption):
    if not caption:
        return None, None

    game_match = re.search(r"Game:\s*([^\n|]+)(?:\s*\|\s*Day\s*(\d+))?", caption, re.IGNORECASE)
    raw_game = None
    raw_day = None
    if game_match:
        raw_game = game_match.group(1).strip()
        raw_day = game_match.group(2)

    if not raw_day:
        day_match = re.search(r"\bDay\s*(\d+)\b", caption, re.IGNORECASE)
        if day_match:
            raw_day = day_match.group(1)

    game_type = normalize_game_mode(raw_game)
    day_number = int(raw_day) if raw_day and raw_day.isdigit() else None

    return game_type, day_number


def load_json_file(path):
    try:
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception as exc:
        print(f"Failed to load {path}: {exc}")
        return None


def load_day_summary(day_number):
    if not day_number:
        return None
    return load_json_file(DATA_ROOT / "days" / f"{day_number}.json")


def find_game_entry(day_summary, game_type):
    if not day_summary or not game_type:
        return None
    matches = [game for game in day_summary.get("games", []) if game.get("game_type") == game_type]
    if not matches:
        return None
    return max(matches, key=lambda game: game.get("timestamp", ""))


def load_game_results(game_id):
    if not game_id:
        return None
    return load_json_file(DATA_ROOT / "games" / f"{game_id}.json")


def get_user_placement(game_data, username):
    if not game_data or not username:
        return None
    target = username.lstrip("@").lower()
    for entry in game_data.get("results", []):
        entry_name = str(entry.get("username", "")).lower()
        if entry_name == target:
            return entry.get("placement")
    return None


def format_results_message(game_display, day_number, placement):
    return (
        f"Your result in the {game_display} - Day {day_number}: {placement}\n"
        f"{RESULTS_FOOTER}"
    )


def format_not_following_message():
    return (
        "You were not following during the making of this game, but you will be part "
        "of tomorrow's games if you are followed.\n"
        f"{RESULTS_FOOTER}"
    )


def format_results_not_ready_message():
    return (
        "Results for this game are not posted yet, but they should be up soon.\n"
        f"{RESULTS_FOOTER}"
    )


def build_results_message(comment_data):
    media_id = comment_data.get('media', {}).get('id')
    commenter_username = comment_data.get('from', {}).get('username')

    caption = fetch_media_caption(media_id)
    game_type, day_number = parse_game_info(caption)

    if not game_type or not day_number:
        print("Missing game or day info from caption")
        return format_results_not_ready_message()

    day_summary = load_day_summary(day_number)
    if not day_summary:
        print(f"No day summary found for day {day_number}")
        return format_results_not_ready_message()

    game_entry = find_game_entry(day_summary, game_type)
    if not game_entry:
        print(f"No game entry found for day {day_number} and game {game_type}")
        return format_results_not_ready_message()

    game_data = load_game_results(game_entry.get("game_id"))
    if not game_data or not game_data.get("results"):
        print(f"No results found for game {game_entry.get('game_id')}")
        return format_results_not_ready_message()

    placement = get_user_placement(game_data, commenter_username)
    if placement is None:
        print(f"User @{commenter_username} not found in results")
        return format_not_following_message()

    day_value = game_data.get("day_number", day_number)
    game_display = GAME_DISPLAY_NAMES.get(game_type, game_type.replace("_", " ").title())

    return format_results_message(game_display, day_value, placement)


# ============== INSTAGRAM API FUNCTIONS ==============

def fetch_comment_text(comment_id):
    if INSTAGRAM_ACCESS_TOKEN_APP == "YOUR_ACCESS_TOKEN_HERE":
        print("Access token not configured - cannot fetch comment text")
        return None
    if not comment_id:
        return None

    url = f"https://graph.facebook.com/v18.0/{comment_id}"
    params = {
        "fields": "text",
        "access_token": INSTAGRAM_ACCESS_TOKEN_APP,
    }

    try:
        response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        if response.status_code == 200:
            return response.json().get("text")
        print(f"Failed to fetch comment text: {response.status_code} - {response.text}")
    except Exception as exc:
        print(f"Error fetching comment text: {exc}")

    return None


def fetch_media_caption(media_id):
    if INSTAGRAM_ACCESS_TOKEN_APP == "YOUR_ACCESS_TOKEN_HERE":
        print("Access token not configured - cannot fetch media caption")
        return None
    if not media_id:
        return None

    url = f"https://graph.facebook.com/v18.0/{media_id}"
    params = {
        "fields": "caption",
        "access_token": INSTAGRAM_ACCESS_TOKEN_APP,
    }

    try:
        response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        if response.status_code == 200:
            return response.json().get("caption")
        print(f"Failed to fetch media caption: {response.status_code} - {response.text}")
    except Exception as exc:
        print(f"Error fetching media caption: {exc}")

    return None


def reply_to_comment(comment_id, message):
    """Reply publicly to a comment via Instagram Graph API"""
    if INSTAGRAM_ACCESS_TOKEN_APP == "YOUR_ACCESS_TOKEN_HERE":
        print("Access token not configured - reply not sent (test mode)")
        return False
    if not comment_id:
        print("Missing comment id - reply skipped")
        return False

    url = f"https://graph.facebook.com/v18.0/{comment_id}/replies"
    payload = {
        "message": message,
        "access_token": INSTAGRAM_ACCESS_TOKEN_APP,
    }

    try:
        response = requests.post(url, data=payload, timeout=REQUEST_TIMEOUT_SECONDS)

        if response.status_code == 200:
            print(f"Reply posted successfully for comment {comment_id}")
            return True
        print(f"Failed to post reply: {response.status_code} - {response.text}")
        return False

    except Exception as exc:
        print(f"Error posting reply: {exc}")
        return False


# ============== HEALTH CHECK ==============

@app.route('/', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    return jsonify({
        'status': 'running',
        'service': 'Follower Battlegrounds Instagram Webhook',
        'verify_token_configured': bool(VERIFY_TOKEN),
        'access_token_configured': INSTAGRAM_ACCESS_TOKEN_APP != "YOUR_ACCESS_TOKEN_HERE"
    }), 200


# ============== MAIN ==============

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("Follower Battlegrounds Instagram Webhook Server")
    print("=" * 60)
    print(f"Verify Token: {VERIFY_TOKEN}")
    print(f"Access Token: {'Configured' if INSTAGRAM_ACCESS_TOKEN_APP != 'YOUR_ACCESS_TOKEN_HERE' else 'NOT SET'}")
    print(f"Trigger Keywords: {TRIGGER_KEYWORDS}")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Run ngrok: ngrok http 5000")
    print("2. Copy the HTTPS URL from ngrok")
    print("3. In Meta Developer Console, set:")
    print("   - Callback URL: <ngrok-url>/webhook")
    print(f"   - Verify Token: {VERIFY_TOKEN}")
    print("4. Click 'Verify and save'")
    print("=" * 60 + "\n")

    app.run(port=5000, debug=WEBHOOK_DEBUG, use_reloader=WEBHOOK_USE_RELOADER)
