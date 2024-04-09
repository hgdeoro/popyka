import json
import logging
import os

from popyka.core import Filter, Processor, Server
from popyka.filters import IgnoreTxFilter
from popyka.processors import LogChangeProcessor, ProduceToKafkaProcessor

logger = logging.getLogger(__name__)


class PopykaConfigurationError(Exception):
    pass


class Main(Server):
    def get_filters(self) -> list[Filter]:
        return [IgnoreTxFilter()]

    def get_processors(self) -> list[Processor]:
        kafka_config_str = os.environ.get("POPYKA_KAFKA_CONF_DICT", "").strip()
        if not kafka_config_str:
            raise PopykaConfigurationError("The environment variable POPYKA_KAFKA_CONF_DICT is not set or empty")

        try:
            kafka_config = json.loads(kafka_config_str)
        except json.decoder.JSONDecodeError:
            raise PopykaConfigurationError(
                "The string from environment variable POPYKA_KAFKA_CONF_DICT is not a valid JSON"
            )
        return [LogChangeProcessor(), ProduceToKafkaProcessor(kafka_config)]

    def get_dsn(self) -> str:
        dsn = os.environ.get("POPYKA_DB_DSN", "").strip()
        if not dsn:
            raise PopykaConfigurationError("The environment variable POPYKA_DB_DSN is not set or empty")
        return dsn


if __name__ == "__main__":
    enable_debug = bool(os.environ.get("POPYKA_DEBUG", "").strip())
    logging.basicConfig(level=logging.DEBUG if enable_debug else logging.INFO)
    Main().run()
