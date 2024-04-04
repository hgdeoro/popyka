import json
import logging
import threading
import time
import uuid

import psycopg2.extras
from psycopg2.extensions import connection as Connection
from psycopg2.extras import ReplicationCursor

logger = logging.getLogger(__name__)


def _db_activity_simulator(
    cn: Connection,
    table_name: str,
    repl_starting_soon_event: threading.Event,
    done: threading.Event,
):
    with cn.cursor() as cur:
        cur: ReplicationCursor
        cur.execute(f"DROP TABLE IF EXISTS {table_name}")
        cn.commit()
        cur.execute(f"CREATE TABLE {table_name} (NAME VARCHAR)")
        cn.commit()

        logger.info("Table created, waiting for event to start inserting data...")
        assert repl_starting_soon_event.wait(timeout=3) is True

        cur.execute(f"INSERT INTO {table_name} (NAME) VALUES (gen_random_uuid())")
        cur.execute(f"INSERT INTO {table_name} (NAME) VALUES (gen_random_uuid())")
        cur.execute(f"INSERT INTO {table_name} (NAME) VALUES (gen_random_uuid())")
        cur.execute(f"INSERT INTO {table_name} (NAME) VALUES (gen_random_uuid())")
        cur.execute(f"INSERT INTO {table_name} (NAME) VALUES (gen_random_uuid())")
        cn.commit()

    done.set()


def _db_stream_consumer(cn: Connection, repl_starting_soon_event: threading.Event, payloads: list, max_payloads=15):
    with cn.cursor() as cur:
        cur.create_replication_slot("pytest_logical", output_plugin="wal2json")
        cur.start_replication(slot_name="pytest_logical", decode=True)

        class DemoConsumer(object):
            def __call__(self, msg: psycopg2.extras.ReplicationMessage):
                logger.info("DemoConsumer received payload: %s", msg.payload)
                payloads.append(msg.payload)
                msg.cursor.send_feedback(flush_lsn=msg.data_start)

                if len(payloads) == max_payloads:
                    raise psycopg2.extras.StopReplication()

        consumer = DemoConsumer()

        repl_starting_soon_event.set()
        try:
            cur.consume_stream(consumer)
        except psycopg2.extras.StopReplication:
            pass

        # TODO: close stream?


def test_db_activity_simulator(conn: Connection, conn2: Connection):
    repl_starting_soon_event = threading.Event()
    db_activity_simulator_done = threading.Event()

    table_name = f"TEST_TABLE_{uuid.uuid4().hex}"
    db_activity_simulator = threading.Thread(
        target=_db_activity_simulator,
        daemon=True,
        args=[conn, table_name, repl_starting_soon_event, db_activity_simulator_done],
    )
    db_activity_simulator.start()
    repl_starting_soon_event.set()
    db_activity_simulator.join(timeout=5)
    assert not db_activity_simulator.is_alive()

    assert db_activity_simulator_done.is_set()

    with conn2.cursor() as cur:
        cur.execute(f"SELECT count(*) FROM {table_name}")
        assert cur.fetchall() == [(5,)]


def test_start_replication(conn: Connection, conn2: Connection, drop_slot):
    table_name = f"TEST_TABLE_{uuid.uuid4().hex}"
    payloads: list = []
    repl_starting_soon_event = threading.Event()
    db_activity_simulator_done = threading.Event()

    db_activity_simulator = threading.Thread(
        target=_db_activity_simulator,
        daemon=True,
        args=[conn, table_name, repl_starting_soon_event, db_activity_simulator_done],
    )

    db_stream_consumer = threading.Thread(
        target=_db_stream_consumer,
        daemon=True,
        args=[conn2, repl_starting_soon_event, payloads, 5],
    )

    db_activity_simulator.start()
    db_stream_consumer.start()

    db_activity_simulator.join(timeout=3)
    assert not db_activity_simulator.is_alive()
    assert db_activity_simulator_done.is_set()

    while len(payloads) < 5:
        logger.info("There are %s items in 'payloads'", len(payloads))
        time.sleep(0.2)

    db_stream_consumer.join(timeout=3)
    assert not db_stream_consumer.is_alive()

    assert len(payloads) == 5

    # {
    #     "change": [
    #         {
    #             "kind": "insert",
    #             "schema": "public",
    #             "table": "test_table_005902aae27f4f7ab33fada1c78d7f14",
    #             "columnnames": [
    #                 "name"
    #             ],
    #             "columntypes": [
    #                 "character varying"
    #             ],
    #             "columnvalues": [
    #                 "53b5cda2-e3cc-4011-a9c7-7f628bc7e008"
    #             ]
    #         }
    #     ]
    # },

    payloads = [json.loads(_) for _ in payloads]
    kinds = [_["change"][0]["kind"] for _ in payloads]
    assert kinds == ["insert"] * 5
