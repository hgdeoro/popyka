import abc
import logging

import psycopg2.extras
from psycopg2.extensions import connection as Connection
from psycopg2.extras import ReplicationCursor

from popyka.adaptors import ReplicationConsumerToProcessorAdaptor
from popyka.api import Filter, Processor
from popyka.config import PopykaConfig
from popyka.errors import StopServer
from popyka.logging import LazyToStr


class Server(abc.ABC):
    logger = logging.getLogger(f"{__name__}.Server")

    def __init__(self, config: "PopykaConfig", *args, **kwargs):
        self._config = config
        self.logger.debug("Instantiating Server with config: %s", LazyToStr(config))
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

    def create_replication_slot(self):
        """
        Creates the replication slot. Can be called from main thread or a different one.

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

        # FIXME: DOC: document the risks of not consuming the stream (full server disk, etc.)
