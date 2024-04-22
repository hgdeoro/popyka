import logging
import threading
import uuid
from unittest.mock import MagicMock

from psycopg2.extensions import connection as Connection

from popyka.api import Processor, Wal2JsonV2Change
from popyka.config import PopykaConfig
from popyka.errors import StopServer
from popyka.server import Server
from tests.utils.db_activity_simulator import DbActivitySimulator

logger = logging.getLogger(__name__)


class ProcessorImpl(Processor):
    def __init__(self, max_changes: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.changes: list[Wal2JsonV2Change] = []
        self.max_changes = max_changes

    def setup(self):
        pass

    def process_change(self, change: Wal2JsonV2Change):
        self.changes.append(change)
        if len(self.changes) >= self.max_changes:
            raise StopServer()


class ServerTestImpl(Server, threading.Thread):
    def __init__(self, config):
        super().__init__(config=config, daemon=True)


def test_server(conn: Connection, conn2: Connection, drop_slot, table_name: str, popyka_env_vars):
    processors = [ProcessorImpl(max_changes=3, config_generic={})]

    server = ServerTestImpl(config=PopykaConfig.get_config(environment=popyka_env_vars))
    server.get_filters = MagicMock()
    server.get_filters.return_value = []
    server.get_processors = MagicMock()
    server.get_processors.return_value = processors
    server.create_replication_slot()  # It's important to start replication before activity is simulated
    server.start()

    uuids = [str(uuid.uuid4()) for _ in range(4)]
    statements = [("INSERT INTO {table_name} (NAME) VALUES (%s)", [_]) for _ in uuids]
    db_activity_simulator = DbActivitySimulator(conn, table_name, statements)
    db_activity_simulator.start()
    db_activity_simulator.join_or_fail(timeout=2)

    server.join(timeout=3)
    assert not server.is_alive()
