"""
Independent platformer physics engine with gravity, jumping, and platform collision.

This is separate from shared/physics.py which handles collision-based knockback for fighter games.
This physics system is designed specifically for platformer mechanics.
"""

import config


class PlatformerPhysics:
    """Handles platformer-specific physics: gravity, jumping, platform collision, climbing"""

    # Physics constants - Jumping
    GRAVITY = 1200.0              # pixels/sec² downward
    MAX_FALL_SPEED = 800.0        # Terminal velocity
    JUMP_VELOCITY = -420.0        # Initial upward velocity (negative = up) - reduced for lower jumps
    JUMP_COOLDOWN = 0.2           # Seconds between jumps
    PLATFORM_SURFACE_HEIGHT = 8.0 # Pixels above platform to be "on ground" (increased for better detection)

    # Physics constants - Climbing
    CLIMB_SPEED = 120.0           # pixels/sec up/down on ladder
    ROPE_CLIMB_SPEED = 100.0      # Slightly slower on rope
    WALL_SHIMMY_SPEED = 80.0      # Horizontal movement on wall
    WALK_SPEED = 150.0            # pixels/sec on ground
    AIR_CONTROL = 0.3             # Reduced control while jumping/falling

    def __init__(self):
        pass

    def apply_gravity(self, racer, dt):
        """
        Apply gravity to racer's vertical velocity

        Args:
            racer: PlatformerRacer instance
            dt: Delta time in seconds
        """
        racer.vy += self.GRAVITY * dt
        # Cap fall speed at terminal velocity
        racer.vy = min(racer.vy, self.MAX_FALL_SPEED)

    def check_platform_landing(self, racer, platforms):
        """
        Check if racer lands on top of a platform

        Conditions for landing:
        1. Racer is falling (vy > 0)
        2. Racer's bottom edge overlaps platform's top surface
        3. Racer was above platform in previous frame

        Args:
            racer: PlatformerRacer instance
            platforms: List of Platform objects

        Returns:
            Platform if landed, None otherwise
        """
        if racer.vy <= 0:  # Not falling
            racer.on_ground = False
            return None

        racer_bottom = racer.y + racer.radius

        for platform in platforms:
            # Check horizontal overlap - use center-based check with edge tolerance
            # This prevents landing on platforms when mostly hanging off the edge
            edge_tolerance = racer.radius * 0.3  # Allow 30% of radius to hang off edge
            if (racer.x >= platform.x - edge_tolerance and
                racer.x <= platform.x + platform.width + edge_tolerance):

                # Check if racer's bottom is near platform top
                # Allow up to 15px leeway to catch racers that fell through
                if (racer_bottom >= platform.y and
                    racer_bottom <= platform.y + self.PLATFORM_SURFACE_HEIGHT + 15):

                    # Land on platform - snap to surface
                    racer.y = platform.y - racer.radius
                    racer.vy = 0
                    racer.on_ground = True
                    return platform

        racer.on_ground = False
        return None

    def check_platform_side_collision(self, racer, platforms):
        """
        Check if racer collides with the SIDE of a platform (not bottom)
        Pushes racer away if collision detected

        Note: Platforms are one-way - you can jump through from below!

        Args:
            racer: PlatformerRacer instance
            platforms: List of Platform objects
        """
        for platform in platforms:
            # Get platform bounds
            plat_left = platform.x
            plat_right = platform.x + platform.width
            plat_top = platform.y
            plat_bottom = platform.y + platform.height

            # Get racer bounds
            racer_left = racer.x - racer.radius
            racer_right = racer.x + racer.radius
            racer_top = racer.y - racer.radius
            racer_bottom = racer.y + racer.radius

            # Check AABB collision
            if (racer_right >= plat_left and racer_left <= plat_right and
                racer_bottom >= plat_top and racer_top <= plat_bottom):

                # Racer is colliding with platform
                # Only handle LEFT and RIGHT collisions (not top or bottom)

                # Calculate overlap on each side
                overlap_left = racer_right - plat_left
                overlap_right = plat_right - racer_left
                overlap_top = racer_bottom - plat_top
                overlap_bottom = plat_bottom - racer_top

                # Find minimum overlap (the side we hit)
                min_overlap = min(overlap_left, overlap_right, overlap_top, overlap_bottom)

                # Only push out from LEFT or RIGHT sides
                if min_overlap == overlap_left:
                    # Hit left side of platform
                    racer.x = plat_left - racer.radius - 1
                    racer.vx = 0  # Stop horizontal movement

                elif min_overlap == overlap_right:
                    # Hit right side of platform
                    racer.x = plat_right + racer.radius + 1
                    racer.vx = 0

                # REMOVED: Bottom collision - allow jumping through from below!
                # Top collision is handled by check_platform_landing()

    def update_horizontal_movement(self, racer, dt):
        """
        Update racer's horizontal position based on constant speed
        No acceleration - just constant forward movement

        Args:
            racer: PlatformerRacer instance
            dt: Delta time in seconds
        """
        racer.x += racer.horizontal_speed * dt

    def update_racer_physics(self, racer, platforms, dt):
        """
        Main physics update - call this each frame

        Args:
            racer: PlatformerRacer instance
            platforms: List of all platforms (static + moving)
            dt: Delta time in seconds
        """
        # Apply gravity
        self.apply_gravity(racer, dt)

        # Update vertical position
        racer.y += racer.vy * dt

        # Horizontal movement is now AI-directed via walk_left/walk_right in racer.update_racer()
        # No automatic horizontal movement for vertical climbing version

        # Check platform landing
        self.check_platform_landing(racer, platforms)

        # Check side collisions
        self.check_platform_side_collision(racer, platforms)

        # Safety check: if racer is inside a platform, snap them to the top
        # This prevents racers from getting stuck or falling through
        # BUT: Use stricter overlap check so racers can fall through gaps
        racer_bottom = racer.y + racer.radius
        for platform in platforms:
            # Check if racer's CENTER is within platform bounds (with small edge tolerance)
            # This allows racers to fall through gaps instead of walking on air
            edge_tolerance = racer.radius * 0.3  # Allow 30% of radius to hang off edge
            if (racer.x >= platform.x - edge_tolerance and
                racer.x <= platform.x + platform.width + edge_tolerance):
                # Check if racer is inside platform (bottom is below platform top)
                if (racer_bottom > platform.y and
                    racer.y < platform.y + platform.height):
                    # Snap racer to top of platform
                    racer.y = platform.y - racer.radius
                    racer.vy = 0
                    racer.on_ground = True

    def update_climbing_movement(self, racer, climbable, direction, dt):
        """
        Update racer position while climbing

        Args:
            racer: PlatformerRacer instance
            climbable: Climbable object (Ladder, Rope, or Wall)
            direction: 1 for up, -1 for down, 0 for no movement
            dt: Delta time in seconds
        """
        if direction == 0:
            return

        # Get climb speed based on object type
        if climbable.type == "ladder":
            speed = self.CLIMB_SPEED
        elif climbable.type == "rope":
            speed = self.ROPE_CLIMB_SPEED
        elif climbable.type == "wall":
            speed = self.WALL_SHIMMY_SPEED
        else:
            speed = self.CLIMB_SPEED

        # Move racer vertically (negative = up)
        racer.y += -direction * speed * dt

        # Clamp to climbable bounds
        racer.y = max(climbable.y, min(racer.y, climbable.y + climbable.height))

        # Reset velocities while climbing
        racer.vy = 0
        racer.vx = 0

    def respawn_at_start(self, racer, start_x=70, start_y=430):
        """
        Respawn racer at starting position (bottom-left)

        Args:
            racer: PlatformerRacer instance
            start_x: X position to respawn at (default 70)
            start_y: Y position to respawn at (default 430)
        """
        racer.x = start_x
        racer.y = start_y
        racer.vx = 0
        racer.vy = 0
        racer.on_ground = False
        # Don't change state here - let racer handle that
