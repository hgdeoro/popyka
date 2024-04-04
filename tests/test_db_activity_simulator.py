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
        # self._statements_done: list[tuple[str, list]] = []

    @property
    def table_name(self) -> str:
        return self._table_name

    def start_activity(self):
        return self._repl_starting_soon_event.set()

    @property
    def is_done(self) -> bool:
        return self._done.is_set()

    def create_table(self, cur):
        cur.execute(f"DROP TABLE IF EXISTS {self._table_name}")
        self._cn.commit()

        cur.execute(f"CREATE TABLE {self._table_name} (NAME VARCHAR)")
        self._cn.commit()

    def run(self) -> None:
        with self._cn.cursor() as cur:
            cur: ReplicationCursor
            self.create_table(cur)

            logger.info("Table %s created, waiting for event to start inserting data...", self._table_name)
            assert self._repl_starting_soon_event.wait(timeout=3) is True

            for stmt in self._statements:
                logger.info("%s | %s", self._table_name, str(stmt))
                cur.execute(stmt[0].format(table_name=self._table_name), stmt[1])
                # self._statements_done.append((stmt[0].format(table_name=self._table_name), stmt[1]))
                self._cn.commit()

        self._done.set()

    # def sql_select_all(self, cn: Connection):
    #     with cn.cursor() as cur:
    #         cur.execute(f"SELECT * FROM {self._table_name}")
    #         return cur.fetchall()

    def sql_count_all(self, cn: Connection, table_name_suffix=""):
        with cn.cursor() as cur:
            cur.execute(f"SELECT count(*) FROM {self._table_name}{table_name_suffix}")
            return cur.fetchall()[0][0]


def test_db_activity_simulator(conn: Connection, conn2: Connection, table_name: str):
    statements = (
        ("INSERT INTO {table_name} (NAME) VALUES (gen_random_uuid())", []),
        ("INSERT INTO {table_name} (NAME) VALUES (gen_random_uuid())", []),
        ("INSERT INTO {table_name} (NAME) VALUES (gen_random_uuid())", []),
    )
    db_activity_simulator = DbActivitySimulator(conn, table_name, statements)
    db_activity_simulator.start()
    db_activity_simulator.start_activity()
    db_activity_simulator.join()

    assert db_activity_simulator.is_done
    assert db_activity_simulator.sql_count_all(conn2) == 3


def test_db_activity_simulator_custom_tables(conn: Connection, conn2: Connection, table_name: str):
    class CustomDbActivitySimulator(DbActivitySimulator):
        def create_table(self, cur):
            cur.execute(f"DROP TABLE IF EXISTS {self._table_name}_a")
            cur.execute(f"DROP TABLE IF EXISTS {self._table_name}_b")
            self._cn.commit()

            cur.execute(f"CREATE TABLE {self._table_name}_a (NAME_A VARCHAR)")
            cur.execute(f"CREATE TABLE {self._table_name}_b (NAME_B VARCHAR)")
            self._cn.commit()

    statements = (
        ("INSERT INTO {table_name}_a (NAME_a) VALUES (gen_random_uuid())", []),
        ("INSERT INTO {table_name}_b (NAME_b) VALUES (gen_random_uuid())", []),
    )
    db_activity_simulator = CustomDbActivitySimulator(conn, table_name, statements)
    db_activity_simulator.start()
    db_activity_simulator.start_activity()
    db_activity_simulator.join()

    assert db_activity_simulator.is_done
    assert db_activity_simulator.sql_count_all(conn2, table_name_suffix="_a") == 1
    assert db_activity_simulator.sql_count_all(conn2, table_name_suffix="_b") == 1
