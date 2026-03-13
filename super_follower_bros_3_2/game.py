from super_follower_bros_shared.scene_game import SuperFollowerBrosSceneGame

GAME_MODE = "super_follower_bros_3_2"


class SuperFollowerBros32Game(SuperFollowerBrosSceneGame):
    def __init__(self):
        super().__init__(GAME_MODE)


def create_game():
    return SuperFollowerBros32Game()


Game = SuperFollowerBros32Game
