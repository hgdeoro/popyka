import logging
import os
import subprocess
import time
import uuid
from typing import Callable

import psycopg2
import psycopg2.extras
import pytest
from psycopg2.extensions import connection as Connection

from tests import conftest_all_scenarios
from tests.utils.kafka import KafkaAdmin
from tests.utils.subp_collector import SubProcCollector

logger = logging.getLogger(__name__)

OVERRIDE_HOST = os.environ.get("OVERRIDE_HOST", "localhost")
OVERRIDE_PORT = os.environ.get("OVERRIDE_PORT", "54016")

DSN_POSTGRES_WAL2JSON = f"postgresql://postgres:pass@{OVERRIDE_HOST}:{OVERRIDE_PORT}/popyka_test"

KAFKA_BOOTSTRAP_SERVERS = os.environ.get("OVERRIDE_KAFKA_BOOTSTRAP_SERVERS", "localhost:9094")

exploration_test = pytest.mark.skipif(
    os.environ.get("EXPLORATION_TEST", "0") == "0", reason="Exploration tests ignored (EXPLORATION_TEST)"
)

system_test = pytest.mark.skipif(os.environ.get("SYSTEM_TEST", "0") == "0", reason="System tests ignored (SYSTEM_TEST)")

system_test_fast = pytest.mark.skipif(
    os.environ.get("SYSTEM_TEST_FAST", "0") == "0", reason="Fast system tests ignored (SYSTEM_TEST_FAST)"
)

contract_test = pytest.mark.skipif(
    os.environ.get("CONTRACT_TEST", "0") == "0", reason="Contract tests ignored (CONTRACT_TEST)"
)

slow_test = pytest.mark.skipif(os.environ.get("SLOW_TEST", "0") == "0", reason="Slow tests ignored (SLOW_TEST)")

all_scenarios = conftest_all_scenarios.all_scenarios  # imported fixture
all_scenarios_predictable = conftest_all_scenarios.all_scenarios_predictable  # imported fixture


@pytest.fixture
def table_name() -> str:
    return f"TEST_TABLE_{uuid.uuid4().hex}"


@pytest.fixture
def dsn():
    return DSN_POSTGRES_WAL2JSON


@pytest.fixture
def kafka_bootstrap_servers():
    return KAFKA_BOOTSTRAP_SERVERS


@pytest.fixture
def popyka_env_vars(dsn: str, table_name: str):
    return {
        "POPYKA_DB_DSN": dsn,
        "POPYKA_KAFKA_BOOTSTRAP_SERVERS": "localhost:1234",
        "POPYKA_DB_SLOT_NAME": f"test_popyka_{table_name}".lower(),
    }


@pytest.fixture
def drop_slot_fn():
    def fn(dsn: str):
        with psycopg2.connect(dsn, connection_factory=psycopg2.extras.LogicalReplicationConnection) as cn:
            with cn.cursor() as cur:
                cur.execute("SELECT slot_name, slot_type, active FROM pg_replication_slots")
                results = cur.fetchall()
                for slot_name, slot_type, active in results:
                    logger.warning("Dropping replication slot %s", slot_name)
                    cur.execute("SELECT pg_drop_replication_slot(%s)", [slot_name])

    return fn


@pytest.fixture
def drop_slot(dsn: str, drop_slot_fn: Callable):
    drop_slot_fn(dsn)


@pytest.fixture
def conn(dsn: str):
    cn: Connection = psycopg2.connect(dsn, connection_factory=psycopg2.extras.LogicalReplicationConnection)

    yield cn

    try:
        cn.close()
    except:  # noqa: E722
        logger.exception("Exception detected when trying to close connection")


@pytest.fixture
def conn2(dsn: str):
    cn: Connection = psycopg2.connect(dsn, connection_factory=psycopg2.extras.LogicalReplicationConnection)

    yield cn

    try:
        cn.close()
    except:  # noqa: E722
        logger.exception("Exception detected when trying to close connection")


@pytest.fixture
def subp_coll() -> type[SubProcCollector]:
    subp_coll_instances: list[SubProcCollector] = []

    def instantiate(*args, **kwargs):
        instance = SubProcCollector(*args, **kwargs)
        subp_coll_instances.append(instance)
        return instance

    yield instantiate

    for _ in subp_coll_instances:
        _.kill()

    for _ in subp_coll_instances:
        try:
            _.wait(timeout=2)
        except subprocess.TimeoutExpired:
            logger.exception(f"Ignoring TimeoutExpired for {_}")


@pytest.fixture
def topic():
    return f"popyka_{int(time.time())}"


@pytest.fixture
def slot_name():
    return f"popyka_test_{int(time.time())}"


@pytest.fixture()
def kafka_admin(kafka_bootstrap_servers: str) -> KafkaAdmin:
    return KafkaAdmin(kafka_bootstrap_servers)
