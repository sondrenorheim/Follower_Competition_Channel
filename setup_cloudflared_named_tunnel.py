#!/usr/bin/env python3
"""
Setup a named Cloudflare Tunnel for the Instagram webhook.

Usage:
  python setup_cloudflared_named_tunnel.py --name fbg-webhook --hostname webhook.example.com

Notes:
  - You must have a Cloudflare account and a domain in that account.
  - This script will run:
      cloudflared tunnel login
      cloudflared tunnel create <name>
      cloudflared tunnel route dns <name> <hostname>
  - It will then write a config file for running the tunnel.
"""

import argparse
import json
import shutil
import subprocess
from pathlib import Path

import config


def _run(cmd, check=True, capture_output=False):
    return subprocess.run(
        cmd,
        check=check,
        capture_output=capture_output,
        text=True,
    )


def _resolve_cloudflared(path_hint: str) -> str | None:
    if path_hint:
        if Path(path_hint).exists():
            return path_hint
        resolved = shutil.which(path_hint)
        if resolved:
            return resolved
    return shutil.which("cloudflared")


def _default_config_path() -> Path:
    cfg = str(getattr(config, "CLOUDFLARED_CONFIG_PATH", "")).strip()
    if cfg:
        return Path(cfg)
    return Path.home() / ".cloudflared" / "config.yml"


def _get_tunnel_id(cloudflared: str, tunnel_name: str) -> str | None:
    try:
        result = _run([cloudflared, "tunnel", "list", "--output", "json"], capture_output=True)
        data = json.loads(result.stdout or "[]")
        for entry in data:
            if entry.get("name") == tunnel_name:
                return entry.get("id")
    except Exception:
        return None
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Setup a named Cloudflare Tunnel for the webhook.")
    parser.add_argument("--name", default=str(getattr(config, "CLOUDFLARED_TUNNEL_NAME", "")).strip())
    parser.add_argument("--hostname", default=str(getattr(config, "CLOUDFLARED_HOSTNAME", "")).strip())
    parser.add_argument("--config-path", default=str(_default_config_path()))
    parser.add_argument("--cloudflared-path", default=str(getattr(config, "CLOUDFLARED_PATH", "")).strip())
    args = parser.parse_args()

    cloudflared = _resolve_cloudflared(args.cloudflared_path)
    if not cloudflared:
        print("cloudflared not found. Set CLOUDFLARED_PATH in config.py or add it to PATH.")
        return 1

    tunnel_name = args.name or input("Tunnel name (e.g. fbg-webhook): ").strip()
    if not tunnel_name:
        print("Tunnel name is required.")
        return 1

    hostname = args.hostname or input("Hostname (e.g. webhook.example.com): ").strip()
    if not hostname or "." not in hostname:
        print("Valid hostname is required.")
        return 1

    config_path = Path(args.config_path).expanduser()

    print("=" * 60)
    print("Cloudflare Named Tunnel Setup")
    print("=" * 60)
    print(f"cloudflared: {cloudflared}")
    print(f"Tunnel name: {tunnel_name}")
    print(f"Hostname:   {hostname}")
    print(f"Config:     {config_path}")
    print("=" * 60)

    print("\nStep 1: cloudflared tunnel login (browser auth)")
    _run([cloudflared, "tunnel", "login"], check=True)

    print("\nStep 2: create tunnel (safe to re-run)")
    try:
        _run([cloudflared, "tunnel", "create", tunnel_name], check=True)
    except subprocess.CalledProcessError:
        print("Tunnel create failed (may already exist). Continuing...")

    print("\nStep 3: route DNS (requires domain in your Cloudflare account)")
    try:
        _run([cloudflared, "tunnel", "route", "dns", tunnel_name, hostname], check=True)
    except subprocess.CalledProcessError:
        print("DNS route failed. Make sure the domain is in your Cloudflare account.")
        print("You can re-run later:")
        print(f'  {cloudflared} tunnel route dns {tunnel_name} {hostname}')

    tunnel_id = _get_tunnel_id(cloudflared, tunnel_name)
    if not tunnel_id:
        print("Could not determine tunnel ID. Run:")
        print(f'  {cloudflared} tunnel list')
        print("Then update config.yml manually.")
        return 1

    creds = Path.home() / ".cloudflared" / f"{tunnel_id}.json"
    if not creds.exists():
        print(f"Warning: credentials file not found at {creds}")

    # Write config
    config_path.parent.mkdir(parents=True, exist_ok=True)
    creds_yaml = str(creds).replace("\\", "/")
    lines = [
        f"tunnel: {tunnel_id}",
        f"credentials-file: {creds_yaml}",
        "",
        "ingress:",
        f"  - hostname: {hostname}",
        f"    service: http://localhost:{getattr(config, 'WEBHOOK_SERVER_PORT', 5000)}",
        "  - service: http_status:404",
        "",
    ]
    config_path.write_text("\n".join(lines), encoding="utf-8")

    print("\nConfig written.")
    print(f"Config path: {config_path}")
    print("\nNext steps:")
    print("1. Update config.py:")
    print(f'   CLOUDFLARED_TUNNEL_MODE = "named"')
    print(f'   CLOUDFLARED_TUNNEL_NAME = "{tunnel_name}"')
    print(f'   CLOUDFLARED_HOSTNAME = "{hostname}"')
    print(f'   CLOUDFLARED_CONFIG_PATH = r"{str(config_path)}"')
    print("2. Restart the webhook:")
    print("   python restart_webhook.py")
    print(f"3. Set Meta callback URL to: https://{hostname}/webhook")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
