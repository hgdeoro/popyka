import logging
import uuid
from pprint import pprint

from psycopg2.extensions import connection as Connection

from tests.conftest_all_scenarios import AllScenarios
from tests.utils.db_activity_simulator import DbActivitySimulator, DbStreamConsumer

logger = logging.getLogger(__name__)


# We want to run this test always, to verify that `all_scenarios` fixture works as expected
def test_all(conn: Connection, conn2: Connection, drop_slot, all_scenarios: AllScenarios):
    db_activity_simulator = DbActivitySimulator(
        conn, f"ignore_{uuid.uuid4().hex}", all_scenarios.statements, create_table_ddl=all_scenarios.create_table_ddl
    )
    db_stream_consumer = DbStreamConsumer(conn2)
    db_stream_consumer.start_replication().start()
    db_activity_simulator.start()
    db_activity_simulator.join_or_fail(timeout=3)
    db_stream_consumer.join_or_fail(timeout=3)

    pprint(db_stream_consumer.payloads_parsed, indent=4, sort_dicts=True, compact=False)

    assert db_stream_consumer.payloads_parsed == all_scenarios.expected
