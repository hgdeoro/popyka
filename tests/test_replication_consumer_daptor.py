import json
from unittest.mock import MagicMock

from popyka.core import (
    Filter,
    Processor,
    ReplicationConsumerToProcessorAdaptor,
    Wal2JsonV2Change,
)
from tests.conftest_all_scenarios import AllScenarios


class CounterProcessorImpl(Processor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.changes: list[Wal2JsonV2Change] = []

    @property
    def count(self):
        return len(self.changes)

    def setup(self):
        pass

    def process_change(self, change: Wal2JsonV2Change):
        self.changes.append(change)


class CounterFilterImpl(Filter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.count = 0

    def setup(self):
        pass

    def filter(self, change: Wal2JsonV2Change) -> Filter.Result:
        self.count += 1
        return Filter.Result.CONTINUE


class ReplicationMessageMock:
    def __init__(self, payload: bytes):
        self._payload = payload

    @property
    def payload(self):
        return self._payload

    @property
    def data_start(self):
        return "mock-data-start"

    @property
    def cursor(self):
        return MagicMock()

    @classmethod
    def from_dict(cls, change: dict):
        return ReplicationMessageMock(payload=json.dumps(change).encode("utf-8"))


class TestAllScenarios:
    def test_doesnt_fails(self, all_scenarios: AllScenarios):
        a_processor = CounterProcessorImpl(config_generic={})
        a_filter = CounterFilterImpl(config_generic={})

        adaptor = ReplicationConsumerToProcessorAdaptor([a_processor], [a_filter])

        assert not a_processor.changes
        assert a_processor.count == 0

        for a_change in all_scenarios.expected:
            adaptor(ReplicationMessageMock.from_dict(a_change))

        assert a_processor.changes
        assert a_filter.count > 0
