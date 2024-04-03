import logging

import psycopg2
import pytest
from psycopg2.extensions import connection as Connection
import psycopg2.extras


logger = logging.getLogger(__name__)


@pytest.fixture
def conn():
    dsn = "host=localhost port=5432 dbname=template1 user=postgres"
    with psycopg2.connect(dsn, connection_factory=psycopg2.extras.LogicalReplicationConnection) as cn:
        with cn.cursor() as cur:
            cur.execute("SELECT slot_name, slot_type, active FROM pg_replication_slots")
            results = cur.fetchall()
            for slot_name, slot_type, active in results:
                logger.warning("Dropping replication slot %s", slot_name)
                cur.execute("SELECT pg_drop_replication_slot(%s)", [slot_name])
        yield cn


def test_connect_to_template1(conn: Connection):
    with conn.cursor() as cur:
        cur.execute("SELECT 1")
        records = cur.fetchall()
        assert records == [(1, )]


def test_start_without_replication_slots(conn: Connection):
    with conn.cursor() as cur:
        cur.execute("SELECT slot_name, slot_type, active FROM pg_replication_slots")
        assert cur.fetchall() == []


def test_pg_create_physical_replication_slot(conn: Connection):
    with conn.cursor() as cur:
        cur: psycopg2.extras.ReplicationCursor
        cur.execute("SELECT * FROM pg_create_physical_replication_slot('pytest')")
        assert cur.fetchone()


def test_start_replication_2():
    dsn = "host=localhost port=5432 dbname=template1 user=postgres"
    cn = psycopg2.connect(dsn, connection_factory=psycopg2.extras.LogicalReplicationConnection)
    cur = cn.cursor()
    try:
        # test_decoding produces textual output
        cur.start_replication(slot_name='pytest_logical', decode=True)
    except psycopg2.ProgrammingError:
        cur.create_replication_slot('pytest_logical', output_plugin='test_decoding')
        cur.start_replication(slot_name='pytest_logical', decode=True)
