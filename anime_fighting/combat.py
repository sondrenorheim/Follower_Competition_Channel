"""
Combat System for Anime Fighting Game

Defines all combat mechanics: attack specifications, hitboxes, projectiles,
and combat resolution logic.
"""

import math
import random
from dataclasses import dataclass, field
from typing import List, Set, Tuple, Optional

import pygame


# ============================================================
# Combat Data Structures
# ============================================================

@dataclass
class AttackSpec:
    """Specification for a single attack move"""
    key: str
    name: str
    windup: float
    active: float
    recovery: float
    radius: float
    range: float
    damage: float
    knockback: float
    hitstun: float
    cooldown: float

    cancel_after: float = 0.0
    cancel_before_end: float = 0.0
    next_keys: Tuple[str, ...] = ()

    spawns_projectile: bool = False
    anti_projectile: bool = False
    impulse: float = 0.0

    # Final Smash properties
    bypasses_invuln: bool = False

    # on-hit FX
    hitstop: float = 0.0
    zoom_punch: float = 0.0
    zoom_hold: float = 0.0


@dataclass
class HitShape:
    """Melee hitbox that follows the owner"""
    owner_id: int
    center: pygame.Vector2
    radius: float
    damage: float
    knockback: float
    hitstun: float
    ttl: float
    follow_owner: bool
    range_offset: float

    # on-hit FX
    hitstop: float
    zoom_punch: float
    zoom_hold: float

    bypasses_invuln: bool = False

    already_hit: Set[int] = field(default_factory=set)


@dataclass
class Projectile:
    """Ranged projectile attack"""
    owner_id: int
    pos: pygame.Vector2
    vel: pygame.Vector2
    radius: float
    damage: float
    knockback: float
    hitstun: float
    ttl: float

    hitstop: float
    zoom_punch: float
    zoom_hold: float

    bypasses_invuln: bool = False

    already_hit: Set[int] = field(default_factory=set)


# ============================================================
# Hit-stop tuning (seconds)
# ============================================================
HITSTOP_LIGHT = 0.028
HITSTOP_HEAVY = 0.040
HITSTOP_FINISH = 0.062
HITSTOP_PROJECTILE = 0.030

# Zoom punch tuning
ZOOM_PUNCH_DEFAULT = 1.14
ZOOM_PUNCH_HEAVY = 1.16
ZOOM_PUNCH_FINISH = 1.22
ZOOM_HOLD_DEFAULT = 0.10
ZOOM_HOLD_HEAVY = 0.12
ZOOM_HOLD_FINISH = 0.16


