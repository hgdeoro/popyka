import logging
import pathlib
import subprocess

import confluent_kafka
import mechanize
import pytest

from tests.conftest import system_test
from tests.utils.kafka import KafkaAdmin, KafkaThreadedConsumer
from tests.utils.subp_collector import SubProcCollector

logger = logging.getLogger(__name__)

# These values are the one hardcoded in docker compose file, either the same, or the adapted for `localhost` use
DOCKER_COMPOSE_DJANGO_ADMIN_PORT = 8081
DOCKER_COMPOSE_POSTGRESQL_DSN = "postgresql://postgres:pass@localhost:54091/postgres"
DOCKER_COMPOSE_KAFKA_BOOTSTRAP_SERVERS = "localhost:54092"
DOCKER_COMPOSE_DB_SLOT_NAME = "popyka"
DOCKER_COMPOSE_KAFKA_TOPIC = "popyka"


# FIXME: there is an insane amount of duplication of code here: fixture `dc_popyka_*`


@pytest.fixture
def kill_popyka():
    dc_file = pathlib.Path(__file__).parent.parent.parent / "samples" / "django-admin" / "docker-compose.yml"
    args = ["docker", "compose", "--file", str(dc_file.absolute()), "kill", "demo-popyka"]
    subprocess.run(args, check=True)


@pytest.fixture
def clean_data(drop_slot_fn, kafka_admin):
    kafka_admin.delete_all_topics()
    drop_slot_fn(DOCKER_COMPOSE_POSTGRESQL_DSN)


@pytest.fixture()
def kafka_admin() -> KafkaAdmin:
    return KafkaAdmin(DOCKER_COMPOSE_KAFKA_BOOTSTRAP_SERVERS)


@pytest.fixture()
def consumer(clean_data, kafka_admin) -> KafkaThreadedConsumer:
    kafka_admin.create_topic(DOCKER_COMPOSE_KAFKA_TOPIC)
    consumer = KafkaThreadedConsumer(DOCKER_COMPOSE_KAFKA_BOOTSTRAP_SERVERS, DOCKER_COMPOSE_KAFKA_TOPIC)
    consumer.start()
    return consumer


@pytest.fixture
def docker_compose_deps(kill_popyka, clean_data) -> SubProcCollector:
    dc_file = pathlib.Path(__file__).parent.parent.parent / "samples" / "django-admin" / "docker-compose.yml"

    # Build
    args = [
        "docker",
        "compose",
        "--file",
        str(dc_file.absolute()),
        "build",
        "--quiet",
        "demo-db",
        "demo-django-admin",
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
        "demo-db",
        "demo-django-admin",
        "demo-kafka",
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


class PopykaDockerComposeLauncher:
    def __init__(self, extra_envs: list[str] | None = None):
        self._collector: SubProcCollector | None = None
        self._envs = ["LAZYTOSTR_COMPACT=1"] + (extra_envs or [])
        assert all(["=" in _ for _ in self._envs])

    @property
    def collector(self) -> SubProcCollector:
        assert self._collector is not None
        return self._collector

    def start(self):
        dc_file = pathlib.Path(__file__).parent.parent.parent / "samples" / "django-admin" / "docker-compose.yml"

        # Build
        args = [
            "docker",
            "compose",
            "--file",
            str(dc_file.absolute()),
            "build",
            "--quiet",
            "demo-popyka",
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
                "demo-popyka",
            ]
        )
        self._collector = SubProcCollector(args=args).start()

    def wait_until_popyka_started(self):
        self._collector.wait_for(f"will start_replication() slot={DOCKER_COMPOSE_DB_SLOT_NAME}", timeout=5)
        self._collector.wait_for("will consume_stream() adaptor=", timeout=1)

    def stop(self):
        assert self._collector is not None
        self._collector.kill()
        self._collector.wait(timeout=20)
        self._collector.join_threads()


# ---------- default config --------------------------------------------------------------------------------


@pytest.fixture
def dc_popyka_default_config() -> SubProcCollector:
    launcher = PopykaDockerComposeLauncher()
    launcher.start()
    launcher.wait_until_popyka_started()
    yield launcher.collector
    launcher.stop()


