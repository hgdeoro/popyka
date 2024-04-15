"""
This module asserts that the payloads generated by wal2json are consistent.

This is run by tox in all combinations of supported python and postgresql versions.
"""

import logging
from pprint import pprint

from psycopg2.extensions import connection as Connection

from tests.conftest import contract_test
from tests.utils.db_activity_simulator import DbActivitySimulator, DbStreamConsumer

logger = logging.getLogger(__name__)


@contract_test
def test_crud_on_table_without_pk(conn: Connection, conn2: Connection, drop_slot, table_name: str):
    statements = [
        "INSERT INTO __table_name__ (NAME) VALUES ('this-is-the-value-1')",
        "INSERT INTO __table_name__ (NAME) VALUES ('this-is-the-value-2')",
        "INSERT INTO __table_name__ (NAME) VALUES ('this-is-the-value-3')",
        "INSERT INTO __table_name__ (NAME) VALUES ('this-is-the-value-4')",
        "UPDATE __table_name__ SET NAME = 'this-is-the-value-4-new' WHERE NAME = 'this-is-the-value-4'",
        "DELETE FROM __table_name__ WHERE NAME = 'this-is-the-value-4-new'",
    ]

    create_table = f"""
    CREATE TABLE {table_name} (
        name varchar not null
    )
    """

    db_activity_simulator = DbActivitySimulator(conn, table_name, statements, create_table_ddl=create_table)
    db_stream_consumer = DbStreamConsumer(conn2)

    db_stream_consumer.start_replication().start()
    db_activity_simulator.start()
    db_activity_simulator.join_or_fail(timeout=3)

    db_stream_consumer.join_or_fail(timeout=3)

    pprint(db_stream_consumer.payloads_parsed, indent=4, sort_dicts=True, compact=False)

    expected = [
        {"action": "B"},
        {"action": "C"},
        {"action": "B"},
        {
            "action": "I",
            "columns": [{"name": "name", "type": "character varying", "value": "this-is-the-value-1"}],
            "schema": "public",
            "table": table_name.lower(),
        },
        {"action": "C"},
        {"action": "B"},
        {
            "action": "I",
            "columns": [{"name": "name", "type": "character varying", "value": "this-is-the-value-2"}],
            "schema": "public",
            "table": table_name.lower(),
        },
        {"action": "C"},
        {"action": "B"},
        {
            "action": "I",
            "columns": [{"name": "name", "type": "character varying", "value": "this-is-the-value-3"}],
            "schema": "public",
            "table": table_name.lower(),
        },
        {"action": "C"},
        {"action": "B"},
        {
            "action": "I",
            "columns": [{"name": "name", "type": "character varying", "value": "this-is-the-value-4"}],
            "schema": "public",
            "table": table_name.lower(),
        },
        {"action": "C"},
        {"action": "B"},
        {"action": "C"},
        {"action": "B"},
        {"action": "C"},
    ]

    assert db_stream_consumer.payloads_parsed == expected


