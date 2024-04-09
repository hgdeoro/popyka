import logging
import threading
import uuid
from unittest.mock import MagicMock

from psycopg2.extensions import connection as Connection

from popyka.core import Filter, Processor, Server, StopServer, Wal2JsonV2Change
from tests.utils import DbActivitySimulator

logger = logging.getLogger(__name__)


class ProcessorImpl(Processor):
    def __init__(self, max_changes: int):
        self.changes: list[Wal2JsonV2Change] = []
        self.max_changes = max_changes

    def process_change(self, change: Wal2JsonV2Change):
        self.changes.append(change)
        if len(self.changes) >= self.max_changes:
            raise StopServer()


class ServerTestImpl(Server, threading.Thread):
    def __init__(
        self,
        dsn: str,
        filters: list[Filter],
        processors: list[Processor],
    ):
        super().__init__(daemon=True)
        self._filters = filters
        self._dsn = dsn
        self._processors = processors

    def get_filters(self) -> list[Filter]:
        return self._filters

    def get_processors(self) -> list[Processor]:
        return self._processors

    def get_dsn(self) -> str:
        return self._dsn

    def get_slot_name(self) -> str:
        raise NotImplementedError()


def test_server(dsn: str, conn: Connection, conn2: Connection, drop_slot, table_name: str):
    filters = []
    processors = [ProcessorImpl(max_changes=3)]
    server = ServerTestImpl(dsn, filters, processors)
    server.get_slot_name = MagicMock()
    server.get_slot_name.return_value = f"pytest_{table_name}".lower()
    server.start_replication()  # It's important to start replication before activity is simulated
    server.start()

    uuids = [str(uuid.uuid4()) for _ in range(4)]
    statements = [("INSERT INTO {table_name} (NAME) VALUES (%s)", [_]) for _ in uuids]
    db_activity_simulator = DbActivitySimulator(conn, table_name, statements)
    db_activity_simulator.start()
    db_activity_simulator.join_or_fail(timeout=2)

    server.join(timeout=3)
    assert not server.is_alive()
