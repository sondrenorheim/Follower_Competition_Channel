#!/usr/bin/env python3
"""
Automated Daily Cycle for Follower Battle
Handles the complete cycle: publish → wait → fetch → simulate → repeat

Usage:
    python auto_daily_cycle.py [--skip-publish] [--skip-fetch] [--skip-simulate]

Flags:
    --skip-publish: Skip publishing videos (start from fetch)
    --skip-fetch: Skip fetching followers (use existing data)
    --skip-simulate: Skip running simulations (end after publish+fetch)
"""

import argparse
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
import re


def log(message: str):
    """Print timestamped log message"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


def run_command(description: str, command: list, **kwargs):
    """Run a command and return success status"""
    log(f"▶️  {description}")
    try:
        result = subprocess.run(command, check=True, **kwargs)
        log(f"✅ {description} - Complete")
        return True
    except subprocess.CalledProcessError as e:
        log(f"❌ {description} - Failed (exit code: {e.returncode})")
        return False
    except Exception as e:
        log(f"❌ {description} - Error: {e}")
        return False


def increment_day_number():
    """Increment DAY_NUMBER in config.py by 1"""
    config_path = Path("config.py")

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Find current day number
        match = re.search(r'DAY_NUMBER\s*=\s*(\d+)', content)
        if not match:
            log("⚠️  Could not find DAY_NUMBER in config.py")
            return None

        current_day = int(match.group(1))
        new_day = current_day + 1

        # Replace day number
        new_content = re.sub(
            r'(DAY_NUMBER\s*=\s*)\d+',
            rf'\g<1>{new_day}',
            content
        )

        # Write back
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        log(f"✅ Updated DAY_NUMBER: {current_day} → {new_day}")
        return new_day

    except Exception as e:
        log(f"❌ Failed to update DAY_NUMBER: {e}")
        return None


def wait_with_countdown(hours: float, description: str):
    """Wait with countdown timer"""
    total_seconds = int(hours * 3600)
    end_time = datetime.now() + timedelta(seconds=total_seconds)

    log(f"⏳ {description}")
    log(f"   Will resume at: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        while total_seconds > 0:
            hours_left = total_seconds // 3600
            minutes_left = (total_seconds % 3600) // 60

            if hours_left > 0:
                print(f"\r   ⏰ Time remaining: {hours_left}h {minutes_left}m", end='', flush=True)
            else:
                print(f"\r   ⏰ Time remaining: {minutes_left}m", end='', flush=True)

            time.sleep(60)  # Update every minute
            total_seconds -= 60

        print()  # New line after countdown
        log(f"✅ Wait complete")

    except KeyboardInterrupt:
        print()
        log("⚠️  Wait interrupted by user")
        raise


def publish_videos():
    """Publish videos with 3-hour delays between each"""
    log("=" * 60)
    log("PHASE 1: PUBLISHING VIDEOS")
    log("=" * 60)

    # Run post_run_publish with 3-hour delays (10800 seconds)
    success = run_command(
        "Publishing videos to Instagram & TikTok",
        ["python", "post_run_publish.py", "--delay-seconds", "10800"],
        cwd=Path.cwd()
    )

    if not success:
        log("⚠️  Video publishing encountered errors")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            return False

    return True


def fetch_followers():
    """Fetch latest followers from Instagram"""
    log("=" * 60)
    log("PHASE 2: FETCHING FOLLOWERS")
    log("=" * 60)

    success = run_command(
        "Fetching followers from Instagram",
        ["python", "fetch_followers_v2.py"],
        cwd=Path.cwd()
    )

    return success


def run_simulations():
    """Run game simulations for all modes"""
    log("=" * 60)
    log("PHASE 3: RUNNING SIMULATIONS")
    log("=" * 60)

    # Increment day number before running simulations
    new_day = increment_day_number()
    if new_day is None:
        log("⚠️  Failed to increment day number")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            return False

    # Run main.py (which runs all game modes)
    success = run_command(
        f"Running simulations for Day {new_day}",
        ["python", "main.py"],
        cwd=Path.cwd()
    )

    return success


def main():
    parser = argparse.ArgumentParser(
        description="Automated daily cycle for Follower Battle"
    )
    parser.add_argument(
        "--skip-publish",
        action="store_true",
        help="Skip publishing videos (start from fetch)"
    )
    parser.add_argument(
        "--skip-fetch",
        action="store_true",
        help="Skip fetching followers (use existing data)"
    )
    parser.add_argument(
        "--skip-simulate",
        action="store_true",
        help="Skip running simulations (end after publish+fetch)"
    )

    args = parser.parse_args()

    start_time = datetime.now()
    log("=" * 60)
    log("AUTOMATED DAILY CYCLE - STARTING")
    log("=" * 60)
    log(f"Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # Phase 1: Publish videos (with 3-hour delays = 15 hours total)
        if not args.skip_publish:
            if not publish_videos():
                log("❌ Publishing failed - aborting cycle")
                return 1
        else:
            log("⏭️  Skipping video publishing")

        # Wait 9 hours after last video publishes
        if not args.skip_publish:
            wait_with_countdown(9.0, "Waiting 9 hours before fetching followers")

        # Phase 2: Fetch followers
        if not args.skip_fetch:
            if not fetch_followers():
                log("❌ Fetching followers failed - aborting cycle")
                return 1
        else:
            log("⏭️  Skipping follower fetch")

        # Phase 3: Run simulations
        if not args.skip_simulate:
            if not run_simulations():
                log("❌ Simulations failed - aborting cycle")
                return 1
        else:
            log("⏭️  Skipping simulations")

        # Complete!
        end_time = datetime.now()
        duration = end_time - start_time

        log("=" * 60)
        log("AUTOMATED DAILY CYCLE - COMPLETE")
        log("=" * 60)
        log(f"Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        log(f"End time:   {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        log(f"Duration:   {duration}")
        log("")
        log("✅ All phases completed successfully!")
        log("📹 New videos ready in Videos/Day_XX/")
        log("🔁 Run 'python auto_daily_cycle.py' again to start next cycle")

        return 0

    except KeyboardInterrupt:
        log("")
        log("⚠️  Cycle interrupted by user")
        return 130
    except Exception as e:
        log(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
