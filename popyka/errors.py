class PopykaException(Exception):
    pass


class StopServer(PopykaException):
    pass


class ConfigError(PopykaException):
    pass


class AbortExecutionException(PopykaException):
    """Used by error handlers to signal the immediate exit (with error) of Popyka"""

    # FIXME: rename to `AbortByErrorHandler` to make intention clear and avoid confusion with other reasons for aborting


class UnhandledErrorHandlerException(PopykaException):
    """An error handled failed to handle an error"""
