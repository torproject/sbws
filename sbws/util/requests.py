import requests

from sbws import settings
from sbws.util import stem as stem_utils


class TimedSession(requests.Session):
    """Requests Session that sends timeout in the head and get methods.
    """

    def get(self, url, **kwargs):
        return super().get(url, timeout=getattr(self, "_timeout", None),
                           **kwargs)

    def head(self, url, **kwargs):
        return super().head(url, timeout=getattr(self, "_timeout", None),
                            **kwargs)


def make_session(controller, timeout):
    s = requests.Session()
    socks_info = stem_utils.get_socks_info(controller)
    s.proxies = {
        'http': 'socks5h://{}:{}'.format(*socks_info),
        'https': 'socks5h://{}:{}'.format(*socks_info),
    }
    s.timeout = timeout
    s.headers = settings.HTTP_HEADERS
    return s
