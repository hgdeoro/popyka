import json
import logging
import threading
import typing

import psycopg2.extras
from psycopg2.extensions import connection as Connection
from psycopg2.extras import ReplicationCursor

logger = logging.getLogger(__name__)


def main():
    dsn = "host=localhost port=5434 dbname=postgres user=postgres"
    logger.info("Connecting...")
    cn: Connection = psycopg2.connect(dsn, connection_factory=psycopg2.extras.LogicalReplicationConnection)
    main_instance = Main(cn=cn, slot_name="popyka", consumer=ConsumerDumpToLog())
    logger.info("Starting consumer...")
    main_instance.start()
    try:
        main_instance.join()
    except KeyboardInterrupt:
        pass


class ConsumerDumpToLog:
    def __call__(self, msg: psycopg2.extras.ReplicationMessage):
        payload = json.dumps(json.loads(msg.payload), indent=4, sort_keys=True)
        logger.info("ConsumerDumpToLog: received payload: %s", payload)
        msg.cursor.send_feedback(flush_lsn=msg.data_start)


class ConsumerStatsToLog:
    def __call__(self, msg: psycopg2.extras.ReplicationMessage):
        logger.info("ConsumerStatsToLog: received payload size: %s", len(msg.payload))
        msg.cursor.send_feedback(flush_lsn=msg.data_start)


class Main(threading.Thread):
    def __init__(self, cn: Connection, slot_name: str, consumer: typing.Callable):
        super().__init__(daemon=True)
        self._cn = cn
        self._slot_name = slot_name
        self._consumer = consumer

    def run(self) -> None:
        with self._cn.cursor() as cur:
            cur: ReplicationCursor
            try:
                cur.create_replication_slot(self._slot_name, output_plugin="wal2json")
            except psycopg2.errors.DuplicateObject:
                logger.info("Replication slot %s already exists", self._slot_name)

            cur.start_replication(slot_name=self._slot_name, decode=True, options={"format-version": "2"})
            cur.consume_stream(self._consumer)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()