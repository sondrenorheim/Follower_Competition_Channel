"""
Camera Effects System for Anime Fighting

Implements hitstop (freeze frames), zoom punch (dynamic zoom), screen shake,
particles, and afterimage effects for impactful combat visuals.
"""

import math
import random
from dataclasses import dataclass
from typing import List, Tuple, Optional

import pygame


# ============================================================
# Camera FX Tuning
# ============================================================
SHAKE_MAX = 12.0  # Increased for more dramatic heavy hits
SHAKE_DECAY = 18.0

AFTERIMAGE_INTERVAL = 0.035
AFTERIMAGE_LIFETIME = 0.18

MAX_PARTICLES = 2000  # Increased for clash effects

# Near-KO dramatic effects (when hitting opponent below this HP%)
NEAR_KO_HP_THRESHOLD = 0.15
NEAR_KO_SLOWDOWN_SCALE = 0.4  # 40% speed
NEAR_KO_SLOWDOWN_DURATION = 0.5

# Zoom tuning
ZOOM_SMOOTH = 18.0


# ============================================================
# Helper Functions
# ============================================================

def clamp(x: float, lo: float, hi: float) -> float:
    """Clamp value between min and max"""
    return max(lo, min(hi, x))


def exp_smooth(current: float, target: float, k: float, dt: float) -> float:
    """Stable exponential smoothing toward target"""
    t = 1.0 - math.exp(-k * dt)
    return current + (target - current) * t


# ============================================================
# Particle & AfterImage Data Structures
# ============================================================

@dataclass
class Particle:
    """Visual particle for impact effects"""
    pos: pygame.Vector2
    vel: pygame.Vector2
    life: float
    radius: float
    color: Tuple[int, int, int]
    drag: float = 7.0

    def update(self, dt: float):
        """Update particle physics"""
        self.life -= dt
        self.vel -= self.vel * self.drag * dt
        self.pos += self.vel * dt


@dataclass
class AfterImage:
    """Motion trail effect for fast movement"""
    pos: pygame.Vector2
    radius: int
    color: Tuple[int, int, int]
    avatar: Optional[pygame.Surface]
    life: float


# ============================================================
# Camera FX (hit-stop + zoom punch + shake)
# ============================================================

