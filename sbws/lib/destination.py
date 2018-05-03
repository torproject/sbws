import logging
import random
import time
from threading import RLock
from urllib.parse import urlparse
import sbws.util.stem as stem_utils

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
    def __init__(self, conf, dests, circuit_builder, relay_list, controller):
        assert len(dests) > 0
        for dest in dests:
            assert isinstance(dest, Destination)
        self._cont = controller
        self._cb = circuit_builder
        self._rl = relay_list
        self._all_dests = dests
        self._usable_dests = []
        self._last_usability_test = 0
        self._usability_test_interval = \
            conf.getint('destinations', 'usability_test_interval')
        self._usability_lock = RLock()

    def _should_perform_usability_test(self):
        return self._last_usability_test + self._usability_test_interval <\
            time.time()

    def _perform_usability_test(self):
        self._usability_lock.acquire()
        log.debug('Perform usability tests')
        cont = self._cont
        for dest in self._all_dests:
            possible_exits = self._rl.exits_can_exit_to(
                dest.hostname, dest.port)
            # Keep the fastest 10% of exits, or 3, whichever is larger
            num_keep = int(max(3, len(possible_exits) * 0.1))
            possible_exits = sorted(
                possible_exits, key=lambda e: e.bandwidth, reverse=True)
            exits = possible_exits[0:num_keep]
            circ_id = None
            # Try three times to build a circuit to test this destination
            for _ in range(0, 3):
                # Pick a random exit
                exit = random.choice(exits)
                circ_id = self._cb.build_circuit([None, exit.fingerprint])
                if circ_id:
                    break
            if not circ_id:
                log.warning('Unable to build a circuit to test the usability '
                            'of %s. Assuming it isn\'t usable.', dest.url)
                continue
            log.debug('Built circ %s %s to test usability of %s', circ_id,
                      stem_utils.circuit_str(cont, circ_id), dest.url)
            self._cb.close_circuit(circ_id)
        self._usability_lock.release()

    @staticmethod
    def from_config(conf, circuit_builder, relay_list, controller):
        assert 'destinations' in conf
        section = conf['destinations']
        default_path = section['default_path']
        dests = []
        for key in section.keys():
            if key in ['default_path', 'usability_test_interval']:
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
        return DestinationList(conf, dests, circuit_builder, relay_list,
                               controller), ''

    def next(self):
        '''
        Returns the next destination that should be used in a measurement
        '''
        with self._usability_lock:
            while True:
                if self._should_perform_usability_test():
                    self._perform_usability_test()
                if len(self._usable_dests) > 0:
                    break
                time_till_next_check = self._usability_test_interval + 0.0001
                log.warning(
                    'Of our %d configured destinations, none are usable at '
                    'this time. Sleeping %f seconds on this blocking call '
                    'to DestinationList.next() until we can check for a '
                    'usable destination again.', len(self._all_dests),
                    time_till_next_check)
                time.sleep(time_till_next_check)

        random.shuffle(self._all_dests)
        return self._all_dests[0]