# ============================================================
# Attack Library
# ============================================================
ATTACKS = {
    # Combo chain
    "L1": AttackSpec(
        key="L1", name="Light 1",
        windup=0.045, active=0.070, recovery=0.085,
        radius=30, range=62,
        damage=6, knockback=230, hitstun=0.16,
        cooldown=0.08,
        cancel_after=0.02, cancel_before_end=0.05,
        next_keys=("L2", "DASH", "ROLL"),
        hitstop=HITSTOP_LIGHT, zoom_punch=ZOOM_PUNCH_DEFAULT, zoom_hold=ZOOM_HOLD_DEFAULT
    ),
    "L2": AttackSpec(
        key="L2", name="Light 2",
        windup=0.040, active=0.070, recovery=0.095,
        radius=32, range=68,
        damage=7, knockback=260, hitstun=0.17,
        cooldown=0.10,
        cancel_after=0.02, cancel_before_end=0.06,
        next_keys=("H1", "DASH", "ROLL"),
        hitstop=HITSTOP_LIGHT, zoom_punch=ZOOM_PUNCH_DEFAULT, zoom_hold=ZOOM_HOLD_DEFAULT
    ),
    "H1": AttackSpec(
        key="H1", name="Heavy",
        windup=0.070, active=0.090, recovery=0.120,
        radius=40, range=78,
        damage=12, knockback=390, hitstun=0.22,
        cooldown=0.22,
        cancel_after=0.03, cancel_before_end=0.05,
        next_keys=("FIN", "DASH"),
        hitstop=HITSTOP_HEAVY, zoom_punch=ZOOM_PUNCH_HEAVY, zoom_hold=ZOOM_HOLD_HEAVY
    ),
    "FIN": AttackSpec(
        key="FIN", name="Finisher",
        windup=0.085, active=0.100, recovery=0.160,
        radius=58, range=74,
        damage=18, knockback=560, hitstun=0.28,
        cooldown=0.45,
        impulse=420,
        hitstop=HITSTOP_FINISH, zoom_punch=ZOOM_PUNCH_FINISH, zoom_hold=ZOOM_HOLD_FINISH
    ),

    # Defense / mobility
    "BLOCK": AttackSpec(
        key="BLOCK", name="Block",
        windup=0.00, active=0.12, recovery=0.00,
        radius=0, range=0, damage=0, knockback=0, hitstun=0,
        cooldown=0.0
    ),
    "ROLL": AttackSpec(
        key="ROLL", name="Roll (i-frames)",
        windup=0.00, active=0.16, recovery=0.06,
        radius=0, range=0, damage=0, knockback=0, hitstun=0,
        cooldown=0.35,
        impulse=720
    ),
    "DASH": AttackSpec(
        key="DASH", name="Flash Step",
        windup=0.00, active=0.10, recovery=0.05,
        radius=0, range=0, damage=0, knockback=0, hitstun=0,
        cooldown=0.18,
        impulse=820
    ),

    # Ranged + anti-ranged
    "SHOT": AttackSpec(
        key="SHOT", name="Ki Shot",
        windup=0.060, active=0.040, recovery=0.090,
        radius=0, range=0, damage=0, knockback=0, hitstun=0,
        cooldown=0.35,
        spawns_projectile=True,
        cancel_after=0.02, cancel_before_end=0.03,
        next_keys=("DASH",),
    ),
    "CUT": AttackSpec(
        key="CUT", name="Projectile Cut",
        windup=0.055, active=0.120, recovery=0.110,
        radius=92, range=0,
        damage=10, knockback=320, hitstun=0.20,
        cooldown=0.70,
        anti_projectile=True,
        cancel_after=0.03, cancel_before_end=0.04,
        next_keys=("DASH",),
        hitstop=HITSTOP_HEAVY, zoom_punch=1.15, zoom_hold=ZOOM_HOLD_HEAVY
    ),

    # Final Smash attacks - unavoidable, high damage, dramatic effects
    "FS_TELEPORT": AttackSpec(
        key="FS_TELEPORT",
        name="Final Smash: Rapid Assault",
        windup=0.15,
        active=4.0,        # Total duration for 10-15 teleports (extended)
        recovery=0.8,
        radius=50,
        range=0,           # Melee (teleports to target)
        damage=0,          # Damage applied per teleport hit
        knockback=800,     # Final knockback at end
        hitstun=0.5,       # Stun between teleports
        cooldown=999,      # Prevent re-use (managed by meter system)
        bypasses_invuln=True,
        hitstop=0.08,      # Dramatic freeze on each hit
        zoom_punch=1.24,
        zoom_hold=0.12
    ),

    "FS_SINGLE": AttackSpec(
        key="FS_SINGLE",
        name="Final Smash: Kamehameha Beam",
        windup=1.2,        # Extended charge-up animation
        active=1.5,        # Extended beam duration
        recovery=0.8,
        radius=60,
        range=80,
        damage=0,          # Calculated as 35% max HP
        knockback=1200,    # Extreme knockback
        hitstun=1.0,
        cooldown=999,
        bypasses_invuln=True,
        impulse=0,         # No dash - stationary beam attack
        hitstop=0.12,      # Long freeze frame
        zoom_punch=1.30,   # Dramatic zoom
        zoom_hold=0.20
    ),

    "FS_AOE": AttackSpec(
        key="FS_AOE",
        name="Final Smash: Energy Burst",
        windup=0.6,        # Charge time
        active=0.3,        # Explosion duration
        recovery=0.9,
        radius=200,        # Large AOE
        range=0,
        damage=0,          # Calculated as 35% max HP
        knockback=700,
        hitstun=0.8,
        cooldown=999,
        bypasses_invuln=True,
        anti_projectile=True,   # Destroys incoming projectiles
        hitstop=0.10,
        zoom_punch=1.26,
        zoom_hold=0.18
    ),
}


