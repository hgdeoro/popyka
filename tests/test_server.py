import logging
import threading
import uuid

from psycopg2.extensions import connection as Connection

from popyka.core import Filter, Processor, Server, StopServer, Wal2JsonV2Change
from tests.test_db_activity_simulator import DbActivitySimulator

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


def test_server(dsn: str, conn: Connection, conn2: Connection, drop_slot, table_name: str):
    filters = []
    processors = [ProcessorImpl(max_changes=3)]
    # slot_name = "pytest_logical"
    server = ServerTestImpl(dsn, filters, processors)
    server.start()
    server.wait_for_replication_started()

    # <8 <8 <8 <8 <8 <8 <8 <8 <8 <8 <8 <8 <8 <8 <8 <8 <8 <8 <8 <8 <8 <8 <8 <8 <8 <8 <8 <8 <8 <8 <8 <8

    uuids = [str(uuid.uuid4()) for _ in range(4)]
    statements = [("INSERT INTO {table_name} (NAME) VALUES (%s)", [_]) for _ in uuids]

    db_activity_simulator = DbActivitySimulator(conn, table_name, statements)
    db_activity_simulator.start()
    db_activity_simulator.start_activity()
    db_activity_simulator.join()
    assert db_activity_simulator.is_done

    server.join(timeout=5)
    assert not server.is_alive()
