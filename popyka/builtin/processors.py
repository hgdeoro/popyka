import json
import logging

from confluent_kafka import Producer

from popyka.core import Processor, Wal2JsonV2Change

logger = logging.getLogger(__name__)


class LogChangeProcessor(Processor):
    """Processor that dumps the payload"""

    def process_change(self, change: Wal2JsonV2Change):
        # TODO: make json.dumps() lazy
        logger.info("LogChangeProcessor: change: %s", json.dumps(change, indent=4))


class ProduceToKafkaProcessor(Processor):
    def __init__(self, kafka_config: dict):
        self._producer = Producer(kafka_config)

    def process_change(self, change: Wal2JsonV2Change):
        self._producer.produce(topic="popyka", value=json.dumps(change))
        self._producer.flush()
        logger.info("Message produced to Kafka was flush()'ed")
