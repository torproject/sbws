import logging
import random
import time
from threading import RLock
import requests
from urllib.parse import urlparse
from stem.control import EventType
import sbws.util.stem as stem_utils

log = logging.getLogger(__name__)


def connect_to_destination_over_circuit(dest, circ_id, session, cont, max_dl):
    '''
    Connect to **dest* over the given **circ_id** using the given Requests
    **session**. Make sure everything seems in order. Return True and a
    dictionary of helpful information if we connected and everything looks
    fine.  Otherwise return False and a string stating what the issue is.

    :param dest Destination: the place to which we should connect
    :param circ_id str: the circuit we should connect over
    :param session Session: the Requests library session object to use to make
        the connection.
    :param cont Controller: them Stem library controller controlling Tor
    :returns: True and a dictionary if everything is in order and measurements
        should commence.  False and an error string otherwise.
    '''
    assert isinstance(dest, Destination)
    error_prefix = 'When sending HTTP HEAD to {}, '.format(dest.url)
    with stem_utils.stream_building_lock:
        listener = stem_utils.attach_stream_to_circuit_listener(cont, circ_id)
        stem_utils.add_event_listener(cont, listener, EventType.STREAM)
        try:
            # TODO:
            # - What other exceptions can this throw?
            # - Add timeout
            head = session.head(dest.url)
        except requests.exceptions.ConnectionError as e:
            return False, 'Could not connect to {} over circ {} {}: {}'.format(
                dest.url, circ_id, stem_utils.circuit_str(cont, circ_id), e)
        stem_utils.remove_event_listener(cont, listener)
    if head.status_code != requests.codes.ok:
        return False, error_prefix + 'we expected HTTP code '\
            '{} not {}'.format(requests.codes.ok, head.status_code)
    if 'content-length' not in head.headers:
        return False, error_prefix + 'we except the header Content-Length '\
                'to exist in the response'
    content_length = int(head.headers['content-length'])
    if max_dl > content_length:
        return False, error_prefix + 'our maximum configured download size '\
            'is {} but the content is only {}'.format(max_dl, content_length)
    log.debug('Connected to %s over circuit %s', dest.url, circ_id)
    return True, {'content_length': content_length}


class Destination:
    def __init__(self, url, default_path, max_dl):
        u = urlparse(url)
        # these things should have been verified in verify_config
        assert u.scheme in ['http', 'https']
        assert u.netloc
        if not u.path:
            assert default_path[0] == '/'
            u = urlparse('{}://{}{}{}{}{}'.format(
                *u[0:2], default_path, *u[2:]))
        self._url = u
        self._max_dl = max_dl

    def is_usable(self, circ_id, session, cont):
        ''' Use **connect_to_destination_over_circuit** to determine if this
        destination is usable and return what it returns. Just a small wrapper.
        '''
        return connect_to_destination_over_circuit(
            self, circ_id, session, cont, self._max_dl)

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
    def from_config(conf_section, default_path, max_dl):
        assert 'url' in conf_section
        url = conf_section['url']
        return Destination(url, default_path, max_dl)


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
        session = requests.Session()
        usable_dests = []
        for dest in self._all_dests:
            possible_exits = self._rl.exits_can_exit_to(
                dest.hostname, dest.port)
            # Keep the fastest 10% of exits, or 3, whichever is larger
            num_keep = int(max(3, len(possible_exits) * 0.1))
            possible_exits = sorted(
                possible_exits, key=lambda e: e.bandwidth, reverse=True)
            exits = possible_exits[0:num_keep]
            # Try three times to build a circuit to test this destination
            circ_id = None
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
            is_usable, data = dest.is_usable(circ_id, session, cont)
            if not is_usable:
                log.warning(data)
                continue
            assert is_usable
            log.debug('%s seems usable so we will keep it', dest.url)
            usable_dests.append(dest)
            self._cb.close_circuit(circ_id)
        self._usable_dests = usable_dests
        self._last_usability_test = time.time()
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
                conf[dest_sec], default_path,
                conf.getint('scanner', 'max_download_size')))
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
