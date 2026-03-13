#!/usr/bin/env python3
"""
One-time git history cleanup helper for large API partitions.

Safety-first behavior:
- Creates a full git bundle backup.
- Copies current heavyweight API data to a backup folder.
- Runs git-filter-repo only when --execute is passed.
- Does NOT push automatically.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


HEAVY_PATHS = [
    Path("website/public/api/games"),
    Path("website/public/api/player_history"),
]


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=check, text=True)


def ensure_repo_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(result.stdout.strip())


def ensure_clean_worktree() -> None:
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        check=True,
        capture_output=True,
        text=True,
    )
    if result.stdout.strip():
        raise RuntimeError(
            "Working tree is not clean. Commit/stash changes first before history rewrite."
        )


def create_backups(repo_root: Path, backup_root: Path) -> None:
    backup_root.mkdir(parents=True, exist_ok=True)

    bundle_path = backup_root / "full_repo.bundle"
    print(f"[backup] Creating git bundle: {bundle_path}")
    run(["git", "bundle", "create", str(bundle_path), "--all"])

    heavy_backup = backup_root / "heavy_api_snapshot"
    heavy_backup.mkdir(parents=True, exist_ok=True)
    for rel in HEAVY_PATHS:
        src = repo_root / rel
        if not src.exists():
            print(f"[backup] Skipping missing path: {rel}")
            continue
        dst = heavy_backup / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        print(f"[backup] Copying {rel} -> {dst}")
        shutil.copytree(src, dst, dirs_exist_ok=True)


def ensure_filter_repo() -> None:
    result = subprocess.run(
        ["git", "filter-repo", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "git-filter-repo is not installed.\n"
            "Install: pip install git-filter-repo\n"
            "Then retry."
        )


def rewrite_history() -> None:
    cmd = [
        "git",
        "filter-repo",
        "--force",
        "--path",
        "website/public/api/games",
        "--path",
        "website/public/api/player_history",
        "--invert-paths",
    ]
    print("[rewrite] Removing heavy API history paths...")
    run(cmd)

    print("[rewrite] Running aggressive garbage collection...")
    run(["git", "reflog", "expire", "--expire=now", "--all"])
    run(["git", "gc", "--prune=now", "--aggressive"])


def print_next_steps(backup_root: Path) -> None:
    print("\nDone.")
    print(f"Backups: {backup_root}")
    print("Next steps:")
    print("1. Validate repo content and website behavior locally.")
    print("2. Force push rewritten history:")
    print("   git push --force-with-lease origin main")
    print("3. Re-clone other local copies of this repo.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Safely rewrite git history for heavy API paths.")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Run backup + rewrite. Without this flag, prints plan only.",
    )
    parser.add_argument(
        "--backup-dir",
        default="backups",
        help="Directory where safety backups will be stored (default: backups).",
    )
    args = parser.parse_args()

    repo_root = ensure_repo_root()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_root = repo_root / args.backup_dir / f"history_cleanup_{stamp}"

    print(f"Repo: {repo_root}")
    print(f"Heavy paths targeted: {', '.join(str(p) for p in HEAVY_PATHS)}")
    print(f"Backup folder: {backup_root}")

    if not args.execute:
        print("\nDry run only. Re-run with --execute to perform cleanup.")
        print("Preconditions:")
        print("- clean working tree")
        print("- git-filter-repo installed")
        return 0

    ensure_clean_worktree()
    ensure_filter_repo()
    create_backups(repo_root, backup_root)
    rewrite_history()
    print_next_steps(backup_root)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(1)
