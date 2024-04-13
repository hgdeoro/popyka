import logging
import os
import uuid
from typing import Callable

import psycopg2
import psycopg2.extras
import pytest
from psycopg2.extensions import connection as Connection

logger = logging.getLogger(__name__)

OVERRIDE_PORT = os.environ.get("OVERRIDE_PORT", "54016")

DSN_POSTGRES_WAL2JSON = f"postgresql://postgres:pass@localhost:{OVERRIDE_PORT}/popyka_test"

exploration_test = pytest.mark.skipif(
    os.environ.get("EXPLORATION_TEST", "0") == "0", reason="Exploration tests ignored (EXPLORATION_TEST)"
)

system_test = pytest.mark.skipif(os.environ.get("SYSTEM_TEST", "0") == "0", reason="System tests ignored (SYSTEM_TEST)")


@pytest.fixture
def table_name() -> str:
    return f"TEST_TABLE_{uuid.uuid4().hex}"


@pytest.fixture
def dsn():
    return DSN_POSTGRES_WAL2JSON


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
