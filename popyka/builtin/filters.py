import logging

from popyka.core import Filter, Wal2JsonV2Change
from popyka.errors import ConfigError

logger = logging.getLogger(__name__)


class IgnoreTxFilter(Filter):
    """
    Ignore changes associated to transaction handling (BEGIN/COMMIT).

    As any filter, this can be configured globally, or per-processor.

    This filter does not accept any configuration.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def setup(self):
        if self.config_generic:
            raise ConfigError("IgnoreTxFilter filter does not accepts any configuration")

    def ignore_change(self, change: Wal2JsonV2Change) -> bool:
        return change["action"] == "B" or change["action"] == "C"
