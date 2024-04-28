import json
import logging
import os

import psycopg2.extras

from popyka.api import ErrorHandler, Filter, Processor, Wal2JsonV2Change
from popyka.errors import (
    AbortExecutionFromErrorHandlerException,
    ConfigError,
    PopykaException,
    StopServer,
    UnhandledErrorHandlerException,
    UnhandledFilterException,
)
from popyka.logging import LazyToStr


class ReplicationConsumerToProcessorAdaptor:
    """Psycopg2 replication consumer that runs configured PoPyKa Processors on the received changes"""

    logger = logging.getLogger(f"{__name__}.ReplicationConsumerToProcessorAdaptor")

    def __init__(self, processors: list[Processor], filters: list[Filter]):
        self._processors = processors
        self._filters = filters

        max_attempts_env = os.environ.get("POPYKA_MAX_PROCESSING_ATTEMPTS", "50")
        try:
            self._max_attempts = int(max_attempts_env)
            if self._max_attempts <= 0:
                raise ValueError("POPYKA_MAX_PROCESSING_ATTEMPTS needs to be > 0")
        except ValueError as err:
            raise ConfigError(f"Invalid value for env 'POPYKA_MAX_PROCESSING_ATTEMPTS': {max_attempts_env}") from err

        default_retries_env = os.environ.get("POPYKA_DEFAULT_RETRIES", "5")
        try:
            self._default_retries = int(default_retries_env)
            if self._default_retries <= 0:
                raise ValueError("POPYKA_DEFAULT_RETRIES needs to be > 0")
        except ValueError as err:
            raise ConfigError(f"Invalid value for env 'POPYKA_DEFAULT_RETRIES': {default_retries_env}") from err

    def _handle_payload(self, payload: bytes) -> ErrorHandler.NextAction | Filter.Result | None:
        """
        :return: `None` if the message was processed. Otherwise, `ErrorHandler.NextAction` or `Filter.Result`.
        """
        change = Wal2JsonV2Change(json.loads(payload))

        for a_filter in self._filters:
            try:
                match a_filter.filter(change):
                    case Filter.Result.IGNORE:
                        self.logger.debug("Ignoring change for change: %s", LazyToStr(change))
                        return Filter.Result.IGNORE
                    case Filter.Result.PROCESS:
                        break  # stop filtering
                    case Filter.Result.CONTINUE:
                        continue  # continue, evaluate other filters
                    case _:
                        raise PopykaException("Filter.filter() returned invalid value")
            except BaseException:
                # self.logger.exception("Caught exception while evaluating filter: %s", a_filter)
                raise UnhandledFilterException(f"Error handling filter {a_filter}")

        for processor in self._processors:
            self.logger.debug("Starting processing with processor: %s", processor)

            result: ErrorHandler.NextAction = self._handle_processor(processor, change)
            match result:
                case ErrorHandler.NextAction.NEXT_PROCESSOR:
                    continue
                case ErrorHandler.NextAction.NEXT_MESSAGE:
                    return result
                case _:
                    raise PopykaException(f"Unexpected result - type={type(result)} - value={result}")

        return None

    def _handle_processor(self, processor: Processor, change: Wal2JsonV2Change) -> ErrorHandler.NextAction:
        """
        Runs a single processor, handling any error and retrying, with a limit in the maximum number of attempts.

        :returns: NextAction.NEXT_PROCESSOR or NextAction.NEXT_MESSAGE

        :raises: popyka.errors.StopServer
        :raises: popyka.errors.PopykaException
        :raises: popyka.errors.AbortExecutionException
        """

        for _ in range(self._max_attempts):
            try:
                processor.process_change(change)
                return ErrorHandler.NextAction.NEXT_PROCESSOR

            except StopServer:
                raise

            except BaseException as err:
                self.logger.exception("Handling exception from processor: %s", processor)
                result: ErrorHandler.NextAction = self._handle_error(processor, change, err)
                match result:
                    case ErrorHandler.NextAction.ABORT:
                        raise AbortExecutionFromErrorHandlerException()
                    case ErrorHandler.NextAction.NEXT_PROCESSOR:
                        return result
                    case ErrorHandler.NextAction.NEXT_MESSAGE:
                        return result

                    case ErrorHandler.NextAction.RETRY_PROCESSOR:
                        continue

                    case ErrorHandler.NextAction.NEXT_ERROR_HANDLER:  # This shouldn't happen!
                        raise PopykaException("Unexpected result: NextAction.NEXT_ERROR_HANDLER")

                    case _:
                        raise PopykaException(f"Unexpected result - type={type(result)} - value={result}")

        raise PopykaException(f"Aborting processing after {self._max_attempts} attempts")

    def _handle_error(
        self, processor: Processor, change: Wal2JsonV2Change, exception: BaseException
    ) -> ErrorHandler.NextAction:
        """Guarantee to return a valid value of ErrorHandler.NextAction"""

        if not processor.error_handlers:
            # When there are no error handlers, the default behavior is to abort
            return ErrorHandler.NextAction.ABORT

        try:
            for err_handler in processor.error_handlers:
                result = err_handler.handle_error(change, exception)
                if not isinstance(result, ErrorHandler.NextAction):
                    raise PopykaException(
                        f"Error handler {err_handler} returned an invalid value. "
                        f"type={type(result)} - value={result}"
                    )

                if result == ErrorHandler.NextAction.ABORT:
                    self.logger.debug("NextAction.ABORT")
                    return result

                elif result == ErrorHandler.NextAction.NEXT_ERROR_HANDLER:
                    self.logger.debug("NextAction.NEXT_ERROR_HANDLER")
                    continue

                elif result == ErrorHandler.NextAction.NEXT_PROCESSOR:
                    self.logger.debug("NextAction.NEXT_PROCESSOR")
                    return result

                elif result == ErrorHandler.NextAction.RETRY_PROCESSOR:
                    change.incr_retry_count()
                    if change.retry_count >= self._default_retries:
                        self.logger.debug("NextAction.RETRY_PROCESSOR ignored (retry_count=%s)", change.retry_count)
                        continue  # Enough retries, let's continue with next error handler
                    else:
                        self.logger.debug("NextAction.RETRY_PROCESSOR")
                        return result

                elif result == ErrorHandler.NextAction.NEXT_MESSAGE:
                    self.logger.debug("NextAction.NEXT_MESSAGE")
                    return result

                else:
                    raise PopykaException(f"Unexpected value for NextAction - type={type(result)} - value={result}")

        except PopykaException:
            raise

        except:  # noqa: E722
            raise UnhandledErrorHandlerException("Error handling failed")

        # When there are no more error handlers to run, let's abort
        return ErrorHandler.NextAction.ABORT

    def __call__(self, msg: psycopg2.extras.ReplicationMessage) -> ErrorHandler.NextAction | Filter.Result | None:
        self.logger.debug("ReplicationConsumerToProcessorAdaptor: received payload: %s", msg)

        # Handle the payload
        result = self._handle_payload(msg.payload)

        # Flush after every message is successfully processed
        self.logger.debug("send_feedback() flush_lsn=%s", msg.data_start)
        try:
            # TODO: does it makes any sense to retry this? Maybe depending on the type of error? Exponential backoff?
            msg.cursor.send_feedback(flush_lsn=msg.data_start)
        except:  # noqa: E722
            raise PopykaException("cursor.send_feedback() failed")

        return result
