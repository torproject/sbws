import collections
import datetime
import logging
import random
import requests
from urllib.parse import urlparse
from stem.control import EventType

from sbws.globals import DESTINATION_VERIFY_CERTIFICATE
import sbws.util.stem as stem_utils
from ..globals import (
    MAX_NUM_DESTINATION_FAILURES,
    DELTA_SECONDS_RETRY_DESTINATION,
    MAX_SECONDS_RETRY_DESTINATION,
    NUM_DESTINATION_ATTEMPTS_STORED,
    FACTOR_INCREMENT_DESTINATION_RETRY
    )
from sbws import settings


log = logging.getLogger(__name__)


# Duplicate some code from DestinationList.from_config,
# it should be refactored.
def parse_destinations_countries(conf):
    """Returns the destinations' country as string separated by comma.

    """
    destinations_countries = []
    for key in conf['destinations'].keys():
        # Not a destination key
        if key in ['usability_test_interval']:
            continue
        # The destination is not enabled
        if not conf['destinations'].getboolean(key):
            continue
        destination_section = 'destinations.{}'.format(key)
        destination_country = conf[destination_section].get('country', None)
        destinations_countries.append(destination_country)
    return ','.join(destinations_countries)


def _parse_verify_option(conf_section):
    if 'verify' not in conf_section:
        return DESTINATION_VERIFY_CERTIFICATE
    try:
        verify = conf_section.getboolean('verify')
    except ValueError:
        log.warning(
            'Currently sbws only supports verify=true/false, not a CA bundle '
            'file. We think %s is not a bool, and thus must be a CA bundle '
            'file. This is supposed to be allowed by the Python Requests '
            'library, but pastly couldn\'t get it to work in his afternoon '
            'of testing. So we will allow this, but expect Requests to throw '
            'SSLError exceptions later. Have fun!', conf_section['verify'])
        return conf_section['verify']
    if not verify:
        # disable urllib3 warning: InsecureRequestWarning
        import urllib3
        urllib3.disable_warnings()
    return verify


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
    log.debug("Connecting to destination over circuit.")
    # Do not start if sbws is stopping
    if settings.end_event.is_set():
        return False, "Shutting down."
    error_prefix = 'When sending HTTP HEAD to {}, '.format(dest.url)
    with stem_utils.stream_building_lock:
        listener = stem_utils.attach_stream_to_circuit_listener(cont, circ_id)
        stem_utils.add_event_listener(cont, listener, EventType.STREAM)
        try:
            head = session.head(dest.url, verify=dest.verify)
        except requests.exceptions.RequestException as e:
            dest.add_failure()
            return False, 'Could not connect to {} over circ {} {}: {}'.format(
                dest.url, circ_id, stem_utils.circuit_str(cont, circ_id), e)
        finally:
            stem_utils.remove_event_listener(cont, listener)
    if head.status_code != requests.codes.ok:
        dest.add_failure()
        return False, error_prefix + 'we expected HTTP code '\
            '{} not {}'.format(requests.codes.ok, head.status_code)
    if 'content-length' not in head.headers:
        dest.add_failure()
        return False, error_prefix + 'we expect the header Content-Length '\
            'to exist in the response'
    content_length = int(head.headers['content-length'])
    if max_dl > content_length:
        dest.add_failure()
        return False, error_prefix + 'our maximum configured download size '\
            'is {} but the content is only {}'.format(max_dl, content_length)
    log.debug('Connected to %s over circuit %s', dest.url, circ_id)
    # Any failure connecting to the destination will call add_failure,
    # It can not be set at the start, to be able to know whether it is
    # failing consecutive times.
    dest.add_success()
    return True, {'content_length': content_length}


