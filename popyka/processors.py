import json
import logging

from confluent_kafka import Producer

from popyka.core import POPYKA_KAFKA_CONF_DICT, Processor, Wal2JsonV2Change

logger = logging.getLogger(__name__)


class LogChangeProcessor(Processor):
    """Processor that dumps the payload"""

    def process_change(self, change: Wal2JsonV2Change):
        # TODO: make json.dumps() lazy
        logger.info("LogChangeProcessor: change: %s", json.dumps(change, indent=4))


class ProduceToKafkaProcessor(Processor):
    @staticmethod
    def _get_conf() -> dict:
        return json.loads(POPYKA_KAFKA_CONF_DICT)

    def __init__(self):
        self._producer = Producer(self._get_conf())

    def process_change(self, change: Wal2JsonV2Change):
        self._producer.produce(topic="popyka", value=json.dumps(change))
        self._producer.flush()
        logger.info("Message produced to Kafka was flush()'ed")
