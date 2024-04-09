import os

import psycopg2
import psycopg2.errors
import pytest
from psycopg2.extensions import connection as Connection


@pytest.mark.skipif(
    os.environ.get("EXPLORATION_TEST", "0") == "0", reason="Exploration tests ignored (EXPLORATION_TEST)"
)
def test_test_decoding_plugin(dsn, drop_slot):
    conn: Connection = psycopg2.connect(dsn, connection_factory=psycopg2.extras.LogicalReplicationConnection)
    with conn.cursor() as cur:
        cur.create_replication_slot("pytest_logical", output_plugin="test_decoding")
        cur.start_replication(slot_name="pytest_logical", decode=False)


@pytest.mark.skipif(
    os.environ.get("EXPLORATION_TEST", "0") == "0", reason="Exploration tests ignored (EXPLORATION_TEST)"
)
def test_pgoutput_plugin(dsn, drop_slot):
    conn: Connection = psycopg2.connect(dsn, connection_factory=psycopg2.extras.LogicalReplicationConnection)
    with conn.cursor() as cur:
        cur.create_replication_slot("pytest_logical", output_plugin="pgoutput")
        with pytest.raises(psycopg2.errors.FeatureNotSupported):
            # https://github.com/psycopg/psycopg2/issues/1690
            cur.start_replication(slot_name="pytest_logical", decode=False)


def test_wal2json_plugin(dsn, drop_slot):
    conn: Connection = psycopg2.connect(dsn, connection_factory=psycopg2.extras.LogicalReplicationConnection)
    with conn.cursor() as cur:
        cur.create_replication_slot("pytest_logical", output_plugin="wal2json")
        cur.start_replication(slot_name="pytest_logical", decode=False)
