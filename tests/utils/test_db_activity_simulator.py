import logging
import random
import uuid

from psycopg2.extensions import connection as Connection

from tests.utils.db_activity_simulator import DbActivitySimulator

logger = logging.getLogger(__name__)


def test_db_activity_simulator_full_statements(conn: Connection, conn2: Connection, table_name: str):
    statements = (
        ("INSERT INTO {table_name} (NAME) VALUES (%s)", [str(uuid.uuid4().hex)]),
        ("INSERT INTO {table_name} (NAME) VALUES (%s)", [str(uuid.uuid4().hex)]),
        ("INSERT INTO {table_name} (NAME) VALUES (%s)", [str(uuid.uuid4().hex)]),
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
    suffix_a = f"_a_{random.randint(1, 99999999)}"
    suffix_b = f"_b_{random.randint(1, 99999999)}"

    ddl = f"""
    DROP TABLE IF EXISTS {table_name}{suffix_a};
    DROP TABLE IF EXISTS {table_name}{suffix_b};
    CREATE TABLE {table_name}{suffix_a} (NAME_A VARCHAR);
    CREATE TABLE {table_name}{suffix_b} (NAME_B VARCHAR);
    """
    statements = (
        f"INSERT INTO {{table_name}}{suffix_a} (NAME_a) VALUES (md5(random()::text))",
        f"INSERT INTO {{table_name}}{suffix_b} (NAME_b) VALUES (md5(random()::text))",
    )
    db_activity_simulator = DbActivitySimulator(conn, table_name, statements, create_table_ddl=ddl)
    db_activity_simulator.start()
    db_activity_simulator.join()

    assert db_activity_simulator.sql_count_all(conn2, table_name_suffix=suffix_a) == 1
    assert db_activity_simulator.sql_count_all(conn2, table_name_suffix=suffix_b) == 1


def test_magic_end_of_test_statement(conn: Connection, conn2: Connection, table_name: str):
    statements = (DbActivitySimulator.MAGIC_END_OF_TEST_STATEMENT,)
    db_activity_simulator = DbActivitySimulator(conn, table_name, statements)
    db_activity_simulator.start()
    db_activity_simulator.join()
    assert db_activity_simulator.sql_count_all(conn2) == 0  # 0 insert, MAGIC_END_OF_TEST_STATEMENT does nothing
