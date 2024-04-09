import logging
import uuid

from psycopg2.extensions import connection as Connection

from tests.conftest import exploration_test
from tests.utils import DbActivitySimulator, DbStreamConsumer

logger = logging.getLogger(__name__)


@exploration_test
def test_insert_are_replicated(conn: Connection, conn2: Connection, drop_slot, table_name: str):
    uuids = [str(uuid.uuid4()) for _ in range(4)]
    statements = [("INSERT INTO {table_name} (NAME) VALUES (%s)", [_]) for _ in uuids]

    db_stream_consumer = DbStreamConsumer(conn2)
    db_activity_simulator = DbActivitySimulator(conn, table_name, statements)

    db_stream_consumer.start_replication().start()
    db_activity_simulator.start()
    db_activity_simulator.join_or_fail(timeout=1)
    db_stream_consumer.join(timeout=3)

    # {
    #     "change": [
    #         {
    #             "kind": "insert",
    #             "schema": "public",
    #             "table": "test_table_005902aae27f4f7ab33fada1c78d7f14",
    #             "columnnames": [
    #                 "name"
    #             ],
    #             "columntypes": [
    #                 "character varying"
    #             ],
    #             "columnvalues": [
    #                 "53b5cda2-e3cc-4011-a9c7-7f628bc7e008"
    #             ]
    #         }
    #     ]
    # },

    json_payloads = db_stream_consumer.payloads_parsed
    json_payloads = [_ for _ in json_payloads if _["change"]]
    assert [_["change"][0]["kind"] for _ in json_payloads] == ["insert"] * 4
    assert [_["change"][0]["columnvalues"][0] for _ in json_payloads] == uuids


@exploration_test
def test_json_for_default_options(conn: Connection, conn2: Connection, drop_slot, table_name: str):
    statements = [
        ("INSERT INTO {table_name} (NAME) VALUES ('this-is-the-value-1')", []),
        ("INSERT INTO {table_name} (NAME) VALUES ('this-is-the-value-2')", []),
    ]
    options = {}

    db_activity_simulator = DbActivitySimulator(conn, table_name, statements)
    db_stream_consumer = DbStreamConsumer(conn2, options=options)

    db_stream_consumer.start_replication().start()
    db_activity_simulator.start()
    db_activity_simulator.join_or_fail(timeout=1)
    db_stream_consumer.join_or_fail(timeout=3)

    assert db_stream_consumer.payloads_parsed == [
        {
            "change": [],
        },
        {
            "change": [
                {
                    "columnnames": [
                        "name",
                    ],
                    "columntypes": [
                        "character varying",
                    ],
                    "columnvalues": [
                        "this-is-the-value-1",
                    ],
                    "kind": "insert",
                    "schema": "public",
                    "table": table_name.lower(),
                },
            ],
        },
        {
            "change": [
                {
                    "columnnames": [
                        "name",
                    ],
                    "columntypes": [
                        "character varying",
                    ],
                    "columnvalues": [
                        "this-is-the-value-2",
                    ],
                    "kind": "insert",
                    "schema": "public",
                    "table": table_name.lower(),
                },
            ],
        },
    ]


def test_format_version_2(conn: Connection, conn2: Connection, drop_slot, table_name: str):
    statements = [
        ("INSERT INTO {table_name} (NAME) VALUES ('this-is-the-value-1')", []),
        ("INSERT INTO {table_name} (NAME) VALUES ('this-is-the-value-2')", []),
    ]
    # https://github.com/eulerto/wal2json?tab=readme-ov-file
    options = {"format-version": "2"}

    db_activity_simulator = DbActivitySimulator(conn, table_name, statements)
    db_stream_consumer = DbStreamConsumer(conn2, options=options)

    db_stream_consumer.start_replication().start()
    db_activity_simulator.start()
    db_activity_simulator.join_or_fail(timeout=3)

    db_stream_consumer.join_or_fail(timeout=3)

    assert [_ for _ in db_stream_consumer.payloads_parsed if _["action"] not in "BC"] == [
        {
            "action": "I",
            "schema": "public",
            "table": table_name.lower(),
            "columns": [{"name": "name", "type": "character varying", "value": "this-is-the-value-1"}],
        },
        {
            "action": "I",
            "schema": "public",
            "table": table_name.lower(),
            "columns": [{"name": "name", "type": "character varying", "value": "this-is-the-value-2"}],
        },
    ]
