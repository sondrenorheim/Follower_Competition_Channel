#!/usr/bin/env python3
"""
Export Discord server members to a JSON file for follower imports.

Reads bot token from DISCORD_BOT_TOKEN, DISCORD_TOKEN, or discord_bot_token.txt.
Reads guild ID from DISCORD_GUILD_ID or guild.txt when not provided.
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

API_BASE = "https://discord.com/api/v10"


def load_token(token_file: Path) -> str:
    env_token = os.getenv("DISCORD_BOT_TOKEN") or os.getenv("DISCORD_TOKEN")
    if env_token:
        return env_token.strip()
    if token_file.exists():
        return token_file.read_text(encoding="utf-8").strip()
    return ""


def load_guild_id(guild_id_file: Path) -> str:
    env_id = os.getenv("DISCORD_GUILD_ID")
    if env_id:
        return env_id.strip()
    if guild_id_file.exists():
        return guild_id_file.read_text(encoding="utf-8").strip()
    return ""


def avatar_url_for_member(user: dict, member: dict, guild_id: str) -> str:
    user_id = user.get("id", "")
    member_avatar = member.get("avatar")
    if member_avatar:
        ext = "gif" if member_avatar.startswith("a_") else "png"
        return (
            f"https://cdn.discordapp.com/guilds/{guild_id}/users/{user_id}/"
            f"avatars/{member_avatar}.{ext}?size=128"
        )

    user_avatar = user.get("avatar")
    if user_avatar:
        ext = "gif" if user_avatar.startswith("a_") else "png"
        return f"https://cdn.discordapp.com/avatars/{user_id}/{user_avatar}.{ext}?size=128"

    discriminator = user.get("discriminator", "0")
    if discriminator and discriminator != "0":
        try:
            index = int(discriminator) % 5
        except ValueError:
            index = 0
    else:
        try:
            index = (int(user_id) >> 22) % 6
        except ValueError:
            index = 0
    return f"https://cdn.discordapp.com/embed/avatars/{index}.png"


def fetch_members(
    token: str,
    guild_id: str,
    use_nick: bool,
    include_bots: bool,
    limit: int,
) -> list[dict]:
    try:
        import requests
    except ImportError:
        raise SystemExit("Missing requests. Install with: pip install requests")

    headers = {"Authorization": f"Bot {token}"}
    members: list[dict] = []
    after = None

    while True:
        params = {"limit": 1000}
        if after:
            params["after"] = after

        resp = requests.get(
            f"{API_BASE}/guilds/{guild_id}/members",
            headers=headers,
            params=params,
            timeout=30,
        )

        if resp.status_code == 429:
            retry_after = resp.json().get("retry_after", 1)
            time.sleep(float(retry_after))
            continue

        if resp.status_code != 200:
            raise SystemExit(f"Discord API error {resp.status_code}: {resp.text}")

        batch = resp.json()
        if not batch:
            break

        for member in batch:
            user = member.get("user", {})
            if not user:
                continue
            if user.get("bot") and not include_bots:
                continue

            discord_username = user.get("username") or ""
            display_name = member.get("nick") if use_nick else discord_username
            if not display_name:
                display_name = discord_username or f"user_{user.get('id', '')}"

            members.append(
                {
                    "username": display_name,
                    "profile_pic_url": avatar_url_for_member(user, member, guild_id),
                    "discord_id": user.get("id", ""),
                    "discord_username": discord_username,
                }
            )

            if limit and len(members) >= limit:
                return members

        after = batch[-1]["user"]["id"]

    return members


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export Discord server members to JSON.")
    parser.add_argument(
        "--guild-id",
        default="",
        help="Discord server (guild) ID (optional if DISCORD_GUILD_ID or file is set).",
    )
    parser.add_argument(
        "--guild-id-file",
        default="guild.txt",
        help="Guild ID file path (used if --guild-id and env var are missing).",
    )
    parser.add_argument(
        "--out",
        default="Followers/discord_followers.json",
        help="Output JSON file path.",
    )
    parser.add_argument(
        "--token-file",
        default="discord_bot_token.txt",
        help="Token file path (used if env vars are missing).",
    )
    parser.add_argument(
        "--use-nick",
        action="store_true",
        help="Use server nickname as username (fallback to account username).",
    )
    parser.add_argument(
        "--include-bots",
        action="store_true",
        help="Include bot accounts in the export.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional max number of members to export (0 = all).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    token_file = Path(args.token_file)
    token = load_token(token_file)
    if not token:
        raise SystemExit(
            "Discord bot token not found. Set DISCORD_BOT_TOKEN, DISCORD_TOKEN, "
            "or add it to discord_bot_token.txt."
        )

    guild_id = args.guild_id.strip()
    if not guild_id:
        guild_id = load_guild_id(Path(args.guild_id_file))
    if not guild_id:
        raise SystemExit(
            "Discord guild ID not found. Provide --guild-id, set DISCORD_GUILD_ID, "
            "or add it to discord_guild_id.txt."
        )

    members = fetch_members(
        token=token,
        guild_id=guild_id,
        use_nick=args.use_nick,
        include_bots=args.include_bots,
        limit=max(0, args.limit),
    )

    output_path = Path(args.out)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(members, indent=2), encoding="utf-8")

    print(f"Exported members: {len(members)}")
    print(f"Output: {output_path}")


if __name__ == "__main__":
    main()
