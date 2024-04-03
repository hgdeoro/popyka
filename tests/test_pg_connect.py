import psycopg2
import pytest
from psycopg2.extensions import connection as Connection
import psycopg2.extras


@pytest.fixture
def conn():
    dsn = "host=localhost port=5432 dbname=template1 user=postgres"
    with psycopg2.connect(dsn, connection_factory=psycopg2.extras.LogicalReplicationConnection) as cn:
        yield cn


def test_connect_to_template1(conn: Connection):
    with conn.cursor() as cur:
        cur.execute("SELECT 1")
        records = cur.fetchall()
        assert records == [(1, )]


def test_start_replication(conn: Connection):
    with conn.cursor() as cur:
        cur.start_replication(slot_name='pytest', decode=True)
