import dataclasses
import logging
import uuid

import pytest

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class AllScenarios:
    table_name_no_pk: str
    table_name_pk: str
    table_name_composite_key: str
    create_table_ddl: str
    statements: list
    expected: list


@pytest.fixture
def all_scenarios() -> AllScenarios:
    table_name_no_pk = f"test_table_no_pk_{uuid.uuid4().hex}".upper()
    table_name_pk = f"test_table_pk_{uuid.uuid4().hex}".upper()
    table_name_composite_key = f"test_table_composite_key_{uuid.uuid4().hex}".upper()

    statements = [
        # --- crud w/o pk
        f"INSERT INTO {table_name_no_pk} (NAME) VALUES ('this-is-the-value-1')",
        f"INSERT INTO {table_name_no_pk} (NAME) VALUES ('this-is-the-value-2')",
        f"INSERT INTO {table_name_no_pk} (NAME) VALUES ('this-is-the-value-3')",
        f"INSERT INTO {table_name_no_pk} (NAME) VALUES ('this-is-the-value-4')",
        f"UPDATE {table_name_no_pk} SET NAME = 'this-is-the-value-4-new' WHERE NAME = 'this-is-the-value-4'",
        f"DELETE FROM {table_name_no_pk} WHERE NAME = 'this-is-the-value-4-new'",
        # --- crud w/pk
        f"INSERT INTO {table_name_pk} (NAME) VALUES ('this-is-the-value-1')",
        f"INSERT INTO {table_name_pk} (NAME) VALUES ('this-is-the-value-2')",
        f"INSERT INTO {table_name_pk} (PK, NAME) VALUES (98, 'this-is-the-value-3')",
        f"INSERT INTO {table_name_pk} (PK, NAME) VALUES (99, 'this-is-the-value-4')",
        f"UPDATE {table_name_pk} SET NAME = 'this-is-the-value-3-new' WHERE PK = 98",
        f"UPDATE {table_name_pk} SET NAME = 'this-is-the-value-4-new' WHERE NAME = 'this-is-the-value-4'",
        f"DELETE FROM {table_name_pk} WHERE PK IN (2, 98)",
        # --- truncate
        f"TRUNCATE TABLE {table_name_no_pk}",
        f"TRUNCATE TABLE {table_name_pk}",
        # --- composite pk
        f"INSERT INTO {table_name_composite_key} (NAME) VALUES ('this-is-the-value-1')",
        f"INSERT INTO {table_name_composite_key} (NAME) VALUES ('this-is-the-value-2')",
        f"INSERT INTO {table_name_composite_key} (ID_1, ID_2, NAME) VALUES (98, 98, 'this-is-the-value-3')",
        f"INSERT INTO {table_name_composite_key} (ID_1, ID_2, NAME) VALUES (99, 99, 'this-is-the-value-4')",
        f"UPDATE {table_name_composite_key} SET NAME = 'this-is-the-value-3-new' WHERE ID_1 = 98 AND ID_2 = 98",
        f"UPDATE {table_name_composite_key} SET NAME = 'this-is-the-value-4-new' WHERE NAME = 'this-is-the-value-4'",
        f"DELETE FROM {table_name_composite_key} WHERE ID_1 = 98 AND ID_2 = 98",
        # --- pg_logical_emit_message() non-tx
        "BEGIN",
        "SELECT * FROM pg_logical_emit_message(FALSE, 'this-is-prefix', 'content-1')",
        "ROLLBACK",
        "BEGIN",
        "SELECT * FROM pg_logical_emit_message(FALSE, 'this-is-prefix', 'content-2')",
        "COMMIT",
        # --- pg_logical_emit_message() tx
        "BEGIN",
        "SELECT * FROM pg_logical_emit_message(TRUE, 'this-is-prefix', 'content-3')",
        "ROLLBACK",
        "BEGIN",
        "SELECT * FROM pg_logical_emit_message(TRUE, 'this-is-prefix', 'content-4')",
        "COMMIT",
    ]

    create_table = f"""
    CREATE TABLE {table_name_no_pk} (
        name varchar not null
    );
    CREATE TABLE {table_name_pk} (
        pk serial not null primary key,
        name varchar not null
    );
    CREATE TABLE {table_name_composite_key} (
        id_1 serial not null,
        id_2 serial not null,
        name varchar not null,
        primary key (id_1, id_2)
    );
    """

    expected = [
        {"action": "B"},
        {"action": "C"},
        {"action": "B"},
        {
            "action": "I",
            "columns": [{"name": "name", "type": "character varying", "value": "this-is-the-value-1"}],
            "schema": "public",
            "table": table_name_no_pk.lower(),
        },
        {"action": "C"},
        {"action": "B"},
        {
            "action": "I",
            "columns": [{"name": "name", "type": "character varying", "value": "this-is-the-value-2"}],
            "schema": "public",
            "table": table_name_no_pk.lower(),
        },
        {"action": "C"},
        {"action": "B"},
        {
            "action": "I",
            "columns": [{"name": "name", "type": "character varying", "value": "this-is-the-value-3"}],
            "schema": "public",
            "table": table_name_no_pk.lower(),
        },
        {"action": "C"},
        {"action": "B"},
        {
            "action": "I",
            "columns": [{"name": "name", "type": "character varying", "value": "this-is-the-value-4"}],
            "schema": "public",
            "table": table_name_no_pk.lower(),
        },
        {"action": "C"},
        {"action": "B"},
        {"action": "C"},
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
            "table": table_name_pk.lower(),
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
            "table": table_name_pk.lower(),
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
            "table": table_name_pk.lower(),
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
            "table": table_name_pk.lower(),
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
            "table": table_name_pk.lower(),
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
            "table": table_name_pk.lower(),
        },
        {"action": "C"},
        {"action": "B"},
        {
            "action": "D",
            "identity": [{"name": "pk", "type": "integer", "value": 2}],
            "schema": "public",
            "table": table_name_pk.lower(),
        },
        {
            "action": "D",
            "identity": [{"name": "pk", "type": "integer", "value": 98}],
            "schema": "public",
            "table": table_name_pk.lower(),
        },
        {"action": "C"},
        {"action": "B"},
        {"action": "T", "schema": "public", "table": table_name_no_pk.lower()},
        {"action": "C"},
        {"action": "B"},
        {"action": "T", "schema": "public", "table": table_name_pk.lower()},
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
            "table": table_name_composite_key.lower(),
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
            "table": table_name_composite_key.lower(),
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
            "table": table_name_composite_key.lower(),
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
            "table": table_name_composite_key.lower(),
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
            "table": table_name_composite_key.lower(),
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
            "table": table_name_composite_key.lower(),
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
            "table": table_name_composite_key.lower(),
        },
        {"action": "C"},
        {"action": "M", "content": "content-1", "prefix": "this-is-prefix", "transactional": False},
        {"action": "M", "content": "content-2", "prefix": "this-is-prefix", "transactional": False},
        {"action": "B"},
        {"action": "M", "content": "content-4", "prefix": "this-is-prefix", "transactional": True},
        {"action": "C"},
    ]

    return AllScenarios(
        table_name_no_pk=table_name_no_pk,
        table_name_pk=table_name_pk,
        table_name_composite_key=table_name_composite_key,
        create_table_ddl=create_table,
        statements=statements,
        expected=expected,
    )
