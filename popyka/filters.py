from popyka.core import Filter, Wal2JsonV2Change


class IgnoreTxFilter(Filter):
    """Ignore changes associated BEGIN/COMMIT"""

    IGNORED_ACTIONS = {"B", "C"}

    def ignore_change(self, change: Wal2JsonV2Change) -> bool:
        return change["action"] in self.IGNORED_ACTIONS
