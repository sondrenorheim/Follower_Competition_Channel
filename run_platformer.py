#!/usr/bin/env python3
"""
Run the Platformer Race Game

Quick runner script for the platformer race.
"""

import sys
import os

# Fix Windows console encoding
if os.name == 'nt':
    try:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
    except:
        pass

# Import and run
from platformer_race import PlatformerRaceGame
import config

if __name__ == "__main__":
    print("Starting Platformer Race...")
    print(f"Video Export: {config.EXPORT_VIDEO}")
    print(f"Follower Count: {config.FOLLOWER_COUNT}")
    print()

    game = PlatformerRaceGame()
    game.start_game()

    # Export video if enabled
    if config.EXPORT_VIDEO:
        game.export_video()
