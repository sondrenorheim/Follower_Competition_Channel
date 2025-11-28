"""
Level generation and management for vertical climbing platformer race.

Hand-designed vertical course with platforms, ladders, ropes, and checkpoints.
"""

from .platform import Platform
from .spike import Spike
from .checkpoint import Checkpoint
from .climbable import Ladder, Rope, ClimbableWall
from .goal import Goal


class PlatformerLevel:
    """Contains all level data and geometry for vertical climbing"""

    def __init__(self):
        """Create empty level"""
        # Level geometry
        self.platforms = []
        self.ladders = []
        self.ropes = []
        self.walls = []
        self.spikes = []
        self.checkpoints = []
        self.goal = None

        # Level bounds (extended viewport: 500x700 game area)
        self.width = 500
        self.height = 700
        self.start_y = 600  # Bottom (Floor 1)
        self.goal_y = 50    # Top-right final platform (updated for extended viewport)

    @staticmethod
    def generate_level():
        """
        Generate 5-floor platformer race level with progressive difficulty
        Theme: Vertical climb with alternating left/right navigation
        Path: Bottom-left to top with increasing challenge

        Returns:
            PlatformerLevel instance with 5-floor layout
        """
        level = PlatformerLevel()

        # Colors
        stone_gray = (90, 90, 90)
        dark_stone = (70, 70, 75)
        goal_green = (100, 200, 100)

        # ===== FLOOR 1: GROUND (Y=600) - Move RIGHT - EASY =====

        # Starting platform
        level.platforms.append(Platform(
            x=10, y=600, width=140, height=20,
            color=stone_gray
        ))

        # Spikes - first challenge
        level.spikes.append(Spike(
            x=150, y=610, width=30, height=8,
            orientation="up"
        ))

        # Mid platform in spike pit
        level.platforms.append(Platform(
            x=180, y=605, width=40, height=15,
            color=dark_stone
        ))

        level.spikes.append(Spike(
            x=220, y=610, width=30, height=8,
            orientation="up"
        ))

        # Landing platform
        level.platforms.append(Platform(
            x=250, y=600, width=100, height=20,
            color=stone_gray
        ))

        # Right platform
        level.platforms.append(Platform(
            x=365, y=600, width=125, height=20,
            color=stone_gray
        ))

        # Stairs to Floor 2
        level.platforms.append(Platform(
            x=430, y=565, width=60, height=12,
            color=stone_gray
        ))

        level.platforms.append(Platform(
            x=420, y=530, width=80, height=12,
            color=stone_gray
        ))

        # ===== FLOOR 2: LOWER MID (Y=480) - Move LEFT - MEDIUM =====

        # Right platform (stairs arrival)
        level.platforms.append(Platform(
            x=350, y=480, width=150, height=15,
            color=stone_gray
        ))

        # Middle platform
        level.platforms.append(Platform(
            x=200, y=480, width=130, height=15,
            color=stone_gray
        ))

        # Left platform (ladder area)
        level.platforms.append(Platform(
            x=10, y=480, width=170, height=15,
            color=stone_gray
        ))

        # Checkpoint 1
        level.checkpoints.append(Checkpoint(
            x=450, y=470, index=1
        ))

        # Ladder to Floor 3
        level.ladders.append(Ladder(
            x=35, y=360, height=120
        ))

        # ===== FLOOR 3: CENTER (Y=360) - Move RIGHT - MEDIUM-HARD =====

        # Ladder arrival
        level.platforms.append(Platform(
            x=10, y=360, width=70, height=15,
            color=stone_gray
        ))

        # Small platform
        level.platforms.append(Platform(
            x=90, y=360, width=50, height=15,
            color=stone_gray
        ))

        # Spike safe platform
        level.platforms.append(Platform(
            x=165, y=363, width=35, height=12,
            color=dark_stone
        ))

        # Spikes
        level.spikes.append(Spike(
            x=145, y=365, width=20, height=8,
            orientation="up"
        ))

        level.spikes.append(Spike(
            x=200, y=365, width=20, height=8,
            orientation="up"
        ))

        # Medium platform
        level.platforms.append(Platform(
            x=220, y=360, width=80, height=15,
            color=stone_gray
        ))

        # After gap (reduced from x=340 to x=320 for smaller jump)
        level.platforms.append(Platform(
            x=320, y=360, width=65, height=15,
            color=stone_gray
        ))

        # Checkpoint platform
        level.platforms.append(Platform(
            x=405, y=360, width=85, height=15,
            color=stone_gray
        ))

        # Checkpoint 2
        level.checkpoints.append(Checkpoint(
            x=45, y=350, index=2
        ))

        # Stairs up
        level.platforms.append(Platform(
            x=460, y=325, width=30, height=12,
            color=stone_gray
        ))

        # ===== FLOOR 4: UPPER MID (Y=240) - Move LEFT - HARD =====
        # Features one large 100px jump challenge

        # Right platform (stairs arrival to jump edge)
        level.platforms.append(Platform(
            x=290, y=240, width=210, height=15,
            color=stone_gray
        ))

        # ===== 100px GAP (x=190 to x=290) =====

        # Left platform (after jump to ladder)
        level.platforms.append(Platform(
            x=10, y=240, width=180, height=15,
            color=stone_gray
        ))

        # Checkpoint 3
        level.checkpoints.append(Checkpoint(
            x=450, y=230, index=3
        ))

        # Ladder to Floor 5
        level.ladders.append(Ladder(
            x=35, y=120, height=120
        ))

        # ===== FLOOR 5: TOP (Y=120) - Move RIGHT - VERY HARD =====
        # Alternating platforms and spikes challenge to the finish

        # Ladder arrival
        level.platforms.append(Platform(
            x=10, y=120, width=50, height=15,
            color=stone_gray
        ))

        # Platform 1
        level.platforms.append(Platform(
            x=70, y=120, width=30, height=15,
            color=stone_gray
        ))

        # Spike 1
        level.spikes.append(Spike(
            x=105, y=125, width=20, height=8,
            orientation="up"
        ))

        # Platform 2
        level.platforms.append(Platform(
            x=130, y=120, width=30, height=15,
            color=stone_gray
        ))

        # Spike 2
        level.spikes.append(Spike(
            x=165, y=125, width=20, height=8,
            orientation="up"
        ))

        # Platform 3
        level.platforms.append(Platform(
            x=190, y=120, width=30, height=15,
            color=stone_gray
        ))

        # Platform 4
        level.platforms.append(Platform(
            x=250, y=120, width=30, height=15,
            color=stone_gray
        ))

        # Spike 4
        level.spikes.append(Spike(
            x=285, y=125, width=20, height=8,
            orientation="up"
        ))

        # Platform 5
        level.platforms.append(Platform(
            x=310, y=120, width=30, height=15,
            color=stone_gray
        ))

        # Spike 5
        level.spikes.append(Spike(
            x=345, y=125, width=20, height=8,
            orientation="up"
        ))

        # Platform 6
        level.platforms.append(Platform(
            x=370, y=120, width=30, height=15,
            color=stone_gray
        ))

        # Spike 6
        level.spikes.append(Spike(
            x=405, y=125, width=20, height=8,
            orientation="up"
        ))

        # Final platform before finish
        level.platforms.append(Platform(
            x=430, y=120, width=60, height=15,
            color=stone_gray
        ))

        # Checkpoint 4
        level.checkpoints.append(Checkpoint(
            x=45, y=110, index=4
        ))

        # ===== FINISH AREA (Y=70) =====

        # Goal platform
        level.platforms.append(Platform(
            x=400, y=70, width=90, height=15,
            color=goal_green
        ))

        # Goal flag
        level.goal = Goal(x=480, y=50)

        return level

    def get_all_climbables(self):
        """
        Get list of all climbable objects

        Returns:
            List of all ladders, ropes, and walls
        """
        return self.ladders + self.ropes + self.walls

    def get_climbable_at(self, x, y):
        """
        Find climbable object at given position

        Args:
            x: X coordinate
            y: Y coordinate

        Returns:
            Climbable object if found, None otherwise
        """
        for obj in self.get_all_climbables():
            if obj.contains_point(x, y):
                return obj
        return None

    def find_climbable_nearby(self, racer, radius=30):
        """
        Find climbable object near racer

        Args:
            racer: Racer object
            radius: Search radius

        Returns:
            Closest climbable object within radius, or None
        """
        import math

        closest = None
        closest_distance = radius

        for obj in self.get_all_climbables():
            # Check distance to climbable object
            # For simplicity, check distance to object center
            obj_center_x = obj.x + (obj.width / 2 if hasattr(obj, 'width') else 0)
            obj_center_y = obj.y + (obj.height / 2)

            distance = math.dist((racer.x, racer.y), (obj_center_x, obj_center_y))

            if distance < closest_distance:
                closest = obj
                closest_distance = distance

        return closest

    def find_platform_above(self, racer, max_distance=150):
        """
        Find nearest platform above racer

        Args:
            racer: Racer object
            max_distance: Maximum vertical distance to search

        Returns:
            Platform above racer, or None
        """
        candidates = []

        for platform in self.platforms:
            # Platform must be above racer
            if platform.y < racer.y:
                vertical_distance = racer.y - platform.y

                if vertical_distance <= max_distance:
                    # Check if racer could potentially reach it horizontally
                    # Allow some horizontal leeway
                    horizontal_distance = abs(platform.x + platform.width / 2 - racer.x)

                    if horizontal_distance < 150:  # Within reasonable horizontal range
                        candidates.append((platform, vertical_distance, horizontal_distance))

        if not candidates:
            return None

        # Sort by vertical distance (prioritize closer platforms)
        candidates.sort(key=lambda x: x[1])
        return candidates[0][0]

    def find_platform_below(self, racer):
        """
        Find nearest platform below racer

        Args:
            racer: Racer object

        Returns:
            Platform below racer, or None
        """
        candidates = []

        for platform in self.platforms:
            # Platform must be below racer
            if platform.y > racer.y:
                vertical_distance = platform.y - racer.y

                # Check horizontal overlap
                if (racer.x + racer.radius >= platform.x and
                    racer.x - racer.radius <= platform.x + platform.width):
                    candidates.append((platform, vertical_distance))

        if not candidates:
            return None

        # Sort by vertical distance (closest first)
        candidates.sort(key=lambda x: x[1])
        return candidates[0][0]
