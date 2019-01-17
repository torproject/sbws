__version__ = '1.0.3-dev0'


import threading  # noqa


class Settings:
    """Singleton settings for all the packages.
    This way change settings can be seen by all the packages that import it.

    It leaves in ``__init__.py`` to leave open the possibility of having a
    ``settings.py`` module for user settings.

    .. note:: After refactoring, globals should only have constants.
      Any other variable that needs to be modified when initializing
      should be initialized here.

    """
    def __init__(self):
        self.end_event = threading.Event()

    def set_end_event(self):
        self.end_event.set()

settings = Settings()  # noqa
