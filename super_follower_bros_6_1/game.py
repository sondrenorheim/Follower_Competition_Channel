from super_follower_bros_shared.scene_game import SuperFollowerBrosSceneGame

GAME_MODE = "super_follower_bros_6_1"


class SuperFollowerBros61Game(SuperFollowerBrosSceneGame):
    def __init__(self):
        super().__init__(GAME_MODE)


def create_game():
    return SuperFollowerBros61Game()


Game = SuperFollowerBros61Game
