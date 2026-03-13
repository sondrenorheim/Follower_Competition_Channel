from .game import SuperFollowerBros12Game


def create_game():
    return SuperFollowerBros12Game()


Game = SuperFollowerBros12Game

__all__ = ["SuperFollowerBros12Game", "Game", "create_game"]
