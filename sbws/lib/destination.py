import logging
import random
from urllib.parse import urlparse

log = logging.getLogger(__name__)


class Destination:
    def __init__(self, url, default_path):
        u = urlparse(url)
        # these things should have been verified in verify_config
        assert u.scheme in ['http', 'https']
        assert u.netloc
        if not u.path:
            assert default_path[0] == '/'
            u = urlparse('{}://{}{}{}{}{}'.format(
                *u[0:2], default_path, *u[2:]))
        self._url = u

    @property
    def url(self):
        return self._url.geturl()

    @property
    def hostname(self):
        return self._url.hostname

    @property
    def port(self):
        p = self._url.port
        scheme = self._url.scheme
        if p is None:
            if scheme == 'http':
                p = 80
            elif scheme == 'https':
                p = 443
            else:
                assert None, 'Unreachable. Unknown scheme {}'.format(scheme)
        assert p is not None
        return p

    @staticmethod
    def from_config(conf_section, default_path):
        assert 'url' in conf_section
        url = conf_section['url']
        return Destination(url, default_path)


class DestinationList:
    def __init__(self, dests):
        assert len(dests) > 0
        for dest in dests:
            assert isinstance(dest, Destination)
        self._all_dests = dests

    @staticmethod
    def from_config(conf):
        assert 'destinations' in conf
        section = conf['destinations']
        default_path = section['default_path']
        dests = []
        for key in section.keys():
            if key == 'default_path':
                continue
            if not section.getboolean(key):
                log.debug('%s is disabled; not loading it', key)
                continue
            dest_sec = 'destinations.{}'.format(key)
            assert dest_sec in conf  # validate_config should require this
            log.debug('Loading info for destination %s', key)
            dests.append(Destination.from_config(
                conf[dest_sec], default_path))
        if len(dests) < 1:
            return None, 'No enabled destinations in config'
        return DestinationList(dests), ''

    def next(self):
        '''
        Returns the next destination that should be used in a measurement
        '''
        random.shuffle(self._all_dests)
        return self._all_dests[0]
