import logging

from psycopg2.extensions import connection as Connection

logger = logging.getLogger(__name__)


def test_connect_to_template1(conn: Connection):
    with conn.cursor() as cur:
        cur.execute("SELECT 1")
        records = cur.fetchall()
        assert records == [(1,)]


def test_start_without_replication_slots(conn: Connection, drop_slot):
    with conn.cursor() as cur:
        cur.execute("SELECT slot_name, slot_type, active FROM pg_replication_slots")
        assert cur.fetchall() == []
