import logging
import threading
import uuid

import psycopg2
import psycopg2.extras
import pytest
from psycopg2.extensions import connection as Connection
from psycopg2.extras import ReplicationCursor

logger = logging.getLogger(__name__)


@pytest.fixture
def dsn():
    return "host=localhost port=5432 dbname=postgres user=postgres"


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
    except:
        logger.exception("Exception detected when trying to close connection")


@pytest.fixture
def conn2(dsn: str):
    cn: Connection = psycopg2.connect(dsn, connection_factory=psycopg2.extras.LogicalReplicationConnection)

    yield cn

    try:
        cn.close()
    except:
        logger.exception("Exception detected when trying to close connection")


def test_connect_to_template1(conn: Connection):
    with conn.cursor() as cur:
        cur.execute("SELECT 1")
        records = cur.fetchall()
        assert records == [(1,)]


def test_start_without_replication_slots(conn: Connection, drop_slot):
    with conn.cursor() as cur:
        cur.execute("SELECT slot_name, slot_type, active FROM pg_replication_slots")
        assert cur.fetchall() == []


def _db_activity_simulator(cn: Connection, table_name: str, repl_starting_soon_event: threading.Event,
                           db_activity_simulator_done: threading.Event):
    with cn.cursor() as cur:
        cur: ReplicationCursor
        cur.execute(f"DROP TABLE IF EXISTS {table_name}")
        cn.commit()
        cur.execute(f"CREATE TABLE {table_name} (NAME VARCHAR)")
        cn.commit()

        logger.info("Table created, waiting for event to start inserting data...")
        event_received = repl_starting_soon_event.wait(timeout=3)
        assert event_received is True

        cur.execute(f"INSERT INTO {table_name} (NAME) VALUES (gen_random_uuid())")
        cur.execute(f"INSERT INTO {table_name} (NAME) VALUES (gen_random_uuid())")
        cur.execute(f"INSERT INTO {table_name} (NAME) VALUES (gen_random_uuid())")
        cur.execute(f"INSERT INTO {table_name} (NAME) VALUES (gen_random_uuid())")
        cur.execute(f"INSERT INTO {table_name} (NAME) VALUES (gen_random_uuid())")
        cn.commit()

    db_activity_simulator_done.set()


def test__db_activity_simulator(conn: Connection, conn2: Connection):
    repl_starting_soon_event = threading.Event()
    db_activity_simulator_done = threading.Event()

    table_name = f"TEST_TABLE_{uuid.uuid4().hex}"
    db_activity_simulator = threading.Thread(target=_db_activity_simulator, daemon=True,
                                             args=[conn, table_name, repl_starting_soon_event, db_activity_simulator_done])
    db_activity_simulator.start()
    repl_starting_soon_event.set()
    db_activity_simulator.join()

    assert db_activity_simulator_done.is_set()

    with conn2.cursor() as cur:
        cur.execute(f"SELECT count(*) FROM {table_name}")
        assert cur.fetchall() == [(5, )]


@pytest.mark.skip
def test_start_replication_2(conn: Connection, conn2: Connection, drop_slot):
    repl_starting_soon_event = threading.Event()
    db_activity_simulator_done = threading.Event()

    db_activity_simulator = threading.Thread(target=_db_activity_simulator, daemon=True,
                                             args=[conn, repl_starting_soon_event, db_activity_simulator_done])
    db_activity_simulator.start()
    db_activity_simulator.join()

    assert db_activity_simulator_done.is_set()

    # with conn.cursor() as cur:
    #     cur.create_replication_slot('pytest_logical', output_plugin='test_decoding')
    #     cur.start_replication(slot_name='pytest_logical', decode=True)
    #
    #     class DemoConsumer(object):
    #         def __call__(self, msg):
    #             print(msg.payload)
    #             msg.cursor.send_feedback(flush_lsn=msg.data_start)
    #
    #     consumer = DemoConsumer()
    #
    #     cur.consume_stream(consumer)
