class PopykaException(Exception):
    pass


class StopServer(PopykaException):
    pass


class ConfigError(PopykaException):
    pass


class AbortExecutionException(Exception):
    """Used by error handlers to signal the immediate exit (with error) of Popyka"""

    pass
