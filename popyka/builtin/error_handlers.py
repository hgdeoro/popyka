from popyka.api import ErrorHandler, Wal2JsonV2Change
from popyka.logging import LazyToStr


class Abort(ErrorHandler):
    """Immediately abort the processing, exit Popyka with error."""

    def setup(self):
        pass

    def handle_error(self, change: Wal2JsonV2Change, exception: Exception):
        self.logger.exception("Aborting: error detected while processing message: %s", LazyToStr(change))
        raise Exception("Aborting")  # FIXME: use custom exception


class ContinueNextProcessor(ErrorHandler):
    """Continue processing: pass the change to the next configured processor."""

    def setup(self):
        pass

    def handle_error(self, change: Wal2JsonV2Change, exception: Exception) -> ErrorHandler.NextAction:
        self.logger.debug("ContinueNextProcessor - change: %s", LazyToStr(change))
        return ErrorHandler.NextAction.NEXT_PROCESSOR


class ContinueNextMessage(ErrorHandler):
    """
    Continue processing: assume the change being handled is done, continue with the next message
    (potentially ignoring next processors).
    """

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
