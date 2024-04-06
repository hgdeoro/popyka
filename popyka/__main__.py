import abc
import json
import logging
import os
import threading
import typing
from urllib.parse import urlparse

import psycopg2.extras
from confluent_kafka import Producer
from psycopg2.extensions import connection as Connection
from psycopg2.extras import ReplicationCursor

logger = logging.getLogger(__name__)


class Wal2JsonV2Change(dict):
    # FIXME: this is pretty awful, name and design
    pass


class Processor(abc.ABC):
    # FIXME: this is pretty awful, name and design
    # on_error?
    # retries?

    def process_change(self, change: Wal2JsonV2Change):
        raise NotImplementedError()


class DumpToStdOutProcessor(Processor):
    """Processor that dumps the payload"""

    def process_change(self, change: Wal2JsonV2Change):
        # FIXME: make json.dumps() lazy
        logger.debug("DumpToStdOutProcessor: change: %s", json.dumps(change, indent=4))


class ProduceToKafkaProcessor(Processor):
    def _get_conf(self) -> dict:
        return json.loads(os.environ.get("KAFKA_CONF_DICT"))

    def __init__(self):
        self._producer = Producer(self._get_conf())

    def process_change(self, change: Wal2JsonV2Change):
        self._producer.produce(topic="popyka", value=json.dumps(change))
        self._producer.flush()
        logger.info("Message produced to Kafka was flush()'ed")


class ReplicationConsumerToProcessorAdapter:
    """Psycopg2 replication consumer that runs configured PoPyKa processors on the received changes"""

    def __init__(self, processors: list[Processor]):
        self._processors = processors

    def __call__(self, msg: psycopg2.extras.ReplicationMessage):
        logger.info("ConsumerRunProcessors: received payload: %s", msg)
        change = Wal2JsonV2Change(json.loads(msg.payload))
        for processor in self._processors:
            processor.process_change(change)

        # Flush after every message is successfully processed
        msg.cursor.send_feedback(flush_lsn=msg.data_start)


def _parse_dsn(dsn: str) -> tuple[object, str]:
    dsn_parsed = urlparse(dsn)
    db_name = dsn_parsed.path
    assert db_name.startswith("/")
    db_name = db_name[1:]
    return dsn_parsed, db_name


def _get_connection() -> Connection:
    # https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-CONNSTRING
    dsn = os.environ.get("DSN")
    dsn_parsed, db_name = _parse_dsn(dsn)
    logger.info(
        "Connecting host=%s port=%s user=%s db=%s", dsn_parsed.hostname, dsn_parsed.port, dsn_parsed.username, db_name
    )
    cn: Connection = psycopg2.connect(dsn, connection_factory=psycopg2.extras.LogicalReplicationConnection)
    logger.info("Server version: %s", cn.info.server_version)
    return cn


def _get_slot_name() -> str:
    # FIXME: let user overwrite via env variables
    _, db_name = _parse_dsn(os.environ.get("DSN"))
    return f"popyka_{db_name}"


def _get_processors() -> list[Processor]:
    return [DumpToStdOutProcessor(), ProduceToKafkaProcessor()]


class Main(threading.Thread):
    # TODO: why a thread? Try to simplify this

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


def main():
    consumer = ReplicationConsumerToProcessorAdapter(_get_processors())
    main_instance = Main(cn=_get_connection(), slot_name=_get_slot_name(), consumer=consumer)
    logger.info("Starting consumer...")
    main_instance.start()
    try:
        main_instance.join()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
