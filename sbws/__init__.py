__version__ = '1.0.3-dev0'


import threading

from . import globals  # noqa


class Settings:
    def __init__(self):
        # update this dict from globals (but only for ALL_CAPS settings)
        for setting in dir(globals):
            if setting.isupper():
                setattr(self, setting, getattr(globals, setting))
        self.end_event = threading.Event()

    def set_end_event(self):
        self.end_event.set()

settings = Settings()  # noqa
