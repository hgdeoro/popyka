import pytest

from popyka.adaptors import ReplicationConsumerToProcessorAdaptor
from popyka.api import ErrorHandler, Filter, Processor, Wal2JsonV2Change
from popyka.config import PopykaConfig
from popyka.errors import (
    AbortExecutionFromErrorHandlerException,
    StopServer,
    UnhandledFilterException,
)
from tests.unit_tests.test_replication_consumer_daptor import ReplicationMessageMock


class GenericProcessor(Processor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._count = 0

    def setup(self):
        pass

    def process_change(self, change: Wal2JsonV2Change):
        self._count += 1
        raise NotImplementedError("This method is intended to be mocked")


class FaultyFilter(Filter):
    def setup(self):
        pass

    def filter(self, change: Wal2JsonV2Change) -> Filter.Result:
        if change["this-key-does-not-exists-will-raise-error"] is None:
            return Filter.Result.IGNORE
        return Filter.Result.CONTINUE


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


class TestStop:
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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._handled_errors = []

    @property
    def handled_errors(self):
        return self._handled_errors

    def setup(self):
        pass

    def action(self):
        match self.config_generic.get("action"):
            case None:
                return ErrorHandler.NextAction.NEXT_ERROR_HANDLER
            case "NEXT_ERROR_HANDLER":
                return ErrorHandler.NextAction.NEXT_ERROR_HANDLER
            case "NEXT_MESSAGE":
                return ErrorHandler.NextAction.NEXT_MESSAGE
            case "NEXT_PROCESSOR":
                return ErrorHandler.NextAction.NEXT_PROCESSOR
            case "ABORT":
                return ErrorHandler.NextAction.ABORT
            case "RETRY_PROCESSOR":
                return ErrorHandler.NextAction.RETRY_PROCESSOR
            case "EXCEPTION":
                raise Exception("Exception raised from error handler")
            case "NONE":
                return None
            case _:
                raise NotImplementedError(f"Invalid value for action='{self.config_generic.get('action')}'")

    def handle_error(self, change: Wal2JsonV2Change, exception: Exception) -> ErrorHandler.NextAction:
        assert isinstance(change, (Wal2JsonV2Change, dict)), "handle_error(): 'change' param of invalid type"
        assert isinstance(exception, BaseException), "handle_error(): 'exception' param of invalid type"

        self._handled_errors.append(exception)
        return self.action()


ERR_HANDLER = f"{__name__}.{GenericErrorHandler.__qualname__}"


class TestAbort:
    def test_abort_by_default(self, min_config, monkeypatch):
        monkeypatch.setattr(GenericProcessor, "process_change", process_change_key_error)

        min_config["processors"] = [{"class": GENERIC}]
        config = PopykaConfig.from_dict(min_config)
        processors = [_.instantiate() for _ in config.processors]

        adaptor = ReplicationConsumerToProcessorAdaptor(processors, filters=[])
        repl_message = ReplicationMessageMock.from_dict(VALID_PAYLOAD)

        with pytest.raises(AbortExecutionFromErrorHandlerException):
            adaptor(repl_message)

    def test_abort_aborts(self, min_config, monkeypatch):
        monkeypatch.setattr(GenericProcessor, "process_change", process_change_key_error)

        min_config["processors"] = [{"class": GENERIC, "error_handlers": [{"class": ERR_HANDLER}]}]
        config = PopykaConfig.from_dict(min_config)
        processors = [_.instantiate() for _ in config.processors]

        adaptor = ReplicationConsumerToProcessorAdaptor(processors, filters=[])
        repl_message = ReplicationMessageMock.from_dict(VALID_PAYLOAD)

        with pytest.raises(AbortExecutionFromErrorHandlerException):
            adaptor(repl_message)

        assert len(processors[0].error_handlers[0].handled_errors) == 1
        assert isinstance(processors[0].error_handlers[0].handled_errors[0], KeyError)

    def test_no_error_handler_is_used_after_abort(self, min_config, monkeypatch):
        monkeypatch.setattr(GenericProcessor, "process_change", process_change_key_error)

        min_config["processors"] = [
            {
                "class": GENERIC,
                "error_handlers": [
                    {"class": ERR_HANDLER, "config": {"action": "ABORT"}},
                    {"class": ERR_HANDLER, "config": {"action": "ABORT"}},
                ],
            }
        ]
        config = PopykaConfig.from_dict(min_config)
        processors = [_.instantiate() for _ in config.processors]

        adaptor = ReplicationConsumerToProcessorAdaptor(processors, filters=[])
        repl_message = ReplicationMessageMock.from_dict(VALID_PAYLOAD)

        with pytest.raises(AbortExecutionFromErrorHandlerException):
            adaptor(repl_message)

        assert len(processors[0].error_handlers[0].handled_errors) == 1
        assert isinstance(processors[0].error_handlers[0].handled_errors[0], KeyError)
        assert len(processors[0].error_handlers[1].handled_errors) == 0


class TestNextErrorHandler:
    def test_second_error_handler_is_used(self, min_config, monkeypatch):
        monkeypatch.setattr(GenericProcessor, "process_change", process_change_key_error)

        min_config["processors"] = [
            {
                "class": GENERIC,
                "error_handlers": [
                    {"class": ERR_HANDLER, "config": {"action": "NEXT_ERROR_HANDLER"}},
                    {"class": ERR_HANDLER, "config": {"action": "ABORT"}},
                ],
            }
        ]
        config = PopykaConfig.from_dict(min_config)
        processors = [_.instantiate() for _ in config.processors]

        adaptor = ReplicationConsumerToProcessorAdaptor(processors, filters=[])
        repl_message = ReplicationMessageMock.from_dict(VALID_PAYLOAD)

        with pytest.raises(AbortExecutionFromErrorHandlerException):
            adaptor(repl_message)

        assert len(processors[0].error_handlers[0].handled_errors) == 1
        assert len(processors[0].error_handlers[1].handled_errors) == 1


class TestNextMessage:
    def test(self, min_config, monkeypatch):
        monkeypatch.setattr(GenericProcessor, "process_change", process_change_key_error)

        min_config["processors"] = [
            {
                "class": GENERIC,
                "error_handlers": [
                    {"class": ERR_HANDLER, "config": {"action": "NEXT_MESSAGE"}},
                    {"class": ERR_HANDLER, "config": {"action": "ABORT"}},
                ],
            }
        ]
        config = PopykaConfig.from_dict(min_config)
        processors = [_.instantiate() for _ in config.processors]

        adaptor = ReplicationConsumerToProcessorAdaptor(processors, filters=[])
        repl_message = ReplicationMessageMock.from_dict(VALID_PAYLOAD)

        assert adaptor(repl_message) == ErrorHandler.NextAction.NEXT_MESSAGE

        assert len(processors[0].error_handlers[0].handled_errors) == 1
        assert len(processors[0].error_handlers[1].handled_errors) == 0


class TestRetry:
    def test(self, min_config, monkeypatch):
        monkeypatch.setattr(GenericProcessor, "process_change", process_change_key_error)

        min_config["processors"] = [
            {
                "class": GENERIC,
                "error_handlers": [
                    {"class": ERR_HANDLER, "config": {"action": "RETRY_PROCESSOR"}},
                    {"class": ERR_HANDLER, "config": {"action": "RETRY_PROCESSOR"}},
                    {"class": ERR_HANDLER, "config": {"action": "ABORT"}},
                ],
            }
        ]
        config = PopykaConfig.from_dict(min_config)
        processors = [_.instantiate() for _ in config.processors]

        adaptor = ReplicationConsumerToProcessorAdaptor(processors, filters=[])
        repl_message = ReplicationMessageMock.from_dict(VALID_PAYLOAD)

        with pytest.raises(AbortExecutionFromErrorHandlerException):
            adaptor(repl_message)

        assert len(processors[0].error_handlers[0].handled_errors) == 5
        assert len(processors[0].error_handlers[1].handled_errors) == 1
        assert len(processors[0].error_handlers[2].handled_errors) == 1


FAULTY_FILTER = f"{__name__}.{FaultyFilter.__qualname__}"


class TestFaultyFilter:
    def test_exception_is_caught(self, min_config, monkeypatch):
        def process_change(_self, *args, **kwargs):
            pass

        monkeypatch.setattr(GenericProcessor, "process_change", process_change)

        assert not min_config["filters"]
        min_config["filters"] = [{"class": FAULTY_FILTER}]
        min_config["processors"] = [{"class": GENERIC}]

        config = PopykaConfig.from_dict(min_config)

        filters = [_.instantiate() for _ in config.filters]
        processors = [_.instantiate() for _ in config.processors]

        adaptor = ReplicationConsumerToProcessorAdaptor(processors, filters=filters)
        repl_message = ReplicationMessageMock.from_dict(VALID_PAYLOAD)

        with pytest.raises(UnhandledFilterException):
            adaptor(repl_message)
