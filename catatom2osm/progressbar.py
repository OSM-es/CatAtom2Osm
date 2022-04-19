import logging

from tqdm import tqdm

from catatom2osm.config import app_name, show_progress_bars

log = logging.getLogger(app_name)


class FakeTqdm:
    """Fake class to disable progress bars."""

    def __init__(self, *args, **kwargs):
        pass

    def set_description(self, *args, **kwargs):
        pass

    def set_postfix(self, *args, **kwargs):
        pass

    def update(self, *args, **kwargs):
        pass

    def close(self):
        pass


def get(*args, **kwargs):
    if show_progress_bars:
        leave = getattr(log, "app_level", logging.DEBUG) <= logging.DEBUG
        kwargs.update({"leave": leave})
        return tqdm(*args, **kwargs)
    return FakeTqdm()
