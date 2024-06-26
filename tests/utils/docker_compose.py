import logging
import pathlib
import subprocess

from tests.utils.subp_collector import SubProcCollector

logger = logging.getLogger(__name__)


class PopykaDockerComposeLauncherBase:
    DOCKER_COMPOSE_FILE: pathlib.Path = None
    POPYKA_SERVICE: str = None
    POPYKA_COMPACT_DUMP: str = "1"

    def __init__(self, slot_name: str, extra_envs: list[str] | None = None):
        assert self.DOCKER_COMPOSE_FILE is not None, "Subclass must set DOCKER_COMPOSE_FILE"
        assert self.POPYKA_SERVICE is not None, "Subclass must set POPYKA_SERVICE"
        self._collector: SubProcCollector | None = None
        self._slot_name: str = slot_name
        self._envs = [f"POPYKA_COMPACT_DUMP={self.POPYKA_COMPACT_DUMP}"] + (extra_envs or [])
        assert all(["=" in _ for _ in self._envs])

    @property
    def collector(self) -> SubProcCollector:
        assert self._collector is not None
        return self._collector

    def start(self):
        # Build
        args = [
            "docker",
            "compose",
            "--file",
            str(self.DOCKER_COMPOSE_FILE.absolute()),
            "build",
            "--quiet",
            self.POPYKA_SERVICE,
        ]
        subprocess.run(args=args, check=True)

        # Up
        args = (
            ["env"]
            + self._envs
            + [
                "docker",
                "compose",
                "--file",
                str(self.DOCKER_COMPOSE_FILE.absolute()),
                "up",
                "--no-log-prefix",
                "--no-deps",  # Not sure if good default, maybe should be configurable?
                self.POPYKA_SERVICE,
            ]
        )
        self._collector = SubProcCollector(args=args).start()

    def wait_until_popyka_started(self):
        self._collector.wait_for(f"will start_replication() slot={self._slot_name}", timeout=5)
        self._collector.wait_for("will consume_stream() adaptor=", timeout=1)

    def wait_custom_config(self, custom_config: str):
        # Check custom config was loaded
        self._collector.wait_for(
            f":popyka.config:Using custom config file. POPYKA_CONFIG={custom_config}",
            timeout=10,
        )

    def stop(self):
        assert self._collector is not None
        self._collector.kill()
        self._collector.wait(timeout=20)
        self._collector.join_threads()


class DepsDockerComposeLauncherBase:
    DOCKER_COMPOSE_FILE = None
    SERVICES: list[str] = None
    TIMEOUT: int = 20

    def __init__(self, extra_envs: list[str] | None = None):
        assert self.DOCKER_COMPOSE_FILE is not None, "Subclass must set DOCKER_COMPOSE_FILE"
        assert self.SERVICES is not None, "Subclass must set SERVICES"
        self._collector: SubProcCollector | None = None
        # self._slot_name: str = slot_name
        self._envs = extra_envs or []
        assert all(["=" in _ for _ in self._envs])

    @property
    def collector(self) -> SubProcCollector:
        assert self._collector is not None
        return self._collector

    def up(self) -> "DepsDockerComposeLauncherBase":
        # Build
        args = [
            "docker",
            "compose",
            "--file",
            str(self.DOCKER_COMPOSE_FILE.absolute()),
            "build",
            "--quiet",
        ] + self.SERVICES

        subprocess.run(args=args, check=True)

        # Up
        args = (
            ["env"]
            + self._envs
            + [
                "docker",
                "compose",
                "--file",
                str(self.DOCKER_COMPOSE_FILE.absolute()),
                "up",
                "--wait",
                "--remove-orphans",
                "--detach",
            ]
            + self.SERVICES
        )

        self._collector = SubProcCollector(args=args).start()
        assert self._collector.wait(timeout=self.TIMEOUT) == 0
        self._collector.join_threads()

        return self
