import json
import logging

from confluent_kafka import Producer

from popyka.core import Processor, Wal2JsonV2Change
from popyka.logging import LazyToStr

logger = logging.getLogger(__name__)


class LogChangeProcessor(Processor):
    """
    This processor logs the payload using Python `logging` module.

    This processor does not accept any configuration.
    """

    def process_change(self, change: Wal2JsonV2Change):
        logger.info("LogChangeProcessor: change: %s", LazyToStr(change))


class ProduceToKafkaProcessor(Processor):
    """
    This processor send the changes to Kafka.

    This processor **requires** configuration:
    * `config.topic`: topic where to write changes.
    * `config.producer_config`: dictionary to configure the `confluent_kafka.Producer` instance (passed as is).
    ```
    processors:
        - class: builtin.ProduceToKafkaProcessor
          config:
            topic: "cdc_django"
            producer_config:
            - "bootstrap.servers": "server1:9092,server2:9092"
            - "client.id": client
    ```
    """

    # FIXME: DOC: document required configuration

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        producer_config = self._config_generic["producer_config"]
        self._producer = Producer(producer_config)

    def _validate_producer_config(self, producer_config: dict):
        pass

    def process_change(self, change: Wal2JsonV2Change):
        self._producer.produce(topic="popyka", value=json.dumps(change))
        self._producer.flush()
        logger.info("Message produced to Kafka was flush()'ed")
