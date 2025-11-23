"""
Particle System Module
Handles particle effects for eliminations, explosions, and visual flair
"""

import pygame
import random
import math
from typing import List, Tuple


class Particle:
    """
    Individual particle with position, velocity, and lifetime
    """

    def __init__(self, x: float, y: float, color: Tuple[int, int, int],
                 velocity: Tuple[float, float], lifetime: float, size: int = 4):
        """
        Initialize a particle

        Args:
            x: Starting X position
            y: Starting Y position
            color: RGB color tuple
            velocity: (vx, vy) velocity
            lifetime: How long the particle lives (seconds)
            size: Initial particle size in pixels
        """
        self.x = x
        self.y = y
        self.color = color
        self.vx, self.vy = velocity
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        self.size = size
        self.initial_size = size

    def update(self, dt: float) -> bool:
        """
        Update particle position and lifetime

        Args:
            dt: Delta time in seconds

        Returns:
            True if particle is still alive, False if dead
        """
        # Update position
        self.x += self.vx * dt * 60
        self.y += self.vy * dt * 60

        # Apply gravity
        self.vy += 200 * dt

        # Apply friction
        self.vx *= 0.98
        self.vy *= 0.98

        # Decrease lifetime
        self.lifetime -= dt

        # Shrink particle as it ages
        life_percent = self.lifetime / self.max_lifetime
        self.size = max(1, int(self.initial_size * life_percent))

        return self.lifetime > 0

    def render(self, screen: pygame.Surface):
        """
        Render the particle

        Args:
            screen: Pygame surface to render to
        """
        # Fade out as particle ages
        life_percent = self.lifetime / self.max_lifetime
        alpha = int(255 * life_percent)

        # Create surface with alpha
        particle_surface = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        color_with_alpha = (*self.color, alpha)
        pygame.draw.circle(particle_surface, color_with_alpha,
                         (self.size, self.size), self.size)

        screen.blit(particle_surface, (int(self.x - self.size), int(self.y - self.size)))


class ParticleSystem:
    """
    Manages multiple particle emitters and effects
    """

    def __init__(self):
        """
        Initialize the particle system
        """
        self.particles: List[Particle] = []

    def create_elimination_explosion(self, x: float, y: float, color: Tuple[int, int, int]):
        """
        Create an explosion effect at elimination location

        Args:
            x: X position
            y: Y position
            color: Base color for particles
        """
        # Create 20-30 particles bursting outward
        particle_count = random.randint(20, 30)

        for _ in range(particle_count):
            # Random direction
            angle = random.random() * 2 * math.pi
            speed = random.uniform(50, 200)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed

            # Vary color slightly
            color_variation = random.randint(-30, 30)
            particle_color = (
                max(0, min(255, color[0] + color_variation)),
                max(0, min(255, color[1] + color_variation)),
                max(0, min(255, color[2] + color_variation))
            )

            # Random lifetime
            lifetime = random.uniform(0.5, 1.5)
            size = random.randint(3, 8)

            particle = Particle(x, y, particle_color, (vx, vy), lifetime, size)
            self.particles.append(particle)

    def create_collision_sparks(self, x: float, y: float):
        """
        Create small sparks at collision point

        Args:
            x: X position
            y: Y position
        """
        # Create 5-10 small white/yellow sparks
        particle_count = random.randint(5, 10)

        for _ in range(particle_count):
            angle = random.random() * 2 * math.pi
            speed = random.uniform(30, 80)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed

            # White or yellow color
            color = random.choice([(255, 255, 255), (255, 255, 100), (255, 200, 50)])
            lifetime = random.uniform(0.2, 0.5)

            particle = Particle(x, y, color, (vx, vy), lifetime, 2)
            self.particles.append(particle)

    def update(self, dt: float):
        """
        Update all particles

        Args:
            dt: Delta time in seconds
        """
        # Update all particles and remove dead ones
        self.particles = [p for p in self.particles if p.update(dt)]

    def render(self, screen: pygame.Surface):
        """
        Render all particles

        Args:
            screen: Pygame surface to render to
        """
        for particle in self.particles:
            particle.render(screen)

    def clear(self):
        """
        Clear all particles
        """
        self.particles.clear()

    def get_particle_count(self) -> int:
        """
        Get current number of active particles

        Returns:
            Number of particles
        """
        return len(self.particles)