@system_test
def test_django_admin_login_with_default_config(
    docker_compose_deps: SubProcCollector, dc_popyka_default_config: SubProcCollector, consumer: KafkaThreadedConsumer
):
    br = mechanize.Browser()
    br.set_handle_robots(False)

    br.open(f"http://localhost:{DOCKER_COMPOSE_DJANGO_ADMIN_PORT}/admin/")
    assert br.response().code == 200
    assert br.title() == "Log in | Django site admin"

    br.select_form(nr=0)
    br["username"] = "admin"
    br["password"] = "admin"
    br.submit()

    assert br.response().code == 200
    assert br.title() == "Site administration | Django site admin"

    dc_popyka_default_config.wait_for_change(timeout=5).assert_insert().assert_table("django_session")
    dc_popyka_default_config.wait_for_change(timeout=5).assert_update().assert_table("auth_user")
    dc_popyka_default_config.wait_for_change(timeout=5).assert_update().assert_table("django_session")

    expected_summaries = sorted([("I", "django_session"), ("U", "auth_user"), ("U", "django_session")])
    messages: list[confluent_kafka.Message] = consumer.wait_for_count(count=3, timeout=10)
    assert sorted(KafkaThreadedConsumer.summarize(messages)) == expected_summaries


# ---------- invalid config is directory ----------------------------------------------------------------------


@pytest.fixture
def dc_popyka_invalid_config_is_directory() -> SubProcCollector:
    launcher = PopykaDockerComposeLauncher(extra_envs=["POPYKA_CONFIG=/"])
    launcher.start()
    yield launcher.collector
    launcher.stop()


@system_test
def test_dc_popyka_invalid_config_is_directory(
    docker_compose_deps: SubProcCollector,
    dc_popyka_invalid_config_is_directory: SubProcCollector,
    consumer: KafkaThreadedConsumer,
):
    dc_popyka_invalid_config_is_directory.wait_for(
        "popyka.errors.ConfigError: Invalid config: / (POPYKA_CONFIG) is a directory", timeout=10
    )


# ---------- invalid config: valid yaml, invalid config ------------------------------------------------------------


@pytest.fixture
def dc_popyka_invalid_config() -> SubProcCollector:
    launcher = PopykaDockerComposeLauncher(extra_envs=["POPYKA_CONFIG=/popyka-config/popyka-invalid-config.yaml"])
    launcher.start()
    yield launcher.collector
    launcher.stop()


@system_test
def test_dc_popyka_invalid_config(
    docker_compose_deps: SubProcCollector, dc_popyka_invalid_config: SubProcCollector, consumer: KafkaThreadedConsumer
):
    dc_popyka_invalid_config.wait_for(
        "popyka.errors.ConfigError: LogChangeProcessor filter does not accepts any configuration", timeout=10
    )


# ---------- valid custom config --------------------------------------------------------------------------------


@pytest.fixture
def dc_popyka_valid_custom_config() -> SubProcCollector:
    launcher = PopykaDockerComposeLauncher(extra_envs=["POPYKA_CONFIG=/popyka-config/popyka-config-ignore-tables.yaml"])
    launcher.start()
    yield launcher.collector
    launcher.stop()


@system_test
def test_dc_popyka_valid_custom_config(
    docker_compose_deps: SubProcCollector,
    dc_popyka_valid_custom_config: SubProcCollector,
    consumer: KafkaThreadedConsumer,
):
    collector = dc_popyka_valid_custom_config

    # Check custom config was loaded
    collector.wait_for(
        ":popyka.config:Using custom config file. POPYKA_CONFIG=/popyka-config/popyka-config-ignore-tables.yaml",
        timeout=10,
    )

    # Wait until Popyka started
    collector.wait_for(f"will start_replication() slot={DOCKER_COMPOSE_DB_SLOT_NAME}", timeout=5)
    collector.wait_for("will consume_stream() adaptor=", timeout=1)

    br = mechanize.Browser()
    br.set_handle_robots(False)

    br.open(f"http://localhost:{DOCKER_COMPOSE_DJANGO_ADMIN_PORT}/admin/")
    assert br.response().code == 200
    assert br.title() == "Log in | Django site admin"

    br.select_form(nr=0)
    br["username"] = "admin"
    br["password"] = "admin"
    br.submit()

    assert br.response().code == 200
    assert br.title() == "Site administration | Django site admin"

    # collector.wait_for_change(timeout=5).assert_insert().assert_table("django_session")
    collector.wait_for_change(timeout=5).assert_update().assert_table("auth_user")
    # collector.wait_for_change(timeout=5).assert_update().assert_table("django_session")

    expected_summaries = sorted([("U", "auth_user")])
    messages: list[confluent_kafka.Message] = consumer.wait_for_count(count=1, timeout=10)
    assert sorted(KafkaThreadedConsumer.summarize(messages)) == expected_summaries
