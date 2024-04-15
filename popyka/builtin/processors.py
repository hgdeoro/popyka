import json
import logging
import pathlib
import time

from confluent_kafka import Producer

from popyka.core import Processor, Wal2JsonV2Change
from popyka.errors import ConfigError
from popyka.logging import LazyToStr


class LogChangeProcessor(Processor):
    """
    This processor logs the payload using Python `logging` module.

    This processor does not accept any configuration.
    """

    logger = logging.getLogger(f"{__name__}.LogChangeProcessor")

    def setup(self):
        if self.config_generic:
            raise ConfigError("LogChangeProcessor filter does not accepts any configuration")

    def process_change(self, change: Wal2JsonV2Change):
        self.logger.info("Change received: %s", LazyToStr(change))


class ProduceToKafkaProcessor(Processor):
    """
    This processor send the changes to Kafka.

    This processor **requires** configuration:
    * `config.topic`: topic where to write changes.
    * `config.producer_config`: dictionary to configure the `confluent_kafka.Producer` instance (passed as is).

    Sample configuration:
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

    logger = logging.getLogger(f"{__name__}.ProduceToKafkaProcessor")

    # FIXME: DOC: document required configuration

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._producer: Producer | None = None
        self._topic: str | None = None

    def setup(self):
        self._topic = self._get_config(self.config_generic, "topic", str, clean=lambda v: v.strip())
        if not self._topic:
            raise ConfigError("Invalid config: `topic` is required")

        producer_config = self._get_config(self.config_generic, "producer_config", dict)
        if not producer_config.get("bootstrap.servers"):
            raise ConfigError("Invalid config: `bootstrap.servers` is required")
        if not producer_config.get("client.id"):
            raise ConfigError("Invalid config: `client.id` is required")

        self._producer = Producer(producer_config)

    def process_change(self, change: Wal2JsonV2Change):
        assert self._producer is not None
        self._producer.produce(topic=self._topic, value=json.dumps(change))
        self._producer.flush()
        self.logger.debug("Message produced to Kafka was flush()'ed")


class DumpToFileProcessor(Processor):
    """
    This processor write a JSON file in the local filesystem.

    This processor **requires** configuration:
    * `target_directory`: absolute path to directory where to store the JSON files. Directory needs to exist.

    Sample configuration:
    ```
    processors:
        - class: builtin.ProduceToKafkaProcessor
          config:
            target_directory: "/tmp"
    ```
    """

    logger = logging.getLogger(f"{__name__}.DumpToFileProcessor")

    # FIXME: DOC: document required configuration

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._target_directory: pathlib.Path | None = None
        self._run_id: int = int(time.time())
        self._serial: int = 0

    def setup(self):
        target_dir = self._get_config(self.config_generic, "target_directory", str, clean=lambda v: v.strip())
        if not target_dir:
            raise ConfigError("Invalid config: `target_directory` is required")

        self._target_directory = pathlib.Path(target_dir)
        if not self._target_directory.is_absolute():
            raise ConfigError("Invalid config: `target_directory` is not an absolute path")
        if not self._target_directory.exists():
            raise ConfigError("Invalid config: `target_directory` is valid path but does not exists")

    def process_change(self, change: Wal2JsonV2Change):
        assert self._target_directory is not None
        target_file = self._target_directory / f"popyka-dump-{self._run_id}-{self._serial:08d}.json"
        assert not target_file.exists()  # Since each time we have a different `self._run_id`, file shouldn't exist
        self.logger.info("Wringing message to %s", target_file)
        target_file.write_text(json.dumps(change, indent=4, sort_keys=True))
        self._serial += 1
