import requests

from sbws import settings
import sbws.util.stem as stem_utils


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
