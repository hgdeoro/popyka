import abc
import json
import logging
import os
import pprint
import threading
import typing

import psycopg2.extras
from confluent_kafka import Producer
from psycopg2.extensions import connection as Connection
from psycopg2.extras import ReplicationCursor

logger = logging.getLogger(__name__)


def _get_connection() -> Connection:
    dsn = os.environ.get("DSN")
    logger.info("Connecting dsn=%s...", dsn[:4])
    cn: Connection = psycopg2.connect(dsn, connection_factory=psycopg2.extras.LogicalReplicationConnection)
    logger.info("Server version: %s", cn.info.server_version)
    return cn


def _get_slot_name() -> str:
    return "popyka"


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
    def process_change(self, change: Wal2JsonV2Change):
        logger.info("DumpToStdOutProcessor: change: %s", pprint.pformat(change))


class ProduceToKafkaProcessor(Processor):
    def _get_conf(self) -> dict:
        return json.loads(os.environ.get("KAFKA_CONF_DICT"))

    def __init__(self):
        self._producer = Producer(self._get_conf())

    def process_change(self, change: Wal2JsonV2Change):
        self._producer.produce(topic="popyka", value=json.dumps(change))
        self._producer.flush()
        logger.info("Message written to Kafka")


def _get_processors() -> list[Processor]:
    return [DumpToStdOutProcessor(), ProduceToKafkaProcessor()]


def main():
    consumer = ConsumerRunProcessors(_get_processors())
    main_instance = Main(cn=_get_connection(), slot_name=_get_slot_name(), consumer=consumer)
    logger.info("Starting consumer...")
    main_instance.start()
    try:
        main_instance.join()
    except KeyboardInterrupt:
        pass


class ConsumerRunProcessors:
    def __init__(self, processors: list[Processor]):
        self._processors = processors

    def __call__(self, msg: psycopg2.extras.ReplicationMessage):
        logger.info("ConsumerRunProcessors: received payload: %s", msg)
        change = Wal2JsonV2Change(json.loads(msg.payload))
        for processor in self._processors:
            processor.process_change(change)
        msg.cursor.send_feedback(flush_lsn=msg.data_start)


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
