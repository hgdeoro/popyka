import logging
import threading
import typing

from psycopg2.extensions import connection as Connection
from psycopg2.extras import ReplicationCursor

logger = logging.getLogger(__name__)


class DbActivitySimulator(threading.Thread):
    def __init__(
        self,
        cn: Connection,
        table_name: str,
        statements: typing.Iterable[tuple[str, list]],
    ):
        super().__init__(daemon=True)
        self._cn = cn
        self._table_name: str = table_name
        self._repl_starting_soon_event: threading.Event = threading.Event()
        self._done: threading.Event = threading.Event()
        self._statements: typing.Iterable[tuple[str, list]] = statements

    @property
    def table_name(self) -> str:
        return self._table_name

    @property
    def repl_starting_soon_event(self) -> threading.Event:
        return self._repl_starting_soon_event

    def done(self) -> threading.Event:
        return self._done

    def run(self) -> None:
        with self._cn.cursor() as cur:
            cur: ReplicationCursor
            cur.execute(f"DROP TABLE IF EXISTS {self._table_name}")
            self._cn.commit()
            cur.execute(f"CREATE TABLE {self._table_name} (NAME VARCHAR)")
            self._cn.commit()

            logger.info("Table %s created, waiting for event to start inserting data...", self._table_name)
            assert self._repl_starting_soon_event.wait(timeout=3) is True

            for stmt in self._statements:
                logger.info("%s | %s", self._table_name, str(stmt))
                cur.execute(stmt[0].format(table_name=self._table_name), stmt[1])
                self._cn.commit()

        self._done.set()


def test_db_activity_simulator(conn: Connection, conn2: Connection, table_name: str):
    statements = (
        ("INSERT INTO {table_name} (NAME) VALUES (gen_random_uuid())", []),
        ("INSERT INTO {table_name} (NAME) VALUES (gen_random_uuid())", []),
        ("INSERT INTO {table_name} (NAME) VALUES (gen_random_uuid())", []),
    )
    db_activity_simulator = DbActivitySimulator(conn, table_name, statements)
    db_activity_simulator.start()
    db_activity_simulator.repl_starting_soon_event.set()
    db_activity_simulator.join()

    assert db_activity_simulator.done().is_set()

    with conn2.cursor() as cur:
        cur.execute(f"SELECT count(*) FROM {table_name}")
        assert cur.fetchall() == [(3,)]