class Destination:
    """Web server from which data is downloaded to measure bandwidth.
    """
    # NOTE: max_dl and verify should be optional and have defaults
    def __init__(self, url, max_dl, verify,
                 max_num_failures=MAX_NUM_DESTINATION_FAILURES,
                 delta_seconds_retry=DELTA_SECONDS_RETRY_DESTINATION,
                 max_seconds_between_retries=MAX_SECONDS_RETRY_DESTINATION,
                 num_attempts_stored=NUM_DESTINATION_ATTEMPTS_STORED,
                 factor_increment_retry=FACTOR_INCREMENT_DESTINATION_RETRY):
        """Initalizes the Web server from which the data is downloaded.

        :param str url: Web server data URL to download.
        :param int max_dl: Maximum size of the the data to download.
        :param bool verify: Whether to verify or not the TLS certificate.
        :param int max_num_failures: Number of consecutive failures when the
            destination is not considered functional.
        :param int delta_seconds_retry: Delta time to try a destination
            that was not functional.
        :param int num_attempts_stored: Number of attempts to store.
        :param int factor_increment_retry: Factor to increment delta by
            before trying to use a destination again.
        """
        self._max_dl = max_dl
        u = urlparse(url)
        self._url = u
        self._verify = verify

        # Attributes to decide whether a destination is functional or not.
        self._max_num_failures = max_num_failures
        self._num_attempts_stored = num_attempts_stored
        # Default delta time to try a destination that was not functional.
        self._default_delta_seconds_retry = delta_seconds_retry
        self._delta_seconds_retry = delta_seconds_retry
        # A cap on the time to wait between destination retries.
        self._max_seconds_between_retries = max_seconds_between_retries
        # Using a deque (FIFO) to do not grow forever and
        # to do not have to remove old attempts.
        # Store tuples of timestamp and whether the destination succed or not
        # (succed, 1, failed, 0).
        # Initialize it as if it never failed.
        self._attempts = collections.deque([(datetime.datetime.utcnow(), 1), ],
                                           maxlen=self._num_attempts_stored)
        self._factor = factor_increment_retry

    def _last_attempts(self, n=None):
        """Return the last ``n`` attempts the destination was used."""
        # deque does not accept slices,
        # a new deque is returned with the last n items
        # (or less if there were less).
        return collections.deque(self._attempts,
                                 maxlen=(n or self._max_num_failures))

    def _are_last_attempts_failures(self, n=None):
        """
        Return True if the last`` n`` times the destination was used
        and failed.
        """
        # Count the number that there was a failure when used
        n = n if n else self._max_num_failures
        return ([i[1] for i in self._last_attempts(n)].count(0)
                >= self._max_num_failures)

    def _increment_time_to_retry(self, factor=None):
        """
        Increment the time a destination will be tried again by a ``factor``.
        """
        self._delta_seconds_retry *= factor or self._factor
        if self._delta_seconds_retry > self._max_seconds_between_retries:
            self._delta_seconds_retry = self._max_seconds_between_retries
            log.debug("Incremented the time to try destination %s past the "
                      "limit, capping it at %s hours.",
                      self.url, self._delta_seconds_retry / 60 / 60)
        else:
            log.debug("Incremented the time to try destination %s to %s "
                      "hours.", self.url, self._delta_seconds_retry / 60 / 60)

    def _get_last_try_in_seconds_ago(self):
        """
        Return the delta between the last try and now, as positive seconds.
        """
        # Timestamp of the last attempt.
        last_time = self._attempts[-1][0]
        return (datetime.datetime.utcnow() - last_time).total_seconds()

    def _is_last_try_old_enough(self, n=None):
        """
        Return True if the last time it was used it was ``n`` seconds ago.
        """
        # If the last attempt is older than _delta_seconds_retry, try again
        return (self._get_last_try_in_seconds_ago() >
                self._delta_seconds_retry)

    def is_functional(self):
        """Whether connections to a destination are failing or not.

        Return True if:
            - It did not fail more than n (by default 3) consecutive times.
            - The last time the destination was tried
              was x (by default 3h) seconds ago.
        And False otherwise.

        When the destination is tried again after the consecutive failures,
        the time to try again is incremented and resetted as soon as the
        destination does not fail.
        """
        # NOTE: does a destination fail because several threads are using
        # it at the same time?
        # If a destination fails for 1 minute and there're 3 threads, the
        # 3 threads will fail.

        # Failed the last X consecutive times
        if self._are_last_attempts_failures():
            # The log here will appear in all the the queued relays and
            # threads.
            log.debug("The last %s times the destination %s failed. "
                      "It last ran %s seconds ago. "
                      "Disabled for %s seconds.",
                      self._max_num_failures, self.url,
                      self._get_last_try_in_seconds_ago(),
                      self._delta_seconds_retry)
            log.warning("The last %s times a destination failed. "
                        "It last ran %s seconds ago. "
                        "Disabled for %s seconds."
                        "Please, add more destinations or increment the "
                        "number of maximum number of consecutive failures "
                        "in the configuration.",
                        self._max_num_failures,
                        self._get_last_try_in_seconds_ago(),
                        self._delta_seconds_retry)
            # It was not used for a while and the last time it was used
            # was long ago, then try again
            if self._is_last_try_old_enough():
                log.debug("The destination %s was not tried for %s seconds, "
                          "it is going to by tried again.", self.url,
                          self._get_last_try_in_seconds_ago())
                # Set the next time to retry higher, in case this attempt fails
                self._increment_time_to_retry()
                return True
            return False
        # Reset the time to retry to the initial value
        # In case it was incrememented
        self._delta_seconds_retry = self._default_delta_seconds_retry
        return True

    def add_failure(self, dt=None):
        self._attempts.append((dt or datetime.datetime.utcnow(), 0))

    def add_success(self, dt=None):
        self._attempts.append((dt or datetime.datetime.utcnow(), 1))

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
    def from_config(conf_section, max_dl, number_threads):
        assert 'url' in conf_section
        url = conf_section['url']
        verify = _parse_verify_option(conf_section)
        try:
            # Because one a destination fails, all the threads that are using
            # it at that moment will fail too, multiply by the number of
            # threads.
            max_num_failures = (conf_section.getint('max_num_failures')
                                or MAX_NUM_DESTINATION_FAILURES)
        except ValueError:
            # If the operator did not setup the number, set to the default.
            max_num_failures = MAX_NUM_DESTINATION_FAILURES

        max_num_failures *= number_threads
        return Destination(url, max_dl, verify, max_num_failures)


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
        return [d for d in self._all_dests if d.is_functional()]

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
                # Multiply by the number of threads since all the threads will
                # fail at the same time.
                conf.getint('scanner', 'max_download_size'),
                conf.getint('scanner', 'measurement_threads')))
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
        # random.choice raises IndexError with an empty list.
        if self.functional_destinations:
            return self._rng.choice(self.functional_destinations)
        else:
            return None