class CameraFX:
    """
    Manages camera effects for impactful combat visuals
    - Hitstop: Freeze simulation during heavy hits
    - Zoom punch: Dynamic zoom on impacts
    - Screen shake: Camera shake on hits
    """

    def __init__(self, w: int, h: int):
        self.w = w
        self.h = h

        self.shake = 0.0
        self.zoom = 1.0
        self.zoom_target = 1.0
        self.zoom_hold_t = 0.0
        self.zoom_focus = pygame.Vector2(w / 2, h / 2)

        self.hitstop_t = 0.0

        # Time slowdown for dramatic effects (Final Smashes)
        self.time_scale = 1.0        # 1.0 = normal, 0.3 = 30% speed
        self.time_scale_t = 0.0      # Duration remaining

        # Screen flash effect
        self.screen_flash_t = 0.0
        self.screen_flash_color = (255, 255, 255)

    def trigger_hitstop(self, seconds: float):
        """
        Trigger hitstop (freeze frame effect)

        Args:
            seconds: Duration of hitstop
        """
        self.hitstop_t = max(self.hitstop_t, seconds)

    def trigger_zoom_punch(self, focus_world: pygame.Vector2, zoom_amount: float, hold_seconds: float):
        """
        Trigger zoom punch effect

        Args:
            focus_world: World position to zoom toward
            zoom_amount: Zoom level (1.0 = normal, >1.0 = zoomed in)
            hold_seconds: How long to hold zoom before relaxing
        """
        self.zoom_focus = pygame.Vector2(focus_world)
        self.zoom_target = max(self.zoom_target, zoom_amount)
        self.zoom_hold_t = max(self.zoom_hold_t, hold_seconds)

    def add_shake(self, amount: float):
        """
        Add screen shake

        Args:
            amount: Shake intensity (pixels)
        """
        self.shake = min(SHAKE_MAX, self.shake + amount)

    def trigger_time_slowdown(self, scale: float, duration: float):
        """
        Trigger time slowdown effect (for dramatic Final Smash sequences)

        Args:
            scale: Time scale multiplier (0.0-1.0, where 0.3 = 30% speed)
            duration: How long to maintain the slowdown (in real time)
        """
        self.time_scale = scale
        self.time_scale_t = duration

    def trigger_screen_flash(self, duration: float = 0.1, color: Tuple[int, int, int] = (255, 255, 255)):
        """
        Trigger a screen flash effect

        Args:
            duration: Flash duration in seconds
            color: Flash color (default white)
        """
        self.screen_flash_t = max(self.screen_flash_t, duration)
        self.screen_flash_color = color

    def get_flash_intensity(self) -> float:
        """
        Get current screen flash intensity (0.0 to 1.0)

        Returns:
            Flash intensity for rendering
        """
        return min(1.0, self.screen_flash_t / 0.1) if self.screen_flash_t > 0 else 0.0

    def trigger_near_ko_hit(self, victim_pos: pygame.Vector2):
        """
        Trigger dramatic effects when hitting near-KO opponent (< 15% HP)

        Args:
            victim_pos: Position of the near-KO fighter
        """
        # Extra dramatic zoom
        self.trigger_zoom_punch(victim_pos, 1.35, 0.25)
        # Extended hitstop
        self.trigger_hitstop(0.1)
        # Intense shake
        self.add_shake(SHAKE_MAX)
        # Time slowdown
        self.trigger_time_slowdown(NEAR_KO_SLOWDOWN_SCALE, NEAR_KO_SLOWDOWN_DURATION)
        # White flash
        self.trigger_screen_flash(0.08)

    def update(self, dt_real: float):
        """
        Update camera effects (runs in real time, not affected by hitstop)

        Args:
            dt_real: Real delta time (unscaled)
        """
        # Hitstop counts down in real time
        self.hitstop_t = max(0.0, self.hitstop_t - dt_real)

        # Time slowdown counts down in real time
        if self.time_scale_t > 0:
            self.time_scale_t = max(0.0, self.time_scale_t - dt_real)
            if self.time_scale_t == 0:
                self.time_scale = 1.0  # Return to normal speed

        # Screen flash decays in real time
        self.screen_flash_t = max(0.0, self.screen_flash_t - dt_real)

        # Shake decays in real time
        self.shake = max(0.0, self.shake - SHAKE_DECAY * dt_real)

        # Zoom relax logic
        if self.zoom_hold_t > 0:
            self.zoom_hold_t = max(0.0, self.zoom_hold_t - dt_real)
        else:
            self.zoom_target = 1.0

        self.zoom = exp_smooth(self.zoom, self.zoom_target, ZOOM_SMOOTH, dt_real)

        if abs(self.zoom - 1.0) < 0.002 and self.zoom_target == 1.0:
            self.zoom_focus.update(self.w / 2, self.h / 2)

    def sim_dt(self, dt_scaled: float) -> float:
        """
        Get simulation delta time (freezes during hitstop, scales during slowdown)

        Args:
            dt_scaled: Scaled delta time

        Returns:
            0.0 during hitstop, dt_scaled * time_scale during slowdown, dt_scaled otherwise
        """
        if self.hitstop_t > 0:
            return 0.0
        return dt_scaled * self.time_scale

    def _shake_offset(self) -> pygame.Vector2:
        """Calculate random shake offset"""
        s = self.shake
        return pygame.Vector2(random.uniform(-s, s), random.uniform(-s, s))

    def blit_world(self, screen: pygame.Surface, world: pygame.Surface):
        """
        Render world surface to screen with camera effects applied

        Args:
            screen: Target screen surface
            world: World surface to render
        """
        # Disable zoom effects - just use shake
        shake = self._shake_offset()
        screen.blit(world, (shake.x, shake.y))


# ============================================================
# Particle System Functions
# ============================================================

