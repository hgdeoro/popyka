import logging
import pathlib

import confluent_kafka
import mechanize
import pytest

from tests.conftest import system_test
from tests.subp_collector import SubProcCollector
from tests.utils import KafkaAdmin, KafkaConsumer

logger = logging.getLogger(__name__)

DEMO_DJANGO_ADMIN_PORT = 8081
DEMO_POSTGRESQL_DSN = "postgresql://postgres:pass@localhost:54091/postgres"
DEMO_KAFKA_BOOTSTRAP_SERVERS = "localhost:54092"


@pytest.fixture
def dc_deps(drop_slot_fn) -> SubProcCollector:
    kafka_admin = KafkaAdmin(DEMO_KAFKA_BOOTSTRAP_SERVERS)

    dc_file = pathlib.Path(__file__).parent.parent.parent / "samples" / "django-admin" / "docker-compose.yml"
    args = [
        "docker",
        "compose",
        "--file",
        str(dc_file.absolute()),
        "up",
        "--build",
        "--wait",
        "-d",
        "demo-db",
        "demo-django-admin",
        "demo-kafka",
    ]
    subp_collector = SubProcCollector(args=args).start()
    assert subp_collector._proc.wait() == 0  # Retry? Timeout?  # FIXME: protected attribute!
    subp_collector._thread_stdout.join()  # FIXME: protected attribute!
    subp_collector._thread_stderr.join()  # FIXME: protected attribute!

    # TODO: busy wait until all dependencies are up

    kafka_admin.delete_all_topics()
    drop_slot_fn(DEMO_POSTGRESQL_DSN)

    yield subp_collector

    kafka_admin.delete_all_topics()
    drop_slot_fn(DEMO_POSTGRESQL_DSN)


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
    subp_collector = SubProcCollector(args=args).start()

    # Wait until Popyka started
    subp_collector.wait_for("will start_replication() slot=popyka", timeout=5)
    subp_collector.wait_for("will consume_stream() adaptor=", timeout=1)

    yield subp_collector

    subp_collector.kill()
    subp_collector._proc.wait()  # FIXME: protected attribute!
    subp_collector._thread_stdout.join()  # FIXME: protected attribute!
    subp_collector._thread_stderr.join()  # FIXME: protected attribute!


@system_test
def test_e2e(dc_deps: SubProcCollector, dc_popyka: SubProcCollector):
    br = mechanize.Browser()
    br.set_handle_robots(False)

    br.open(f"http://localhost:{DEMO_DJANGO_ADMIN_PORT}/admin/")
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

    topic_name = "popyka"
    consumer = KafkaConsumer(DEMO_KAFKA_BOOTSTRAP_SERVERS, topic_name)
    messages: list[confluent_kafka.Message] = consumer.wait_for_count(count=3, timeout=10)

    expected_summaries = sorted([("I", "django_session"), ("U", "auth_user"), ("U", "django_session")])
    assert sorted(KafkaConsumer.summarize(messages)) == expected_summaries