@contract_test
def test_crud_on_table_with_pk(conn: Connection, conn2: Connection, drop_slot, table_name: str):
    statements = [
        "INSERT INTO __table_name__ (NAME) VALUES ('this-is-the-value-1')",
        "INSERT INTO __table_name__ (NAME) VALUES ('this-is-the-value-2')",
        "INSERT INTO __table_name__ (PK, NAME) VALUES (98, 'this-is-the-value-3')",
        "INSERT INTO __table_name__ (PK, NAME) VALUES (99, 'this-is-the-value-4')",
        "UPDATE __table_name__ SET NAME = 'this-is-the-value-3-new' WHERE PK = 98",
        "UPDATE __table_name__ SET NAME = 'this-is-the-value-4-new' WHERE NAME = 'this-is-the-value-4'",
        "DELETE FROM __table_name__ WHERE PK = 98",
        "DELETE FROM __table_name__ WHERE NAME = 'this-is-the-value-4-new'",
    ]

    create_table = f"""
    CREATE TABLE {table_name} (
        pk serial not null primary key,
        name varchar not null
    )
    """

    db_activity_simulator = DbActivitySimulator(conn, table_name, statements, create_table_ddl=create_table)
    db_stream_consumer = DbStreamConsumer(conn2)

    db_stream_consumer.start_replication().start()
    db_activity_simulator.start()
    db_activity_simulator.join_or_fail(timeout=3)

    db_stream_consumer.join_or_fail(timeout=3)

    pprint(db_stream_consumer.payloads_parsed, indent=4, sort_dicts=True, compact=False)

    expected = [
        {"action": "B"},
        {"action": "C"},
        {"action": "B"},
        {
            "action": "I",
            "columns": [
                {"name": "pk", "type": "integer", "value": 1},
                {"name": "name", "type": "character varying", "value": "this-is-the-value-1"},
            ],
            "schema": "public",
            "table": table_name.lower(),
        },
        {"action": "C"},
        {"action": "B"},
        {
            "action": "I",
            "columns": [
                {"name": "pk", "type": "integer", "value": 2},
                {"name": "name", "type": "character varying", "value": "this-is-the-value-2"},
            ],
            "schema": "public",
            "table": table_name.lower(),
        },
        {"action": "C"},
        {"action": "B"},
        {
            "action": "I",
            "columns": [
                {"name": "pk", "type": "integer", "value": 98},
                {"name": "name", "type": "character varying", "value": "this-is-the-value-3"},
            ],
            "schema": "public",
            "table": table_name.lower(),
        },
        {"action": "C"},
        {"action": "B"},
        {
            "action": "I",
            "columns": [
                {"name": "pk", "type": "integer", "value": 99},
                {"name": "name", "type": "character varying", "value": "this-is-the-value-4"},
            ],
            "schema": "public",
            "table": table_name.lower(),
        },
        {"action": "C"},
        {"action": "B"},
        {
            "action": "U",
            "columns": [
                {"name": "pk", "type": "integer", "value": 98},
                {"name": "name", "type": "character varying", "value": "this-is-the-value-3-new"},
            ],
            "identity": [{"name": "pk", "type": "integer", "value": 98}],
            "schema": "public",
            "table": table_name.lower(),
        },
        {"action": "C"},
        {"action": "B"},
        {
            "action": "U",
            "columns": [
                {"name": "pk", "type": "integer", "value": 99},
                {"name": "name", "type": "character varying", "value": "this-is-the-value-4-new"},
            ],
            "identity": [{"name": "pk", "type": "integer", "value": 99}],
            "schema": "public",
            "table": table_name.lower(),
        },
        {"action": "C"},
        {"action": "B"},
        {
            "action": "D",
            "identity": [{"name": "pk", "type": "integer", "value": 98}],
            "schema": "public",
            "table": table_name.lower(),
        },
        {"action": "C"},
        {"action": "B"},
        {
            "action": "D",
            "identity": [{"name": "pk", "type": "integer", "value": 99}],
            "schema": "public",
            "table": table_name.lower(),
        },
        {"action": "C"},
    ]

    assert db_stream_consumer.payloads_parsed == expected


