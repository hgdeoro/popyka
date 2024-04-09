import abc
import json
import logging
import os

import psycopg2.extras
from psycopg2.extensions import connection as Connection
from psycopg2.extras import ReplicationCursor

logger = logging.getLogger(__name__)


POPYKA_DB_DSN = os.environ.get("POPYKA_DB_DSN")
"""URI: DSN to connect to PostgreSql"""


POPYKA_KAFKA_CONF_DICT = os.environ.get("POPYKA_KAFKA_CONF_DICT")
"""JSON formatted configuration of Kafka producer"""


class Wal2JsonV2Change(dict):
    """Represent a change generated by wal2json using format version 2"""

    # TODO: use class or dataclass, to make API more clear and easier for implementations of `Processors`


class Processor(abc.ABC):
    """Base class for processors of changes"""

    # FIXME: this is pretty awful, name and design.
    # TODO: Implement error handling, retries, etc.

    def process_change(self, change: Wal2JsonV2Change):
        """Receives a change and process it."""
        raise NotImplementedError()


class Filter(abc.ABC):
    """Base class for change filters"""

    def ignore_change(self, change: Wal2JsonV2Change) -> bool:
        """
        Receives a change and returns True if should be ignored.
        Ignored changes won't reach the processors.
        """
        raise NotImplementedError()


class ReplicationConsumerToProcessorAdaptor:
    """Psycopg2 replication consumer that runs configured PoPyKa Processors on the received changes"""

    def __init__(self, processors: list[Processor], filters: list[Filter]):
        self._processors = processors
        self._filters = filters

    def __call__(self, msg: psycopg2.extras.ReplicationMessage):
        logger.info("ConsumerRunProcessors: received payload: %s", msg)
        change = Wal2JsonV2Change(json.loads(msg.payload))
        ignore = any([a_filter.ignore_change(change) for a_filter in self._filters])

        if ignore:
            logger.info("Ignoring change")
        else:
            for processor in self._processors:
                processor.process_change(change)

        # Flush after every message is successfully processed
        msg.cursor.send_feedback(flush_lsn=msg.data_start)


class Server(abc.ABC):
    @abc.abstractmethod
    def get_filters(self) -> list[Filter]:
        raise NotImplementedError()

    @abc.abstractmethod
    def get_processors(self) -> list[Processor]:
        raise NotImplementedError()

    @abc.abstractmethod
    def get_slot_name(self) -> str:
        # TODO: let user overwrite via env variables
        raise NotImplementedError()

    @abc.abstractmethod
    def get_connection(self) -> Connection:
        """Returns a psycopg2 connection"""
        # https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-CONNSTRING
        raise NotImplementedError()

    @abc.abstractmethod
    def get_dsn(self) -> tuple[str, object, str]:
        """Return DSN, parsed URI and database name"""
        raise NotImplementedError()

    def run(self):
        adaptor = ReplicationConsumerToProcessorAdaptor(self.get_processors(), self.get_filters())
        cn = self.get_connection()
        slot_name = self.get_slot_name()

        with cn.cursor() as cur:
            cur: ReplicationCursor
            try:
                cur.create_replication_slot(slot_name, output_plugin="wal2json")
                logger.info("Replication slot %s created", slot_name)
            except psycopg2.errors.DuplicateObject:
                logger.info("Replication slot %s already exists", slot_name)

            cur.start_replication(slot_name=slot_name, decode=True, options={"format-version": "2"})
            cur.consume_stream(adaptor)
