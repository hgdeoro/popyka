import logging
import re

from popyka.api import Filter, Wal2JsonV2Change
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

    def filter(self, change: Wal2JsonV2Change) -> Filter.Result:
        if change["action"] == "B" or change["action"] == "C":
            return Filter.Result.IGNORE
        return Filter.Result.CONTINUE


class TableNameIgnoreFilter(Filter):
    """
    Ignore changes from specific tables.

    As any filter, this can be configured globally, or per-processor.

    This filter **requires** configuration:
    * `ignore_regex`: ignore changes from tables that matches the provided regular expression.

    Sample configuration:
    ```
    processors:
        - class: builtin.IgnoreTable
          ignore_regex: '^django_.*'
    ```
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._ignore_regex: re.Pattern | None = None

    def setup(self):
        ignore_regex = self._get_config(self.config_generic, "ignore_regex", str, clean=lambda v: v.strip())
        if not ignore_regex:
            raise ConfigError("Invalid config: `ignore_regex` is required")

        self._ignore_regex = re.compile(ignore_regex)

    def filter(self, change: Wal2JsonV2Change) -> Filter.Result:
        table_name = change.get("table")
        if table_name is None:
            return Filter.Result.CONTINUE

        if self._ignore_regex.fullmatch(table_name):
            return Filter.Result.IGNORE
        return Filter.Result.CONTINUE
