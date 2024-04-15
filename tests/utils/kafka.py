import json
import logging
import time
import uuid

import confluent_kafka
from confluent_kafka import Consumer
from confluent_kafka.admin import AdminClient, ClusterMetadata
from confluent_kafka.cimpl import NewTopic

logger = logging.getLogger(__name__)


class KafkaAdmin:
    def __init__(self, bootstrap_servers: str):
        self._admin = AdminClient({"bootstrap.servers": bootstrap_servers})

    def create_topic(self, topic_name: str):
        self._admin.create_topics([NewTopic(topic=topic_name, num_partitions=1)], operation_timeout=1.0)

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
                "enable.auto.commit": False,
                "debug": "all",
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
            msg = self._consumer.poll(0.2)
            if msg is None:
                continue

            if msg.error():
                logger.debug("consumer.poll(): Ignoring error: %s", msg.error())
                continue

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
