import abc
import logging
from enum import Enum

from popyka.errors import ConfigError
from popyka.logging import LazyToStr


class Wal2JsonV2Change(dict):
    """Represent a change generated by wal2json using format version 2"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._retry_count = 0

    def incr_retry_count(self):
        self._retry_count += 1

    @property
    def retry_count(self):
        return self._retry_count

    # TODO: use class or dataclass, to make API more clear and easier for implementations of `Processors`


class Configurable:
    """Base class for Filters and Processors."""

    def __init__(self, config_generic: dict, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._config_generic = config_generic

    @property
    def config_generic(self):
        return self._config_generic

    def _get_config(self, config: dict, key: str, value_type: type, clean: callable = None):
        try:
            value = config[key]
        except KeyError:
            raise ConfigError(f"Invalid config: '{key}' is required and was not found or is 'null'")

        if not isinstance(value, value_type):
            raise ConfigError(f"Invalid config: '{key}' is expected to be a '{value_type}' but was {type(value)}")

        if clean is not None:
            value = clean(value)

        return value


class Processor(abc.ABC, Configurable):
    """Base class for processors of changes"""

    logger = logging.getLogger(f"{__name__}.Processor")

    def __init__(self, config_generic: dict, error_handlers: list["ErrorHandler"]):
        super().__init__(config_generic=config_generic)
        self.logger.debug("Instantiating processor with config: %s", LazyToStr(config_generic))
        self.__error_handlers: list[ErrorHandler] = error_handlers or []

    @property
    def error_handlers(self):
        return self.__error_handlers

    @abc.abstractmethod
    def setup(self):
        """Setup the component (validate configuration, setup clients, etc.)."""
        raise NotImplementedError()

    @abc.abstractmethod
    def process_change(self, change: Wal2JsonV2Change):
        """Receives a change and process it."""
        raise NotImplementedError()


class Filter(abc.ABC, Configurable):
    """Base class for change filters"""

    class Result(Enum):
        PROCESS = "PROCESS"
        """Immediately accept the change. Other filters are not evaluated."""

        IGNORE = "IGNORE"
        """Immediately ignore the change. Other filters are not evaluated."""

        CONTINUE = "CONTINUE"
        """Don't decide. Other filters will evaluate this change."""

    logger = logging.getLogger(f"{__name__}.Filter")

    def __init__(self, config_generic: dict):
        super().__init__(config_generic=config_generic)
        self.logger.debug("Instantiating filter with config: %s", LazyToStr(config_generic))

    @abc.abstractmethod
    def setup(self):
        """Setup the component (validate configuration, setup clients, etc.)."""
        raise NotImplementedError()

    @abc.abstractmethod
    def filter(self, change: Wal2JsonV2Change) -> "Filter.Result":
        """
        Receives a change and returns a `Result`:

        * `PROCESS`: the change is "accepted", any other filters are not evaluated.
        * `IGNORE`: the change is "ignored", any other filters are not evaluated.
        * `CONTINUE`: there's no decision regarding this change, other filters WILL be evaluated.
        """
        raise NotImplementedError()


class ErrorHandler(abc.ABC, Configurable):
    """Base class for error handlers"""

    class NextAction(Enum):
        NEXT_ERROR_HANDLER = "NEXT_ERROR_HANDLER"
        NEXT_PROCESSOR = "NEXT_PROCESSOR"
        NEXT_MESSAGE = "NEXT_MESSAGE"
        RETRY_PROCESSOR = "RETRY_PROCESSOR"
        ABORT = "ABORT"

    logger = logging.getLogger(f"{__name__}.ErrorHandler")

    def __init__(self, config_generic: dict):
        super().__init__(config_generic=config_generic)
        self.logger.debug("Instantiating error handler with config: %s", LazyToStr(config_generic))

    @abc.abstractmethod
    def setup(self):
        """Setup the component (validate configuration, setup clients, etc.)."""
        raise NotImplementedError()

    @abc.abstractmethod
    def handle_error(self, change: Wal2JsonV2Change, exception: Exception) -> NextAction:
        raise NotImplementedError()
