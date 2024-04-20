import json
import logging
import time
import uuid

import pytest

from tests.utils.db_activity_simulator import DbActivitySimulator
from tests.utils.kafka import KafkaAdmin, KafkaThreadedConsumer
from tests.utils.subp_collector import SubProcCollector

logger = logging.getLogger(__name__)


@pytest.fixture
def topic():
    # TODO: Refactor to avoid code duplication: this was copied from system-tests.
    return f"popyka_{int(time.time())}"


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
    # config_file = pathlib.Path(__file__).parent.parent / "resources" / "config-test-main.yaml"
    # popyka_env_vars["POPYKA_CONFIG"] = str(config_file.absolute())
    popyka_env_vars["LAZYTOSTR_COMPACT"] = "1"
    popyka_env_vars["POPYKA_KAFKA_BOOTSTRAP_SERVERS"] = kafka_bootstrap_servers
    popyka_env_vars["POPYKA_KAFKA_TOPIC"] = topic

    for key, value in popyka_env_vars.items():
        monkeypatch.setenv(key, value)

    args = ["python3", "-m", "popyka"]
    main = subp_coll(args=args)

    main.start()
    # main.wait_for("Using custom config file", timeout=5)
    main.wait_for("will consume_stream() adaptor=", timeout=5)

    uuids = [str(uuid.uuid4()) for _ in range(4)]
    statements = [("INSERT INTO {table_name} (NAME) VALUES (%s)", [_]) for _ in uuids]
    db_activity_simulator = DbActivitySimulator(conn, table_name, statements)
    db_activity_simulator.start()
    db_activity_simulator.join_or_fail(timeout=2)

    # check changes detected in popyka's stdout
    changes = []
    for an_uuid in uuids:
        change = main.wait_for_change(timeout=3)
        changes.append(change)
        assert change["action"] == "I"
        assert change["columns"][0]["value"] == an_uuid

    main.kill()
    main.wait()
    main.join_threads()

    assert len(changes) == 4
    del change
    del changes

    # check kafka
    messages = consumer.wait_for_count(4, timeout=10)
    assert len(messages) >= 4  # `DbActivitySimulator` can generate an extra event that we should ignore

    for an_uuid, change in zip(uuids, messages[:4]):
        change = json.loads(change)
        assert change["action"] == "I"
        assert change["columns"][0]["value"] == an_uuid
