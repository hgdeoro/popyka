import logging

import psycopg2.errors
import pytest
from psycopg2.extensions import connection as Connection

from tests.conftest import exploration_test

logger = logging.getLogger(__name__)


@exploration_test
def test_connect_works(conn: Connection):
    with conn.cursor() as cur:
        cur.execute("SELECT 1")
        records = cur.fetchall()
        assert records == [(1,)]


@exploration_test
def test_drop_slot(conn: Connection, drop_slot):
    with conn.cursor() as cur:
        cur.execute("SELECT slot_name, slot_type, active FROM pg_replication_slots")
        assert cur.fetchall() == []


@exploration_test
def test_create_replication_slot_fails_with_invalid_output_plugin(conn: Connection, drop_slot):
    with conn.cursor() as cur:
        with pytest.raises(psycopg2.errors.UndefinedFile):
            cur.create_replication_slot("pytest_logical", output_plugin="invalid_output_plugin")


@exploration_test
def test_start_replication_with_plugin_test_decoding(conn: Connection, drop_slot):
    with conn.cursor() as cur:
        cur.create_replication_slot("pytest_logical", output_plugin="test_decoding")
        cur.start_replication(slot_name="pytest_logical", decode=True)


@exploration_test
def test_start_replication_with_plugin_pgoutput(conn: Connection, drop_slot):
    with conn.cursor() as cur:
        cur.create_replication_slot("pytest_logical", output_plugin="pgoutput")
        with pytest.raises(psycopg2.errors.FeatureNotSupported):
            # https://github.com/psycopg/psycopg2/issues/1690
            cur.start_replication(slot_name="pytest_logical", decode=False)
