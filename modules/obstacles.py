"""
Obstacles Module
Defines different types of obstacles for the obstacle course
"""

import pygame
from typing import Tuple
import config


class Obstacle:
    """Base class for all obstacles"""

    def __init__(self, position: Tuple[float, float], size: Tuple[float, float]):
        """
        Initialize obstacle

        Args:
            position: (x, y) position of obstacle
            size: (width, height) of obstacle
        """
        self.x, self.y = position
        self.width, self.height = size
        self.is_moving = False
        self.color = (100, 100, 100)  # Default gray

    def update(self, dt: float):
        """Update obstacle state (override for moving obstacles)"""
        pass

    def get_bounds(self) -> Tuple[float, float, float, float]:
        """
        Get obstacle bounding box

        Returns:
            (left, top, right, bottom) bounds
        """
        return (self.x, self.y, self.x + self.width, self.y + self.height)

    def check_collision(self, racer_pos: Tuple[float, float], racer_radius: float) -> bool:
        """
        Check if a racer collides with this obstacle

        Args:
            racer_pos: (x, y) position of racer
            racer_radius: Radius of racer

        Returns:
            True if collision detected
        """
        # Circle-rectangle collision
        # Find closest point on rectangle to circle center
        closest_x = max(self.x, min(racer_pos[0], self.x + self.width))
        closest_y = max(self.y, min(racer_pos[1], self.y + self.height))

        # Calculate distance from circle center to closest point
        distance_x = racer_pos[0] - closest_x
        distance_y = racer_pos[1] - closest_y
        distance_squared = (distance_x * distance_x) + (distance_y * distance_y)

        return distance_squared < (racer_radius * racer_radius)

    def apply_collision_effect(self, racer):
        """
        Apply effect when racer collides with obstacle
        Override in subclasses for different behaviors

        Args:
            racer: Racer object that collided
        """
        pass


class StaticWall(Obstacle):
    """
    Static wall obstacle that blocks movement
    Racers must navigate around it
    """

    def __init__(self, position: Tuple[float, float], size: Tuple[float, float]):
        super().__init__(position, size)
        self.color = (80, 80, 80)  # Dark gray
        self.is_moving = False

    def apply_collision_effect(self, racer):
        """
        Push racer away from wall to prevent overlap

        Args:
            racer: Racer object that collided
        """
        # Calculate penetration and push racer out
        racer_center = (racer.x, racer.y)
        bounds = self.get_bounds()

        # Find closest edge and push away from it
        distances = {
            'left': abs(racer_center[0] - bounds[0]),
            'right': abs(racer_center[0] - bounds[2]),
            'top': abs(racer_center[1] - bounds[1]),
            'bottom': abs(racer_center[1] - bounds[3])
        }

        closest_edge = min(distances, key=distances.get)

        # Push racer away from closest edge (exactly touching, no gap)
        push_strength = 2.0
        if closest_edge == 'left':
            racer.x = bounds[0] - config.FOLLOWER_RADIUS
            racer.vx = min(racer.vx, -push_strength)
        elif closest_edge == 'right':
            racer.x = bounds[2] + config.FOLLOWER_RADIUS
            racer.vx = max(racer.vx, push_strength)
        elif closest_edge == 'top':
            racer.y = bounds[1] - config.FOLLOWER_RADIUS
            racer.vy = min(racer.vy, -push_strength)
        elif closest_edge == 'bottom':
            racer.y = bounds[3] + config.FOLLOWER_RADIUS
            racer.vy = max(racer.vy, push_strength)


class MovingWall(Obstacle):
    """
    Wall that moves up and down across the track
    Racers get pushed along with it if they collide
    """

    def __init__(self, position: Tuple[float, float], size: Tuple[float, float],
                 velocity: float, min_y: float, max_y: float):
        """
        Initialize moving wall

        Args:
            position: Starting (x, y) position
            size: (width, height) of wall
            velocity: Vertical movement speed (pixels per second)
            min_y: Minimum Y position
            max_y: Maximum Y position
        """
        super().__init__(position, size)
        self.velocity_x = 0
        self.velocity_y = velocity
        self.min_y = min_y
        self.max_y = max_y
        self.is_moving = True
        self.color = (150, 100, 100)  # Reddish brown

    def update(self, dt: float):
        """
        Update wall position

        Args:
            dt: Delta time in seconds
        """
        # Move wall vertically
        self.y += self.velocity_y * dt

        # Bounce at boundaries
        if self.y <= self.min_y:
            self.y = self.min_y
            self.velocity_y = abs(self.velocity_y)  # Reverse to positive
        elif self.y + self.height >= self.max_y:
            self.y = self.max_y - self.height
            self.velocity_y = -abs(self.velocity_y)  # Reverse to negative

    def apply_collision_effect(self, racer):
        """
        Push racer along with the wall's movement
        Racer can escape by moving perpendicular to wall

        Args:
            racer: Racer object that collided
        """
        # Racer moves with the wall vertically
        racer.push_vy = self.velocity_y * 0.8

        # Also push racer away from wall slightly to prevent sticking
        racer_center_x = racer.x
        wall_center_x = self.x + self.width / 2

        if racer_center_x < wall_center_x:
            # Racer left of wall, push left
            racer.push_vx = -5.0
        else:
            # Racer right of wall, push right
            racer.push_vx = 5.0


