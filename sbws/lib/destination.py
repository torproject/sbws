import logging
import random
from urllib.parse import urlparse

log = logging.getLogger(__name__)


class Destination:
    def __init__(self, url):
        u = urlparse(url)
        # these things should have been verified in verify_config
        assert u.scheme in ['http', 'https']
        assert u.netloc
        self._url = u

    @property
    def url(self):
        return self._url.geturl()

    @staticmethod
    def from_config(conf_section):
        assert 'url' in conf_section
        url = conf_section['url']
        return Destination(url)


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
        dests = []
        for key in section.keys():
            if not section.getboolean(key):
                log.debug('%s is disabled; not loading it', key)
                continue
            dest_sec = 'destinations.{}'.format(key)
            assert dest_sec in conf  # validate_config should require this
            log.debug('Loading info for destination %s', key)
            dests.append(Destination.from_config(conf[dest_sec]))
        if len(dests) < 1:
            return None, 'No enabled destinations in config'
        return DestinationList(dests), ''

    def next(self):
        '''
        Returns the next destination that should be used in a measurement
        '''
        random.shuffle(self._all_dests)
        return self._all_dests[0]
