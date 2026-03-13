from super_follower_bros_shared.player import SuperFollowerBrosPlayer as _SharedSuperFollowerBrosPlayer


class SuperFollowerBrosPlayer(_SharedSuperFollowerBrosPlayer):
    """Thin game-local wrapper around the shared Super Follower Bros movement AI."""


__all__ = ["SuperFollowerBrosPlayer"]