def update_particles(particles: List[Particle], dt: float):
    """
    Update all particles

    Args:
        particles: List of Particle instances
        dt: Delta time
    """
    for p in particles:
        p.update(dt)
    particles[:] = [p for p in particles if p.life > 0]


def draw_particles(surf: pygame.Surface, particles: List[Particle]):
    """
    Draw all particles

    Args:
        surf: Surface to draw on
        particles: List of Particle instances
    """
    for p in particles:
        a = int(255 * clamp(p.life / 0.22, 0.0, 1.0))
        s = pygame.Surface((int(p.radius * 4 + 2), int(p.radius * 4 + 2)), pygame.SRCALPHA)
        pygame.draw.circle(s, (*p.color, a), (s.get_width() // 2, s.get_height() // 2), int(p.radius * 2))
        surf.blit(s, (p.pos.x - s.get_width() // 2, p.pos.y - s.get_height() // 2))


# ============================================================
# AfterImage System Functions
# ============================================================

def update_afterimages(afterimages: List[AfterImage], dt: float):
    """
    Update all afterimages

    Args:
        afterimages: List of AfterImage instances
        dt: Delta time
    """
    for a in afterimages:
        a.life -= dt
    afterimages[:] = [a for a in afterimages if a.life > 0]


def draw_afterimages(surf: pygame.Surface, afterimages: List[AfterImage]):
    """
    Draw all afterimages

    Args:
        surf: Surface to draw on
        afterimages: List of AfterImage instances
    """
    for a in afterimages:
        alpha = int(150 * clamp(a.life / AFTERIMAGE_LIFETIME, 0.0, 1.0))
        s = pygame.Surface((a.radius * 2 + 6, a.radius * 2 + 6), pygame.SRCALPHA)
        pygame.draw.circle(s, (*a.color, alpha), (s.get_width() // 2, s.get_height() // 2), a.radius)
        if a.avatar:
            av = a.avatar.copy()
            av.fill((255, 255, 255, alpha), special_flags=pygame.BLEND_RGBA_MULT)
            rect = av.get_rect(center=(s.get_width() // 2, s.get_height() // 2))
            s.blit(av, rect)
        surf.blit(s, s.get_rect(center=(int(a.pos.x), int(a.pos.y))))


# ============================================================
# Hit Rendering (debug visualization)
# ============================================================

def draw_hitfields(surf: pygame.Surface, hitshapes: List):
    """
    Draw active hitboxes (for debugging/visual feedback)

    Args:
        surf: Surface to draw on
        hitshapes: List of HitShape instances
    """
    for h in hitshapes:
        alpha = int(120 * clamp(h.ttl / 0.12, 0.25, 1.0))
        s = pygame.Surface((int(h.radius * 2 + 6), int(h.radius * 2 + 6)), pygame.SRCALPHA)
        pygame.draw.circle(s, (255, 255, 255, alpha), (s.get_width() // 2, s.get_height() // 2), int(h.radius), 3)
        surf.blit(s, s.get_rect(center=(int(h.center.x), int(h.center.y))))


def draw_projectiles(surf: pygame.Surface, projectiles: List):
    """
    Draw active projectiles

    Args:
        surf: Surface to draw on
        projectiles: List of Projectile instances
    """
    for pr in projectiles:
        pygame.draw.circle(surf, (230, 230, 250), pr.pos, pr.radius)
        pygame.draw.circle(surf, (40, 40, 55), pr.pos, pr.radius, 2)


def draw_screen_flash(surf: pygame.Surface, intensity: float, color: Tuple[int, int, int] = (255, 255, 255)):
    """
    Draw a screen flash overlay

    Args:
        surf: Surface to draw on
        intensity: Flash intensity (0.0 to 1.0)
        color: Flash color (default white)
    """
    if intensity <= 0:
        return

    alpha = int(180 * intensity)
    w, h = surf.get_size()
    flash_surface = pygame.Surface((w, h), pygame.SRCALPHA)
    flash_surface.fill((*color, alpha))
    surf.blit(flash_surface, (0, 0))
