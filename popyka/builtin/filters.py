from popyka.core import Filter, Wal2JsonV2Change


class IgnoreTxFilter(Filter):
    """
    Ignore changes associated to transaction handling (BEGIN/COMMIT).

    As any filter, this can be configured globally, or per-processor.

    This filter does not accept any configuration.
    """

    IGNORED_ACTIONS = {"B", "C"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        assert not self._config_generic, "This filter does not accepts any configuration"
        # FIXME: use something better than a plain `assert`, since this is a configuration error, not an internal err

    def ignore_change(self, change: Wal2JsonV2Change) -> bool:
        return change["action"] in self.IGNORED_ACTIONS
