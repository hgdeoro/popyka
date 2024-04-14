import logging
import pathlib

import confluent_kafka
import mechanize
import pytest

from tests.conftest import system_test
from tests.utils.kafka import KafkaAdmin, KafkaConsumer
from tests.utils.subp_collector import SubProcCollector

logger = logging.getLogger(__name__)

# These values are the one hardcoded in docker compose file, either the same, or the adapted for `localhost` use
DOCKER_COMPOSE_DJANGO_ADMIN_PORT = 8081
DOCKER_COMPOSE_POSTGRESQL_DSN = "postgresql://postgres:pass@localhost:54091/postgres"
DOCKER_COMPOSE_KAFKA_BOOTSTRAP_SERVERS = "localhost:54092"
DOCKER_COMPOSE_DB_SLOT_NAME = "popyka"
DOCKER_COMPOSE_KAFKA_TOPIC = "popyka"


@pytest.fixture
def dc_deps(drop_slot_fn) -> SubProcCollector:
    kafka_admin = KafkaAdmin(DOCKER_COMPOSE_KAFKA_BOOTSTRAP_SERVERS)

    dc_file = pathlib.Path(__file__).parent.parent.parent / "samples" / "django-admin" / "docker-compose.yml"
    args = [
        "docker",
        "compose",
        "--file",
        str(dc_file.absolute()),
        "up",
        "--build",
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

    kafka_admin.delete_all_topics()
    drop_slot_fn(DOCKER_COMPOSE_POSTGRESQL_DSN)

    # To have a predictable environment, we can create new slot + topic (this was the initial approach): but...
    #   1. there is a limited number of slots that can be created on postgresql... if slots are not dropped,
    #      this cause problems when running tests many times.
    #   2. a second test is needed to validate the demo app with the default configuration (default slot & topic)
    #
    # It's easier to just delete everything before the test run, this way the environment is predictable,
    # and we're testing default configuration... If tests pass, the demo app should work as is.

    yield collector

    kafka_admin.delete_all_topics()
    drop_slot_fn(DOCKER_COMPOSE_POSTGRESQL_DSN)


@pytest.fixture
def dc_popyka(monkeypatch) -> SubProcCollector:
    dc_file = pathlib.Path(__file__).parent.parent.parent / "samples" / "django-admin" / "docker-compose.yml"
    args = [
        "docker",
        "compose",
        "--file",
        str(dc_file.absolute()),
        "up",
        "--build",
        "demo-popyka",
    ]
    collector = SubProcCollector(args=args).start()

    # Wait until Popyka started
    collector.wait_for(f"will start_replication() slot={DOCKER_COMPOSE_DB_SLOT_NAME}", timeout=5)
    collector.wait_for("will consume_stream() adaptor=", timeout=1)

    yield collector

    collector.kill()
    collector.wait(timeout=20)
    collector.join_threads()


@system_test
def test_e2e(dc_deps: SubProcCollector, dc_popyka: SubProcCollector):
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

    dc_popyka.wait_for('"table": "django_session"', timeout=5)
    dc_popyka.wait_for('"table": "auth_user"', timeout=5)

    consumer = KafkaConsumer(DOCKER_COMPOSE_KAFKA_BOOTSTRAP_SERVERS, DOCKER_COMPOSE_KAFKA_TOPIC)
    messages: list[confluent_kafka.Message] = consumer.wait_for_count(count=3, timeout=10)

    expected_summaries = sorted([("I", "django_session"), ("U", "auth_user"), ("U", "django_session")])
    assert sorted(KafkaConsumer.summarize(messages)) == expected_summaries
