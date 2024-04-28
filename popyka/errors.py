class PopykaException(Exception):
    pass


class StopServer(PopykaException):
    pass


class ConfigError(PopykaException):
    pass


class AbortExecutionFromErrorHandlerException(PopykaException):
    """Used by error handlers to signal the immediate exit (with error) of Popyka"""


class UnhandledErrorHandlerException(PopykaException):
    """An error handled failed to handle an error"""


class UnhandledFilterException(PopykaException):
    """A filter raised an execution while being evaluated"""