@contract_test
def test_crud_on_table_with_composite_key(conn: Connection, conn2: Connection, drop_slot, table_name: str):
    statements = [
        "INSERT INTO __table_name__ (NAME) VALUES ('this-is-the-value-1')",
        "INSERT INTO __table_name__ (NAME) VALUES ('this-is-the-value-2')",
        "INSERT INTO __table_name__ (ID_1, ID_2, NAME) VALUES (98, 98, 'this-is-the-value-3')",
        "INSERT INTO __table_name__ (ID_1, ID_2, NAME) VALUES (99, 99, 'this-is-the-value-4')",
        "UPDATE __table_name__ SET NAME = 'this-is-the-value-3-new' WHERE ID_1 = 98 AND ID_2 = 98",
        "UPDATE __table_name__ SET NAME = 'this-is-the-value-4-new' WHERE NAME = 'this-is-the-value-4'",
        "DELETE FROM __table_name__ WHERE ID_1 = 98 AND ID_2 = 98",
        "DELETE FROM __table_name__ WHERE NAME = 'this-is-the-value-4-new'",
    ]

    create_table = f"""
    CREATE TABLE {table_name} (
        id_1 serial not null,
        id_2 serial not null,
        name varchar not null,
        primary key (id_1, id_2)
    )
    """

    db_activity_simulator = DbActivitySimulator(conn, table_name, statements, create_table_ddl=create_table)
    db_stream_consumer = DbStreamConsumer(conn2)

    db_stream_consumer.start_replication().start()
    db_activity_simulator.start()
    db_activity_simulator.join_or_fail(timeout=3)

    db_stream_consumer.join_or_fail(timeout=3)

    pprint(db_stream_consumer.payloads_parsed, indent=4, sort_dicts=True, compact=False)

    expected = [
        {"action": "B"},
        {"action": "C"},
        {"action": "B"},
        {
            "action": "I",
            "columns": [
                {"name": "id_1", "type": "integer", "value": 1},
                {"name": "id_2", "type": "integer", "value": 1},
                {"name": "name", "type": "character varying", "value": "this-is-the-value-1"},
            ],
            "schema": "public",
            "table": table_name.lower(),
        },
        {"action": "C"},
        {"action": "B"},
        {
            "action": "I",
            "columns": [
                {"name": "id_1", "type": "integer", "value": 2},
                {"name": "id_2", "type": "integer", "value": 2},
                {"name": "name", "type": "character varying", "value": "this-is-the-value-2"},
            ],
            "schema": "public",
            "table": table_name.lower(),
        },
        {"action": "C"},
        {"action": "B"},
        {
            "action": "I",
            "columns": [
                {"name": "id_1", "type": "integer", "value": 98},
                {"name": "id_2", "type": "integer", "value": 98},
                {"name": "name", "type": "character varying", "value": "this-is-the-value-3"},
            ],
            "schema": "public",
            "table": table_name.lower(),
        },
        {"action": "C"},
        {"action": "B"},
        {
            "action": "I",
            "columns": [
                {"name": "id_1", "type": "integer", "value": 99},
                {"name": "id_2", "type": "integer", "value": 99},
                {"name": "name", "type": "character varying", "value": "this-is-the-value-4"},
            ],
            "schema": "public",
            "table": table_name.lower(),
        },
        {"action": "C"},
        {"action": "B"},
        {
            "action": "U",
            "columns": [
                {"name": "id_1", "type": "integer", "value": 98},
                {"name": "id_2", "type": "integer", "value": 98},
                {"name": "name", "type": "character varying", "value": "this-is-the-value-3-new"},
            ],
            "identity": [
                {"name": "id_1", "type": "integer", "value": 98},
                {"name": "id_2", "type": "integer", "value": 98},
            ],
            "schema": "public",
            "table": table_name.lower(),
        },
        {"action": "C"},
        {"action": "B"},
        {
            "action": "U",
            "columns": [
                {"name": "id_1", "type": "integer", "value": 99},
                {"name": "id_2", "type": "integer", "value": 99},
                {"name": "name", "type": "character varying", "value": "this-is-the-value-4-new"},
            ],
            "identity": [
                {"name": "id_1", "type": "integer", "value": 99},
                {"name": "id_2", "type": "integer", "value": 99},
            ],
            "schema": "public",
            "table": table_name.lower(),
        },
        {"action": "C"},
        {"action": "B"},
        {
            "action": "D",
            "identity": [
                {"name": "id_1", "type": "integer", "value": 98},
                {"name": "id_2", "type": "integer", "value": 98},
            ],
            "schema": "public",
            "table": table_name.lower(),
        },
        {"action": "C"},
        {"action": "B"},
        {
            "action": "D",
            "identity": [
                {"name": "id_1", "type": "integer", "value": 99},
                {"name": "id_2", "type": "integer", "value": 99},
            ],
            "schema": "public",
            "table": table_name.lower(),
        },
        {"action": "C"},
    ]

    assert db_stream_consumer.payloads_parsed == expected


