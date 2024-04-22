import itertools
import json
from collections import defaultdict
from unittest.mock import MagicMock

from popyka.adaptors import ReplicationConsumerToProcessorAdaptor
from popyka.api import Filter, Processor, Wal2JsonV2Change
from tests.conftest_all_scenarios import AllScenarios


class MemoryStoreProcessorImpl(Processor):
    """Store the changes in memory"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._changes: list[Wal2JsonV2Change] = []

    @property
    def count(self):
        return len(self._changes)

    @property
    def changes(self):
        return self._changes

    def setup(self):
        pass

    def process_change(self, change: Wal2JsonV2Change):
        self._changes.append(change)


class CycleFilterImpl(Filter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cycle_result = itertools.cycle([Filter.Result.CONTINUE, Filter.Result.IGNORE, Filter.Result.PROCESS])
        self._changes: dict[Filter.Result, list] = defaultdict(list)

    def setup(self):
        pass

    @property
    def count(self):
        return sum(len(v) for k, v in self._changes.items())

    @property
    def result_ignore(self) -> list:
        return self._changes[Filter.Result.IGNORE]

    @property
    def result_continue(self) -> list:
        return self._changes[Filter.Result.CONTINUE]

    @property
    def result_process(self) -> list:
        return self._changes[Filter.Result.PROCESS]

    @property
    def count_ignore(self) -> int:
        return len(self._changes[Filter.Result.IGNORE])

    @property
    def count_continue(self) -> int:
        return len(self._changes[Filter.Result.CONTINUE])

    @property
    def count_process(self) -> int:
        return len(self._changes[Filter.Result.PROCESS])

    def filter(self, change: Wal2JsonV2Change) -> Filter.Result:
        result: Filter.Result = next(self._cycle_result)
        self._changes[result].append(change)
        return result


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
        adaptor = ReplicationConsumerToProcessorAdaptor(
            [MemoryStoreProcessorImpl(config_generic={})], [CycleFilterImpl(config_generic={})]
        )
        for a_change in all_scenarios.expected:
            adaptor(ReplicationMessageMock.from_dict(a_change))

    def test_dummy_filter_and_processor(self, all_scenarios: AllScenarios):
        a_processor = MemoryStoreProcessorImpl(config_generic={})
        a_filter = CycleFilterImpl(config_generic={})

        adaptor = ReplicationConsumerToProcessorAdaptor([a_processor], [a_filter])

        assert not a_processor.changes
        assert a_processor.count == 0

        for a_change in all_scenarios.expected:
            adaptor(ReplicationMessageMock.from_dict(a_change))

        assert a_processor.changes
        assert a_filter.count
        assert a_filter.count_ignore
        assert a_filter.count_process
        assert a_filter.count_continue

        assert len(all_scenarios.expected) == a_filter.count
        assert a_processor.count == a_filter.count_process + a_filter.count_continue
        assert len(all_scenarios.expected) - a_processor.count == a_filter.count_ignore
