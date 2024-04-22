import json
import logging
import uuid

import pytest

from tests.conftest import system_test_fast
from tests.utils.db_activity_simulator import DbActivitySimulator
from tests.utils.kafka import KafkaAdmin, KafkaThreadedConsumer
from tests.utils.subp_collector import SubProcCollector

logger = logging.getLogger(__name__)


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


@system_test_fast
def test_main(
    dsn: str,
    conn,
    drop_slot,
    table_name: str,
    popyka_env_vars,
    monkeypatch,
    subp_coll: type[SubProcCollector],
    kafka_bootstrap_servers,
    consumer: KafkaThreadedConsumer,
    topic: str,
):
    popyka_env_vars["POPYKA_COMPACT_DUMP"] = "1"
    popyka_env_vars["POPYKA_KAFKA_BOOTSTRAP_SERVERS"] = kafka_bootstrap_servers
    popyka_env_vars["POPYKA_KAFKA_TOPIC"] = topic

    for key, value in popyka_env_vars.items():
        monkeypatch.setenv(key, value)

    uuids = [str(uuid.uuid4()) for _ in range(4)]

    main = subp_coll(args=["python3", "-m", "popyka"])
    main.start()
    main.wait_for("will consume_stream() adaptor=", timeout=5)

    # Now popyka is consuming the stream, any activity on the db will be consumed

    db_activity_simulator = DbActivitySimulator(
        conn, table_name, [f"INSERT INTO __table_name__ (NAME) VALUES ('{_}')" for _ in uuids]
    )
    db_activity_simulator.start()
    db_activity_simulator.join_or_fail(timeout=2)

    # check changes detected in popyka's stdout

    for an_uuid, change in zip(uuids, main.wait_for_changes(count=len(uuids), timeout_each=3)):
        assert change["action"] == "I"
        assert change["columns"][0]["value"] == an_uuid

    main.kill()
    main.wait()
    main.join_threads()

    # check kafka

    messages = consumer.wait_for_count(4, timeout=10)
    assert len(messages) == 4

    for an_uuid, change in zip(uuids, messages[:4]):
        change = json.loads(change)
        assert change["action"] == "I"
        assert change["columns"][0]["value"] == an_uuid
