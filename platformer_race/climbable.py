"""
Climbable objects for vertical climbing platformer.

Includes Ladder, Rope, and ClimbableWall classes.
"""


class Ladder:
    """
    Ladder that players can climb up and down
    """

    def __init__(self, x, y, height, width=20):
        """
        Create a ladder

        Args:
            x: X position (left edge)
            y: Y position (top edge)
            height: Height of ladder in pixels
            width: Width of ladder in pixels (default 20)
        """
        self.type = "ladder"
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.color = (139, 90, 43)  # Brown

    def contains_point(self, x, y):
        """Check if point is within ladder bounds"""
        return (self.x <= x <= self.x + self.width and
                self.y <= y <= self.y + self.height)

    def check_overlap(self, racer):
        """Check if racer overlaps with ladder - reasonable tolerance for gameplay"""
        # Reasonable horizontal overlap - 10 pixels on each side
        racer_left = racer.x - racer.radius
        racer_right = racer.x + racer.radius

        # Moderate horizontal tolerance for grabbing
        horizontal_tolerance = 10
        if racer_right >= self.x - horizontal_tolerance and racer_left <= self.x + self.width + horizontal_tolerance:
            # Check vertical overlap - moderate grab zone
            racer_top = racer.y - racer.radius
            racer_bottom = racer.y + racer.radius

            # Moderate vertical grab zone
            ladder_grab_zone_top = self.y - racer.radius * 2  # Moderate distance above
            ladder_grab_zone_bottom = self.y + self.height + racer.radius * 2  # Moderate distance below

            if racer_bottom >= ladder_grab_zone_top and racer_top <= ladder_grab_zone_bottom:
                return True

        return False


class Rope:
    """
    Rope that players can climb up and down
    Slightly slower than ladder
    """

    def __init__(self, x, y, height, width=8):
        """
        Create a rope

        Args:
            x: X position (center)
            y: Y position (top edge)
            height: Height of rope in pixels
            width: Width for grab detection (default 8)
        """
        self.type = "rope"
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.color = (101, 67, 33)  # Dark brown

    def contains_point(self, x, y):
        """Check if point is within rope grab distance"""
        # Rope has wider grab area than visible width
        grab_distance = 20
        return (abs(x - self.x) <= grab_distance and
                self.y <= y <= self.y + self.height)

    def check_overlap(self, racer):
        """Check if racer is close enough to grab rope"""
        # Rope has wider grab area
        grab_distance = 20
        distance = abs(racer.x - self.x)

        if distance < grab_distance:
            # Check vertical overlap
            racer_top = racer.y - racer.radius
            racer_bottom = racer.y + racer.radius

            if racer_bottom >= self.y and racer_top <= self.y + self.height:
                return True

        return False


class ClimbableWall:
    """
    Wall that players can grab and shimmy along
    Allows horizontal movement but slower climb speed
    """

    def __init__(self, x, y, height, width=15):
        """
        Create a climbable wall

        Args:
            x: X position (left edge)
            y: Y position (top edge)
            height: Height of wall in pixels
            width: Width of wall in pixels (default 15)
        """
        self.type = "wall"
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.color = (100, 100, 110)  # Gray

    def contains_point(self, x, y):
        """Check if point is within wall bounds"""
        return (self.x <= x <= self.x + self.width and
                self.y <= y <= self.y + self.height)

    def check_overlap(self, racer):
        """Check if racer is adjacent to wall"""
        # Check if racer is touching wall from either side
        grab_distance = racer.radius + 5

        # Left side
        distance_left = abs((racer.x + racer.radius) - self.x)
        # Right side
        distance_right = abs((racer.x - racer.radius) - (self.x + self.width))

        min_distance = min(distance_left, distance_right)

        if min_distance < grab_distance:
            # Check vertical overlap
            racer_top = racer.y - racer.radius
            racer_bottom = racer.y + racer.radius

            if racer_bottom >= self.y and racer_top <= self.y + self.height:
                return True

        return False


def get_climbable_at_position(x, y, climbables):
    """
    Find climbable object at given position

    Args:
        x: X coordinate
        y: Y coordinate
        climbables: List of all climbable objects (ladders, ropes, walls)

    Returns:
        Climbable object if found, None otherwise
    """
    for obj in climbables:
        if obj.contains_point(x, y):
            return obj
    return None


def get_climbable_for_racer(racer, climbables):
    """
    Find climbable object that racer can grab

    Args:
        racer: Racer object
        climbables: List of all climbable objects (ladders, ropes, walls)

    Returns:
        Climbable object if found, None otherwise
    """
    for obj in climbables:
        if obj.check_overlap(racer):
            return obj
    return None
