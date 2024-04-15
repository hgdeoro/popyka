import threading
import time
import uuid

import pytest
from confluent_kafka import Consumer

from tests.conftest import exploration_test

"""
docker exec -ti popyka-kafka-1 /bin/bash -c 'echo "HELLO WORLD" | \
    kafka-console-producer.sh --topic popyka --bootstrap-server localhost:9092'
"""


@pytest.mark.skip
@exploration_test
def test_debug_consume_one(kafka_bootstrap_servers):
    config = {
        "bootstrap.servers": kafka_bootstrap_servers,
        "group.id": str(uuid.uuid4().hex),
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
        "debug": "all",
    }
    consumer = Consumer(config)
    consumer.subscribe(["popyka"])

    msg = None
    while not msg:
        msg = consumer.poll(timeout=0.5)
        print(msg)


@pytest.mark.skip
@exploration_test
def test_wait_after_subscribe(kafka_bootstrap_servers):
    config = {
        "bootstrap.servers": kafka_bootstrap_servers,
        "group.id": str(uuid.uuid4().hex),
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
        "debug": "all",
    }
    consumer = Consumer(config)
    consumer.subscribe(["popyka"])

    print("Will sleep for 3 seconds...")
    time.sleep(3)
    print("Continuing")

    msg = None
    while not msg:
        msg = consumer.poll(timeout=0.5)
        print(msg)


class LoopConsumer(threading.Thread):
    def __init__(self, bootstrap_servers):
        super().__init__(daemon=True)
        self._messages = []
        self._bootstrap_servers = bootstrap_servers
        self._stopped = False

    def stop(self):
        self._stopped = True

    def run(self):
        config = {
            "bootstrap.servers": self._bootstrap_servers,
            "group.id": str(uuid.uuid4().hex),
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
            "debug": "all",
        }
        consumer = Consumer(config)
        consumer.subscribe(["popyka"])

        while not self._stopped:
            msg = consumer.poll(timeout=0.1)
            print(msg)
            if msg:
                self._messages.append(msg)

    @property
    def messages(self):
        return list(self._messages)


@pytest.mark.skip
@exploration_test
def test_join_group_in_thread(kafka_bootstrap_servers):
    loop_consumer = LoopConsumer(bootstrap_servers=kafka_bootstrap_servers)
    loop_consumer.start()
    while not loop_consumer.messages:
        print("Waiting until there are messages in loop_consumer.messages")
        time.sleep(1.0)

    loop_consumer.stop()
    loop_consumer.join()
    print(f"Messages: {loop_consumer.messages}")
