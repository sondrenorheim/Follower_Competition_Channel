#!/usr/bin/env python3
"""
Daily Automation Loop for Follower Battle Grounds

COMPLETE AUTOMATION CYCLE:
1. Push stats to GitHub
2. Upload videos to Instagram & TikTok (one at a time with 2-3 hour delays)
3. Wait until 6 AM next day
4. Fetch fresh follower list at 6 AM
5. Run all games to generate new videos
6. Loop back to step 1

Usage:
    python daily_automation_loop.py

Features:
- Randomized delays (2-3 hours) between uploads for human-like behavior
- Safe Selenium-based uploads (no API violations)
- Scheduled 6 AM follower fetching for consistent daily updates
- Automatic day number incrementing
- Error handling and recovery
- Logs all activities
"""

import time
import random
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timedelta
import json
import traceback

import config
from shared import auto_push
from instagram_story_generator import generate_story_image
from safe_instagram_uploader import SafeInstagramUploader


class DailyAutomationLoop:
    """
    Manages the complete daily automation cycle
    """

    def __init__(self):
        self.log_file = "automation_loop.log"
        self.state_file = "automation_state.json"
        self.load_state()

    def log(self, message: str):
        """Log message to both console and file"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] {message}"
        # Print with UTF-8 encoding on Windows to avoid emoji issues
        try:
            print(log_line)
        except UnicodeEncodeError:
            # Fallback: remove emojis if encoding fails
            import re
            log_line_ascii = re.sub(r'[^\x00-\x7F]+', '', log_line)
            print(log_line_ascii)

        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_line + '\n')

    def load_state(self):
        """Load automation state from file"""
        if Path(self.state_file).exists():
            with open(self.state_file, 'r') as f:
                self.state = json.load(f)
        else:
            self.state = {
                'last_upload_date': None,
                'last_game_run_date': None,
                'current_day': config.DAY_NUMBER,
                # Legacy key kept for backward compatibility
                'videos_uploaded_today': [],
                'videos_uploaded_instagram': [],
                'videos_uploaded_tiktok': []
            }

        # Migrate legacy state to per-platform tracking so we can retry failed platforms
        if 'videos_uploaded_instagram' not in self.state or 'videos_uploaded_tiktok' not in self.state:
            legacy = self.state.get('videos_uploaded_today', [])
            self.state.setdefault('videos_uploaded_instagram', list(legacy))
            self.state.setdefault('videos_uploaded_tiktok', list(legacy))

        # If config.py has been bumped (e.g., you generated newer-day videos manually),
        # keep the automation state in sync so uploads target the latest day.
        config_day = getattr(config, 'DAY_NUMBER', None)
        if config_day and self.state.get('current_day', 0) < config_day:
            self.state['current_day'] = config_day
            self.state['videos_uploaded_today'] = []
            self.state['videos_uploaded_instagram'] = []
            self.state['videos_uploaded_tiktok'] = []
            self.save_state()

    def save_state(self):
        """Save automation state to file"""
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)

    def push_stats_to_github(self):
        """Push stats to GitHub"""
        self.log("=" * 60)
        self.log("STEP 1: Pushing stats to GitHub")
        self.log("=" * 60)

        try:
            success = auto_push.push_stats_to_github()
            if success:
                self.log("SUCCESS: Stats pushed successfully")
                return True
            else:
                self.log("WARNING: Stats push failed (non-critical)")
                return False
        except Exception as e:
            self.log(f"ERROR: Stats push error: {e}")
            return False

    def get_videos_to_upload(self) -> list:
        """
        Get list of videos to upload for current day

        Returns:
            List of (video_path, game_mode) tuples
        """
        day_number = self.state['current_day']
        videos = []

        # Get all game modes
        game_modes = getattr(config, 'ALL_GAME_MODES', [
            'battle_royale',
            'fighter_arena',
            'obstacle_course',
            'snake_escape',
            'team_battle',
            'platformer_race'
        ])

        for game_mode in game_modes:
            # Build video path
            video_path = config.get_output_video_path(
                game_mode=game_mode,
                day_number=day_number,
                test_mode=False
            )
            video_path = Path(video_path)

            if video_path.exists():
                videos.append((str(video_path), game_mode))
                self.log(f"   Found: {video_path.name}")
            else:
                self.log(f"   Missing: {video_path.name}")

        return videos

    def build_caption(self, game_mode: str, day_number: int) -> str:
        """
        Build caption for video upload

        Args:
            game_mode: Name of game mode
            day_number: Current day number

        Returns:
            Caption text
        """
        # Varied captions to seem more human (no emojis to avoid encoding issues)
        caption_templates = [
            f"Day {day_number} of making my followers battle every day! Follow to enter the battle\n\nCheck the link in the bio for your result and overall monthly ranking!\n\n#followerbattlegrounds",
            f"Day {day_number}! My followers are fighting again. Follow to join the next round!\n\n#followerbattlegrounds #battle",
            f"Making my followers compete - Day {day_number}! Follow to participate!\n\n#followerbattlegrounds #gaming",
            f"Day {day_number} of the ultimate follower battle! Who will win?\n\n#followerbattlegrounds",
        ]

        # Pick random template
        caption = random.choice(caption_templates)
        return caption

    def upload_video_instagram(self, video_path: str, caption: str) -> bool:
        """
        Upload video to Instagram using safe Selenium uploader

        Args:
            video_path: Path to video file
            caption: Caption text

        Returns:
            True if upload successful
        """
        try:
            self.log(f"   Instagram upload: {Path(video_path).name}")

            # Run safe Instagram uploader
            cmd = [
                sys.executable,
                "safe_instagram_uploader.py",
                "--video", video_path,
                "--caption", caption,
                "--headless"  # Run in background
            ]

            # Don't capture output - let it stream in real-time so we see detailed logging
            result = subprocess.run(
                cmd,
                text=True,
                encoding='utf-8',
                errors='replace',  # Replace encoding errors instead of crashing
                timeout=300  # 5 minute timeout (reduced from 10)
            )

            if result.returncode == 0:
                self.log("   SUCCESS: Instagram upload successful")
                return True
            else:
                self.log(f"   ERROR: Instagram upload failed (exit code {result.returncode})")
                return False

        except subprocess.TimeoutExpired:
            self.log("   ERROR: Instagram upload timed out")
            return False
        except Exception as e:
            self.log(f"   ERROR: Instagram upload error: {e}")
            return False

    def upload_video_tiktok(self, video_path: str, caption: str) -> bool:
        """
        Upload video to TikTok using TiktokAutoUploader

        Args:
            video_path: Path to video file
            caption: Caption text

        Returns:
            True if upload successful
        """
        try:
            self.log(f"   TikTok upload: {Path(video_path).name}")

            # Use TiktokAutoUploader CLI
            uploader_dir = Path("TiktokAutoUploader")
            cli_script = uploader_dir / "cli.py"

            if not cli_script.exists():
                self.log("   WARNING: TiktokAutoUploader not found, skipping")
                return False

            # TikTok CLI expects: python cli.py upload -u <username> -v <video> -t <title>
            # We need to have logged in first with: python cli.py login -n <username>

            # Check if cookies exist (TikTok uses CookiesDir, not cookies)
            cookies_dir = uploader_dir / "CookiesDir"
            cookie_file = cookies_dir / "tiktok_session-followerbattlegro.cookie"
            if not cookie_file.exists():
                self.log("   WARNING: TikTok cookies not found. Run: python TiktokAutoUploader/cli.py login -n followerbattlegro")
                return False

            # Run TikTok uploader with correct arguments
            # Use absolute path for video, relative path for cli.py since we're in uploader_dir
            cmd = [
                sys.executable,
                "cli.py",  # Just the filename since cwd is set to uploader_dir
                "upload",
                "-u", "followerbattlegro",
                "-v", str(Path(video_path).resolve()),  # Absolute path to video
                "-t", caption[:100]  # TikTok title has char limit
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',  # Replace encoding errors instead of crashing
                timeout=600,
                cwd=str(uploader_dir)
            )

            if result.returncode == 0:
                self.log("   SUCCESS: TikTok upload successful")
                return True
            else:
                # Show first 500 chars of error
                error_msg = result.stderr[:500] if result.stderr else result.stdout[:500]
                self.log(f"   WARNING: TikTok upload failed (non-critical): {error_msg}")
                return False

        except subprocess.TimeoutExpired:
            self.log("   ERROR: TikTok upload timed out")
            return False
        except Exception as e:
            self.log(f"   WARNING: TikTok upload error (non-critical): {e}")
            return False

    def upload_videos_with_delays(self):
        """
        Upload all videos with random delays between them

        STEP 2: Upload videos one at a time
        """
        self.log("=" * 60)
        self.log("STEP 2: Uploading videos with delays")
        self.log("=" * 60)

        videos = self.get_videos_to_upload()

        if not videos:
            self.log("WARNING: No videos found to upload")
            return

        self.log(f"Found {len(videos)} videos to upload")

        for idx, (video_path, game_mode) in enumerate(videos):
            ig_done = video_path in self.state.get('videos_uploaded_instagram', [])
            tt_done = video_path in self.state.get('videos_uploaded_tiktok', [])

            if ig_done and tt_done:
                self.log(f"SKIP: {Path(video_path).name} (already uploaded to Instagram and TikTok)")
                continue

            self.log(f"\nUploading video {idx + 1}/{len(videos)}: {game_mode}")

            # Build caption
            caption = self.build_caption(game_mode, self.state['current_day'])

            # Upload to Instagram
            ig_success = False
            if ig_done:
                self.log(f"   SKIP Instagram: {Path(video_path).name} (already uploaded)")
            else:
                ig_success = self.upload_video_instagram(video_path, caption)

            # Upload to TikTok
            tt_success = False
            if tt_done:
                self.log(f"   SKIP TikTok: {Path(video_path).name} (already uploaded)")
            else:
                tt_success = self.upload_video_tiktok(video_path, caption)

            # Mark per-platform successes
            if ig_success:
                if video_path not in self.state['videos_uploaded_instagram']:
                    self.state['videos_uploaded_instagram'].append(video_path)
            if tt_success:
                if video_path not in self.state['videos_uploaded_tiktok']:
                    self.state['videos_uploaded_tiktok'].append(video_path)

            if ig_success or tt_success:
                self.save_state()

            # Log upload results
            if ig_success and tt_success:
                self.log("   SUCCESS: Uploaded to both Instagram and TikTok")
            elif ig_success:
                self.log("   SUCCESS: Uploaded to Instagram (TikTok failed)")
            elif tt_success:
                self.log("   SUCCESS: Uploaded to TikTok (Instagram failed)")
            else:
                self.log("   WARNING: Both uploads failed")

            # Delay before next upload (except for last one)
            if idx < len(videos) - 1:
                # Random delay between 2-3 hours
                delay_hours = random.uniform(2.0, 3.0)
                delay_seconds = delay_hours * 3600

                self.log(f"\nWaiting {delay_hours:.2f} hours before next upload...")
                self.log(f"   Next upload at: {(datetime.now() + timedelta(seconds=delay_seconds)).strftime('%Y-%m-%d %H:%M:%S')}")

                # Sleep in chunks to allow interruption
                chunk_size = 60  # 1 minute chunks
                chunks = int(delay_seconds / chunk_size)
                for i in range(chunks):
                    time.sleep(chunk_size)
                    if (i + 1) % 10 == 0:  # Log every 10 minutes
                        remaining = (chunks - i - 1) * chunk_size / 60
                        self.log(f"   {remaining:.0f} minutes remaining...")

                # Sleep remaining seconds
                time.sleep(delay_seconds % chunk_size)

        self.log("\nSUCCESS: All videos uploaded!")

    def post_story_after_videos(self):
        """
        STEP 2.5: Post Instagram story 2 hours after video uploads

        Shows top 3 daily performers with branded template
        """
        self.log("=" * 60)
        self.log("STEP 2.5: Posting Instagram story")
        self.log("=" * 60)

        # Check if story already posted
        if self.state.get('story_posted_today', False):
            self.log("Story already posted today, skipping")
            return

        # Check if enabled in config
        if not config.ENABLE_STORY_POSTING:
            self.log("Story posting disabled in config, skipping")
            return

        try:
            # Wait configured delay hours
            self.log(f"Waiting {config.STORY_DELAY_HOURS} hours before posting story...")
            delay_seconds = config.STORY_DELAY_HOURS * 3600
            chunk_size = 60  # 1-minute chunks for interruptibility
            chunks = int(delay_seconds / chunk_size)

            for i in range(chunks):
                time.sleep(chunk_size)
                if (i + 1) % 20 == 0:  # Log every 20 minutes
                    remaining = (chunks - i - 1) * chunk_size / 60
                    self.log(f"   {remaining:.0f} minutes remaining...")

            # Generate story image
            self.log("Generating story image...")
            story_path = f"story_day_{self.state['current_day']}.png"

            if not generate_story_image(self.state['current_day'], story_path):
                self.log("ERROR: Failed to generate story image")
                return

            self.log(f"Story image generated: {story_path}")

            # Get top 3 usernames for tagging
            from instagram_story_generator import get_top_3_daily_performers
            top_3 = get_top_3_daily_performers(self.state['current_day'])
            usernames_to_tag = [performer['username'] for performer in top_3] if top_3 else []

            if usernames_to_tag:
                self.log(f"Will tag {len(usernames_to_tag)} users: {', '.join(usernames_to_tag)}")

            # Upload story
            self.log("Uploading story to Instagram...")
            uploader = SafeInstagramUploader(headless=True)

            if not uploader.upload_story(story_path, usernames_to_tag=usernames_to_tag):
                self.log("WARNING: Story upload failed")
                return

            # Mark success
            self.state['story_posted_today'] = True
            self.save_state()
            self.log("SUCCESS: Story posted successfully!")

        except Exception as e:
            self.log(f"ERROR: Story posting failed: {e}")
            traceback.print_exc()

    def wait_until_next_day(self):
        """
        Wait until 6 AM next day to fetch fresh followers
        If current time is between 6 AM and 11 AM, proceed immediately

        STEP 3: Wait until next day (6 AM)
        """
        self.log("=" * 60)
        self.log("STEP 3: Waiting until 6 AM to fetch new followers")
        self.log("=" * 60)

        now = datetime.now()

        # Check if current time is between 6 AM and 11 AM
        if 6 <= now.hour < 11:
            self.log(f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
            self.log("Time is between 6 AM and 11 AM - proceeding immediately!")
            return

        # Calculate next 6 AM
        target_time = now.replace(hour=6, minute=0, second=0, microsecond=0)

        # If it's already past 6 AM today, target tomorrow's 6 AM
        if now.hour >= 6:
            target_time += timedelta(days=1)

        wait_seconds = (target_time - now).total_seconds()

        self.log(f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        self.log(f"Target time: {target_time.strftime('%Y-%m-%d %H:%M:%S')} (6 AM)")
        self.log(f"Waiting {wait_seconds / 3600:.2f} hours...")

        # Sleep in chunks
        chunk_size = 300  # 5 minute chunks
        chunks = int(wait_seconds / chunk_size)
        for i in range(chunks):
            time.sleep(chunk_size)
            if (i + 1) % 12 == 0:  # Log every hour
                remaining_hours = (chunks - i - 1) * chunk_size / 3600
                self.log(f"   {remaining_hours:.1f} hours until 6 AM...")

        # Sleep remaining seconds
        time.sleep(wait_seconds % chunk_size)

        self.log("SUCCESS: 6 AM reached - ready to fetch fresh followers!")

    def fetch_fresh_followers(self):
        """
        Run safe HTML follower scraper to get fresh follower list

        STEP 4: Fetch fresh followers
        """
        self.log("=" * 60)
        self.log("STEP 4: Fetching fresh follower list")
        self.log("=" * 60)

        try:
            cmd = [sys.executable, "safe_html_follower_scraper.py"]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',  # Replace problematic characters instead of crashing
                timeout=3600  # 1 hour timeout
            )

            if result.returncode == 0:
                self.log("SUCCESS: Follower scraping successful")
                # Output will show "Saved to followers_safe_YYYYMMDD.json"
                self.log(result.stdout[-200:])  # Show last 200 chars
                return True
            else:
                self.log(f"ERROR: Follower scraping failed: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            self.log("ERROR: Follower scraping timed out")
            return False
        except Exception as e:
            self.log(f"ERROR: Follower scraping error: {e}")
            return False

    def run_games_to_generate_videos(self):
        """
        Run main.py to generate all game videos

        STEP 5: Run games
        """
        self.log("=" * 60)
        self.log("STEP 5: Running games to generate videos")
        self.log("=" * 60)

        # Increment day number
        self.state['current_day'] += 1
        self.save_state()

        # Update config.py with new day number
        self.update_config_day_number(self.state['current_day'])

        try:
            cmd = [sys.executable, "main.py"]

            self.log(f"Running games for Day {self.state['current_day']}...")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',  # Replace problematic characters instead of crashing
                timeout=7200  # 2 hour timeout
            )

            if result.returncode == 0:
                self.log("SUCCESS: Games completed successfully")
                # Reset uploaded videos list for new day
                self.state['videos_uploaded_today'] = []
                self.state['videos_uploaded_instagram'] = []
                self.state['videos_uploaded_tiktok'] = []
                self.state['story_posted_today'] = False  # Reset story flag for new day
                self.state['last_game_run_date'] = datetime.now().isoformat()
                self.save_state()
                return True
            else:
                self.log(f"ERROR: Games failed: {result.stderr[-500:]}")
                return False

        except subprocess.TimeoutExpired:
            self.log("ERROR: Game execution timed out")
            return False
        except Exception as e:
            self.log(f"ERROR: Game execution error: {e}")
            traceback.print_exc()
            return False

    def update_config_day_number(self, new_day: int):
        """Update DAY_NUMBER in config.py"""
        config_path = Path("config.py")

        if not config_path.exists():
            self.log("WARNING: config.py not found, cannot update day number")
            return

        # Read config
        with open(config_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Update DAY_NUMBER line
        for i, line in enumerate(lines):
            if line.strip().startswith('DAY_NUMBER ='):
                lines[i] = f'DAY_NUMBER = {new_day}  # Increment this each time you record a new video\n'
                break

        # Write back
        with open(config_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)

        self.log(f"SUCCESS: Updated config.py: DAY_NUMBER = {new_day}")

    def run_daily_cycle(self):
        """
        Run one complete daily cycle

        Returns:
            True if cycle completed successfully
        """
        self.log("\n" + "=" * 60)
        self.log(f"STARTING DAILY CYCLE - Day {self.state['current_day']}")
        self.log("=" * 60)

        try:
            # Step 1: Push stats to GitHub
            self.push_stats_to_github()

            # Step 2: Upload videos with delays
            self.upload_videos_with_delays()

            # Step 2.5: Post story after uploads
            self.post_story_after_videos()

            # Step 3: Wait until next day
            self.wait_until_next_day()

            # Step 4: Fetch fresh followers
            if not self.fetch_fresh_followers():
                self.log("WARNING: Follower fetch failed, continuing anyway...")

            # Step 5: Run games to generate new videos
            if not self.run_games_to_generate_videos():
                self.log("ERROR: Game generation failed, stopping cycle")
                return False

            self.log("\nSUCCESS: DAILY CYCLE COMPLETED SUCCESSFULLY")
            return True

        except KeyboardInterrupt:
            self.log("\nWARNING: Cycle interrupted by user")
            raise
        except Exception as e:
            self.log(f"\nERROR: Cycle error: {e}")
            traceback.print_exc()
            return False

    def run_infinite_loop(self):
        """
        Run infinite daily cycles

        This is the main entry point for continuous automation
        """
        self.log("=" * 60)
        self.log("DAILY AUTOMATION LOOP STARTED")
        self.log("=" * 60)
        self.log("This will run continuously. Press Ctrl+C to stop.")

        cycle_count = 0

        try:
            while True:
                cycle_count += 1
                self.log(f"\n{'=' * 60}")
                self.log(f"CYCLE #{cycle_count}")
                self.log(f"{'=' * 60}")

                success = self.run_daily_cycle()

                if not success:
                    self.log(f"\nWARNING: Cycle #{cycle_count} failed, waiting 1 hour before retry...")
                    time.sleep(3600)

        except KeyboardInterrupt:
            self.log("\nWARNING: Automation loop stopped by user")
            self.log(f"Total cycles completed: {cycle_count}")


def main():
    """Main entry point"""
    print("=" * 60)
    print("DAILY AUTOMATION LOOP")
    print("=" * 60)
    print()
    print("This will run the complete automation cycle:")
    print("1. Push stats to GitHub")
    print("2. Upload videos (with 2-3 hour delays)")
    print("3. Wait until 6 AM next day")
    print("4. Fetch fresh followers at 6 AM")
    print("5. Run games to generate new videos")
    print("6. Loop back to step 1")
    print()
    print("Press Ctrl+C to stop at any time.")
    print()

    input("Press Enter to start automation loop...")

    loop = DailyAutomationLoop()
    loop.run_infinite_loop()


if __name__ == "__main__":
    main()
