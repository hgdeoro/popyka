import json
import logging
import threading
import time
import uuid

import psycopg2.extras
from psycopg2.extensions import connection as Connection
from psycopg2.extras import ReplicationCursor

from tests.test_db_activity_simulator import DbActivitySimulator

logger = logging.getLogger(__name__)


def _db_activity_simulator(
    cn: Connection,
    table_name: str,
    repl_starting_soon_event: threading.Event,
    done: threading.Event,
    statements: tuple[tuple[str, tuple]],
):
    with cn.cursor() as cur:
        cur: ReplicationCursor
        cur.execute(f"DROP TABLE IF EXISTS {table_name}")
        cn.commit()
        cur.execute(f"CREATE TABLE {table_name} (NAME VARCHAR)")
        cn.commit()

        logger.info("Table %s created, waiting for event to start inserting data...", table_name)
        assert repl_starting_soon_event.wait(timeout=3) is True

        for stmt in statements:
            logger.info("%s | %s", table_name, str(stmt))
            cur.execute(stmt[0], stmt[1])
            cn.commit()

    done.set()


def _db_stream_consumer(cn: Connection, db_activity_simulator: DbActivitySimulator, payloads: list, max_payloads: int):
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

        db_activity_simulator.start_activity()
        try:
            cur.consume_stream(consumer)
        except psycopg2.extras.StopReplication:
            pass

        # TODO: close stream?


def test_db_activity_simulator_fn(conn: Connection, conn2: Connection):
    repl_starting_soon_event = threading.Event()
    db_activity_simulator_done = threading.Event()

    table_name = f"TEST_TABLE_{uuid.uuid4().hex}"
    statements = (
        (f"INSERT INTO {table_name} (NAME) VALUES (gen_random_uuid())", []),
        (f"INSERT INTO {table_name} (NAME) VALUES (gen_random_uuid())", []),
        (f"INSERT INTO {table_name} (NAME) VALUES (gen_random_uuid())", []),
    )
    db_activity_simulator = threading.Thread(
        target=_db_activity_simulator,
        daemon=True,
        args=[conn, table_name, repl_starting_soon_event, db_activity_simulator_done, statements],
    )
    db_activity_simulator.start()
    repl_starting_soon_event.set()
    db_activity_simulator.join()

    assert db_activity_simulator_done.is_set()

    with conn2.cursor() as cur:
        cur.execute(f"SELECT count(*) FROM {table_name}")
        assert cur.fetchall() == [(3,)]


def test_insert_are_replicated(conn: Connection, conn2: Connection, drop_slot, table_name: str):
    uuids = [str(uuid.uuid4()) for _ in range(4)]
    statements = [("INSERT INTO {table_name} (NAME) VALUES (%s)", [_]) for _ in uuids]

    payloads: list = []

    db_activity_simulator = DbActivitySimulator(conn, table_name, statements)

    db_stream_consumer = threading.Thread(
        target=_db_stream_consumer,
        daemon=True,
        args=[conn2, db_activity_simulator, payloads, len(statements)],
    )

    db_activity_simulator.start()
    db_stream_consumer.start()

    db_activity_simulator.join()
    assert db_activity_simulator.is_done

    while len(payloads) < len(statements):
        logger.info("There are %s items in 'payloads'", len(payloads))
        time.sleep(0.2)

    db_stream_consumer.join()

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
    assert [_["change"][0]["kind"] for _ in payloads] == ["insert"] * 4
    assert [_["change"][0]["columnvalues"][0] for _ in payloads] == uuids
