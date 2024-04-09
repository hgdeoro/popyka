import json
import logging
import threading
import typing

import psycopg2.extras
from psycopg2.extensions import connection as Connection
from psycopg2.extras import ReplicationCursor

logger = logging.getLogger(__name__)


class DbStreamConsumer(threading.Thread):
    def __init__(self, cn: Connection, options=None):
        super().__init__(daemon=True)
        self._cn = cn
        self._payloads = []
        self._options = options or {}
        self._cursor = self._cn.cursor()

    def start_replication(self) -> "DbStreamConsumer":
        """
        We create the slot as soon as possible, this way no change will be lost.
        consumer = DbStreamConsumerSimple().start_replication()
            or
        consumer = DbStreamConsumerSimple()
        consumer.start_replication().start()
        """
        self._cursor.create_replication_slot("pytest_logical", output_plugin="wal2json")
        self._cursor.start_replication(slot_name="pytest_logical", decode=True, options=self._options)
        return self

    @property
    def payloads(self) -> list:
        return list(self._payloads)

    @property
    def payloads_parsed(self) -> list[dict]:
        return [json.loads(_) for _ in self._payloads]

    def join_or_fail(self, timeout):
        self.join(timeout=timeout)
        assert not self.is_alive()

    def run(self) -> None:
        _payloads = self._payloads

        class DemoConsumer(object):
            def __call__(self, msg: psycopg2.extras.ReplicationMessage):
                logger.info("DemoConsumer received payload: %s", msg.payload)
                msg.cursor.send_feedback(flush_lsn=msg.data_start)

                if DbActivitySimulator.is_magic_end_of_test_change(json.loads(msg.payload)):
                    raise psycopg2.extras.StopReplication()

                # FIXME: ^^^ maybe we should add also the payload from the "magic" statement?

                _payloads.append(msg.payload)

        consumer = DemoConsumer()

        try:
            self._cursor.consume_stream(consumer)
        except psycopg2.extras.StopReplication:
            pass

        # TODO: close stream?


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
        self._statements: typing.Iterable[tuple[str, list]] = statements

    #  pg_logical_emit_message ( transactional boolean, prefix text, content text ) → pg_lsn
    MAGIC_END_OF_TEST_PREFIX = "popyka_pytest"
    MAGIC_END_OF_TEST_CONTENT = "742cad81-3416-4dc8-9f7a-d667b54c98cf"
    MAGIC_END_OF_TEST_STATEMENT = (
        "SELECT * FROM pg_logical_emit_message(FALSE, %s, %s)",
        [MAGIC_END_OF_TEST_PREFIX, MAGIC_END_OF_TEST_CONTENT],
    )

    @classmethod
    def is_magic_end_of_test_change(cls, change: dict):
        # v1
        # {
        #     "change": [
        #         {
        #             "kind": "message",
        #             "transactional": false,
        #             "prefix": "popyka_pytest",
        #             "content": "742cad81-3416-4dc8-9f7a-d667b54c98cf"
        #         }
        #     ]
        # }
        if "change" in change:
            for a_change in change["change"]:
                if (
                    a_change.get("kind") == "message"
                    and a_change.get("prefix") == DbActivitySimulator.MAGIC_END_OF_TEST_PREFIX
                    and a_change.get("content") == DbActivitySimulator.MAGIC_END_OF_TEST_CONTENT
                ):
                    return True
            return False

        # v2
        # {
        #     "action": "M",
        #     "transactional": false,
        #     "prefix": "popyka_pytest",
        #     "content": "742cad81-3416-4dc8-9f7a-d667b54c98cf"
        # }
        if "action" in change:
            return (
                change.get("action") == "M"
                and change.get("prefix") == DbActivitySimulator.MAGIC_END_OF_TEST_PREFIX
                and change.get("content") == DbActivitySimulator.MAGIC_END_OF_TEST_CONTENT
            )
            return False

        print(json.dumps(change, indent=4))
        raise NotImplementedError("Unknown payload version. Payload: " + json.dumps(change, indent=4))

    @property
    def table_name(self) -> str:
        return self._table_name

    def _create_table(self, cur):
        cur.execute(f"DROP TABLE IF EXISTS {self._table_name}")
        self._cn.commit()

        cur.execute(f"CREATE TABLE {self._table_name} (NAME VARCHAR)")
        self._cn.commit()
        return self

    def join_or_fail(self, timeout):
        self.join(timeout=timeout)
        assert not self.is_alive()

    def run(self) -> None:
        with self._cn.cursor() as cur:
            cur: ReplicationCursor
            self._create_table(cur)

            for stmt in self._statements:
                logger.info("%s | %s", self._table_name, str(stmt))
                cur.execute(stmt[0].format(table_name=self._table_name), stmt[1])
                self._cn.commit()

            stmt = self.MAGIC_END_OF_TEST_STATEMENT
            logger.info("%s | %s", self._table_name, str(stmt))
            cur.execute(stmt[0].format(table_name=self._table_name), stmt[1])
            self._cn.commit()

    def sql_count_all(self, cn: Connection, table_name_suffix=""):
        with cn.cursor() as cur:
            cur.execute(f"SELECT count(*) FROM {self._table_name}{table_name_suffix}")
            return cur.fetchall()[0][0]
