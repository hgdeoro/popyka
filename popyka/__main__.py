import logging
import os

from popyka.config import PopykaConfig
from popyka.core import Server

logger = logging.getLogger(__name__)


class PopykaConfigurationError(Exception):
    # FIXME: remove this exception
    pass


class Main(Server):
    pass

    # This class used to use 2 environment variables:
    # - POPYKA_DB_DSN
    # - POPYKA_KAFKA_CONF_DICT


if __name__ == "__main__":
    enable_debug = bool(os.environ.get("POPYKA_DEBUG", "").strip())
    logging.basicConfig(level=logging.DEBUG if enable_debug else logging.INFO)
    main = Main(config=PopykaConfig.get_default_config())
    main.start_replication()
    main.run()
