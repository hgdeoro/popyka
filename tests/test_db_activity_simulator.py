import logging

from psycopg2.extensions import connection as Connection

from tests.utils import DbActivitySimulator

logger = logging.getLogger(__name__)


def test_db_activity_simulator(conn: Connection, conn2: Connection, table_name: str):
    statements = (
        ("INSERT INTO {table_name} (NAME) VALUES (md5(random()::text))", []),
        ("INSERT INTO {table_name} (NAME) VALUES (md5(random()::text))", []),
        ("INSERT INTO {table_name} (NAME) VALUES (md5(random()::text))", []),
    )
    db_activity_simulator = DbActivitySimulator(conn, table_name, statements)
    db_activity_simulator.start()
    db_activity_simulator.join()

    assert db_activity_simulator.sql_count_all(conn2) == 3


def test_db_activity_simulator_simplified_statements(conn: Connection, conn2: Connection, table_name: str):
    statements = (
        "INSERT INTO {table_name} (NAME) VALUES (md5(random()::text))",
        "INSERT INTO {table_name} (NAME) VALUES (md5(random()::text))",
        "INSERT INTO {table_name} (NAME) VALUES (md5(random()::text))",
    )
    db_activity_simulator = DbActivitySimulator(conn, table_name, statements)
    db_activity_simulator.start()
    db_activity_simulator.join()

    assert db_activity_simulator.sql_count_all(conn2) == 3


def test_db_activity_simulator_magic_table_name(conn: Connection, conn2: Connection, table_name: str):
    statements = (
        "INSERT INTO __table_name__ (NAME) VALUES (md5(random()::text))",
        "INSERT INTO __table_name__ (NAME) VALUES (md5(random()::text))",
        "INSERT INTO __table_name__ (NAME) VALUES (md5(random()::text))",
    )
    db_activity_simulator = DbActivitySimulator(conn, table_name, statements)
    db_activity_simulator.start()
    db_activity_simulator.join()

    assert db_activity_simulator.sql_count_all(conn2) == 3


def test_db_activity_simulator_custom_tables(conn: Connection, conn2: Connection, table_name: str):
    class CustomDbActivitySimulator(DbActivitySimulator):
        def _create_table(self, cur):
            cur.execute(f"DROP TABLE IF EXISTS {self._table_name}_a")
            cur.execute(f"DROP TABLE IF EXISTS {self._table_name}_b")
            self._cn.commit()

            cur.execute(f"CREATE TABLE {self._table_name}_a (NAME_A VARCHAR)")
            cur.execute(f"CREATE TABLE {self._table_name}_b (NAME_B VARCHAR)")
            self._cn.commit()

    statements = (
        ("INSERT INTO {table_name}_a (NAME_a) VALUES (md5(random()::text))", []),
        ("INSERT INTO {table_name}_b (NAME_b) VALUES (md5(random()::text))", []),
    )
    db_activity_simulator = CustomDbActivitySimulator(conn, table_name, statements)
    db_activity_simulator.start()
    db_activity_simulator.join()

    assert db_activity_simulator.sql_count_all(conn2, table_name_suffix="_a") == 1
    assert db_activity_simulator.sql_count_all(conn2, table_name_suffix="_b") == 1


def test_magic_end_of_test_statement(conn: Connection, conn2: Connection, table_name: str):
    statements = (DbActivitySimulator.MAGIC_END_OF_TEST_STATEMENT,)
    db_activity_simulator = DbActivitySimulator(conn, table_name, statements)
    db_activity_simulator.start()
    db_activity_simulator.join()
    assert db_activity_simulator.sql_count_all(conn2) == 0  # 0 insert, MAGIC_END_OF_TEST_STATEMENT does nothing
