__version__ = '1.1.0'

import threading  # noqa

from . import globals  # noqa


class Settings:
    """Singleton settings for all the packages.
    This way change settings can be seen by all the packages that import it.

    It lives in ``__init__.py`` to leave open the possibility of having a
    ``settings.py`` module for user settings.

    .. note:: After refactoring, globals should only have constants.
      Any other variable that needs to be modified when initializing
      should be initialized here.

    """
    def __init__(self):
        # update this dict from globals (but only for ALL_CAPS settings)
        for setting in dir(globals):
            if setting.isupper():
                setattr(self, setting, getattr(globals, setting))
        self.end_event = threading.Event()

    def init_http_headers(self, nickname, uuid, tor_version):
        self.HTTP_HEADERS['Tor-Bandwidth-Scanner-Nickname'] = nickname
        self.HTTP_HEADERS['Tor-Bandwidth-Scanner-UUID'] = uuid
        self.HTTP_HEADERS['User-Agent'] += tor_version

    def set_end_event(self):
        self.end_event.set()


settings = Settings()  # noqa
