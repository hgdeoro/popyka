import logging
import pathlib
import subprocess
import time
import uuid

import pytest

from tests.conftest import system_test
from tests.utils.db_activity_simulator import DbActivitySimulator
from tests.utils.docker_compose import (
    DepsDockerComposeLauncherBase,
    PopykaDockerComposeLauncherBase,
)
from tests.utils.kafka import KafkaAdmin, KafkaThreadedConsumer
from tests.utils.subp_collector import SubProcCollector

logger = logging.getLogger(__name__)

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent


# FIXME: `PopykaDockerComposeLauncher` was copied from `test_sample_django_admin.py`


class PopykaDockerComposeLauncher(PopykaDockerComposeLauncherBase):
    DOCKER_COMPOSE_FILE = PROJECT_ROOT / "docker-compose.yml"
    POPYKA_SERVICE = "popyka"


class DepsDockerComposeLauncher(DepsDockerComposeLauncherBase):
    DOCKER_COMPOSE_FILE = PROJECT_ROOT / "docker-compose.yml"
    SERVICES = [
        "pg16",
        "kafka",
    ]


@pytest.fixture
def docker_compose_deps() -> SubProcCollector:
    deps = DepsDockerComposeLauncher().up()
    yield deps.collector


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
