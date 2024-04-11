import logging
import os
import uuid

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


@pytest.fixture
def table_name() -> str:
    return f"TEST_TABLE_{uuid.uuid4().hex}"


@pytest.fixture
def dsn():
    return DSN_POSTGRES_WAL2JSON


@pytest.fixture
def drop_slot(dsn: str):
    with psycopg2.connect(dsn, connection_factory=psycopg2.extras.LogicalReplicationConnection) as cn:
        with cn.cursor() as cur:
            cur.execute("SELECT slot_name, slot_type, active FROM pg_replication_slots")
            results = cur.fetchall()
            for slot_name, slot_type, active in results:
                logger.warning("Dropping replication slot %s", slot_name)
                cur.execute("SELECT pg_drop_replication_slot(%s)", [slot_name])


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