# ============================================================
# Combat Helper Functions
# ============================================================

def safe_normalize(v: pygame.Vector2, fallback: pygame.Vector2 = pygame.Vector2(1, 0)) -> pygame.Vector2:
    """Safely normalize a vector, returning fallback if zero length"""
    if v.length_squared() <= 1e-8:
        return pygame.Vector2(fallback)
    return v.normalize()


def circle_overlap(a_pos: pygame.Vector2, a_r: float, b_pos: pygame.Vector2, b_r: float) -> bool:
    """Check if two circles overlap"""
    return (a_pos - b_pos).length_squared() <= (a_r + b_r) ** 2


def spawn_sparks(
    particles: List,  # List[Particle] (defined in camera_fx.py)
    pos: pygame.Vector2,
    facing: pygame.Vector2,
    count: int,
    color: Tuple[int, int, int],
    speed: float,
    max_particles: int = 1400
):
    """
    Spawn particle effects at position

    Args:
        particles: List to append particles to
        pos: Spawn position
        facing: Direction to spray particles
        count: Number of particles
        color: RGB color
        speed: Initial particle velocity
        max_particles: Maximum particle count (performance limit)
    """
    if len(particles) > max_particles:
        return

    from .camera_fx import Particle  # Import here to avoid circular dependency

    base = safe_normalize(facing, pygame.Vector2(1, 0))
    for _ in range(count):
        ang = random.uniform(-0.9, 0.9)
        rot = pygame.Vector2(
            base.x * math.cos(ang) - base.y * math.sin(ang),
            base.x * math.sin(ang) + base.y * math.cos(ang),
        )
        v = rot * random.uniform(speed * 0.35, speed)
        particles.append(
            Particle(
                pos=pygame.Vector2(pos),
                vel=v,
                life=random.uniform(0.08, 0.22),
                radius=random.uniform(1.6, 3.2),
                color=color,
                drag=random.uniform(9.0, 15.0),
            )
        )


def separate_fighters(fighter_a, fighter_b):
    """
    Push apart overlapping fighters

    Args:
        fighter_a: AnimeFighter instance
        fighter_b: AnimeFighter instance
    """
    delta = fighter_b.pos - fighter_a.pos
    dist = delta.length()
    min_d = fighter_a.radius + fighter_b.radius + 2

    if dist <= 1e-6 or dist >= min_d:
        return

    push = (min_d - dist) * 0.5
    n = delta.normalize()
    fighter_a.pos -= n * push
    fighter_b.pos += n * push
    fighter_a.vel -= n * 45
    fighter_b.vel += n * 45


def update_hitshapes(hitshapes: List[HitShape], dt: float, fighters: List):
    """
    Update all active hitshapes

    Args:
        hitshapes: List of HitShape instances
        dt: Delta time
        fighters: List of all fighters (for owner position tracking)
    """
    id_map = {f.id: f for f in fighters}

    for h in hitshapes:
        h.ttl -= dt
        if h.follow_owner and h.owner_id in id_map:
            owner = id_map[h.owner_id]
            h.center = owner.pos + owner.facing * h.range_offset

    # Remove expired hitshapes
    hitshapes[:] = [h for h in hitshapes if h.ttl > 0]


def update_projectiles(projectiles: List[Projectile], dt: float, arena: pygame.Rect, particles: List):
    """
    Update all active projectiles

    Args:
        projectiles: List of Projectile instances
        dt: Delta time
        arena: Arena boundaries
        particles: Particle list for trail effects
    """
    from .camera_fx import Particle  # Import here to avoid circular dependency

    for pr in projectiles:
        pr.ttl -= dt
        pr.pos += pr.vel * dt

        # Add trailing particles
        if random.random() < 0.45:
            particles.append(
                Particle(
                    pos=pygame.Vector2(pr.pos),
                    vel=pygame.Vector2(random.uniform(-40, 40), random.uniform(-40, 40)),
                    life=random.uniform(0.05, 0.12),
                    radius=random.uniform(1.2, 2.2),
                    color=(230, 230, 250),
                    drag=12.0,
                )
            )

        # Remove if out of bounds
        if not arena.collidepoint(pr.pos.x, pr.pos.y):
            pr.ttl = -1

    # Remove expired projectiles
    projectiles[:] = [p for p in projectiles if p.ttl > 0]


