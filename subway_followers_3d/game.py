import random
import time

import config
from shared import GameHistory, PlayerStatistics, ScoringSystem, auto_push

from panda3d.core import (
    AmbientLight,
    ClockObject,
    DirectionalLight,
    WindowProperties,
    loadPrcFileData,
)
from direct.showbase.ShowBase import ShowBase

from .track import SubwayTrack3D
from .runner import SubwayRunner3D
from .spawner import SubwayObstacleSpawner3D
from .scenery import SubwayScenery3D
from .ui import SubwayUI3D
from .recorder import PandaVideoRecorder


class SubwayFollowers3DGame(ShowBase):
    GAME_TITLE = "SUBWAY FOLLOWERS"
    GAME_SUBTITLE = "Making my followers run every day"
    PLAYER_LABEL = "runners"

    def __init__(self):
        loadPrcFileData("", f"win-size {config.SCREEN_WIDTH} {config.SCREEN_HEIGHT}")
        loadPrcFileData("", "sync-video #f")
        loadPrcFileData("", "show-frame-rate-meter #f")

        super().__init__()
        self.disableMouse()

        props = WindowProperties()
        props.setTitle(self.GAME_TITLE)
        self.win.requestProperties(props)

        self.setBackgroundColor(0.05, 0.05, 0.08)
        self.clock = ClockObject.getGlobalClock()

        self.game_time = 0.0
        self.game_over = False
        self.end_timer = 0.0
        self.recent_eliminations = []

        self.statistics = PlayerStatistics()
        self.scoring = ScoringSystem()
        self.game_history = GameHistory()

        self._setup_lighting()
        self._setup_camera()

        self.track = SubwayTrack3D(
            render=self.render,
            loader=self.loader,
            width=float(getattr(config, "SUBWAY_3D_TRACK_WIDTH", 10.0)),
            segment_length=float(getattr(config, "SUBWAY_3D_TRACK_SEGMENT_LENGTH", 12.0)),
            segment_count=int(getattr(config, "SUBWAY_3D_TRACK_SEGMENT_COUNT", 8)),
            lane_count=int(getattr(config, "SUBWAY_LANE_COUNT", 3)),
            lane_padding=float(getattr(config, "SUBWAY_3D_LANE_PADDING", 0.6)),
            floor_color=getattr(config, "SUBWAY_3D_TRACK_COLOR", (0.22, 0.24, 0.28)),
            lane_line_color=getattr(config, "SUBWAY_3D_LANE_LINE_COLOR", (0.6, 0.6, 0.65)),
            config=config,
        )
        self.scenery = SubwayScenery3D(self.render, self.track, config)

        self.runners = []
        self._setup_runners()

        self.obstacles = []
        self.spawner = SubwayObstacleSpawner3D(self.render, self.loader, self.track, config)

        self.ui = SubwayUI3D(config)
        self.ui.update_day_counter(len(self.runners), self.PLAYER_LABEL)

        self.base_speed = float(getattr(config, "SUBWAY_3D_BASE_SPEED", 18.0))
        self.speed_boost = float(getattr(config, "SUBWAY_3D_SPEED_BOOST", 12.0))
        self.difficulty_ramp = float(getattr(config, "SUBWAY_DIFFICULTY_RAMP", 55.0))
        self.max_game_time = float(getattr(config, "SUBWAY_3D_MAX_GAME_TIME", getattr(config, "SUBWAY_MAX_GAME_TIME", 90.0)))

        self.video_recorder = PandaVideoRecorder(
            base=self,
            output_path=config.get_output_video_path(game_mode="subway_followers"),
            fps=getattr(config, "VIDEO_FPS", 30),
            record=getattr(config, "EXPORT_VIDEO", True),
        )

        self.taskMgr.add(self._update_task, "subway_followers_3d_update")

    def _setup_lighting(self):
        ambient = AmbientLight("ambient")
        ambient.setColor((0.45, 0.45, 0.5, 1))
        ambient_node = self.render.attachNewNode(ambient)
        self.render.setLight(ambient_node)

        directional = DirectionalLight("directional")
        directional.setColor((0.8, 0.8, 0.85, 1))
        directional_node = self.render.attachNewNode(directional)
        directional_node.setHpr(35, -45, 0)
        self.render.setLight(directional_node)

    def _setup_camera(self):
        cam_pos = getattr(config, "SUBWAY_3D_CAMERA_POS", (0, -18, 8))
        cam_look = getattr(config, "SUBWAY_3D_CAMERA_LOOK_AT", (0, 20, 3))
        self.camera.setPos(*cam_pos)
        self.camera.lookAt(*cam_look)

    def _setup_runners(self):
        if config.TEST_MINIMAL_PLAYERS:
            follower_data = self._fetch_followers(config.TEST_MINIMAL_PLAYER_COUNT)
        else:
            follower_data = self._fetch_followers(config.FOLLOWER_COUNT)

        random.shuffle(follower_data)

        runner_y = float(getattr(config, "SUBWAY_3D_RUNNER_Y", 8.0))
        jitter = float(getattr(config, "SUBWAY_3D_RUNNER_Y_JITTER", 1.5))

        for idx, data in enumerate(follower_data):
            payload = dict(data)
            if "avatar_image" not in payload and "avatar" in payload:
                payload["avatar_image"] = payload["avatar"]
            y_offset = runner_y + random.uniform(-jitter, jitter)
            runner = SubwayRunner3D(payload, self.render, self.track, config, idx, y_offset)
            self.runners.append(runner)

    def _fetch_followers(self, count):
        from shared import InstagramAPI
        api = InstagramAPI()
        return api.fetch_followers(count)

    def _difficulty(self) -> float:
        if self.difficulty_ramp <= 0:
            return 1.0
        return min(1.0, self.game_time / self.difficulty_ramp)

    def _update_task(self, task):
        dt = self.clock.getDt()
        dt = min(dt, config.MAX_DELTA_TIME)
        if getattr(config, "EXPORT_TIME_SCALE", 1.0) and getattr(config, "EXPORT_VIDEO", True):
            dt *= float(getattr(config, "EXPORT_TIME_SCALE", 1.0))

        if self.game_over:
            self.game_time += dt
            self.end_timer += dt
            if self.end_timer >= float(getattr(config, "SUBWAY_3D_END_SCREEN_DURATION", 5.0)):
                self._shutdown()
                return task.done
            self.video_recorder.capture_frame(self.game_time)
            return task.cont

        self.game_time += dt
        difficulty = self._difficulty()
        speed = self.base_speed + self.speed_boost * difficulty

        self.track.update(dt, speed, recycle_y=float(getattr(config, "SUBWAY_3D_TRACK_RECYCLE_Y", -5.0)))
        self.scenery.update(dt, speed)
        self.spawner.update(dt, difficulty, self.obstacles)

        for obstacle in list(self.obstacles):
            obstacle.update(dt, speed)

        despawn_y = float(getattr(config, "SUBWAY_3D_DESPAWN_Y", -10.0))
        remaining = []
        for obstacle in self.obstacles:
            if obstacle.y() > despawn_y:
                remaining.append(obstacle)
            else:
                try:
                    obstacle.node.removeNode()
                except Exception:
                    pass
        self.obstacles = remaining

        for runner in self.runners:
            runner.update(dt, self.track, self.obstacles, self.game_time)

        self._check_collisions()

        alive_count = sum(1 for r in self.runners if r.alive)
        if alive_count <= 1 or self.game_time >= self.max_game_time:
            self._finish_game()

        self.ui.update_stats(alive_count, speed, self.game_time)
        self.video_recorder.capture_frame(self.game_time)

        return task.cont

    def _check_collisions(self):
        for runner in self.runners:
            if not runner.alive:
                continue
            for obstacle in self.obstacles:
                if not self._lanes_overlap(runner.lane_index, 1, obstacle.lane_index, obstacle.lane_span):
                    continue
                if not self._overlaps(runner, obstacle):
                    continue
                if self._is_avoided(runner, obstacle):
                    continue
                runner.hit(self.game_time)
                if runner.username:
                    self.recent_eliminations.insert(0, runner.username)
                break

    def _overlaps(self, runner, obstacle) -> bool:
        dx = abs(runner.x - obstacle.x())
        dy = abs(runner.y - obstacle.y())
        x_hit = dx < (runner.radius + obstacle.width * 0.5)
        y_hit = dy < (runner.depth + obstacle.length * 0.5)
        return x_hit and y_hit

    def _is_avoided(self, runner, obstacle) -> bool:
        if obstacle.required_action == "jump":
            return runner.z >= obstacle.height * 0.6
        if obstacle.required_action == "roll":
            return runner.state == "roll"
        return False

    @staticmethod
    def _lanes_overlap(start_a: int, span_a: int, start_b: int, span_b: int) -> bool:
        end_a = start_a + max(1, span_a) - 1
        end_b = start_b + max(1, span_b) - 1
        return not (end_a < start_b or end_b < start_a)

    def _finish_game(self):
        if self.game_over:
            return
        self.game_over = True
        sorted_runners = sorted(
            self.runners,
            key=lambda r: (
                not r.alive,
                -(r.survival_time or 0.0),
                r.username,
            ),
        )

        for idx, runner in enumerate(sorted_runners):
            runner.placement = idx + 1

        self._calculate_and_save_scores(sorted_runners)

        lines = ["GAME COMPLETE", ""]
        for idx, runner in enumerate(sorted_runners[:10]):
            lines.append(f"{idx + 1}. {runner.username}")
        self.ui.show_end_screen(lines)

    def _calculate_and_save_scores(self, sorted_players):
        total_participants = len(self.runners)
        game_results = []
        history_results = []

        game_type = "subway_followers"
        game_display_name = "Subway Followers"
        day_number = getattr(config, "DAY_NUMBER", 1)

        for runner in sorted_players:
            placement = runner.placement
            games_played = self.statistics.get_games_played(runner.username)
            survival_time = runner.survival_time

            points_breakdown = self.scoring.calculate_total_points(
                placement=placement,
                total_participants=total_participants,
                survival_time=survival_time,
                games_played=games_played,
            )
            points = points_breakdown["total_points"]

            self.statistics.update_player_stats(
                username=runner.username,
                placement=placement,
                points_earned=points,
                survival_time=survival_time,
                total_participants=total_participants,
                game_type=game_type,
                game_id="",
            )

            game_results.append((runner.username, placement, points, survival_time))
            history_results.append({
                "username": runner.username,
                "placement": placement,
                "points": points,
                "survival_time": survival_time,
                "kills": 0,
                "damage": 0.0,
            })

        self.game_history.record_game_session(
            game_type=game_type,
            game_display_name=game_display_name,
            day_number=day_number,
            results=history_results,
        )

        self.statistics.save_statistics()

        if not config.TEST_MODE and getattr(config, "AUTO_PUSH_STATS", False):
            auto_push.push_stats_to_github()

        self.current_game_leaderboard = self.statistics.get_current_game_leaderboard(game_results)

    def _shutdown(self):
        try:
            self.video_recorder.finalize(include_audio=True)
        finally:
            self.ui.cleanup()
            self.userExit()

    def run_game(self):
        self.run()
