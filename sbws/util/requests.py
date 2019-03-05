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
    """
    Initialize a TimedSession with the timeout, the proxies and the headers.

    """
    s = TimedSession()
    socks_info = stem_utils.get_socks_info(controller)
    # Probably because scanner is stopping.
    if socks_info is None:
        return None
    s.proxies = {
        'http': 'socks5h://{}:{}'.format(*socks_info),
        'https': 'socks5h://{}:{}'.format(*socks_info),
    }
    # ``_timeout`` is not used by request's Session, but it is by TimedSession.
    s._timeout = timeout
    s.headers = settings.HTTP_HEADERS
    return s
