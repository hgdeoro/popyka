import json
import logging
import os
import pathlib
import random
import time
import uuid

import confluent_kafka
import mechanize
import pytest
from confluent_kafka import Consumer

from tests.conftest import system_test
from tests.subp_collector import SubProcCollector

logger = logging.getLogger(__name__)


DEMO_DJANGO_ADMIN_PORT = 8081
DEMO_POSTGRESQL_DSN = "postgresql://postgres:pass@localhost:54091/postgres"
DEMO_KAFKA_BOOTSTRAP_SERVERS = "localhost:54092"


@pytest.fixture
def dc_deps() -> SubProcCollector:
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

    yield subp_collector


@pytest.fixture
def dc_popyka(monkeypatch, drop_slot_fn) -> SubProcCollector:
    slot_name = f"django_admin_demo_popyka_{random.randint(1, 999999999)}"
    topic_name = f"django_admin_demo_popyka_{random.randint(1, 999999999)}"
    monkeypatch.setenv("POPYKA_DB_SLOT_NAME", slot_name)
    monkeypatch.setenv("POPYKA_KAFKA_TOPIC", topic_name)

    drop_slot_fn(DEMO_POSTGRESQL_DSN)

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
    subp_collector.wait_for(f"will start_replication() slot={slot_name}", timeout=5)
    subp_collector.wait_for("will consume_stream() adaptor=", timeout=1)

    yield subp_collector

    subp_collector.kill()
    subp_collector._proc.wait()  # FIXME: protected attribute!
    subp_collector._thread_stdout.join()  # FIXME: protected attribute!
    subp_collector._thread_stderr.join()  # FIXME: protected attribute!


class KafkaConsumer:
    def __init__(self, bootstrap_servers: str, topic: str):
        self._topic = topic
        self._consumed_msg: list[confluent_kafka.Message] = []
        self._consumer = Consumer(
            {
                "bootstrap.servers": bootstrap_servers,
                "group.id": str(uuid.uuid4().hex),
                "auto.offset.reset": "earliest",
            }
        )
        self._consumer.subscribe([topic])

    @property
    def consumed_msg(self) -> list[confluent_kafka.Message]:
        return list(self._consumed_msg)

    # def clean(self):
    #     self._consumed_msg = []

    def wait_for_count(self, count: int, timeout: float) -> list[confluent_kafka.Message]:
        print(f"Waiting for {count} messages in topic {self._topic}")
        assert timeout > 0
        start = time.monotonic()
        while time.monotonic() - start < timeout and len(self._consumed_msg) < count:
            logger.debug(
                "Waiting for %s messages in topic %s. There are %s at the moment",
                count,
                self._topic,
                len(self._consumed_msg),
            )
            msg = self._consumer.poll(0.1)
            if msg is None:
                continue
            assert not msg.error()

            self._consumed_msg.append(msg)

        # self._consumer.close()  # How can we know if client will try again :/

        if len(self._consumed_msg) < count:
            raise Exception(f"Timeout waiting for {count} messages. Got: only {len(self._consumed_msg)}")

        return self._consumed_msg

    @classmethod
    def summarize(cls, messages: list[confluent_kafka.Message]):
        changes_dict = [json.loads(_.value()) for _ in messages]
        changes_summary = [(_["action"], _["table"]) for _ in changes_dict]
        return changes_summary


@system_test
def test_default_configuration(dc_deps: SubProcCollector, dc_popyka: SubProcCollector):
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

    topic_name = os.environ["POPYKA_KAFKA_TOPIC"]  # set by fixture
    consumer = KafkaConsumer(DEMO_KAFKA_BOOTSTRAP_SERVERS, topic_name)
    messages: list[confluent_kafka.Message] = consumer.wait_for_count(count=3, timeout=10)

    expected_summaries = sorted([("I", "django_session"), ("U", "auth_user"), ("U", "django_session")])
    assert sorted(KafkaConsumer.summarize(messages)) == expected_summaries
