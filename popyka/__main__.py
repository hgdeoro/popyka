import abc
import logging
from urllib.parse import urlparse

import psycopg2.extras
from psycopg2.extensions import connection as Connection
from psycopg2.extras import ReplicationCursor

from popyka.core import (
    POPYKA_DB_DSN,
    Filter,
    Processor,
    ReplicationConsumerToProcessorAdaptor,
)
from popyka.filters import IgnoreTxFilter
from popyka.processors import LogChangeProcessor, ProduceToKafkaProcessor

logger = logging.getLogger(__name__)


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


class Main(Server):
    def get_filters(self) -> list[Filter]:
        return [IgnoreTxFilter()]

    def get_processors(self) -> list[Processor]:
        return [LogChangeProcessor(), ProduceToKafkaProcessor()]

    def get_slot_name(self) -> str:
        _, _, db = self.get_dsn()
        return f"popyka_{db}"

    def get_connection(self) -> Connection:
        # https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-CONNSTRING
        dsn, parsed, db = self.get_dsn()
        logger.info("DSN host=%s port=%s user=%s db=%s", parsed.hostname, parsed.port, parsed.username, db)
        return psycopg2.connect(dsn, connection_factory=psycopg2.extras.LogicalReplicationConnection)

    def get_dsn(self) -> tuple[str, object, str]:
        parsed = urlparse(POPYKA_DB_DSN)
        assert parsed.path.startswith("/")
        return POPYKA_DB_DSN, parsed, parsed.path[1:]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    Main().run()
