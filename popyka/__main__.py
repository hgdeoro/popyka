import logging
from urllib.parse import urlparse

import psycopg2.extras
from psycopg2.extensions import connection as Connection

from popyka.core import POPYKA_DB_DSN, Filter, Processor, Server
from popyka.filters import IgnoreTxFilter
from popyka.processors import LogChangeProcessor, ProduceToKafkaProcessor

logger = logging.getLogger(__name__)


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
