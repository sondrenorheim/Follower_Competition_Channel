"""
Vertical Climbing AI system for platformer race.

Improved AI with pathfinding, stuck detection, and intelligent navigation.
"""

import random
import math


class JumpAI:
    """AI for vertical climbing platformer with intelligent pathfinding"""

    def __init__(self):
        pass

    def decide_action(self, racer, level):
        """
        Main AI decision function for horizontal racing with vertical elements

        Args:
            racer: PlatformerRacer instance
            level: PlatformerLevel instance

        Returns:
            String: Action to take ("jump", "climb_up", "walk_left", "walk_right", "air_left", "air_right", "air_brake", "air_continue", "none")
        """
        if not level.goal:
            return "none"

        # Apply mistake chance
        if random.random() < racer.mistake_chance:
            return self._make_mistake(racer)

        # Priority 1: If currently climbing, keep climbing
        if racer.current_climbable and racer.y > level.goal.y + 20:
            if racer.y > racer.current_climbable.y + 5:
                return "climb_up"

        # Priority 2: If on ground, navigate intelligently
        if racer.on_ground:
            # Use floor-based direction instead of always moving toward goal
            # This allows dynamic zig-zag navigation
            moving_right = (racer.target_direction == "right")

            # CHECK FOR GAPS: Look ahead and jump if there's a gap
            # If they fail the jump, they'll fall through as punishment
            gap_ahead = self._check_gap_ahead(racer, level.platforms, moving_right)

            if gap_ahead:
                # There's a gap ahead - jump to cross it
                return "jump"

            # Priority: On floor 2 (moving left), constantly try to climb
            if racer.current_floor == 2:
                # Always try to climb - the massive overlap check will handle whether it works
                # If we're in the left area where the ladder is, this will grab it
                if racer.x < 120:  # Left side of floor 2 where ladder is located
                    return "climb_up"
                # Otherwise keep moving left to reach the ladder
                return "walk_left"

            # Check if we should change floors (reached edge of current floor)
            # If moving right and close to right edge, or moving left and close to left edge
            # Then look for vertical movement options
            if moving_right and racer.x > 450:  # Near right edge
                # Look for ways to go up/down
                best_climbable = self._find_best_climbable(racer, level)
                if best_climbable and self._is_close_to_climbable(racer, best_climbable):
                    return "climb_up"
                # Or try to jump to platform above
                platform_above = self._find_best_platform_above(racer, level)
                if platform_above and self._can_reach_with_jump(racer, platform_above):
                    return "jump"
            elif not moving_right and racer.x < 50:  # Near left edge
                # Look for ways to go up/down
                best_climbable = self._find_best_climbable(racer, level)
                if best_climbable and self._is_close_to_climbable(racer, best_climbable):
                    return "climb_up"
                # Or try to jump to platform above
                platform_above = self._find_best_platform_above(racer, level)
                if platform_above and self._can_reach_with_jump(racer, platform_above):
                    return "jump"

            # Special handling for top floor (near goal) - move towards goal precisely
            # Only apply to Floor 5, not Floor 4 (Floor 4 needs to reach ladder on left)
            if racer.current_floor >= 5 and level.goal:
                # Near the goal - move towards it carefully
                horizontal_distance = level.goal.x - racer.x
                if abs(horizontal_distance) < 10:
                    # Very close to goal - stop moving to avoid running past it
                    return "none"
                elif horizontal_distance > 0:
                    return "walk_right"
                else:
                    return "walk_left"

            # Continue moving in the target direction for this floor
            return "walk_right" if moving_right else "walk_left"

        # Priority 3: If in air, smart air control
        if not racer.on_ground:
            # First priority: grab climbables if available
            nearby_climbable = level.find_climbable_nearby(racer, radius=25)
            if nearby_climbable and self._should_grab_climbable(racer, nearby_climbable, level.goal):
                return "climb_up"

            # Second priority: air control to land safely
            # Check if there's a safe platform below
            safe_landing = self._find_safe_landing_spot(racer, level.platforms, level.spikes if hasattr(level, 'spikes') else [])

            if safe_landing:
                # We see a safe landing spot - only adjust if it's in our movement direction
                distance_to_landing = safe_landing - racer.x
                moving_right = (racer.target_direction == "right")

                # Only use air control if the landing spot is in the direction we're already moving
                if (moving_right and distance_to_landing > 0) or (not moving_right and distance_to_landing < 0):
                    if abs(distance_to_landing) < 5:
                        # We're very close to the safe spot - slow down to land precisely
                        return "air_brake"
                    else:
                        # Continue in floor direction
                        return "air_continue"
                else:
                    # Landing spot is behind us - just continue forward
                    return "air_continue"
            else:
                # No safe landing visible - continue in floor direction
                return "air_continue"

        return "none"

    def _find_safe_landing_spot(self, racer, platforms, spikes):
        """
        Find a safe platform to land on (avoiding spikes)

        Args:
            racer: PlatformerRacer instance
            platforms: List of platforms
            spikes: List of spikes

        Returns:
            float: X coordinate of safe landing center, or None if no safe spot found
        """
        # Only look for landing spots below the racer
        racer_bottom = racer.y + racer.radius

        # Find platforms within reasonable landing distance below
        landing_candidates = []

        for platform in platforms:
            # Platform must be below racer
            if platform.y > racer_bottom:
                vertical_distance = platform.y - racer_bottom

                # Must be within landing range (not too far below)
                if vertical_distance < 150:
                    # Check if platform has spikes on it
                    platform_safe = True
                    for spike in spikes:
                        # Check if spike is on this platform
                        spike_on_platform = (
                            spike.y >= platform.y - 10 and
                            spike.x >= platform.x and
                            spike.x <= platform.x + platform.width
                        )
                        if spike_on_platform:
                            platform_safe = False
                            break

                    if platform_safe:
                        # Calculate center of safe landing area
                        safe_center = platform.x + platform.width / 2
                        landing_candidates.append((safe_center, vertical_distance))

        if not landing_candidates:
            return None

        # Return the nearest safe landing (smallest vertical distance)
        landing_candidates.sort(key=lambda x: x[1])
        return landing_candidates[0][0]

    def _check_gap_ahead(self, racer, platforms, moving_right):
        """
        Check if there's a gap ahead of the racer

        Args:
            racer: PlatformerRacer instance
            platforms: List of platforms
            moving_right: True if moving right, False if moving left

        Returns:
            bool: True if there's a gap ahead and racer should jump
        """
        # Look ahead distance - increased to 35px to jump early enough
        look_ahead_distance = 35

        # Calculate the check position (ahead of racer)
        if moving_right:
            check_x = racer.x + racer.radius + look_ahead_distance
        else:
            check_x = racer.x - racer.radius - look_ahead_distance

        # Check if there's solid ground at the check position
        # Look for a platform at the same Y level (or slightly below)
        racer_bottom = racer.y + racer.radius

        for platform in platforms:
            # Check if platform is at the right height (same floor)
            if abs(platform.y - (racer_bottom)) < 20:
                # Check if platform covers the check position
                if platform.x <= check_x <= platform.x + platform.width:
                    # There's ground ahead, no gap
                    return False

        # No ground found ahead - there's a gap!
        return True

    def _find_best_climbable(self, racer, level):
        """
        Find the best climbable object to use (one that leads upward)

        Args:
            racer: PlatformerRacer instance
            level: PlatformerLevel instance

        Returns:
            Climbable object or None
        """
        climbables = level.get_all_climbables()

        # Find climbables that are above racer and within reasonable distance
        candidates = []
        for climbable in climbables:
            # Must lead upward
            if climbable.y < racer.y - 20:
                # Calculate distance
                horizontal_dist = abs(climbable.x + (climbable.width / 2 if hasattr(climbable, 'width') else 0) - racer.x)
                vertical_dist = racer.y - climbable.y

                # Must be within reasonable reach
                if horizontal_dist < 150 and vertical_dist < 200:
                    # Score based on how much it helps us progress + how close it is
                    score = vertical_dist * 2 - horizontal_dist  # Prioritize upward progress
                    candidates.append((climbable, score))

        if not candidates:
            return None

        # Return best climbable (highest score)
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]

    def _find_best_platform_above(self, racer, level):
        """
        Find the best platform to jump to (prioritizes upward progress)

        Args:
            racer: PlatformerRacer instance
            level: PlatformerLevel instance

        Returns:
            Platform object or None
        """
        all_platforms = level.platforms
        candidates = []

        for platform in all_platforms:
            # Must be above racer
            if platform.y < racer.y - 10:
                vertical_dist = racer.y - platform.y
                horizontal_dist = abs(platform.x + platform.width / 2 - racer.x)

                # Must be reachable
                if self._can_reach_with_jump(racer, platform):
                    # Score: prioritize vertical progress, but consider horizontal distance
                    score = vertical_dist * 3 - horizontal_dist
                    candidates.append((platform, score))

        if not candidates:
            return None

        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]

    def _find_nearest_useful_object(self, racer, level):
        """
        Find nearest object that can help progress upward

        Args:
            racer: PlatformerRacer instance
            level: PlatformerLevel instance

        Returns:
            Object (climbable or platform) or None
        """
        # Combine climbables and platforms
        objects = []

        # Add climbables that lead upward
        for climbable in level.get_all_climbables():
            if climbable.y < racer.y - 20:
                dist = math.dist((racer.x, racer.y),
                               (climbable.x + (climbable.width / 2 if hasattr(climbable, 'width') else 0),
                                climbable.y + climbable.height / 2))
                objects.append((climbable, dist))

        # Add platforms that are above
        for platform in level.platforms:
            if platform.y < racer.y - 10:
                dist = math.dist((racer.x, racer.y),
                               (platform.x + platform.width / 2, platform.y))
                objects.append((platform, dist))

        if not objects:
            return None

        # Return nearest
        objects.sort(key=lambda x: x[1])
        return objects[0][0]

    def _is_close_to_climbable(self, racer, climbable):
        """
        Check if racer is close enough to grab climbable
        Uses the climbable's own overlap check for consistency
        """
        # Use the climbable's built-in overlap check
        # This ensures AI and climbing logic are consistent
        return climbable.check_overlap(racer)

    def _get_direction_to_object(self, racer, obj):
        """
        Get horizontal direction to object

        Args:
            racer: PlatformerRacer instance
            obj: Object with x and possibly width attributes

        Returns:
            float: Negative for left, positive for right, magnitude is distance
        """
        if hasattr(obj, 'width'):
            target_x = obj.x + obj.width / 2
        else:
            target_x = obj.x

        return target_x - racer.x

    def _should_grab_climbable(self, racer, climbable, goal):
        """
        Check if racer should grab the climbable object

        Args:
            racer: PlatformerRacer instance
            climbable: Climbable object
            goal: Goal object

        Returns:
            bool: True if should grab
        """
        # Climb if it leads upward toward goal
        if climbable.y < racer.y and racer.y > goal.y:
            return True
        return False

    def _can_reach_with_jump(self, racer, platform):
        """
        Check if racer can reach platform with a jump

        Args:
            racer: PlatformerRacer instance
            platform: Platform object

        Returns:
            bool: True if reachable
        """
        if not racer.on_ground:
            return False

        # Calculate max jump height
        jump_velocity = racer.jump_velocity  # Negative value
        gravity = 1200.0
        max_jump_height = abs(jump_velocity ** 2) / (2 * gravity)

        # Check vertical distance
        vertical_distance = racer.y - platform.y

        if vertical_distance <= 0:
            return False  # Platform is not above

        if vertical_distance > max_jump_height:
            return False  # Too high to reach

        # Check horizontal distance
        platform_center = platform.x + platform.width / 2
        horizontal_distance = abs(platform_center - racer.x)

        # Can only jump ~100px horizontally
        if horizontal_distance > 100:
            return False

        return True

    def _calculate_direction_toward_goal(self, racer, level):
        """
        Calculate direction toward goal (fallback when no clear path)

        Args:
            racer: PlatformerRacer instance
            level: PlatformerLevel instance

        Returns:
            float: Negative for left, positive for right
        """
        if not level.goal:
            return 0

        goal_x = level.goal.x
        distance = goal_x - racer.x

        if abs(distance) < 20:
            return 0  # Close enough horizontally

        return distance

    def _make_mistake(self, racer):
        """
        Make a mistake action (for AI variety)

        Args:
            racer: PlatformerRacer instance

        Returns:
            String: Random action or no action
        """
        # Random chance to do nothing or wrong action
        choices = ["none", "none", "none", "jump", "walk_left", "walk_right"]
        return random.choice(choices)

    # Legacy methods for compatibility (not used but keep for now)
    def should_jump(self, racer, platforms, fireballs, current_time):
        """Legacy method - returns False"""
        return False
