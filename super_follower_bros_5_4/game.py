from super_follower_bros_shared.scene_game import SuperFollowerBrosSceneGame

GAME_MODE = "super_follower_bros_5_4"


class SuperFollowerBros54Game(SuperFollowerBrosSceneGame):
    def __init__(self):
        super().__init__(GAME_MODE)


def create_game():
    return SuperFollowerBros54Game()


Game = SuperFollowerBros54Game
