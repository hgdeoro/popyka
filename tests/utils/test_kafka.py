import uuid

from confluent_kafka import Consumer


def test_debug_consume_one(kafka_bootstrap_servers):
    """
    docker exec -ti popyka-kafka-1 /bin/bash -c 'echo "HELLO WORLD" | \
        kafka-console-producer.sh --topic popyka --bootstrap-server localhost:9092'
    """
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