class Spinner(Obstacle):
    """
    Rotating bar that spins around a center point
    Knocks racers backward on contact
    """

    def __init__(self, position: Tuple[float, float], bar_length: float = 80,
                 rotation_speed: float = 2.0):
        """
        Initialize spinner

        Args:
            position: (x, y) center position of spinner
            bar_length: Length of the spinning bar
            rotation_speed: Rotations per second (can be negative for reverse)
        """
        import math
        # Size is the bounding box of rotation
        super().__init__(position, (bar_length, bar_length))
        self.center_x = position[0]
        self.center_y = position[1]
        self.bar_length = bar_length
        self.bar_width = 12  # Thickness of the bar
        self.rotation_speed = rotation_speed  # Radians per second
        self.angle = 0.0  # Current rotation angle
        self.is_moving = True
        self.color = (200, 100, 50)  # Orange

    def update(self, dt: float):
        """Update spinner rotation"""
        import math
        self.angle += self.rotation_speed * dt * math.pi * 2
        # Keep angle in 0-2pi range
        self.angle = self.angle % (math.pi * 2)

    def check_collision(self, racer_pos: Tuple[float, float], racer_radius: float) -> bool:
        """Check collision with rotating bar"""
        import math

        # Calculate bar endpoints based on current angle
        half_length = self.bar_length / 2
        end1_x = self.center_x + math.cos(self.angle) * half_length
        end1_y = self.center_y + math.sin(self.angle) * half_length
        end2_x = self.center_x - math.cos(self.angle) * half_length
        end2_y = self.center_y - math.sin(self.angle) * half_length

        # Point-to-line-segment distance
        # Find closest point on line segment to racer
        px, py = racer_pos
        ax, ay = end1_x, end1_y
        bx, by = end2_x, end2_y

        # Vector from a to b
        abx = bx - ax
        aby = by - ay

        # Vector from a to point
        apx = px - ax
        apy = py - ay

        # Project point onto line
        ab_sq = abx * abx + aby * aby
        if ab_sq == 0:
            t = 0
        else:
            t = max(0, min(1, (apx * abx + apy * aby) / ab_sq))

        # Closest point on segment
        closest_x = ax + t * abx
        closest_y = ay + t * aby

        # Distance to closest point
        dx = px - closest_x
        dy = py - closest_y
        distance = math.sqrt(dx * dx + dy * dy)

        return distance < (racer_radius + self.bar_width / 2)

    def apply_collision_effect(self, racer):
        """Knock racer backward"""
        import math
        # Push racer away from center and backward
        dx = racer.x - self.center_x
        dy = racer.y - self.center_y
        dist = math.sqrt(dx * dx + dy * dy)

        if dist > 0:
            # Push away from center
            racer.push_vx = (dx / dist) * 8.0 - 3.0  # Also push backward
            racer.push_vy = (dy / dist) * 8.0

    def get_bar_endpoints(self) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        """Get current bar endpoints for rendering"""
        import math
        half_length = self.bar_length / 2
        end1 = (self.center_x + math.cos(self.angle) * half_length,
                self.center_y + math.sin(self.angle) * half_length)
        end2 = (self.center_x - math.cos(self.angle) * half_length,
                self.center_y - math.sin(self.angle) * half_length)
        return end1, end2


class SpeedBoost(Obstacle):
    """
    Green zone that temporarily increases racer speed
    """

    def __init__(self, position: Tuple[float, float], size: Tuple[float, float] = (60, 100),
                 boost_multiplier: float = 1.8):
        """
        Initialize speed boost zone

        Args:
            position: (x, y) position
            size: (width, height) of zone
            boost_multiplier: Speed multiplier when in zone
        """
        super().__init__(position, size)
        self.boost_multiplier = boost_multiplier
        self.boost_duration = 1.5  # Seconds the boost lasts after leaving
        self.is_moving = False
        self.color = (50, 200, 50)  # Green

    def check_collision(self, racer_pos: Tuple[float, float], racer_radius: float) -> bool:
        """Check if racer is inside the boost zone"""
        # Simple rectangle check (racer center inside zone)
        return (self.x <= racer_pos[0] <= self.x + self.width and
                self.y <= racer_pos[1] <= self.y + self.height)

    def apply_collision_effect(self, racer):
        """Apply speed boost to racer"""
        import time
        racer.speed_boost = self.boost_multiplier
        racer.speed_boost_end_time = time.time() + self.boost_duration


