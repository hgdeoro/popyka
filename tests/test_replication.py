import json
import logging
import os
import threading
import time
import uuid

import psycopg2.extras
import pytest
from psycopg2.extensions import connection as Connection

from tests.test_db_activity_simulator import DbActivitySimulator

logger = logging.getLogger(__name__)

#  pg_logical_emit_message ( transactional boolean, prefix text, content text ) → pg_lsn
MAGIC_END_OF_TEST_PREFIX = "popyka_pytest"
MAGIC_END_OF_TEST_CONTENT = "742cad81-3416-4dc8-9f7a-d667b54c98cf"
MAGIC_END_OF_TEST_STATEMENT = (
    "SELECT * FROM pg_logical_emit_message(FALSE, %s, %s)",
    [MAGIC_END_OF_TEST_PREFIX, MAGIC_END_OF_TEST_CONTENT],
)


class DbStreamConsumer(threading.Thread):
    def __init__(self, cn: Connection, db_activity_simulator: DbActivitySimulator, max_payloads: int, options=None):
        super().__init__(daemon=True)
        self._cn = cn
        self._db_activity_simulator = db_activity_simulator
        self._max_payloads = max_payloads
        self._payloads = []
        self._options = options or {}

    @property
    def payloads(self) -> list:
        return self._payloads

    @property
    def payloads_parsed(self) -> list[dict]:
        return [json.loads(_) for _ in self._payloads]

    def run(self) -> None:
        with self._cn.cursor() as cur:
            cur.create_replication_slot("pytest_logical", output_plugin="wal2json")
            cur.start_replication(slot_name="pytest_logical", decode=True, options=self._options)

            _payloads = self._payloads
            _max_payloads = self._max_payloads

            class DemoConsumer(object):
                def __call__(self, msg: psycopg2.extras.ReplicationMessage):
                    logger.info("DemoConsumer received payload: %s", msg.payload)
                    msg.cursor.send_feedback(flush_lsn=msg.data_start)

                    if _max_payloads is None:
                        decoded = json.loads(msg.payload)
                        if (
                            decoded.get("action") == "M"
                            and decoded.get("prefix") == MAGIC_END_OF_TEST_PREFIX
                            and decoded.get("content") == MAGIC_END_OF_TEST_CONTENT
                        ):
                            # {
                            #     "action": "M",
                            #     "transactional": false,
                            #     "prefix": "popyka_pytest",
                            #     "content": "742cad81-3416-4dc8-9f7a-d667b54c98cf"
                            # }
                            raise psycopg2.extras.StopReplication()

                    _payloads.append(msg.payload)

                    if len(_payloads) == _max_payloads:
                        raise psycopg2.extras.StopReplication()

            consumer = DemoConsumer()

            self._db_activity_simulator.start_activity()
            try:
                cur.consume_stream(consumer)
            except psycopg2.extras.StopReplication:
                pass

            # TODO: close stream?


@pytest.mark.skipif(
    os.environ.get("EXPLORATION_TEST", "0") == "0", reason="Exploration tests ignored (EXPLORATION_TEST)"
)
def test_insert_are_replicated(conn: Connection, conn2: Connection, drop_slot, table_name: str):
    uuids = [str(uuid.uuid4()) for _ in range(4)]
    statements = [("INSERT INTO {table_name} (NAME) VALUES (%s)", [_]) for _ in uuids]

    db_activity_simulator = DbActivitySimulator(conn, table_name, statements)
    db_stream_consumer = DbStreamConsumer(conn2, db_activity_simulator, len(statements))

    db_activity_simulator.start()
    db_stream_consumer.start()
    db_activity_simulator.join()
    assert db_activity_simulator.is_done

    while len(db_stream_consumer.payloads) < len(statements):
        logger.info("There are %s items in 'payloads'", len(db_stream_consumer.payloads))
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

    json_payloads = db_stream_consumer.payloads_parsed
    assert [_["change"][0]["kind"] for _ in json_payloads] == ["insert"] * 4
    assert [_["change"][0]["columnvalues"][0] for _ in json_payloads] == uuids


@pytest.mark.skipif(
    os.environ.get("EXPLORATION_TEST", "0") == "0", reason="Exploration tests ignored (EXPLORATION_TEST)"
)
def test_json_for_default_options(conn: Connection, conn2: Connection, drop_slot, table_name: str):
    statements = [
        ("INSERT INTO {table_name} (NAME) VALUES ('this-is-the-value-1')", []),
        ("INSERT INTO {table_name} (NAME) VALUES ('this-is-the-value-2')", []),
    ]
    expected_payloads = 2
    options = {}

    db_activity_simulator = DbActivitySimulator(conn, table_name, statements)
    db_stream_consumer = DbStreamConsumer(conn2, db_activity_simulator, expected_payloads, options=options)

    db_activity_simulator.start()
    db_stream_consumer.start()
    db_activity_simulator.join()
    assert db_activity_simulator.is_done

    while len(db_stream_consumer.payloads) < expected_payloads:
        logger.info("There are %s items in 'payloads'", len(db_stream_consumer.payloads))
        time.sleep(0.2)

    db_stream_consumer.join()

    assert db_stream_consumer.payloads_parsed == [
        {
            "change": [
                {
                    "columnnames": [
                        "name",
                    ],
                    "columntypes": [
                        "character varying",
                    ],
                    "columnvalues": [
                        "this-is-the-value-1",
                    ],
                    "kind": "insert",
                    "schema": "public",
                    "table": table_name.lower(),
                },
            ],
        },
        {
            "change": [
                {
                    "columnnames": [
                        "name",
                    ],
                    "columntypes": [
                        "character varying",
                    ],
                    "columnvalues": [
                        "this-is-the-value-2",
                    ],
                    "kind": "insert",
                    "schema": "public",
                    "table": table_name.lower(),
                },
            ],
        },
    ]


def test_format_version_2(conn: Connection, conn2: Connection, drop_slot, table_name: str):
    statements = [
        ("INSERT INTO {table_name} (NAME) VALUES ('this-is-the-value-1')", []),
        ("INSERT INTO {table_name} (NAME) VALUES ('this-is-the-value-2')", []),
        MAGIC_END_OF_TEST_STATEMENT,
    ]
    expected_payloads = 6
    # https://github.com/eulerto/wal2json?tab=readme-ov-file
    options = {"format-version": "2"}

    db_activity_simulator = DbActivitySimulator(conn, table_name, statements)
    db_stream_consumer = DbStreamConsumer(conn2, db_activity_simulator, max_payloads=None, options=options)

    db_activity_simulator.start()
    db_stream_consumer.start()
    db_activity_simulator.join()
    assert db_activity_simulator.is_done

    while len(db_stream_consumer.payloads) < expected_payloads:
        logger.info("There are %s items in 'payloads'", len(db_stream_consumer.payloads))
        time.sleep(0.2)

    db_stream_consumer.join()

    assert db_stream_consumer.payloads_parsed == [
        {"action": "B"},
        {
            "action": "I",
            "schema": "public",
            "table": table_name.lower(),
            "columns": [{"name": "name", "type": "character varying", "value": "this-is-the-value-1"}],
        },
        {"action": "C"},
        {"action": "B"},
        {
            "action": "I",
            "schema": "public",
            "table": table_name.lower(),
            "columns": [{"name": "name", "type": "character varying", "value": "this-is-the-value-2"}],
        },
        {"action": "C"},
    ]
