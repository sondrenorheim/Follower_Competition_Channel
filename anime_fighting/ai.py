"""
AI Combat System for Anime Fighting

Implements intelligent bot behavior for 1v1 matches:
- Distance management (approach/retreat/strafe)
- Defensive reactions (roll/block when threatened)
- Random attack selection with varied patterns
- Ranged pressure (ki shots)
- Dynamic combo variations
"""

import random
import pygame

from .combat import safe_normalize


def bot_brain(me, other, dt: float, match_time: float):
    """
    AI decision-making for one fighter

    Args:
        me: AnimeFighter instance (bot)
        other: AnimeFighter instance (opponent)
        dt: Delta time
        match_time: Current match time
    """
    if not me.is_alive():
        me.acc.update(0, 0)
        return

    to_other = other.pos - me.pos
    dist = to_other.length()
    dir_to_other = safe_normalize(to_other, me.facing)
    me.facing = dir_to_other

    # Aggressive movement - always moving, circling, approaching
    strafe = pygame.Vector2(-dir_to_other.y, dir_to_other.x)
    strafe *= (1.0 if random.random() < 0.5 else -1.0)

    # Dynamic distance preference - randomly vary desired distance
    desired = random.uniform(80.0, 130.0)
    approach = dist > desired
    retreat = dist < 50  # Only retreat when very close

    # Calculate movement vector - always moving!
    move_vec = pygame.Vector2(0, 0)
    if approach:
        move_vec += dir_to_other * 1.5  # Stronger approach
    elif retreat:
        move_vec -= dir_to_other * 0.8  # Weaker retreat
    else:
        # Circle around opponent when in range
        move_vec += strafe

    # Strong strafing even when approaching
    move_vec += strafe * 1.2

    # Add jitter for dynamic movement
    move_vec += pygame.Vector2(random.uniform(-0.6, 0.6), random.uniform(-0.6, 0.6))

    if move_vec.length_squared() > 0:
        move_vec = move_vec.normalize()

    me.acc = move_vec

    # Final Smash - highest priority attack
    if me.final_smash_ready and me.can_use("FS_TELEPORT"):
        # Randomly choose one of three Final Smash types
        fs_type = random.choice(["FS_TELEPORT", "FS_SINGLE", "FS_AOE"])
        me.start(fs_type, dir_to_other)
        me.final_smash_ready = False    # Consume the charge
        me.final_smash_meter = 0.0      # Reset meter
        me.final_smash_cooldown = 2.0   # 2s cooldown before next charge
        return

    # Defense reactions
    under_threat = dist < 120 and other.state in ("windup", "active")

    if under_threat and me.can_use("ROLL") and random.random() < 0.55:
        me.start("ROLL", -dir_to_other)
        return

    if under_threat and me.can_use("BLOCK") and random.random() < 0.45:
        me.start("BLOCK", dir_to_other)
        return

    # Ranged pressure
    if 220 < dist < 520 and me.can_use("SHOT") and random.random() < 0.28:
        me.start("SHOT", dir_to_other)
        return

    # Anti-projectile / AOE
    if dist < 190 and me.can_use("CUT") and random.random() < 0.16:
        me.start("CUT", dir_to_other)
        return

    # Flash step (dash to close distance) - much more aggressive
    if dist > 180 and me.can_use("DASH") and random.random() < 0.70:
        me.start("DASH", dir_to_other)
        return

    # Combo "hit confirm"
    recently_landed = (match_time - me.last_hit_time) < 0.55

    # Expanded attack range and higher aggression
    if dist < 140:
        # Execute buffered combo
        if me.combo_buffer and me.can_use(me.combo_buffer) and random.random() < 0.90:
            me.start(me.combo_buffer, dir_to_other)
            me.combo_buffer = None
            return

        # Start L1→L2 combo - much more likely
        if me.can_use("L1") and random.random() < (0.85 if recently_landed else 0.70):
            me.start("L1", dir_to_other)
            me.combo_buffer = "L2"
            return

        # Start H1→FIN combo - more aggressive
        if me.can_use("H1") and random.random() < (0.75 if recently_landed else 0.50):
            me.start("H1", dir_to_other)
            me.combo_buffer = "FIN"
            return

        # Finisher if recent hit - more likely
        if me.can_use("FIN") and recently_landed and random.random() < 0.70:
            me.start("FIN", dir_to_other)
            me.combo_buffer = None
            return
