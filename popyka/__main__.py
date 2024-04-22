import logging
import os
import sys

from popyka.config import PopykaConfig
from popyka.server import Server

logger = logging.getLogger(__name__)


class Main(Server):
    pass


if __name__ == "__main__":
    enable_debug = bool(os.environ.get("POPYKA_DEBUG", "").strip())
    logging.basicConfig(level=logging.DEBUG if enable_debug else logging.INFO)
    for new_path in [_ for _ in os.environ.get("POPYKA_PYTHONPATH", "").strip().split(":") if _.strip()]:
        logger.info("Added %s to PYTHONPATH", new_path)
        sys.path.append(new_path)

    main = Main(config=PopykaConfig.get_config(environment=os.environ))
    main.create_replication_slot()
    main.run()