def resolve_hits(
    hitshapes: List[HitShape],
    projectiles: List[Projectile],
    fighters: List,
    particles: List,
    camera_fx,  # CameraFX instance
    match_time: float,
    sound=None  # SoundManager instance (optional)
):
    """
    Resolve all combat collisions

    Args:
        hitshapes: Active melee hitboxes
        projectiles: Active projectiles
        fighters: All fighters in match
        particles: Particle list for hit effects
        camera_fx: CameraFX instance for screen effects
        match_time: Current match time
        sound: SoundManager instance for hit sounds (optional)
    """
    # Melee/AOE hits
    for h in hitshapes:
        for f in fighters:
            if not f.is_alive() or f.id == h.owner_id:
                continue
            if f.id in h.already_hit:
                continue

            if circle_overlap(h.center, h.radius, f.pos, f.radius):
                knock_dir = safe_normalize(
                    f.pos - h.center,
                    pygame.Vector2(random.uniform(-1, 1), random.uniform(-1, 1)),
                )

                # Track hit for owner
                owner = next((x for x in fighters if x.id == h.owner_id), None)
                if owner:
                    owner.last_hit_time = match_time

                f.take_hit(h.damage, knock_dir * h.knockback, h.hitstun, bypasses_invuln=h.bypasses_invuln)
                h.already_hit.add(f.id)

                # FX: hit-stop + zoom punch centered on victim
                if h.hitstop > 0:
                    camera_fx.trigger_hitstop(h.hitstop)
                if h.zoom_punch > 0:
                    camera_fx.trigger_zoom_punch(f.pos, h.zoom_punch, h.zoom_hold)
                camera_fx.add_shake(4.5)

                # Sound effects based on damage
                if sound:
                    if h.damage >= 15:
                        sound.play_finisher_hit()
                    elif h.damage >= 10:
                        sound.play_heavy_hit()
                    else:
                        sound.play_light_hit()

                spawn_sparks(particles, f.pos, -knock_dir, 18, (255, 255, 255), 720)

    # Anti-projectile fields remove enemy projectiles
    anti_fields = [h for h in hitshapes if h.radius >= 80]  # CUT is 92
    if anti_fields:
        for af in anti_fields:
            kept = []
            for pr in projectiles:
                if pr.owner_id == af.owner_id:
                    kept.append(pr)
                    continue
                if (pr.pos - af.center).length_squared() <= (af.radius + pr.radius) ** 2:
                    spawn_sparks(particles, pr.pos, safe_normalize(pr.vel), 14, (200, 245, 255), 700)
                    camera_fx.add_shake(2.5)
                else:
                    kept.append(pr)
            projectiles[:] = kept

    # Projectile hits
    for pr in projectiles:
        for f in fighters:
            if not f.is_alive() or f.id == pr.owner_id:
                continue
            if f.id in pr.already_hit:
                continue

            if circle_overlap(pr.pos, pr.radius, f.pos, f.radius):
                knock_dir = safe_normalize(pr.vel)

                # Track hit for owner
                owner = next((x for x in fighters if x.id == pr.owner_id), None)
                if owner:
                    owner.last_hit_time = match_time

                f.take_hit(pr.damage, knock_dir * pr.knockback, pr.hitstun, bypasses_invuln=pr.bypasses_invuln)
                pr.already_hit.add(f.id)
                pr.ttl = -1

                camera_fx.trigger_hitstop(pr.hitstop)
                camera_fx.trigger_zoom_punch(f.pos, pr.zoom_punch, pr.zoom_hold)
                camera_fx.add_shake(4.0)

                # Projectile impact sound
                if sound:
                    sound.play_ki_blast_hit()

                spawn_sparks(particles, f.pos, -knock_dir, 20, (245, 245, 255), 820)
