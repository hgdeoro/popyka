import pytest

from popyka.adaptors import ReplicationConsumerToProcessorAdaptor
from popyka.api import Processor, Wal2JsonV2Change
from popyka.config import PopykaConfig
from popyka.errors import AbortExecutionException, StopServer
from tests.unit_tests.test_replication_consumer_daptor import ReplicationMessageMock


class GenericProcessor(Processor):
    def setup(self):
        pass

    def process_change(self, change: Wal2JsonV2Change):
        raise NotImplementedError("This method is intended to be mocked")


GENERIC = f"{__name__}.{GenericProcessor.__qualname__}"

VALID_PAYLOAD = {
    "action": "I",
    "columns": [
        {"name": "pk", "type": "integer", "value": 1},
        {"name": "name", "type": "character varying", "value": "this-is-the-value-1"},
    ],
    "schema": "public",
    "table": "table_name",
}


class TestErrorHandling:
    def test_abort_without_error_handlers(self, min_config, monkeypatch):
        def process_change(change: Wal2JsonV2Change, *args, **kwargs):
            print(change["this-key-does-not-exists"])

        monkeypatch.setattr(GenericProcessor, "process_change", process_change)

        min_config["processors"] = [{"class": GENERIC}]
        config = PopykaConfig.from_dict(min_config)
        processors = [_.instantiate() for _ in config.processors]

        adaptor = ReplicationConsumerToProcessorAdaptor(processors, filters=[])
        repl_message = ReplicationMessageMock.from_dict(VALID_PAYLOAD)

        with pytest.raises(AbortExecutionException):
            adaptor(repl_message)

    def test_stop_is_propagated(self, min_config, monkeypatch):
        def process_change(*args, **kwargs):
            raise StopServer()

        monkeypatch.setattr(GenericProcessor, "process_change", process_change)

        min_config["processors"] = [{"class": GENERIC}]
        config = PopykaConfig.from_dict(min_config)
        processors = [_.instantiate() for _ in config.processors]

        adaptor = ReplicationConsumerToProcessorAdaptor(processors, filters=[])
        repl_message = ReplicationMessageMock.from_dict(VALID_PAYLOAD)

        with pytest.raises(StopServer):
            adaptor(repl_message)
