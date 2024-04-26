import json
import logging

import psycopg2.extras

from popyka.api import ErrorHandler, Filter, Processor, Wal2JsonV2Change
from popyka.errors import (
    AbortExecutionException,
    PopykaException,
    StopServer,
    UnhandledErrorHandlerException,
)
from popyka.logging import LazyToStr


class ReplicationConsumerToProcessorAdaptor:
    """Psycopg2 replication consumer that runs configured PoPyKa Processors on the received changes"""

    logger = logging.getLogger(f"{__name__}.ReplicationConsumerToProcessorAdaptor")

    def __init__(self, processors: list[Processor], filters: list[Filter]):
        self._processors = processors
        self._filters = filters

    def _handle_payload(self, payload: bytes):
        change = Wal2JsonV2Change(json.loads(payload))

        for a_filter in self._filters:
            match a_filter.filter(change):
                case Filter.Result.IGNORE:
                    self.logger.debug("Ignoring change for change: %s", LazyToStr(change))
                    return  # ignore this message
                case Filter.Result.PROCESS:
                    break  # stop filtering
                case Filter.Result.CONTINUE:
                    continue  # continue, evaluate other filters
                case _:
                    raise PopykaException("Filter.filter() returned invalid value")

        for processor in self._processors:
            self.logger.debug("Starting processing with processor: %s", processor)
            try:
                processor.process_change(change)

            except StopServer:
                raise  # FIXME: do we still need this exception?

            except BaseException as err:
                self.logger.exception("Unhandled exception: processor: %s", processor)
                result: ErrorHandler.NextAction = self._handle_error(processor, change, err)
                if result == ErrorHandler.NextAction.ABORT:
                    raise AbortExecutionException()

                # elif result == ErrorHandler.NextAction.NEXT_ERROR_HANDLER:

                elif result == ErrorHandler.NextAction.NEXT_PROCESSOR:
                    continue

                elif result == ErrorHandler.NextAction.RETRY_PROCESSOR:
                    raise NotImplementedError()

                elif result == ErrorHandler.NextAction.NEXT_MESSAGE:
                    return ErrorHandler.NextAction.NEXT_MESSAGE

                else:
                    raise PopykaException(f"Unexpected result - type={type(result)} - value={result}")

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

    def __call__(self, msg: psycopg2.extras.ReplicationMessage):
        self.logger.debug("ReplicationConsumerToProcessorAdaptor: received payload: %s", msg)

        # Handle the payload
        self._handle_payload(msg.payload)

        # Flush after every message is successfully processed
        self.logger.debug("send_feedback() flush_lsn=%s", msg.data_start)
        msg.cursor.send_feedback(flush_lsn=msg.data_start)