@contract_test
def test_truncate_table(conn: Connection, conn2: Connection, drop_slot, table_name: str):
    statements = [
        "INSERT INTO __table_name__ (NAME) VALUES ('this-is-the-value-1')",
        "INSERT INTO __table_name__ (NAME) VALUES ('this-is-the-value-2')",
        "TRUNCATE TABLE __table_name__",
        "INSERT INTO __table_name__ (NAME) VALUES ('after-truncate')",
        "DELETE FROM __table_name__",
    ]

    create_table = f"""
    CREATE TABLE {table_name} (
        pk serial not null primary key,
        name varchar not null
    )
    """

    db_activity_simulator = DbActivitySimulator(conn, table_name, statements, create_table_ddl=create_table)
    db_stream_consumer = DbStreamConsumer(conn2)

    db_stream_consumer.start_replication().start()
    db_activity_simulator.start()
    db_activity_simulator.join_or_fail(timeout=3)

    db_stream_consumer.join_or_fail(timeout=3)

    pprint(db_stream_consumer.payloads_parsed, indent=4, sort_dicts=True, compact=False)

    expected = [
        {"action": "B"},
        {"action": "C"},
        {"action": "B"},
        {
            "action": "I",
            "columns": [
                {"name": "pk", "type": "integer", "value": 1},
                {"name": "name", "type": "character varying", "value": "this-is-the-value-1"},
            ],
            "schema": "public",
            "table": table_name.lower(),
        },
        {"action": "C"},
        {"action": "B"},
        {
            "action": "I",
            "columns": [
                {"name": "pk", "type": "integer", "value": 2},
                {"name": "name", "type": "character varying", "value": "this-is-the-value-2"},
            ],
            "schema": "public",
            "table": table_name.lower(),
        },
        {"action": "C"},
        {"action": "B"},
        {"action": "T", "schema": "public", "table": table_name.lower()},
        {"action": "C"},
        {"action": "B"},
        {
            "action": "I",
            "columns": [
                {"name": "pk", "type": "integer", "value": 3},
                {"name": "name", "type": "character varying", "value": "after-truncate"},
            ],
            "schema": "public",
            "table": table_name.lower(),
        },
        {"action": "C"},
        {"action": "B"},
        {
            "action": "D",
            "identity": [{"name": "pk", "type": "integer", "value": 3}],
            "schema": "public",
            "table": table_name.lower(),
        },
        {"action": "C"},
    ]

    assert db_stream_consumer.payloads_parsed == expected


@contract_test
def test_manual_transaction_handling(conn: Connection, conn2: Connection, drop_slot, table_name: str):
    """
    This not only tests wal2json, but also tx handling done by DbActivitySimulator.
    """
    statements = [
        "BEGIN",
        "INSERT INTO __table_name__ (NAME) VALUES ('this-is-the-value-1')",
        "INSERT INTO __table_name__ (NAME) VALUES ('this-is-the-value-2')",
        "COMMIT",
        "BEGIN",
        "INSERT INTO __table_name__ (NAME) VALUES ('this-is-the-value-3')",
        "INSERT INTO __table_name__ (NAME) VALUES ('this-is-the-value-4')",
        "ROLLBACK",
        "INSERT INTO __table_name__ (NAME) VALUES ('this-is-the-value-5')",
    ]

    create_table = f"""
    CREATE TABLE {table_name} (
        pk serial not null primary key,
        name varchar not null
    )
    """

    db_activity_simulator = DbActivitySimulator(conn, table_name, statements, create_table_ddl=create_table)
    db_stream_consumer = DbStreamConsumer(conn2)

    db_stream_consumer.start_replication().start()
    db_activity_simulator.start()
    db_activity_simulator.join_or_fail(timeout=3)

    db_stream_consumer.join_or_fail(timeout=3)

    pprint(db_stream_consumer.payloads_parsed, indent=4, sort_dicts=True, compact=False)

    expected = [
        {"action": "B"},
        {"action": "C"},
        {"action": "B"},
        {
            "action": "I",
            "columns": [
                {"name": "pk", "type": "integer", "value": 1},
                {"name": "name", "type": "character varying", "value": "this-is-the-value-1"},
            ],
            "schema": "public",
            "table": table_name.lower(),
        },
        {
            "action": "I",
            "columns": [
                {"name": "pk", "type": "integer", "value": 2},
                {"name": "name", "type": "character varying", "value": "this-is-the-value-2"},
            ],
            "schema": "public",
            "table": table_name.lower(),
        },
        {"action": "C"},
        {"action": "B"},
        {
            "action": "I",
            "columns": [
                {"name": "pk", "type": "integer", "value": 5},
                {"name": "name", "type": "character varying", "value": "this-is-the-value-5"},
            ],
            "schema": "public",
            "table": table_name.lower(),
        },
        {"action": "C"},
    ]

    assert db_stream_consumer.payloads_parsed == expected


