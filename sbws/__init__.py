__version__ = '1.0.3-dev0'

from . import globals  # noqa


class Settings:
    def __init__(self):
        # update this dict from globals (but only for ALL_CAPS settings)
        for setting in dir(globals):
            if setting.isupper():
                setattr(self, setting, getattr(globals, setting))

    def init_http_headers(self, nickname, uuid, tor_version):
        self.HTTP_HEADERS['Tor-Bandwidth-Scanner-Nickname'] = nickname
        self.HTTP_HEADERS['Tor-Bandwidth-Scanner-UUID'] = uuid
        self.HTTP_HEADERS['User-Agent'] += tor_version

settings = Settings()  # noqa
