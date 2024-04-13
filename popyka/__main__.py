import logging
import os

from popyka.config import PopykaConfig
from popyka.core import Server

logger = logging.getLogger(__name__)


class Main(Server):
    pass


if __name__ == "__main__":
    enable_debug = bool(os.environ.get("POPYKA_DEBUG", "").strip())
    logging.basicConfig(level=logging.DEBUG if enable_debug else logging.INFO)
    main = Main(config=PopykaConfig.get_default_config())
    main.start_replication()
    main.run()
