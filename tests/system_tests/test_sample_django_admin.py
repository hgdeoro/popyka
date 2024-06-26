import logging
import pathlib
import subprocess

import mechanize
import pytest

from tests.conftest import system_test
from tests.utils.docker_compose import (
    DepsDockerComposeLauncherBase,
    PopykaDockerComposeLauncherBase,
)
from tests.utils.kafka import KafkaAdmin, KafkaThreadedConsumer
from tests.utils.subp_collector import SubProcCollector

logger = logging.getLogger(__name__)

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent

# These values are the one hardcoded in docker compose file, either the same, or the adapted for `localhost` use
DOCKER_COMPOSE_DJANGO_ADMIN_PORT = 8081
DOCKER_COMPOSE_POSTGRESQL_DSN = "postgresql://postgres:pass@localhost:54091/postgres"
DOCKER_COMPOSE_KAFKA_BOOTSTRAP_SERVERS = "localhost:54092"
DOCKER_COMPOSE_DB_SLOT_NAME = "popyka"
DOCKER_COMPOSE_KAFKA_TOPIC = "popyka"


@pytest.fixture
def kill_popyka(docker_compose_deps):
    dc_file = pathlib.Path(__file__).parent.parent.parent / "samples" / "django-admin" / "docker-compose.yml"
    args = ["docker", "compose", "--file", str(dc_file.absolute()), "kill", "demo-popyka"]
    subprocess.run(args, check=True)


@pytest.fixture
def clean_data(drop_slot_fn, kafka_admin, docker_compose_deps):
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
def setup_env(kill_popyka, clean_data, docker_compose_deps):
    yield


def django_admin_login():
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


# ---------- docker compose --------------------------------------------------------------------------------


class PopykaDockerComposeLauncher(PopykaDockerComposeLauncherBase):
    DOCKER_COMPOSE_FILE = PROJECT_ROOT / "samples" / "django-admin" / "docker-compose.yml"
    POPYKA_SERVICE = "demo-popyka"


class DepsDockerComposeLauncher(DepsDockerComposeLauncherBase):
    DOCKER_COMPOSE_FILE = PROJECT_ROOT / "samples" / "django-admin" / "docker-compose.yml"
    SERVICES: list[str] = [
        "demo-db",
        "demo-django-admin",
        "demo-kafka",
    ]


@pytest.fixture
def docker_compose_deps() -> SubProcCollector:
    deps = DepsDockerComposeLauncher().up()
    yield deps.collector


# ---------- default config --------------------------------------------------------------------------------


@pytest.fixture
def dc_popyka_default_config() -> SubProcCollector:
    launcher = PopykaDockerComposeLauncher(slot_name=DOCKER_COMPOSE_DB_SLOT_NAME)
    launcher.start()
    launcher.wait_until_popyka_started()
    yield launcher.collector
    launcher.stop()


@system_test
def test_django_admin_login_with_default_config(
    setup_env, dc_popyka_default_config: SubProcCollector, consumer: KafkaThreadedConsumer
):
    django_admin_login()

    dc_popyka_default_config.wait_for_change(timeout=5).assert_insert().assert_table("django_session")
    dc_popyka_default_config.wait_for_change(timeout=5).assert_update().assert_table("auth_user")
    dc_popyka_default_config.wait_for_change(timeout=5).assert_update().assert_table("django_session")

    expected_summaries = [("I", "django_session"), ("U", "auth_user"), ("U", "django_session")]
    actual_summaries = consumer.wait_for_count_summarized(3, timeout=10)
    assert sorted(actual_summaries) == sorted(expected_summaries)


# ---------- invalid config is directory ----------------------------------------------------------------------


@pytest.fixture
def dc_popyka_invalid_config_is_directory() -> SubProcCollector:
    launcher = PopykaDockerComposeLauncher(slot_name=DOCKER_COMPOSE_DB_SLOT_NAME, extra_envs=["POPYKA_CONFIG=/"])
    launcher.start()
    yield launcher.collector
    launcher.stop()


@system_test
def test_dc_popyka_invalid_config_is_directory(
    setup_env,
    dc_popyka_invalid_config_is_directory: SubProcCollector,
    consumer: KafkaThreadedConsumer,
):
    dc_popyka_invalid_config_is_directory.wait_for(
        "popyka.errors.ConfigError: Invalid config: / (POPYKA_CONFIG) is a directory", timeout=10
    )


# ---------- invalid config: valid yaml, invalid config ------------------------------------------------------------


@pytest.fixture
def dc_popyka_invalid_config() -> SubProcCollector:
    launcher = PopykaDockerComposeLauncher(
        slot_name=DOCKER_COMPOSE_DB_SLOT_NAME, extra_envs=["POPYKA_CONFIG=/popyka-config/popyka-invalid-config.yaml"]
    )
    launcher.start()
    yield launcher.collector
    launcher.stop()


@system_test
def test_dc_popyka_invalid_config(
    setup_env, dc_popyka_invalid_config: SubProcCollector, consumer: KafkaThreadedConsumer
):
    dc_popyka_invalid_config.wait_for(
        "popyka.errors.ConfigError: LogChangeProcessor filter does not accepts any configuration", timeout=10
    )


# ---------- valid custom config --------------------------------------------------------------------------------


@pytest.fixture
def dc_popyka_valid_custom_config() -> SubProcCollector:
    launcher = PopykaDockerComposeLauncher(
        slot_name=DOCKER_COMPOSE_DB_SLOT_NAME,
        extra_envs=["POPYKA_CONFIG=/popyka-config/popyka-config-ignore-tables.yaml"],
    )
    launcher.start()
    launcher.wait_custom_config("/popyka-config/popyka-config-ignore-tables.yaml")
    launcher.wait_until_popyka_started()
    yield launcher.collector
    launcher.stop()


@system_test
def test_dc_popyka_valid_custom_config(
    setup_env,
    dc_popyka_valid_custom_config: SubProcCollector,
    consumer: KafkaThreadedConsumer,
):
    django_admin_login()

    dc_popyka_valid_custom_config.wait_for_change(timeout=5).assert_update().assert_table("auth_user")

    assert sorted(consumer.wait_for_count_summarized(1, timeout=10)) == sorted([("U", "auth_user")])
