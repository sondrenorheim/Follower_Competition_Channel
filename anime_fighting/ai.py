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


DEBUG_AI = True  # Set to False to disable logging

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

    # Debug logging - only print occasionally to avoid spam
    if DEBUG_AI and random.random() < 0.02:  # ~2% of frames
        print(f"[AI {me.username[:8]}] state={me.state}, dist={dist:.0f}, attack={me.attack.key if me.attack else None}")

    # Desperation mode - more aggressive when low HP
    is_desperate = getattr(me, 'is_desperate', False)
    aggression_mult = 1.3 if is_desperate else 1.0

    # Aggressive movement - always moving, circling, approaching
    strafe = pygame.Vector2(-dir_to_other.y, dir_to_other.x)
    strafe *= (1.0 if random.random() < 0.5 else -1.0)

    # Dynamic distance preference - closer when desperate
    desired = random.uniform(60.0, 100.0) if is_desperate else random.uniform(80.0, 130.0)
    approach = dist > desired
    retreat = dist < 50 and not is_desperate  # Desperate fighters don't retreat

    # Calculate movement vector - always moving!
    move_vec = pygame.Vector2(0, 0)
    if approach:
        move_vec += dir_to_other * (1.8 if is_desperate else 1.5)  # Even stronger approach when desperate
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

    # Defense reactions (less likely when desperate - fight or die!)
    under_threat = dist < 120 and other.state in ("windup", "active")
    defense_chance = 0.3 if is_desperate else 1.0  # 30% defense when desperate

    if under_threat and random.random() < defense_chance:
        if me.can_use("ROLL") and random.random() < 0.55:
            me.start("ROLL", -dir_to_other)
            return

        if me.can_use("BLOCK") and random.random() < 0.45:
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

    # Flash step (dash to close distance) - even more aggressive when desperate
    dash_chance = 0.85 if is_desperate else 0.70
    if dist > 180 and me.can_use("DASH") and random.random() < dash_chance:
        me.start("DASH", dir_to_other)
        return

    # Combo "hit confirm"
    recently_landed = (match_time - me.last_hit_time) < 0.55

    # === MELEE COMBAT ZONE ===
    # When close enough to attack, ALWAYS try to attack
    if dist < 140:
        # Debug: Log why we can't attack
        if DEBUG_AI and random.random() < 0.05:
            can_use_attacks = {atk: me.can_use(atk) for atk in ["L1", "H1", "L2", "FIN", "CUT", "DASH"]}
            print(f"[AI {me.username[:8]}] MELEE ZONE: state={me.state}, can_use={can_use_attacks}")

        # Execute buffered combo first (high priority)
        if me.combo_buffer and me.can_use(me.combo_buffer):
            if DEBUG_AI:
                print(f"[AI {me.username[:8]}] Using buffered combo: {me.combo_buffer}")
            me.start(me.combo_buffer, dir_to_other)
            me.combo_buffer = None
            return

        # Direct finisher if recently landed a hit
        if me.can_use("FIN") and recently_landed:
            if DEBUG_AI:
                print(f"[AI {me.username[:8]}] Using FIN (recently landed)")
            me.start("FIN", dir_to_other)
            me.combo_buffer = None
            return

        # === GUARANTEED ATTACK - Try attacks in priority order ===
        # This ensures fighters ALWAYS attack when in range and able
        attack_priority = ["L1", "H1", "L2", "FIN", "CUT"]
        for attack in attack_priority:
            if me.can_use(attack):
                if DEBUG_AI:
                    print(f"[AI {me.username[:8]}] Starting attack: {attack}")
                me.start(attack, dir_to_other)
                # Set up combo follow-up
                if attack == "L1":
                    me.combo_buffer = "L2"
                elif attack in ("L2", "H1"):
                    me.combo_buffer = "FIN"
                return

        # If no attacks available but we can dash, dash in to pressure
        if me.can_use("DASH") and dist > 60:
            if DEBUG_AI:
                print(f"[AI {me.username[:8]}] Dashing to pressure")
            me.start("DASH", dir_to_other)
            me.combo_buffer = random.choice(["L1", "H1"])
            return

        # Debug: If we reach here, no action was taken in melee range
        if DEBUG_AI and random.random() < 0.1:
            print(f"[AI {me.username[:8]}] WARNING: In melee range but NO ACTION taken! state={me.state}")
