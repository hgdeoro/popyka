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


class Main:
    def get_filters(self) -> list[Filter]:
        # TODO: take class name of filters from env
        return [IgnoreTxFilter()]

    def get_processors(self) -> list[Processor]:
        # TODO: take class name of processors from env
        return [LogChangeProcessor(), ProduceToKafkaProcessor()]

    def get_slot_name(self) -> str:
        # TODO: let user overwrite via env variables
        _, _, db = self.get_dsn()
        return f"popyka_{db}"

    def get_connection(self) -> Connection:
        # https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-CONNSTRING
        dsn, parsed, db = self.get_dsn()
        logger.info("DSN host=%s port=%s user=%s db=%s", parsed.hostname, parsed.port, parsed.username, db)
        return psycopg2.connect(dsn, connection_factory=psycopg2.extras.LogicalReplicationConnection)

    def get_dsn(self) -> tuple[str, object, str]:
        """Return DSN, also parsed URI and database name"""
        parsed = urlparse(POPYKA_DB_DSN)
        assert parsed.path.startswith("/")
        return POPYKA_DB_DSN, parsed, parsed.path[1:]

    def main(self):
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


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    Main().main()