@contract_test
def test_no_db_activity(conn: Connection, conn2: Connection, drop_slot, table_name: str):
    statements = ["SELECT 1"]

    db_activity_simulator = DbActivitySimulator(conn, table_name, statements)
    db_stream_consumer = DbStreamConsumer(conn2)

    db_stream_consumer.start_replication().start()
    db_activity_simulator.start()
    db_activity_simulator.join_or_fail(timeout=3)

    db_stream_consumer.join_or_fail(timeout=3)

    pprint(db_stream_consumer.payloads_parsed, indent=4, sort_dicts=True, compact=False)

    expected = [{"action": "B"}, {"action": "C"}]

    assert db_stream_consumer.payloads_parsed == expected


@contract_test
class TestPgLogicalEmitMessage:
    """
    About `pg_logical_emit_message ( transactional boolean, prefix text, content text ) → pg_lsn`:

    Emits a logical decoding message.
    This can be used to pass generic messages to logical decoding plugins through WAL.

    * The `transactional` parameter specifies if the message should be part of the current transaction,
    or if it should be written immediately and decoded as soon as the logical decoder reads the record.

    * The `prefix` parameter is a textual prefix that can be used by logical decoding plugins to
    easily recognize messages that are interesting for them.

    * The `content` parameter is the content of the message, given either in text or binary form.
    """

    def test_emit_non_transactional(self, conn: Connection, conn2: Connection, drop_slot, table_name: str):
        statements = [
            "BEGIN",
            "SELECT * FROM pg_logical_emit_message(FALSE, 'this-is-prefix', 'content-1')",
            "ROLLBACK",
            "BEGIN",
            "SELECT * FROM pg_logical_emit_message(FALSE, 'this-is-prefix', 'content-2')",
            "COMMIT",
        ]

        db_activity_simulator = DbActivitySimulator(conn, table_name, statements)
        db_stream_consumer = DbStreamConsumer(conn2)

        db_stream_consumer.start_replication().start()
        db_activity_simulator.start()
        db_activity_simulator.join_or_fail(timeout=3)

        db_stream_consumer.join_or_fail(timeout=3)

        pprint(db_stream_consumer.payloads_parsed, indent=4, sort_dicts=True, compact=False)

        expected = [
            {"action": "B"},
            {"action": "C"},
            {"action": "M", "content": "content-1", "prefix": "this-is-prefix", "transactional": False},
            {"action": "M", "content": "content-2", "prefix": "this-is-prefix", "transactional": False},
        ]

        assert db_stream_consumer.payloads_parsed == expected

    def test_emit_transactional(self, conn: Connection, conn2: Connection, drop_slot, table_name: str):
        statements = [
            "BEGIN",
            "SELECT * FROM pg_logical_emit_message(TRUE, 'this-is-prefix', 'content-1')",
            "ROLLBACK",
            "BEGIN",
            "SELECT * FROM pg_logical_emit_message(TRUE, 'this-is-prefix', 'content-2')",
            "COMMIT",
        ]

        db_activity_simulator = DbActivitySimulator(conn, table_name, statements)
        db_stream_consumer = DbStreamConsumer(conn2)

        db_stream_consumer.start_replication().start()
        db_activity_simulator.start()
        db_activity_simulator.join_or_fail(timeout=3)

        db_stream_consumer.join_or_fail(timeout=3)

        pprint(db_stream_consumer.payloads_parsed, indent=4, sort_dicts=True, compact=False)

        expected = [
            {"action": "B"},
            {"action": "C"},
            {"action": "B"},
            {"action": "M", "content": "content-2", "prefix": "this-is-prefix", "transactional": True},
            {"action": "C"},
        ]

        assert db_stream_consumer.payloads_parsed == expected
