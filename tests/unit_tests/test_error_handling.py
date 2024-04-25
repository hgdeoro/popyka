import pytest

from popyka.adaptors import ReplicationConsumerToProcessorAdaptor
from popyka.api import Processor, Wal2JsonV2Change
from popyka.config import PopykaConfig
from popyka.errors import AbortExecutionException
from tests.unit_tests.test_replication_consumer_daptor import ReplicationMessageMock


class SampleProcessor1(Processor):
    def setup(self):
        pass

    def process_change(self, change: Wal2JsonV2Change):
        print(change["this-key-does-not-exists"])


PROCESSOR_1 = f"{__name__}.{SampleProcessor1.__qualname__}"

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
    def test_abort_by_default(self, min_config):
        min_config["processors"] = [{"class": PROCESSOR_1}]
        config = PopykaConfig.from_dict(min_config)
        processors = [_.instantiate() for _ in config.processors]

        adaptor = ReplicationConsumerToProcessorAdaptor(processors, filters=[])
        repl_message = ReplicationMessageMock.from_dict(VALID_PAYLOAD)

        with pytest.raises(AbortExecutionException):
            adaptor(repl_message)
