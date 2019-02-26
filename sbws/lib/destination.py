import logging
import random
import requests
from urllib.parse import urlparse
from stem.control import EventType
import sbws.util.stem as stem_utils
import sbws.util.requests as requests_utils

from ..globals import MAXIMUM_NUMBER_DESTINATION_FAILURES

log = logging.getLogger(__name__)


def _parse_verify_option(conf_section):
    if 'verify' not in conf_section:
        return True
    try:
        return conf_section.getboolean('verify')
    except ValueError:
        log.warning(
            'Currently sbws only supports verify=true/false, not a CA bundle '
            'file. We think %s is not a bool, and thus must be a CA bundle '
            'file. This is supposed to be allowed by the Python Requests '
            'library, but pastly couldn\'t get it to work in his afternoon '
            'of testing. So we will allow this, but expect Requests to throw '
            'SSLError exceptions later. Have fun!', conf_section['verify'])
        return conf_section['verify']


def connect_to_destination_over_circuit(dest, circ_id, session, cont, max_dl):
    '''
    Connect to **dest* over the given **circ_id** using the given Requests
    **session**. Make sure the destination seems usable. Return True and a
    dictionary of helpful information if we connected and the destination is
    usable.  Otherwise return False and a string stating what the issue is.

    This function has two effects, and which one is the "side effect" depends
    on your goal.

    1. It creates a stream to the destination. It persists in the requests
    library **session** object so future requests use the same stream.
    Therefore, the primary effect of this function could be to open a
    connection to the destination that measurements can be made over the given
    **circ_id**, which makes the usability checks a side effect (yet important
    sanity check).

    2. It determines if a destination is usable. Therefore, the primary effect
    of this function could be to perform the usability checks and return the
    results of those checks, which makes the persistent stream a side effect
    that we don't care about.

    As of the time of writing, you'll find that sbws/core/scanner.py uses this
    function in order to obtain that stream over which to perform measurements.
    You will also find in sbws/lib/destination.py (this file) this function
    being used to determine if a Destination is usable. The first relies on the
    persistent stream side effect, the second ignores it (and in fact throws it
    away when it closes the circuit).

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
            head = requests_utils.head(session, dest.url, verify=dest.verify)
        except (requests.exceptions.ConnectionError,
                requests.exceptions.ReadTimeout) as e:
            dest.set_failure()
            return False, 'Could not connect to {} over circ {} {}: {}'.format(
                dest.url, circ_id, stem_utils.circuit_str(cont, circ_id), e)
        finally:
            stem_utils.remove_event_listener(cont, listener)
    if head.status_code != requests.codes.ok:
        dest.set_failure()
        return False, error_prefix + 'we expected HTTP code '\
            '{} not {}'.format(requests.codes.ok, head.status_code)
    if 'content-length' not in head.headers:
        dest.set_failure()
        return False, error_prefix + 'we except the header Content-Length '\
            'to exist in the response'
    content_length = int(head.headers['content-length'])
    if max_dl > content_length:
        dest.set_failure()
        return False, error_prefix + 'our maximum configured download size '\
            'is {} but the content is only {}'.format(max_dl, content_length)
    log.debug('Connected to %s over circuit %s', dest.url, circ_id)
    # Any failure connecting to the destination will call set_failure,
    # which will set `failed` to True and count consecutives failures.
    # It can not be set at the start, to be able to know if it failed a
    # a previous time, which is checked by set_failure.
    # Future improvement: store a list or fixed size dequeue of timestamps
    # when it fails.
    dest.failed = False
    return True, {'content_length': content_length}


class Destination:
    def __init__(self, url, max_dl, verify):
        self._max_dl = max_dl
        u = urlparse(url)
        # these things should have been verified in verify_config
        assert u.scheme in ['http', 'https']
        assert u.netloc
        self._url = u
        self._verify = verify
        # Flag to record whether this destination failed in the last
        # measurement.
        # Failures can happen if:
        # - an HTTPS request can not be made over Tor
        # (which might be the relays fault, not the destination being
        # unreachable)
        # - the destination does not support HTTP Range requests.
        self.failed = False
        self.consecutive_failures = 0

    @property
    def is_functional(self):
        """
        Returns True if there has not been a number consecutive measurements.
        Otherwise warn about it and return False.

        """
        if self.consecutive_failures > MAXIMUM_NUMBER_DESTINATION_FAILURES:
            log.warning("Destination %s is not functional. Please check that "
                        "it is correct.", self._url)
            return False
        return True

    def set_failure(self):
        """Set failed to True and increase the number of consecutive failures.
        Only if it also failed in the previous measuremnt.

        """
        # if it failed in the last measurement
        if self.failed:
            self.consecutive_failures += 1
        self.failed = True

    @property
    def url(self):
        return self._url.geturl()

    @property
    def verify(self):
        return self._verify

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
    def from_config(conf_section, max_dl):
        assert 'url' in conf_section
        url = conf_section['url']
        verify = _parse_verify_option(conf_section)
        return Destination(url, max_dl, verify)


class DestinationList:
    def __init__(self, conf, dests, circuit_builder, relay_list, controller):
        assert len(dests) > 0
        for dest in dests:
            assert isinstance(dest, Destination)
        self._rng = random.SystemRandom()
        self._cont = controller
        self._cb = circuit_builder
        self._rl = relay_list
        self._all_dests = dests

    @property
    def functional_destinations(self):
        return [d for d in self._all_dests if d.is_functional]

    @staticmethod
    def from_config(conf, circuit_builder, relay_list, controller):
        assert 'destinations' in conf
        section = conf['destinations']
        dests = []
        for key in section.keys():
            if key in ['usability_test_interval']:
                continue
            if not section.getboolean(key):
                log.debug('%s is disabled; not loading it', key)
                continue
            dest_sec = 'destinations.{}'.format(key)
            assert dest_sec in conf  # validate_config should require this
            log.debug('Loading info for destination %s', key)
            dests.append(Destination.from_config(
                conf[dest_sec],
                conf.getint('scanner', 'max_download_size')))
        if len(dests) < 1:
            msg = 'No enabled destinations in config. Please see '\
                'docs/source/man_sbws.ini.rst" or "man 5 sbws.ini" ' \
                'for help adding and enabling destinations.'
            return None, msg
        return DestinationList(conf, dests, circuit_builder, relay_list,
                               controller), ''

    def next(self):
        '''
        Returns the next destination that should be used in a measurement
        '''
        # Do not perform usability tests since a destination is already proven
        # usable or not in every measurement, and it should depend on a X
        # number of failures.
        # This removes the need for an extra lock for every measurement.
        # Do not change the order of the destinations, just return a
        # destination.
        return self._rng.choice(self.functional_destinations)
