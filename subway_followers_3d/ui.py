from direct.gui.OnscreenText import OnscreenText
from panda3d.core import TextNode


class SubwayUI3D:
    def __init__(self, config):
        self.config = config
        self.title = OnscreenText(
            text="SUBWAY FOLLOWERS",
            pos=(0, 0.86),
            scale=0.085,
            fg=(1, 1, 1, 1),
            align=TextNode.ACenter,
        )
        self.subtitle = OnscreenText(
            text="Making my followers run every day",
            pos=(0, 0.79),
            scale=0.05,
            fg=(1, 1, 1, 1),
            align=TextNode.ACenter,
        )
        self.day_counter = OnscreenText(
            text="",
            pos=(0, -0.9),
            scale=0.055,
            fg=(1, 1, 1, 1),
            align=TextNode.ACenter,
        )
        self.stats = OnscreenText(
            text="",
            pos=(-1.15, 0.8),
            scale=0.045,
            fg=(1, 1, 1, 1),
            align=TextNode.ALeft,
            mayChange=True,
        )
        self.end_card = None

    def update_day_counter(self, total_players: int, label: str):
        text = f"Day {self.config.DAY_NUMBER}: {total_players} {label}"
        self.day_counter.setText(text)

    def update_stats(self, alive_count: int, speed: float, elapsed: float):
        text = f"Alive: {alive_count}\nSpeed: {speed:.1f}\nTime: {elapsed:.1f}s"
        self.stats.setText(text)

    def show_end_screen(self, lines: list):
        if self.end_card:
            self.end_card.destroy()
        joined = "\n".join(lines)
        self.end_card = OnscreenText(
            text=joined,
            pos=(0, 0.2),
            scale=0.055,
            fg=(1, 0.95, 0.7, 1),
            align=TextNode.ACenter,
            mayChange=False,
        )

    def cleanup(self):
        for item in (self.title, self.subtitle, self.day_counter, self.stats, self.end_card):
            if item:
                item.destroy()
