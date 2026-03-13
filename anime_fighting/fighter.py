"""
Anime Fighter Character

Extends the base Follower class with anime-style combat mechanics:
combos, stamina, blocking, dashing, and special moves.
"""

from typing import Tuple, Optional, List
import pygame
import math
import random
from PIL import Image

from battle_royale.follower import Follower
from shared.avatar_initials import draw_avatar_initials
from .combat import ATTACKS, AttackSpec, HitShape, Projectile, spawn_sparks
from .camera_fx import AfterImage, AFTERIMAGE_INTERVAL, AFTERIMAGE_LIFETIME

# Final Smash meter charge rates
FS_CHARGE_PER_SECOND = 3.0           # Base: 3% per second (33 seconds to full)
FS_CHARGE_PER_HIT_TAKEN = 8.0        # Bonus: +8% when taking damage
FS_DAMAGE_PERCENT = 0.35             # 35% of max HP (between 30-40% range)


class AnimeFighter(Follower):
    """
    Fighter with anime-style combat mechanics

    Extends Follower with:
    - HP and stamina systems
    - Attack state machine (windup → active → recovery)
    - Combo canceling system
    - Blocking and invulnerability frames
    - Impulse-based movement (dash, roll, finisher)
    """

    def __init__(self, follower_data: dict, position: Tuple[float, float]):
        """
        Initialize fighter

        Args:
            follower_data: Dict with 'id', 'username', 'avatar', 'color'
            position: (x, y) starting position
        """
        super().__init__(follower_data, position)

        # Override radius for 1v1 avatars (smaller for zoomed-out camera effect)
        self.radius = 24

        # Convert PIL avatar_image to pygame avatar_surface for rendering
        self.avatar_surface = None
        avatar_size = self.radius * 2
        if self.avatar_image is not None:
            try:
                self.avatar_surface = self._pil_to_pygame(self.avatar_image, avatar_size)
            except Exception as e:
                print(f"Failed to load avatar for {self.username}: {e}")
                self.avatar_surface = None
        if self.avatar_surface is None:
            self.avatar_surface = self._create_initials_avatar_surface(avatar_size)

        # Combat attributes
        self.max_hp = 280.0  # Doubled for longer, more intense matches
        self.hp = self.max_hp

        self.facing = pygame.Vector2(1, 0)

        # Final Smash meter system
        self.final_smash_meter = 0.0        # 0.0 to 100.0
        self.final_smash_ready = False       # Flag for when meter is full
        self.final_smash_cooldown = 0.0      # Time until next FS allowed (prevents spam)

        # State machine
        self.state = "idle"  # idle/move/windup/active/recovery/hitstun/dead
        self.state_t = 0.0
        self.attack: Optional[AttackSpec] = None
        self.hitstun_t = 0.0

        # Attack cooldowns (per-attack)
        self.attack_cd = {k: 0.0 for k in ATTACKS.keys()}

        # Combat flags
        self.invuln_t = 0.0
        self.is_blocking = False
        self.last_hit_time = -999.0
        self.combo_buffer: Optional[str] = None

        # Statistics tracking
        self.damage_dealt = 0.0
        self.damage_taken = 0.0
        self.attacks_landed = 0

        # Visual effects
        self.afterimage_t = 0.0

        # Desperation mode (low HP effects)
        self.is_desperate = False
        self.desperation_aura_timer = 0.0
        self._was_desperate = False  # Track state changes

        # Physics override (using pygame.Vector2 instead of separate vx, vy)
        self.vel = pygame.Vector2(0, 0)
        self.acc = pygame.Vector2(0, 0)

    def is_alive(self) -> bool:
        """Check if fighter is still alive"""
        return self.hp > 0

    def _pil_to_pygame(self, pil_image: Image.Image, size: int) -> pygame.Surface:
        """
        Convert PIL image to pygame surface

        Args:
            pil_image: PIL Image object
            size: Target size (width and height)

        Returns:
            Pygame surface with the avatar
        """
        # Resize to target size
        pil_image = pil_image.resize((size, size), Image.Resampling.LANCZOS)

        # Ensure RGBA mode for transparency
        if pil_image.mode != 'RGBA':
            pil_image = pil_image.convert('RGBA')

        # Convert to pygame surface
        mode = pil_image.mode
        img_size = pil_image.size
        data = pil_image.tobytes()

        surface = pygame.image.fromstring(data, img_size, mode).convert_alpha()

        # Crop to circle with alpha mask
        circle_surface = pygame.Surface((size, size), pygame.SRCALPHA)
        circle_surface.blit(surface, (0, 0))
        mask = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(mask, (255, 255, 255, 255), (size // 2, size // 2), size // 2)
        circle_surface.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        return circle_surface

    def _create_initials_avatar_surface(self, size: int) -> pygame.Surface:
        """Create a circular fallback avatar with username initials."""
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        center = (size // 2, size // 2)
        pygame.draw.circle(surface, self.color, center, size // 2)
        draw_avatar_initials(surface, self.username, center=center, diameter=size)
        return surface

    def get_beam_data(self) -> Optional[dict]:
        """
        Get active beam data for rendering (Kamehameha)

        Returns:
            Dict with beam_start, beam_end, beam_intensity, or None if no beam active
        """
        if hasattr(self, 'fs_kamehameha_state') and self.fs_kamehameha_state.get('beam_active'):
            state = self.fs_kamehameha_state
            if 'beam_start' in state and 'beam_end' in state:
                return {
                    'start': state['beam_start'],
                    'end': state['beam_end'],
                    'intensity': state.get('beam_intensity', 1.0),
                    'color': self.color  # Fighter's color for beam tint
                }
        return None

    def update_cooldowns(self, dt: float):
        """
        Update attack cooldowns and invulnerability

        Args:
            dt: Delta time
        """
        for k in self.attack_cd:
            self.attack_cd[k] = max(0.0, self.attack_cd[k] - dt)
        self.invuln_t = max(0.0, self.invuln_t - dt)

    def update_final_smash_meter(self, dt: float):
        """
        Charge Final Smash meter over time

        Args:
            dt: Delta time
        """
        # Cooldown for preventing immediate re-use
        if self.final_smash_cooldown > 0:
            self.final_smash_cooldown -= dt
            return  # Don't charge meter while on cooldown

        # Charge meter if not full
        if self.final_smash_meter < 100.0:
            self.final_smash_meter = min(100.0, self.final_smash_meter + FS_CHARGE_PER_SECOND * dt)
            if self.final_smash_meter >= 100.0:
                self.final_smash_ready = True

    def update_desperation_mode(self, dt: float, particles: list):
        """
        Update desperation mode status and visual effects when HP < 25%

        Creates dramatic low-HP visuals:
        - Red glowing aura particles floating upward
        - Red particle trail when moving
        - Burst of particles when first entering desperation

        Args:
            dt: Delta time
            particles: Particle list for visual effects
        """
        from .camera_fx import Particle

        hp_percent = self.hp / self.max_hp
        self._was_desperate = self.is_desperate
        self.is_desperate = hp_percent < 0.25 and self.is_alive()

        if not self.is_desperate:
            return

        # First frame entering desperation - burst of particles
        if not self._was_desperate and self.is_desperate:
            for _ in range(30):
                angle = random.uniform(0, 2 * math.pi)
                particles.append(Particle(
                    pos=pygame.Vector2(self.pos),
                    vel=pygame.Vector2(math.cos(angle) * 200, math.sin(angle) * 200),
                    life=0.5,
                    radius=random.uniform(4, 10),
                    color=(255, 100, 100)  # Red
                ))

        # Continuous aura effect
        self.desperation_aura_timer += dt
        if self.desperation_aura_timer >= 0.04:
            self.desperation_aura_timer = 0.0

            # Glowing aura particles around fighter (float upward)
            for _ in range(2):
                angle = random.uniform(0, 2 * math.pi)
                offset = pygame.Vector2(math.cos(angle) * 30, math.sin(angle) * 30)
                particles.append(Particle(
                    pos=self.pos + offset,
                    vel=pygame.Vector2(0, random.uniform(-60, -100)),  # Float upward
                    life=random.uniform(0.2, 0.4),
                    radius=random.uniform(3, 7),
                    color=(255, 80 + random.randint(0, 40), 80)  # Red/orange
                ))

            # Movement trail particles when moving
            if self.vel.length() > 100:
                particles.append(Particle(
                    pos=pygame.Vector2(self.pos),
                    vel=pygame.Vector2(random.uniform(-30, 30), random.uniform(-30, 30)),
                    life=0.15,
                    radius=random.uniform(2, 5),
                    color=(255, 60, 60)
                ))

    def can_cancel_into(self, key: str) -> bool:
        """
        Check if current attack can be canceled into another

        Args:
            key: Attack key to check

        Returns:
            True if cancel is allowed
        """
        if not self.attack:
            return False

        spec = self.attack
        if self.state not in ("windup", "active", "recovery"):
            return False

        t = self.state_t
        end = (spec.windup if self.state == "windup" else
               spec.active if self.state == "active" else
               spec.recovery)

        if end <= 1e-6:
            return False

        if t < spec.cancel_after:
            return False

        if spec.cancel_before_end > 0 and t > max(0.0, end - spec.cancel_before_end):
            return False

        # Dash/Roll can always cancel
        if key in ("DASH", "ROLL"):
            return True

        return key in spec.next_keys

    def can_use(self, key: str) -> bool:
        """
        Check if attack is available (cooldown + stamina)

        Args:
            key: Attack key

        Returns:
            True if attack can be used
        """
        if self.attack_cd.get(key, 0.0) > 0:
            return False

        return self.state in ("idle", "move") or self.can_cancel_into(key)

    def start(self, key: str, target_dir: pygame.Vector2):
        """
        Start an attack

        Args:
            key: Attack key
            target_dir: Direction to face/attack
        """
        spec = ATTACKS[key]
        self.attack_cd[key] = spec.cooldown

        if target_dir.length_squared() > 0:
            self.facing = target_dir.normalize()

        self.attack = spec
        self.state = "windup" if spec.windup > 0 else "active"
        self.state_t = 0.0
        self.is_blocking = (key == "BLOCK")

        # I-frames
        if key == "ROLL":
            self.invuln_t = spec.active
        elif key == "DASH":
            self.invuln_t = 0.05

        # Impulse for dash/roll/finisher
        if spec.impulse > 0:
            self.vel += self.facing * spec.impulse

    def take_hit(self, damage: float, knock_vec: pygame.Vector2, hitstun: float, bypasses_invuln: bool = False):
        """
        Take damage from an attack

        Args:
            damage: Damage amount
            knock_vec: Knockback vector
            hitstun: Hitstun duration
            bypasses_invuln: If True, bypasses invulnerability frames (for Final Smash)
        """
        # Allow unavoidable attacks to bypass invulnerability
        if self.invuln_t > 0 and not bypasses_invuln:
            return

        if not self.is_alive():
            return

        # Immune during Final Smash execution (can only be interrupted by another Final Smash)
        if self.attack and self.attack.key in ("FS_TELEPORT", "FS_SINGLE", "FS_AOE") and not bypasses_invuln:
            return

        # Blocking reduces damage/knockback (but not for Final Smash)
        if self.is_blocking and not bypasses_invuln:
            damage *= 0.45
            knock_vec *= 0.40
            hitstun = min(hitstun, 0.12)

        self.hp = max(0.0, self.hp - damage)
        self.vel += knock_vec
        self.damage_taken += damage

        # Charge Final Smash meter when taking damage
        if self.final_smash_meter < 100.0:
            self.final_smash_meter = min(100.0, self.final_smash_meter + FS_CHARGE_PER_HIT_TAKEN)
            if self.final_smash_meter >= 100.0:
                self.final_smash_ready = True

        if self.hp <= 0:
            self.state = "dead"
            self.attack = None
            self.is_blocking = False
            self.invuln_t = 0.0
            self.alive = False  # Mark as dead for Follower base class
            return

        # For Final Smash attacks (bypasses_invuln=True), don't override hitstun state
        # The choreography already set up the hitstun duration
        if not bypasses_invuln:
            self.state = "hitstun"
            self.state_t = 0.0
            self.hitstun_t = hitstun
            self.attack = None
            self.is_blocking = False

            # Tiny invuln to prevent instant re-hit spam
            self.invuln_t = 0.06

    def _execute_final_smash_teleport(self, spec, dt, other_fighter, particles, camera_fx, sound=None):
        """
        Choreography for FS_TELEPORT: Rapid teleporting strikes

        Timeline:
        - 0.0-0.15s: Windup (charge energy)
        - 0.15-4.15s: Active (10-15 teleport strikes) - EXTENDED
        - 4.15-4.95s: Recovery (final pose)
        """
        from .camera_fx import Particle

        if not hasattr(self, 'fs_teleport_state'):
            # Initialize choreography state
            self.fs_teleport_state = {
                'hits_remaining': random.randint(10, 15),  # Increased from 5-7 to 10-15
                'next_hit_time': 0.0,   # First hit immediately when active starts
                'hit_interval': 0.28    # Slightly faster interval (0.28 vs 0.35)
            }
            # Freeze the opponent for the entire Final Smash duration
            other_fighter.state = "hitstun"
            other_fighter.hitstun_t = spec.active + spec.recovery
            other_fighter.vel = pygame.Vector2(0, 0)

            # Trigger time slowdown (40% speed for dramatic effect)
            if camera_fx:
                total_duration = spec.windup + spec.active + spec.recovery
                camera_fx.trigger_time_slowdown(0.4, total_duration)

            # Final Smash charge-up sound
            if sound:
                sound.play_final_smash_charge()

        # During windup: Charge particles
        if self.state == "windup":
            # Spawn energy particles around self
            if random.random() < 0.3:
                particles.append(Particle(
                    pos=self.pos + pygame.Vector2(random.uniform(-30, 30), random.uniform(-30, 30)),
                    vel=pygame.Vector2(0, 0),
                    life=0.4,
                    radius=random.uniform(4, 10),
                    color=(255, 215, 0)  # Gold energy
                ))

        # During active: Teleport and strike
        elif self.state == "active":
            # Use state_t which is the time spent in active state
            if self.state_t >= self.fs_teleport_state['next_hit_time'] and \
               self.fs_teleport_state['hits_remaining'] > 0:

                # Teleport to random position around opponent
                angle = random.uniform(0, 2 * math.pi)
                distance = 40  # Close range
                target_pos = other_fighter.pos + pygame.Vector2(
                    math.cos(angle) * distance,
                    math.sin(angle) * distance
                )

                # Departure particles (purple)
                for _ in range(20):
                    particles.append(Particle(
                        pos=pygame.Vector2(self.pos),
                        vel=pygame.Vector2(random.uniform(-200, 200), random.uniform(-200, 200)),
                        life=0.4,
                        radius=random.uniform(3, 8),
                        color=(150, 100, 255)
                    ))

                # Teleport!
                self.pos = target_pos
                self.vel = pygame.Vector2(0, 0)

                # Teleport sound
                if sound:
                    sound.play_teleport()

                # Arrival particles (blue + gold)
                for _ in range(20):
                    particles.append(Particle(
                        pos=pygame.Vector2(self.pos),
                        vel=pygame.Vector2(random.uniform(-200, 200), random.uniform(-200, 200)),
                        life=0.4,
                        radius=random.uniform(3, 8),
                        color=(100, 200, 255) if random.random() < 0.5 else (255, 215, 0)
                    ))

                # Deal damage (35% max HP divided by number of hits)
                damage_per_hit = (other_fighter.max_hp * FS_DAMAGE_PERCENT) / 15  # Max 15 hits
                knock_dir = (other_fighter.pos - self.pos)
                if knock_dir.length() > 0:
                    knock_dir = knock_dir.normalize()
                else:
                    knock_dir = self.facing
                other_fighter.take_hit(damage_per_hit, knock_dir * 200, 0.15, bypasses_invuln=True)

                # Camera effects
                if camera_fx:
                    camera_fx.trigger_hitstop(0.05)
                    camera_fx.trigger_zoom_punch(other_fighter.pos, 1.18, 0.08)
                    camera_fx.add_shake(12)

                # Next hit
                self.fs_teleport_state['hits_remaining'] -= 1
                self.fs_teleport_state['next_hit_time'] += self.fs_teleport_state['hit_interval']

                # Final knockback on last hit
                if self.fs_teleport_state['hits_remaining'] == 0:
                    final_knock = knock_dir * spec.knockback
                    other_fighter.vel = final_knock
                    if camera_fx:
                        camera_fx.trigger_hitstop(0.12)
                        camera_fx.add_shake(25)
                    # Final impact sound
                    if sound:
                        sound.play_final_smash_impact()

        # Cleanup after recovery
        if self.state == "idle" and hasattr(self, 'fs_teleport_state'):
            delattr(self, 'fs_teleport_state')

    def _execute_final_smash_single(self, spec, dt, other_fighter, particles, camera_fx, sound=None):
        """
        Choreography for FS_SINGLE: Kamehameha Beam Attack

        Timeline:
        - 0.0-1.2s: Windup (dramatic charge-up with cupped hands)
        - 1.2-2.7s: Active (sustained energy beam)
        - 2.7-3.5s: Recovery (aftermath)
        """
        from .camera_fx import Particle

        # Initialize and freeze opponent
        if not hasattr(self, 'fs_kamehameha_state'):
            other_fighter.state = "hitstun"
            other_fighter.hitstun_t = spec.windup + spec.active + spec.recovery
            other_fighter.vel = pygame.Vector2(0, 0)

            self.fs_kamehameha_state = {
                'charge_intensity': 0.0,  # 0 to 1 during windup
                'beam_active': False,
                'beam_particles': [],  # Store beam segment positions
                'hit_applied': False,
                'continuous_damage_timer': 0.0,
                'damage_ticks': 0
            }

            # Trigger time slowdown (35% speed for maximum drama)
            if camera_fx:
                total_duration = spec.windup + spec.active + spec.recovery
                camera_fx.trigger_time_slowdown(0.35, total_duration)

            # Final Smash charge-up sound
            if sound:
                sound.play_final_smash_charge()

        state = self.fs_kamehameha_state

        # PHASE 1: Windup - Energy charge-up animation
        if self.state == "windup":
            # Gradually increase charge intensity
            state['charge_intensity'] = min(1.0, self.state_t / spec.windup)

            # Hands position - cupped at side (simulated)
            charge_offset = self.facing * -15  # Behind the fighter
            charge_pos = self.pos + charge_offset

            # Intensifying energy sphere particles
            spawn_chance = 0.3 + state['charge_intensity'] * 0.5  # 30% to 80%
            if random.random() < spawn_chance:
                # Converging particles toward hands
                angle = random.uniform(0, 2 * math.pi)
                distance = random.uniform(40, 80) * (1.2 - state['charge_intensity'])  # Tightens as charge builds
                start_pos = charge_pos + pygame.Vector2(
                    math.cos(angle) * distance,
                    math.sin(angle) * distance
                )
                vel_to_hands = (charge_pos - start_pos) * (3.0 + state['charge_intensity'] * 2.0)

                # Color shifts from blue to white as charge builds
                intensity = int(state['charge_intensity'] * 255)
                color = (
                    min(255, 100 + intensity // 2),
                    min(255, 150 + intensity // 2),
                    255
                )

                particles.append(Particle(
                    pos=start_pos,
                    vel=vel_to_hands,
                    life=0.6,
                    radius=random.uniform(3, 8) * (1.0 + state['charge_intensity']),
                    color=color
                ))

            # Energy sphere at hands (gets brighter)
            if random.random() < 0.7:
                particles.append(Particle(
                    pos=charge_pos + pygame.Vector2(random.uniform(-5, 5), random.uniform(-5, 5)),
                    vel=pygame.Vector2(0, 0),
                    life=0.15,
                    radius=random.uniform(8, 16) * state['charge_intensity'],
                    color=(min(255, 200 + int(55 * state['charge_intensity'])),
                           min(255, 220 + int(35 * state['charge_intensity'])),
                           255)
                ))

            # Electrical sparks near peak charge
            if state['charge_intensity'] > 0.7 and random.random() < 0.4:
                particles.append(Particle(
                    pos=charge_pos + pygame.Vector2(random.uniform(-20, 20), random.uniform(-20, 20)),
                    vel=pygame.Vector2(random.uniform(-100, 100), random.uniform(-100, 100)),
                    life=0.2,
                    radius=random.uniform(2, 5),
                    color=(255, 255, 100)  # Yellow electric
                ))

        # PHASE 2: Active - Beam firing
        elif self.state == "active":
            state['beam_active'] = True

            # Beam origin (at fighter's position, offset forward)
            beam_start = self.pos + self.facing * 25
            beam_direction = (other_fighter.pos - self.pos)
            if beam_direction.length() > 0:
                beam_direction = beam_direction.normalize()
            else:
                beam_direction = self.facing

            # Calculate beam endpoint (extends past opponent for visual effect)
            beam_length = (other_fighter.pos - beam_start).length() + 50
            beam_end = beam_start + beam_direction * beam_length

            # Store beam data for rendering (will be drawn as actual lines by renderer)
            state['beam_start'] = beam_start
            state['beam_end'] = beam_end
            state['beam_direction'] = beam_direction
            state['beam_intensity'] = min(1.0, self.state_t / 0.3)  # Ramps up quickly

            # Perpendicular vector for edge particles
            perp = pygame.Vector2(-beam_direction.y, beam_direction.x)

            # Origin energy burst (at hands)
            if random.random() < 0.6:
                for _ in range(3):
                    offset = perp * random.uniform(-15, 15)
                    particles.append(Particle(
                        pos=beam_start + offset,
                        vel=beam_direction * random.uniform(100, 200) + perp * random.uniform(-50, 50),
                        life=0.15,
                        radius=random.uniform(4, 8),
                        color=(200, 220, 255)
                    ))

            # Edge sparks along beam (sparse, stylish)
            if random.random() < 0.4:
                t = random.uniform(0.1, 0.9)
                edge_pos = beam_start + beam_direction * (beam_length * t)
                side = 1 if random.random() < 0.5 else -1
                edge_pos += perp * (12 + random.uniform(0, 8)) * side
                particles.append(Particle(
                    pos=edge_pos,
                    vel=perp * side * random.uniform(30, 80) + beam_direction * random.uniform(-20, 20),
                    life=random.uniform(0.1, 0.2),
                    radius=random.uniform(2, 5),
                    color=(150, 200, 255) if random.random() < 0.7 else (255, 255, 255)
                ))

            # Impact explosion at opponent (dramatic)
            for _ in range(4):
                angle = random.uniform(0, 2 * math.pi)
                speed = random.uniform(150, 350)
                particles.append(Particle(
                    pos=other_fighter.pos + pygame.Vector2(random.uniform(-8, 8), random.uniform(-8, 8)),
                    vel=pygame.Vector2(math.cos(angle) * speed, math.sin(angle) * speed),
                    life=random.uniform(0.15, 0.3),
                    radius=random.uniform(5, 12),
                    color=(255, 255, 255) if random.random() < 0.6 else (255, 200, 100)
                ))

            # Continuous damage over beam duration (divided into ticks)
            state['continuous_damage_timer'] += dt
            if state['continuous_damage_timer'] >= 0.15:  # Damage tick every 0.15s
                state['continuous_damage_timer'] = 0.0
                state['damage_ticks'] += 1

                # Total damage divided across beam duration (~10 ticks)
                total_ticks = int(spec.active / 0.15)
                damage_per_tick = (other_fighter.max_hp * FS_DAMAGE_PERCENT) / total_ticks

                knock_dir = beam_direction
                other_fighter.take_hit(damage_per_tick, knock_dir * 100, 0.1, bypasses_invuln=True)

                # Camera effects on damage ticks
                if camera_fx and state['damage_ticks'] % 2 == 0:  # Every other tick
                    camera_fx.add_shake(8)

            # Final massive knockback on last frame
            if self.state_t >= spec.active - 0.1 and not state['hit_applied']:
                final_knock = beam_direction * spec.knockback
                other_fighter.vel = final_knock

                # Massive explosion at impact point
                for _ in range(60):
                    angle = random.uniform(0, 2 * math.pi)
                    speed = random.uniform(200, 500)
                    particles.append(Particle(
                        pos=other_fighter.pos,
                        vel=pygame.Vector2(math.cos(angle) * speed, math.sin(angle) * speed),
                        life=random.uniform(0.4, 0.8),
                        radius=random.uniform(6, 18),
                        color=(255, 255, 255) if random.random() < 0.5 else (255, 200, 100)
                    ))

                if camera_fx:
                    camera_fx.trigger_hitstop(spec.hitstop)
                    camera_fx.trigger_zoom_punch(other_fighter.pos, spec.zoom_punch, spec.zoom_hold)
                    camera_fx.add_shake(40)

                # Final Smash impact sound
                if sound:
                    sound.play_final_smash_impact()

                state['hit_applied'] = True

        # PHASE 3: Recovery - Dissipating energy
        elif self.state == "recovery":
            # Residual energy particles fading away
            if random.random() < 0.3:
                particles.append(Particle(
                    pos=self.pos + pygame.Vector2(random.uniform(-30, 30), random.uniform(-30, 30)),
                    vel=pygame.Vector2(random.uniform(-50, 50), random.uniform(-50, 50)),
                    life=random.uniform(0.2, 0.4),
                    radius=random.uniform(4, 10),
                    color=(150, 180, 255)
                ))

        # Cleanup
        if self.state == "idle" and hasattr(self, 'fs_kamehameha_state'):
            delattr(self, 'fs_kamehameha_state')

    def _execute_final_smash_aoe(self, spec, dt, other_fighter, particles, camera_fx, sound=None):
        """
        Choreography for FS_AOE: Energy burst explosion
        """
        from .camera_fx import Particle

        # Initialize and freeze opponent
        if not hasattr(self, 'fs_aoe_initialized'):
            other_fighter.state = "hitstun"
            other_fighter.hitstun_t = spec.windup + spec.active + spec.recovery
            other_fighter.vel = pygame.Vector2(0, 0)
            self.fs_aoe_initialized = True

            # Trigger time slowdown (40% speed for energy buildup effect)
            if camera_fx:
                total_duration = spec.windup + spec.active + spec.recovery
                camera_fx.trigger_time_slowdown(0.4, total_duration)

            # Final Smash charge-up sound
            if sound:
                sound.play_final_smash_charge()

        # During windup: Build up energy
        if self.state == "windup":
            if random.random() < 0.5:
                # Particles converge towards self
                angle = random.uniform(0, 2 * math.pi)
                distance = random.uniform(60, 100)
                start_pos = self.pos + pygame.Vector2(math.cos(angle) * distance, math.sin(angle) * distance)
                vel_to_self = (self.pos - start_pos) * 2.5
                particles.append(Particle(
                    pos=start_pos,
                    vel=vel_to_self,
                    life=0.6,
                    radius=random.uniform(3, 8),
                    color=(100, 200, 255)
                ))

        # During active: Explosion!
        elif self.state == "active":
            if not hasattr(self, 'fs_aoe_hit'):
                # Deal damage
                damage = other_fighter.max_hp * FS_DAMAGE_PERCENT
                knock_dir = (other_fighter.pos - self.pos)
                if knock_dir.length() > 0:
                    knock_dir = knock_dir.normalize()
                else:
                    knock_dir = pygame.Vector2(1, 0)

                other_fighter.take_hit(damage, knock_dir * spec.knockback, spec.hitstun, bypasses_invuln=True)

                # Circular explosion particles
                for _ in range(60):
                    angle = random.uniform(0, 2 * math.pi)
                    speed = random.uniform(300, 600)
                    particles.append(Particle(
                        pos=pygame.Vector2(self.pos),
                        vel=pygame.Vector2(math.cos(angle) * speed, math.sin(angle) * speed),
                        life=random.uniform(0.4, 0.8),
                        radius=random.uniform(5, 15),
                        color=(100, 150, 255) if random.random() < 0.6 else (255, 255, 255)
                    ))

                if camera_fx:
                    camera_fx.trigger_hitstop(spec.hitstop)
                    camera_fx.trigger_zoom_punch(self.pos, spec.zoom_punch, spec.zoom_hold)
                    camera_fx.add_shake(30)

                # Final Smash impact sound
                if sound:
                    sound.play_final_smash_impact()

                self.fs_aoe_hit = True

        # Cleanup
        if self.state == "idle":
            if hasattr(self, 'fs_aoe_hit'):
                delattr(self, 'fs_aoe_hit')
            if hasattr(self, 'fs_aoe_initialized'):
                delattr(self, 'fs_aoe_initialized')

    def update_state(
        self,
        dt: float,
        hitshapes: List[HitShape],
        projectiles: List[Projectile],
        particles: List,
        other_fighter=None,
        camera_fx=None,
        sound=None
    ):
        """
        Update combat state machine

        Args:
            dt: Delta time
            hitshapes: List to spawn hitboxes into
            projectiles: List to spawn projectiles into
            particles: List to spawn particles into
            other_fighter: Opponent fighter (for Final Smash choreography)
            camera_fx: Camera effects instance (for Final Smash choreography)
            sound: SoundManager instance for attack sounds (optional)
        """
        if self.state == "dead":
            self.is_blocking = False
            return

        if self.state == "hitstun":
            self.hitstun_t -= dt
            if self.hitstun_t <= 0:
                self.state = "idle"
                self.state_t = 0.0
            return

        if not self.attack:
            self.is_blocking = False
            return

        self.state_t += dt
        spec = self.attack

        # Block is a sustained "active" state
        if spec.key == "BLOCK":
            self.state = "active"
            if self.state_t >= spec.active:
                self.attack = None
                self.is_blocking = False
                self.state = "idle"
                self.state_t = 0.0
            return

        # Windup -> Active
        if self.state == "windup":
            # Special choreography for Final Smash windups
            if other_fighter and camera_fx:
                if spec.key == "FS_TELEPORT":
                    self._execute_final_smash_teleport(spec, dt, other_fighter, particles, camera_fx, sound)
                elif spec.key == "FS_SINGLE":
                    self._execute_final_smash_single(spec, dt, other_fighter, particles, camera_fx, sound)
                elif spec.key == "FS_AOE":
                    self._execute_final_smash_aoe(spec, dt, other_fighter, particles, camera_fx, sound)

            # Extra pull for finisher
            if spec.key == "FIN" and spec.impulse > 0:
                self.vel += self.facing * (spec.impulse * 0.12) * dt

            if self.state_t >= spec.windup:
                self.state = "active"
                self.state_t = 0.0

                # Skip hitshape/projectile spawning for Final Smash moves (handled by choreography)
                if spec.key not in ("FS_TELEPORT", "FS_SINGLE", "FS_AOE"):
                    if spec.spawns_projectile:
                        # Spawn ki blast
                        speed = 920.0
                        projectiles.append(
                            Projectile(
                                owner_id=self.id,
                                pos=self.pos + self.facing * (self.radius + 10),
                                vel=self.facing * speed,
                                radius=12,
                                damage=11,
                                knockback=330,
                                hitstun=0.18,
                                ttl=1.2,
                                hitstop=0.030,
                                zoom_punch=1.10,
                                zoom_hold=0.08,
                            )
                        )
                        spawn_sparks(particles, self.pos + self.facing * (self.radius + 8),
                                    self.facing, 14, self.color, 520)
                        # Ki blast fire sound
                        if sound:
                            sound.play_ki_blast_fire()
                    else:
                        # Spawn melee hitshape
                        hitshapes.append(
                            HitShape(
                                owner_id=self.id,
                                center=pygame.Vector2(self.pos),
                                radius=spec.radius,
                                damage=spec.damage,
                                knockback=spec.knockback,
                                hitstun=spec.hitstun,
                                ttl=spec.active,
                                follow_owner=True,
                                range_offset=spec.range,
                                hitstop=spec.hitstop,
                                zoom_punch=spec.zoom_punch,
                                zoom_hold=spec.zoom_hold,
                            )
                        )
                        spawn_sparks(particles, self.pos + self.facing * min(28, spec.range),
                                    self.facing, 12, (240, 240, 255), 420)

        # Active -> Recovery
        elif self.state == "active":
            # Special choreography for Final Smash attacks
            if other_fighter and camera_fx:
                if spec.key == "FS_TELEPORT":
                    self._execute_final_smash_teleport(spec, dt, other_fighter, particles, camera_fx, sound)
                elif spec.key == "FS_SINGLE":
                    self._execute_final_smash_single(spec, dt, other_fighter, particles, camera_fx, sound)
                elif spec.key == "FS_AOE":
                    self._execute_final_smash_aoe(spec, dt, other_fighter, particles, camera_fx, sound)

            # Anti-projectile field (CUT move)
            if spec.anti_projectile:
                exists = any(
                    h.owner_id == self.id and abs(h.radius - spec.radius) < 0.1 and h.follow_owner
                    for h in hitshapes
                )
                if not exists:
                    hitshapes.append(
                        HitShape(
                            owner_id=self.id,
                            center=pygame.Vector2(self.pos),
                            radius=spec.radius,
                            damage=spec.damage,
                            knockback=spec.knockback,
                            hitstun=spec.hitstun,
                            ttl=spec.active,
                            follow_owner=True,
                            range_offset=0.0,
                            hitstop=spec.hitstop,
                            zoom_punch=spec.zoom_punch,
                            zoom_hold=spec.zoom_hold,
                        )
                    )

            if self.state_t >= spec.active:
                self.state = "recovery"
                self.state_t = 0.0

        # Recovery -> end
        elif self.state == "recovery":
            if self.state_t >= spec.recovery:
                self.attack = None
                self.state = "idle"
                self.state_t = 0.0

    def move(self, dt: float, arena: pygame.Rect):
        """
        Update fighter movement physics

        Args:
            dt: Delta time
            arena: Arena boundaries
        """
        # Desperation mode speed boost (10%)
        speed_mult = 1.10 if self.is_desperate else 1.0

        # Anime-style movement
        max_speed = (520.0 if self.attack and self.attack.key in ("DASH", "ROLL") else 420.0) * speed_mult
        accel_strength = 1800.0 * speed_mult
        damping = 10.5

        steer_mult = 1.0 if self.state in ("idle", "move") else 0.35
        self.vel += self.acc * accel_strength * steer_mult * dt

        self.vel -= self.vel * damping * dt
        if self.vel.length_squared() > max_speed * max_speed:
            self.vel = self.vel.normalize() * max_speed

        self.pos += self.vel * dt

        # Keep inside arena
        left = arena.left + self.radius
        right = arena.right - self.radius
        top = arena.top + self.radius
        bottom = arena.bottom - self.radius

        if self.pos.x < left:
            self.pos.x = left
            self.vel.x *= -0.35
        elif self.pos.x > right:
            self.pos.x = right
            self.vel.x *= -0.35

        if self.pos.y < top:
            self.pos.y = top
            self.vel.y *= -0.35
        elif self.pos.y > bottom:
            self.pos.y = bottom
            self.vel.y *= -0.35

    def update_afterimages(self, dt: float, afterimages: List[AfterImage]):
        """
        Create afterimage trails when moving fast

        Args:
            dt: Delta time
            afterimages: List to append afterimages to
        """
        self.afterimage_t += dt
        if self.vel.length() > 250 and self.afterimage_t >= AFTERIMAGE_INTERVAL:
            self.afterimage_t = 0.0
            afterimages.append(
                AfterImage(
                    pos=pygame.Vector2(self.pos),
                    radius=self.radius,
                    color=self.color,
                    avatar=self.avatar_surface if hasattr(self, 'avatar_surface') else None,
                    life=AFTERIMAGE_LIFETIME,
                )
            )

    def draw(self, surf: pygame.Surface):
        """
        Draw fighter (override to add combat visuals)

        Args:
            surf: Surface to draw on
        """
        # Draw base circle
        pygame.draw.circle(surf, self.color, self.pos, self.radius)

        # Draw avatar if available
        if hasattr(self, 'avatar_surface') and self.avatar_surface:
            rect = self.avatar_surface.get_rect(center=(int(self.pos.x), int(self.pos.y)))
            surf.blit(self.avatar_surface, rect)

        # Draw border
        pygame.draw.circle(surf, (28, 28, 32), self.pos, self.radius, 3)

        # Invulnerability indicator
        if self.invuln_t > 0:
            pygame.draw.circle(surf, (255, 255, 255), self.pos, self.radius + 7, 2)

        # Facing direction indicator
        tip = self.pos + self.facing * (self.radius - 6)
        pygame.draw.circle(surf, (240, 240, 245), tip, 3)

    def reset_for_match(self, position: Tuple[float, float], hp_multiplier: float = 1.0):
        """
        Reset fighter state for new match

        Args:
            position: (x, y) spawn position
            hp_multiplier: HP multiplier (e.g., 0.5 for half HP)
        """
        self.pos = pygame.Vector2(position)
        self.vel = pygame.Vector2(0, 0)
        self.acc = pygame.Vector2(0, 0)

        self.hp = self.max_hp * hp_multiplier
        self.match_start_hp = self.hp  # Track starting HP for this match (for HP bar percentage)
        self.alive = True

        self.state = "idle"
        self.state_t = 0.0
        self.attack = None
        self.hitstun_t = 0.0

        for k in self.attack_cd:
            self.attack_cd[k] = 0.0

        self.invuln_t = 0.0
        self.is_blocking = False
        self.last_hit_time = -999.0
        self.combo_buffer = None

        # Reset Final Smash meter
        self.final_smash_meter = 0.0
        self.final_smash_ready = False
        self.final_smash_cooldown = 0.0

        # Clean up Final Smash state attributes (prevents beam/effects from persisting)
        if hasattr(self, 'fs_kamehameha_state'):
            delattr(self, 'fs_kamehameha_state')
        if hasattr(self, 'fs_teleport_state'):
            delattr(self, 'fs_teleport_state')
        if hasattr(self, 'fs_aoe_initialized'):
            delattr(self, 'fs_aoe_initialized')
        if hasattr(self, 'fs_aoe_hit'):
            delattr(self, 'fs_aoe_hit')

    def __repr__(self):
        """String representation"""
        status = "DEAD" if not self.is_alive() else self.state.upper()
        return f"AnimeFighter({self.username}, HP={self.hp:.0f}/{self.max_hp:.0f}, {status})"
