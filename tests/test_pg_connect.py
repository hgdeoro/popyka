import logging

import pytest
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


def test_start_replication_plugin_test_decoding(conn: Connection, drop_slot):
    with conn.cursor() as cur:
        cur.create_replication_slot("pytest_logical", output_plugin="test_decoding")
        cur.start_replication(slot_name="pytest_logical", decode=True)


@pytest.mark.xfail
def test_start_replication_plugin_pgoutput(conn: Connection, drop_slot):
    with conn.cursor() as cur:
        cur.create_replication_slot("pytest_logical", output_plugin="pgoutput")
        cur.start_replication(slot_name="pytest_logical", decode=False)

    # >       self.start_replication_expert(
    #             command, decode=decode, status_interval=status_interval)
    # E       psycopg2.errors.FeatureNotSupported:
    #                           client sent proto_version=0 but server only supports protocol 1 or higher
    # E       CONTEXT:  slot "pytest_logical", output plugin "pgoutput", in the startup callback
