"""Exceptions definitions."""


class CatException(Exception):
    """Base class for application exceptions."""

    def __init__(self, message=None):
        super().__init__(message)


class CatValueError(CatException):
    """Value error exception."""

    def __init__(self, message=None):
        super().__init__(message)


class CatIOError(CatException):
    """Input/output error exception."""

    def __init__(self, message=None):
        super().__init__(message)
