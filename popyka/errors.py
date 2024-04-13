class PopykaException(Exception):
    pass


class StopServer(PopykaException):
    pass


class ConfigError(PopykaException):
    pass
