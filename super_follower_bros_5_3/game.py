from super_follower_bros_shared.scene_game import SuperFollowerBrosSceneGame

GAME_MODE = "super_follower_bros_5_3"


class SuperFollowerBros53Game(SuperFollowerBrosSceneGame):
    def __init__(self):
        super().__init__(GAME_MODE)


def create_game():
    return SuperFollowerBros53Game()


Game = SuperFollowerBros53Game
