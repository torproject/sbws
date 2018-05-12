import requests
import sbws.util.stem as stem_utils

def make_session(controller, timeout):
    s = requests.Session()
    socks_info = stem_utils.get_socks_info(controller)
    s.proxies = {
        'http': 'socks5h://{}:{}'.format(*socks_info),
        'https': 'socks5h://{}:{}'.format(*socks_info),
    }
    s.sbws_timeout = timeout
    return s

def get(s, url, **kw):
    return s.get(url, timeout=s.sbws_timeout, **kw)

def head(s, url, **kw):
    return s.head(url, timeout=s.sbws_timeout, **kw)