class SlowZone(Obstacle):
    """
    Brown muddy zone that slows down racers
    """

    def __init__(self, position: Tuple[float, float], size: Tuple[float, float] = (80, 120),
                 slow_multiplier: float = 0.4):
        """
        Initialize slow zone

        Args:
            position: (x, y) position
            size: (width, height) of zone
            slow_multiplier: Speed multiplier when in zone (0.5 = half speed)
        """
        super().__init__(position, size)
        self.slow_multiplier = slow_multiplier
        self.is_moving = False
        self.color = (139, 90, 43)  # Brown/mud color

    def check_collision(self, racer_pos: Tuple[float, float], racer_radius: float) -> bool:
        """Check if racer is inside the slow zone"""
        return (self.x <= racer_pos[0] <= self.x + self.width and
                self.y <= racer_pos[1] <= self.y + self.height)

    def apply_collision_effect(self, racer):
        """Apply slow effect to racer"""
        racer.in_slow_zone = True
        racer.slow_zone_multiplier = self.slow_multiplier


class Bumper(Obstacle):
    """
    Circular pinball-style bumper that bounces racers away
    """

    def __init__(self, position: Tuple[float, float], radius: float = 25,
                 bounce_force: float = 12.0):
        """
        Initialize bumper

        Args:
            position: (x, y) center position
            radius: Radius of bumper
            bounce_force: Force applied when bouncing racer
        """
        super().__init__(position, (radius * 2, radius * 2))
        self.center_x = position[0]
        self.center_y = position[1]
        self.radius = radius
        self.bounce_force = bounce_force
        self.is_moving = False
        self.color = (255, 100, 150)  # Pink
        self.hit_color = (255, 255, 100)  # Yellow flash when hit
        self.is_hit = False
        self.hit_timer = 0

    def update(self, dt: float):
        """Update hit flash timer"""
        if self.is_hit:
            self.hit_timer -= dt
            if self.hit_timer <= 0:
                self.is_hit = False

    def check_collision(self, racer_pos: Tuple[float, float], racer_radius: float) -> bool:
        """Check circle-circle collision"""
        import math
        dx = racer_pos[0] - self.center_x
        dy = racer_pos[1] - self.center_y
        distance = math.sqrt(dx * dx + dy * dy)
        return distance < (self.radius + racer_radius)

    def apply_collision_effect(self, racer):
        """Bounce racer away from bumper"""
        import math
        dx = racer.x - self.center_x
        dy = racer.y - self.center_y
        distance = math.sqrt(dx * dx + dy * dy)

        if distance > 0:
            # Normalize direction
            norm_dx = dx / distance
            norm_dy = dy / distance

            # Push racer outside the bumper immediately to prevent sticking
            min_distance = self.radius + config.FOLLOWER_RADIUS + 2
            if distance < min_distance:
                racer.x = self.center_x + norm_dx * min_distance
                racer.y = self.center_y + norm_dy * min_distance

            # Apply strong bounce force
            racer.push_vx = norm_dx * self.bounce_force
            racer.push_vy = norm_dy * self.bounce_force

            # Also clear committed direction to force new path
            racer.committed_direction = None

            # Trigger hit flash (only if not already flashing)
            if not self.is_hit:
                self.is_hit = True
                self.hit_timer = 0.15


class Crusher(Obstacle):
    """
    Piston that extends across part of track then retracts
    Timing-based obstacle
    """

    def __init__(self, position: Tuple[float, float], size: Tuple[float, float] = (30, 80),
                 extend_time: float = 1.0, retract_time: float = 2.0,
                 extended_width: float = 80):
        """
        Initialize crusher

        Args:
            position: (x, y) base position (retracted)
            size: (width, height) when retracted
            extend_time: Time crusher stays extended
            retract_time: Time crusher stays retracted
            extended_width: Width when fully extended
        """
        super().__init__(position, size)
        self.base_x = position[0]
        self.base_width = size[0]
        self.extended_width = extended_width
        self.extend_time = extend_time
        self.retract_time = retract_time
        self.cycle_time = extend_time + retract_time
        self.timer = 0
        self.is_extended = False
        self.current_width = self.base_width
        self.is_moving = True
        self.color = (100, 100, 150)  # Blue-gray
        self.extended_color = (200, 80, 80)  # Red when extended

    def update(self, dt: float):
        """Update crusher state"""
        self.timer += dt

        # Cycle through retract/extend (start retracted so racers can pass)
        cycle_pos = self.timer % self.cycle_time

        if cycle_pos < self.retract_time:
            # Retracted phase - racers can pass
            self.is_extended = False
            self.current_width = self.base_width
            self.width = self.current_width
        else:
            # Extended phase - blocks passage
            self.is_extended = True
            self.current_width = self.extended_width
            self.width = self.current_width

    def apply_collision_effect(self, racer):
        """Push racer back and out of crusher"""
        # Push racer to the left of the crusher (behind it)
        racer.x = self.x - config.FOLLOWER_RADIUS - 5

        # Apply strong push back velocity
        racer.push_vx = -20.0

        # Clear direction to pick new path
        racer.committed_direction = None
