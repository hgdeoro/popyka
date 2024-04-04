import json
import logging
import threading
import time
import uuid

import psycopg2.extras
from psycopg2.extensions import connection as Connection

from tests.test_db_activity_simulator import DbActivitySimulator

logger = logging.getLogger(__name__)


class DbStreamConsumer(threading.Thread):
    def __init__(self, cn: Connection, db_activity_simulator: DbActivitySimulator, max_payloads: int):
        super().__init__(daemon=True)
        self._cn = cn
        self._db_activity_simulator = db_activity_simulator
        self._max_payloads = max_payloads
        self._payloads = []

    @property
    def payloads(self) -> list:
        return self._payloads

    @property
    def payloads_parsed(self) -> list[dict]:
        return [json.loads(_) for _ in self._payloads]

    def run(self) -> None:
        with self._cn.cursor() as cur:
            cur.create_replication_slot("pytest_logical", output_plugin="wal2json")
            cur.start_replication(slot_name="pytest_logical", decode=True)

            _payloads = self._payloads
            _max_payloads = self._max_payloads

            class DemoConsumer(object):
                def __call__(self, msg: psycopg2.extras.ReplicationMessage):
                    logger.info("DemoConsumer received payload: %s", msg.payload)
                    _payloads.append(msg.payload)
                    msg.cursor.send_feedback(flush_lsn=msg.data_start)

                    if len(_payloads) == _max_payloads:
                        raise psycopg2.extras.StopReplication()

            consumer = DemoConsumer()

            self._db_activity_simulator.start_activity()
            try:
                cur.consume_stream(consumer)
            except psycopg2.extras.StopReplication:
                pass

            # TODO: close stream?


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
