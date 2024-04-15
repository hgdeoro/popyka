import json
import logging
import threading
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


class KafkaThreadedConsumer(threading.Thread):
    def __init__(self, bootstrap_servers: str, topic: str):
        super().__init__(daemon=True)
        self._stopped = False
        self._topic = topic
        self._messages: list = []
        self._config = {
            "bootstrap.servers": bootstrap_servers,
            "group.id": str(uuid.uuid4().hex),
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
            # "debug": "all",
        }

    def stop(self):
        self._stopped = True

    @property
    def messages(self) -> list:
        return list(self._messages)

    def run(self):
        consumer = Consumer(self._config)
        consumer.subscribe([self._topic])

        while not self._stopped:
            msg = consumer.poll(timeout=0.5)
            if msg:
                logger.debug("Messages consumed: %s", msg)
                if msg.error():
                    logger.debug("consumer.poll(): Ignoring error: %s", msg.error())
                    continue
                self._messages.append(msg.value())

    def wait_for_count(self, count: int, timeout: float) -> list[confluent_kafka.Message]:
        assert timeout > 0
        print(f"Waiting for {count} messages in topic {self._topic}")
        start = time.monotonic()
        while time.monotonic() - start < timeout and len(self._messages) < count:
            logger.debug(
                "Waiting for %s messages in topic %s. There are %s at the moment",
                count,
                self._topic,
                len(self._messages),
            )
            time.sleep(0.1)

        if len(self._messages) < count:
            raise Exception(f"Timeout waiting for {count} messages. Got: only {len(self._messages)}")

        return self._messages

    def wait_for_count_summarized(self, count: int, timeout: float) -> list:
        return self.summarize(self.wait_for_count(count, timeout))

    @classmethod
    def summarize(cls, messages: list):
        changes_dict = [json.loads(_) for _ in messages]
        changes_summary = [(_["action"], _["table"]) for _ in changes_dict]
        return changes_summary
