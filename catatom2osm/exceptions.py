"""Exceptions definitions."""


class CatException(Exception):
    """Base class for application exceptions."""

    def __init__(self, message=None):
        super(CatException, self).__init__(message)


class CatValueError(CatException):
    """Value error exception."""

    def __init__(self, message=None):
        super(CatValueError, self).__init__(message)


class CatIOError(CatException):
    """Input/output error exception."""

    def __init__(self, message=None):
        super(CatIOError, self).__init__(message)


class CatConfigError(CatException):
    """Can't read config."""

    def __init__(self, message=None):
        super(CatConfigError, self).__init__(message)
