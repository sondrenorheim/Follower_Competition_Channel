from super_follower_bros_shared.scene_game import SuperFollowerBrosSceneGame

GAME_MODE = "super_follower_bros"


class SuperFollowerBrosGame(SuperFollowerBrosSceneGame):
    def __init__(self):
        super().__init__(GAME_MODE)


def create_game():
    return SuperFollowerBrosGame()


Game = SuperFollowerBrosGame

__all__ = ["SuperFollowerBrosGame", "Game", "create_game"]
