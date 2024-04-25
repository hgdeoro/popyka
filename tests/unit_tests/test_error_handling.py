import pytest

from popyka.adaptors import ReplicationConsumerToProcessorAdaptor
from popyka.api import ErrorHandler, Processor, Wal2JsonV2Change
from popyka.config import PopykaConfig
from popyka.errors import AbortExecutionException, StopServer
from tests.unit_tests.test_replication_consumer_daptor import ReplicationMessageMock


class GenericProcessor(Processor):
    def setup(self):
        pass

    def process_change(self, change: Wal2JsonV2Change):
        raise NotImplementedError("This method is intended to be mocked")


def process_change_key_error(_self, change: Wal2JsonV2Change, *args, **kwargs):
    print(change["this-key-does-not-exists"])


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


class TestNoErrorHandlingConfigured:
    def test_abort_without_error_handlers(self, min_config, monkeypatch):
        monkeypatch.setattr(GenericProcessor, "process_change", process_change_key_error)

        min_config["processors"] = [{"class": GENERIC}]
        config = PopykaConfig.from_dict(min_config)
        processors = [_.instantiate() for _ in config.processors]

        adaptor = ReplicationConsumerToProcessorAdaptor(processors, filters=[])
        repl_message = ReplicationMessageMock.from_dict(VALID_PAYLOAD)

        with pytest.raises(AbortExecutionException):
            adaptor(repl_message)

    def test_stop_is_propagated(self, min_config, monkeypatch):
        def process_change(_self, *args, **kwargs):
            raise StopServer()

        monkeypatch.setattr(GenericProcessor, "process_change", process_change)

        min_config["processors"] = [{"class": GENERIC}]
        config = PopykaConfig.from_dict(min_config)
        processors = [_.instantiate() for _ in config.processors]

        adaptor = ReplicationConsumerToProcessorAdaptor(processors, filters=[])
        repl_message = ReplicationMessageMock.from_dict(VALID_PAYLOAD)

        with pytest.raises(StopServer):
            adaptor(repl_message)


class GenericErrorHandler(ErrorHandler):
    handled_errors = []

    def setup(self):
        self.handled_errors.clear()

    def get_next(self):
        return ErrorHandler.NextAction.NEXT_ERROR_HANDLER

    def handle_error(self, change: Wal2JsonV2Change, exception: Exception) -> ErrorHandler.NextAction:
        assert isinstance(change, (Wal2JsonV2Change, dict)), "handle_error(): 'change' param of invalid type"
        assert isinstance(exception, BaseException), "handle_error(): 'exception' param of invalid type"

        self.handled_errors.append(exception)
        return self.get_next()


ERR_HANDLER = f"{__name__}.{GenericErrorHandler.__qualname__}"


def test_single_error_handler_is_used(min_config, monkeypatch):
    monkeypatch.setattr(GenericProcessor, "process_change", process_change_key_error)

    min_config["processors"] = [{"class": GENERIC, "error_handlers": [{"class": ERR_HANDLER}]}]
    config = PopykaConfig.from_dict(min_config)
    processors = [_.instantiate() for _ in config.processors]

    adaptor = ReplicationConsumerToProcessorAdaptor(processors, filters=[])
    repl_message = ReplicationMessageMock.from_dict(VALID_PAYLOAD)
    assert not GenericErrorHandler.handled_errors

    with pytest.raises(AbortExecutionException):
        adaptor(repl_message)

    assert len(GenericErrorHandler.handled_errors) == 1
    assert isinstance(GenericErrorHandler.handled_errors[0], KeyError)
