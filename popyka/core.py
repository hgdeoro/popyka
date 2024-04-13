import abc
import json
import logging
from typing import TYPE_CHECKING

import psycopg2.extras
from psycopg2.extensions import connection as Connection
from psycopg2.extras import ReplicationCursor

from popyka.errors import StopServer
from popyka.logging import LazyJson

if TYPE_CHECKING:
    from popyka.config import PopykaConfig


_logger = logging.getLogger(__name__)


class Wal2JsonV2Change(dict):
    """Represent a change generated by wal2json using format version 2"""

    # TODO: use class or dataclass, to make API more clear and easier for implementations of `Processors`


class Processor(abc.ABC):
    """Base class for processors of changes"""

    logger = logging.getLogger(f"{__name__}.Filter")

    # TODO: Implement error handling, retries, etc.

    def __init__(self, config_generic: dict):
        self.logger.debug("Instantiating processor with config: %s", LazyJson(config_generic))
        self._config_generic = config_generic

    # TODO: should we have a post_init()/setup()/init()/etc?

    @abc.abstractmethod
    def process_change(self, change: Wal2JsonV2Change):
        """Receives a change and process it."""
        raise NotImplementedError()


class Filter(abc.ABC):
    """Base class for change filters"""

    logger = logging.getLogger(f"{__name__}.Filter")

    def __init__(self, config_generic: dict):
        self.logger.debug("Instantiating filter with config: %s", LazyJson(config_generic))
        self._config_generic = config_generic

    # TODO: should we have a post_init()/setup()/init()/etc?

    @abc.abstractmethod
    def ignore_change(self, change: Wal2JsonV2Change) -> bool:
        """
        Receives a change and returns True if should be ignored.
        Ignored changes won't reach the processors.
        """
        # FIXME: is `ignore_change()` a good API? Wouldn't be better `should_process()` or something like that?
        raise NotImplementedError()


class ReplicationConsumerToProcessorAdaptor:
    """Psycopg2 replication consumer that runs configured PoPyKa Processors on the received changes"""

    logger = logging.getLogger(f"{__name__}.ReplicationConsumerToProcessorAdaptor")

    def __init__(self, processors: list[Processor], filters: list[Filter]):
        self._processors = processors
        self._filters = filters

    def __call__(self, msg: psycopg2.extras.ReplicationMessage):
        self.logger.debug("ReplicationConsumerToProcessorAdaptor: received payload: %s", msg)
        change = Wal2JsonV2Change(json.loads(msg.payload))

        process_change = True
        for a_filter in self._filters:
            if a_filter.ignore_change(change):
                process_change = False
                self.logger.debug("Ignoring change for change: %s", LazyJson(change))
                break

        if process_change:
            for processor in self._processors:
                self.logger.debug("Starting processing with processor: %s", processor)
                processor.process_change(change)

        # Flush after every message is successfully processed
        self.logger.debug("send_feedback() flush_lsn=%s", msg.data_start)
        msg.cursor.send_feedback(flush_lsn=msg.data_start)


class Server(abc.ABC):
    logger = logging.getLogger(f"{__name__}.Server")

    def __init__(self, config: "PopykaConfig", *args, **kwargs):
        self._config = config
        self.logger.debug("Instantiating Server with config: %s", LazyJson(config))
        super().__init__(*args, **kwargs)

    def get_filters(self) -> list[Filter]:
        return [_.instantiate() for _ in self._config.filters]

    def get_processors(self) -> list[Processor]:
        return [_.instantiate() for _ in self._config.processors]

    def get_dsn(self) -> str:
        return self._config.database.connect_url

    def get_connection(self) -> Connection:
        """Returns a psycopg2 connection"""
        # https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-CONNSTRING
        conn = psycopg2.connect(self.get_dsn(), connection_factory=psycopg2.extras.LogicalReplicationConnection)
        self.logger.debug("Created Connection: %s", conn)
        return conn

    def get_slot_name(self) -> str:
        return self._config.database.slot_name

    def get_adaptor(self) -> ReplicationConsumerToProcessorAdaptor:
        return ReplicationConsumerToProcessorAdaptor(self.get_processors(), self.get_filters())

    def start_replication(self):
        # FIXME: old and misleading! Rename to `create_replication_slot()` and update docstring.
        """
        Start the replication. Can be called from main thread or a different one.

        This step needs to be done before starting to consume.
        It's a different method because makes testing much easier with no major disadvantage.
        """
        cn = self.get_connection()
        slot_name = self.get_slot_name()

        self.logger.info("create_replication_slot(): conn=%s slot_name=%s", cn, slot_name)

        with cn.cursor() as cur:
            cur: ReplicationCursor
            try:
                cur.create_replication_slot(slot_name, output_plugin="wal2json")
                self.logger.info("Replication slot %s created", slot_name)
            except psycopg2.errors.DuplicateObject:
                self.logger.info("Replication slot %s already exists", slot_name)

    def run(self):
        adaptor = self.get_adaptor()
        cn = self.get_connection()
        slot_name = self.get_slot_name()

        with cn.cursor() as cur:
            self.logger.info("run(): will start_replication() slot=%s", slot_name)
            cur: ReplicationCursor
            cur.start_replication(slot_name=slot_name, decode=True, options={"format-version": "2"})

            try:
                self.logger.info("run(): will consume_stream() adaptor=%s", adaptor)
                cur.consume_stream(adaptor)
            except StopServer:
                self.logger.info("StopServer received. Slot is still active, this can cause problems in your DB.")
                return
            except KeyboardInterrupt:
                self.logger.info("StopServer received. Slot is still active, this can cause problems in your DB.")
                return

        # FIXME: do `drop_replication_slot()`, by default or when requested or depending on configuration
        # FIXME: if `drop_replication_slot()` is not done, log the dangers
