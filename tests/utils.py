import json
import logging
import threading
import time
import typing
import uuid

import confluent_kafka
import psycopg2.extras
from confluent_kafka import Consumer
from confluent_kafka.admin import AdminClient, ClusterMetadata
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
        create_table_ddl: str | None = None,
    ):
        super().__init__(daemon=True)
        self._cn = cn
        self._table_name: str = table_name
        self._statements: typing.Iterable[tuple[str, list]] = statements
        self._create_table_ddl = create_table_ddl or f"CREATE TABLE {self._table_name} (NAME VARCHAR)"

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

    def _get_create_table_ddl(self) -> str:
        return self._create_table_ddl

    def _create_table(self, cur):
        cur.execute(f"DROP TABLE IF EXISTS {self._table_name}")
        self._cn.commit()

        cur.execute(self._get_create_table_ddl())
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


class KafkaAdmin:
    def __init__(self, bootstrap_servers: str):
        self._admin = AdminClient({"bootstrap.servers": bootstrap_servers})

    def delete_all_topics(self, op_timeout=3.0):
        cluster_meta: ClusterMetadata = self._admin.list_topics()
        topics_to_delete = [_ for _ in cluster_meta.topics if not _.startswith("_")]
        for topic in topics_to_delete:
            print(f"Deleting topic {topic}")
            self._admin.delete_topics(topics_to_delete, operation_timeout=op_timeout)


class KafkaConsumer:
    def __init__(self, bootstrap_servers: str, topic: str):
        self._topic = topic
        self._consumed_msg: list[confluent_kafka.Message] = []
        self._consumer = Consumer(
            {
                "bootstrap.servers": bootstrap_servers,
                "group.id": str(uuid.uuid4().hex),
                "auto.offset.reset": "earliest",
            }
        )
        self._consumer.subscribe([topic])

    @property
    def consumed_msg(self) -> list[confluent_kafka.Message]:
        return list(self._consumed_msg)

    # def clean(self):
    #     self._consumed_msg = []

    def wait_for_count(self, count: int, timeout: float) -> list[confluent_kafka.Message]:
        print(f"Waiting for {count} messages in topic {self._topic}")
        assert timeout > 0
        start = time.monotonic()
        while time.monotonic() - start < timeout and len(self._consumed_msg) < count:
            logger.debug(
                "Waiting for %s messages in topic %s. There are %s at the moment",
                count,
                self._topic,
                len(self._consumed_msg),
            )
            msg = self._consumer.poll(0.1)
            if msg is None:
                continue
            assert not msg.error()

            self._consumed_msg.append(msg)

        # self._consumer.close()  # How can we know if client will try again :/

        if len(self._consumed_msg) < count:
            raise Exception(f"Timeout waiting for {count} messages. Got: only {len(self._consumed_msg)}")

        return self._consumed_msg

    @classmethod
    def summarize(cls, messages: list[confluent_kafka.Message]):
        changes_dict = [json.loads(_.value()) for _ in messages]
        changes_summary = [(_["action"], _["table"]) for _ in changes_dict]
        return changes_summary
