import logging
import pathlib
import subprocess
import time
import uuid

import pytest

from tests.conftest import system_test
from tests.utils.db_activity_simulator import DbActivitySimulator
from tests.utils.kafka import KafkaAdmin, KafkaThreadedConsumer
from tests.utils.subp_collector import SubProcCollector

logger = logging.getLogger(__name__)


# FIXME: `PopykaDockerComposeLauncher` was copied from `test_sample_django_admin.py`


class PopykaDockerComposeLauncher:
    def __init__(self, slot_name: str, extra_envs: list[str] | None = None):
        self._collector: SubProcCollector | None = None
        self._envs = ["POPYKA_COMPACT_DUMP=1"] + (extra_envs or [])
        assert all(["=" in _ for _ in self._envs])
        self._slot_name: str = slot_name

    @property
    def collector(self) -> SubProcCollector:
        assert self._collector is not None
        return self._collector

    def start(self):
        dc_file = pathlib.Path(__file__).parent.parent.parent / "docker-compose.yml"

        # Build
        args = [
            "docker",
            "compose",
            "--file",
            str(dc_file.absolute()),
            "build",
            "--quiet",
            "popyka",
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
                str(dc_file.absolute()),
                "up",
                "--no-log-prefix",
                "--no-deps",  # We brought dependencies up manually
                "popyka",
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


@pytest.fixture
def docker_compose_deps() -> SubProcCollector:
    dc_file = pathlib.Path(__file__).parent.parent.parent / "docker-compose.yml"

    # Build
    args = [
        "docker",
        "compose",
        "--file",
        str(dc_file.absolute()),
        "build",
        "--quiet",
        "pg16",
        "kafka",
    ]
    subprocess.run(args=args, check=True)

    # Run
    args = [
        "docker",
        "compose",
        "--file",
        str(dc_file.absolute()),
        "up",
        "--wait",
        "--remove-orphans",
        "--detach",
        "pg16",
        "kafka",
    ]
    collector = SubProcCollector(args=args).start()
    assert collector.wait(timeout=20) == 0
    collector.join_threads()

    # TODO: busy wait until all dependencies are up

    # To have a predictable environment, we can create new slot + topic (this was the initial approach): but...
    #   1. there is a limited number of slots that can be created on postgresql... if slots are not dropped,
    #      this cause problems when running tests many times.
    #   2. a second test is needed to validate the demo app with the default configuration (default slot & topic)
    #
    # It's easier to just delete everything before the test run, this way the environment is predictable,
    # and we're testing default configuration... If tests pass, the demo app should work as is.

    yield collector


@pytest.fixture
def topic():
    # TODO: Refactor to avoid code duplication: this was copied from system-tests.
    return f"popyka_{int(time.time())}"


@pytest.fixture
def slot_name():
    # TODO: Refactor to avoid code duplication: this was copied from system-tests.
    return f"popyka_test_{int(time.time())}"


@pytest.fixture
def clean_data(drop_slot_fn, kafka_admin, dsn: str):
    # TODO: Refactor to avoid code duplication: this was copied from system-tests.
    kafka_admin.delete_all_topics()
    drop_slot_fn(dsn)


@pytest.fixture()
def kafka_admin(kafka_bootstrap_servers: str) -> KafkaAdmin:
    # TODO: Refactor to avoid code duplication: this was copied from system-tests.
    return KafkaAdmin(kafka_bootstrap_servers)


@pytest.fixture()
def consumer(clean_data, kafka_admin, kafka_bootstrap_servers: str, topic: str) -> KafkaThreadedConsumer:
    # TODO: Refactor to avoid code duplication: this was copied from system-tests.
    kafka_admin.create_topic(topic)
    consumer = KafkaThreadedConsumer(kafka_bootstrap_servers, topic)
    consumer.start()
    return consumer


@pytest.fixture
def kill_popyka(docker_compose_deps):
    dc_file = pathlib.Path(__file__).parent.parent.parent / "docker-compose.yml"
    args = ["docker", "compose", "--file", str(dc_file.absolute()), "kill", "popyka", "db-activity-simulator"]
    subprocess.run(args, check=True)


@pytest.fixture
def setup_env(kill_popyka, clean_data, docker_compose_deps):
    yield


@pytest.fixture
def dc_popyka(setup_env, slot_name, topic, kafka_bootstrap_servers) -> SubProcCollector:
    extra_envs = [
        "POPYKA_CONFIG=/external-repository/popyka-config.yaml",
        "POPYKA_PYTHONPATH=/external-repository",
        f"POPYKA_DB_SLOT_NAME={slot_name}",
        f"POPYKA_KAFKA_TOPIC={topic}",
    ]
    launcher = PopykaDockerComposeLauncher(slot_name=slot_name, extra_envs=extra_envs)
    launcher.start()
    launcher.wait_until_popyka_started()
    yield launcher.collector
    launcher.stop()


@system_test
def test(setup_env, dc_popyka: SubProcCollector, consumer: KafkaThreadedConsumer, conn, table_name):
    """
    INFO:mycompany.MyCompanyCustomProcessor:MyCompanyCustomProcessor-received-a-change
    ####
    {
        "action": "...",
    }
    ####
    """
    sql = [f"INSERT INTO __table_name__ (NAME) VALUES ('{uuid.uuid4().hex}')"]
    DbActivitySimulator(conn, table_name, sql).execute()

    dc_popyka.wait_for("mycompany.MyCompanyCustomProcessor:MyCompanyCustomProcessor-received-a-change")
    dc_popyka.wait_for_change(timeout=1).assert_insert().assert_table(table_name)

    expected_summaries = [("I", table_name.lower())]
    actual_summaries = consumer.wait_for_count_summarized(1, timeout=10)
    assert sorted(actual_summaries) == sorted(expected_summaries)
