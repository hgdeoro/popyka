"""
Some thoughts about error handling:

Most flexible implementation:
- configure generic 'error handler'
- add 'context' to message (to be able to implement retries)

With this, we can implement:
- silent, log
- retry (keep track of attempts on `context`)
- dlq
- fatal

The bad: more complex to implement initially
The good: simple API, completely decoupled from Processor

SILENT -> popyka.builtin.error.SilentErrorHandler
LOG    -> popyka.builtin.error.LogErrorHandler
RETRY  -> popyka.builtin.error.RetryErrorHandler
DLQ    -> popyka.builtin.error.DlqErrorHandler
FATAL  -> popyka.builtin.error.FatalErrorHandler

Implementation:
* function after execution?
* wrapper?
* how django handle middlewares?
* maybe pass message + exception to function would be enough?
"""

from popyka.api import ErrorHandler, Wal2JsonV2Change
from popyka.logging import LazyToStr


class Abort(ErrorHandler):
    def setup(self):
        pass

    def handle_error(self, change: Wal2JsonV2Change, exception: Exception):
        self.logger.exception("Aborting: error detected while processing message: %s", LazyToStr(change))
        raise Exception("Aborting")  # FIXME: use custom exception


class ContinueNextProcessor(ErrorHandler):
    def setup(self):
        pass

    def handle_error(self, change: Wal2JsonV2Change, exception: Exception) -> ErrorHandler.NextAction:
        self.logger.debug("ContinueNextProcessor - change: %s", LazyToStr(change))
        return ErrorHandler.NextAction.NEXT_PROCESSOR


class ContinueNextMessage(ErrorHandler):
    def setup(self):
        pass

    def handle_error(self, change: Wal2JsonV2Change, exception: Exception) -> ErrorHandler.NextAction:
        self.logger.debug("ContinueNextMessage - change: %s", LazyToStr(change))
        return ErrorHandler.NextAction.NEXT_MESSAGE


# class LogErrorHandler(ErrorHandler):
#     def setup(self):
#         pass
#
#     def handle_error(self, change: Wal2JsonV2Change, exception: Exception) -> ErrorHandler.NextAction:
#         self.logger.exception("Error detected while processing message: %s", LazyToStr(change))
#         return ErrorHandler.NextAction.NEXT_ERROR_HANDLER
