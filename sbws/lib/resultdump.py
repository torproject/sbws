import os
import json
import time
import logging
from glob import glob
from threading import Thread
from threading import RLock
from queue import Queue
from queue import Empty
from datetime import datetime
from datetime import timedelta
from enum import Enum
from sbws.globals import RESULT_VERSION, fail_hard
from sbws.util.filelock import DirectoryLock
from sbws.util.json import CustomEncoder, CustomDecoder
from sbws.lib.relaylist import Relay
from .. import settings

log = logging.getLogger(__name__)


def merge_result_dicts(d1, d2):
    '''
    Given two dictionaries that contain Result data, merge them.  Result
    dictionaries have keys of relay fingerprints and values of lists of results
    for those relays.
    '''
    for key in d2:
        if key not in d1:
            d1[key] = []
        d1[key].extend(d2[key])
    return d1


def load_result_file(fname, success_only=False):
    ''' Reads in all lines from the given file, and parses them into Result
    structures (or subclasses of Result). Optionally only keeps ResultSuccess.
    Returns all kept Results as a result dictionary. This function does not
    care about the age of the results '''
    assert os.path.isfile(fname)
    d = {}
    num_total = 0
    num_ignored = 0
    with DirectoryLock(os.path.dirname(fname)):
        with open(fname, 'rt') as fd:
            for line in fd:
                num_total += 1
                try:
                    r = Result.from_dict(
                        json.loads(line.strip(), cls=CustomDecoder)
                    )
                except json.decoder.JSONDecodeError:
                    log.warning('Could not decode result %s', line.strip())
                    r = None
                if r is None:
                    num_ignored += 1
                    continue
                if success_only and isinstance(r, ResultError):
                    continue
                fp = r.fingerprint
                if fp not in d:
                    d[fp] = []
                d[fp].append(r)
    num_kept = sum([len(d[fp]) for fp in d])
    log.debug('Keeping %d/%d read lines from %s', num_kept, num_total, fname)
    if num_ignored > 0:
        log.warning('Had to ignore %d results due to not knowing how to '
                    'parse them.', num_ignored)
    return d


def trim_results(fresh_days, result_dict):
    ''' Given a result dictionary, remove all Results that are no longer valid
    and return the new dictionary '''
    assert isinstance(fresh_days, int)
    assert isinstance(result_dict, dict)
    data_period = fresh_days * 24*60*60
    oldest_allowed = time.time() - data_period
    out_results = {}
    for fp in result_dict:
        for result in result_dict[fp]:
            if result.time >= oldest_allowed:
                if fp not in out_results:
                    out_results[fp] = []
                out_results[fp].append(result)
    num_in = sum([len(result_dict[fp]) for fp in result_dict])
    num_out = sum([len(out_results[fp]) for fp in out_results])
    log.debug('Keeping %d/%d results after removing old ones', num_out, num_in)
    return out_results


def trim_results_ip_changed(result_dict, on_changed_ipv4=False,
                            on_changed_ipv6=False):
    """When there are results for the same relay with different IPs,
    create a new results' dictionary without that relay's results using an
    older IP.

    :param dict result_dict: a dictionary of results
    :param bool on_changed_ipv4: whether to trim the results when a relay's
        IPv4 changes
    :param bool on_changed_ipv6: whether to trim the results when a relay's
        IPv6 changes
    :returns: a new results dictionary
    """
    assert isinstance(result_dict, dict)
    new_results_dict = {}
    if on_changed_ipv4 is True:
        for fp in result_dict.keys():
            results = result_dict[fp]
            # find if the results for a relay have more than one ipv4
            # address
            ipv4s = set([result.address for result in results])
            if len(ipv4s) > 1:
                # keep only the results for the last ip used
                # probably we should not just discard all the results for
                # a relay that change address
                ordered_results = sorted(results, key=lambda r: r.time)
                latest_address = ordered_results[-1].address
                last_ip_results = [result for result in results
                                   if result.address == latest_address]
                new_results_dict[fp] = last_ip_results
            else:
                new_results_dict[fp] = results
        return new_results_dict
    if on_changed_ipv6 is True:
        log.warning("Reseting bandwidth results when IPv6 changes,"
                    " is not yet implemented.")
    return result_dict


def load_recent_results_in_datadir(fresh_days, datadir, success_only=False,
                                   on_changed_ipv4=False,
                                   on_changed_ipv6=False):
    ''' Given a data directory, read all results files in it that could have
    results in them that are still valid. Trim them, and return the valid
    Results as a list '''
    assert isinstance(fresh_days, int)
    assert os.path.isdir(datadir)
    # Inform the results are being loaded, since it takes some seconds.
    log.info("Reading and processing previous measurements.")
    results = {}
    today = datetime.utcfromtimestamp(time.time())
    data_period = fresh_days + 2
    oldest_day = today - timedelta(days=data_period)
    working_day = oldest_day
    while working_day <= today:
        # Cannot use ** and recursive=True in glob() because we support 3.4
        # So instead settle on finding files in the datadir and one
        # subdirectory below the datadir that fit the form of YYYY-MM-DD*.txt
        d = working_day.date()
        patterns = [os.path.join(datadir, '{}*.txt'.format(d)),
                    os.path.join(datadir, '*', '{}*.txt'.format(d))]
        for pattern in patterns:
            for fname in glob(pattern):
                new_results = load_result_file(
                    fname, success_only=success_only)
                results = merge_result_dicts(results, new_results)
        working_day += timedelta(days=1)
    results = trim_results(fresh_days, results)
    # in time fresh days is possible that a relay changed ip,
    # if that's the case, keep only the results for the last ip
    results = trim_results_ip_changed(results, on_changed_ipv4,
                                      on_changed_ipv6)
    num_res = sum([len(results[fp]) for fp in results])
    if num_res == 0:
        log.warning('Results files that are valid not found. '
                    'Probably sbws scanner was not run first or '
                    'it ran more than %d days ago or '
                    'it was using a different datadir than %s.', data_period,
                    datadir)
    return results


def write_result_to_datadir(result, datadir):
    ''' Can be called from any thread '''
    assert isinstance(result, Result)
    assert os.path.isdir(datadir)
    dt = datetime.utcfromtimestamp(result.time)
    ext = '.txt'
    result_fname = os.path.join(
        datadir, '{}{}'.format(dt.date(), ext))
    with DirectoryLock(datadir):
        log.debug('Writing a result to %s', result_fname)
        with open(result_fname, 'at') as fd:
            fd.write('{}\n'.format(str(result)))


class _StrEnum(str, Enum):
    pass


class _ResultType(_StrEnum):
    Success = 'success'
    Error = 'error-misc'
    ErrorCircuit = 'error-circ'
    ErrorStream = 'error-stream'
    ErrorAuth = 'error-auth'
    # When it can not be found a second relay suitable to measure a relay.
    # It is used in ``ResultErrorSecondRelay``.
    ErrorSecondRelay = 'error-second-relay'
    # When there is not a working destination Web Server.
    # It is used in ``ResultErrorDestionation``.
    ErrorDestination = 'error-destination'


class Result:
    """A bandwidth measurement for a relay.

    It re-implements :class:`~sbws.lib.relaylist.Relay` as a inner class.
    """

    class Relay:
        """A Tor relay.

        It re-implements :class:`~sbws.lib.relaylist.Relay`
        with the attributes needed.

        .. note:: in a future refactor it would be simpler if a ``Relay`` has
           measurements and a measurement has a relay,
           instead of every measurement re-implementing ``Relay``.
        """
        def __init__(self, fingerprint, nickname, address, master_key_ed25519,
                     average_bandwidth=None, burst_bandwidth=None,
                     observed_bandwidth=None, consensus_bandwidth=None,
                     consensus_bandwidth_is_unmeasured=None,
                     # Counters to be stored by relay and not per measurement,
                     # since the measurements might fail.
                     relay_in_recent_consensus=None,
                     relay_recent_measurement_attempt=None,
                     relay_recent_priority_list=None):
            """
            Initializes a ``Result.Relay``.

            .. note:: in a future refactor the attributes should be dinamic
               to easy adding/removing them.
               They are shared by  :class:`~sbws.lib.relaylist.Relay` and
               :class:`~sbws.lib.v3bwfile.V3BWLine` and there should not be
               repeated in every class.
            """
            self.fingerprint = fingerprint
            self.nickname = nickname
            self.address = address
            self.master_key_ed25519 = master_key_ed25519
            self.average_bandwidth = average_bandwidth
            self.burst_bandwidth = burst_bandwidth
            self.observed_bandwidth = observed_bandwidth
            self.consensus_bandwidth = consensus_bandwidth
            self.consensus_bandwidth_is_unmeasured = \
                consensus_bandwidth_is_unmeasured
            self.relay_in_recent_consensus = \
                relay_in_recent_consensus
            self.relay_recent_measurement_attempt = \
                relay_recent_measurement_attempt
            self.relay_recent_priority_list = \
                relay_recent_priority_list

    def __init__(self, relay, circ, dest_url, scanner_nick, t=None):
        """
        Initilizes the measurement and the relay with all the relay attributes.
        """
        self._relay = Result.Relay(
            relay.fingerprint, relay.nickname,
            relay.address, relay.master_key_ed25519,
            relay.average_bandwidth,
            relay.burst_bandwidth,
            relay.observed_bandwidth,
            relay.consensus_bandwidth,
            relay.consensus_bandwidth_is_unmeasured,
            relay.relay_in_recent_consensus,
            relay.relay_recent_measurement_attempt,
            relay.relay_recent_priority_list
            )
        self._circ = circ
        self._dest_url = dest_url
        self._scanner = scanner_nick
        self._time = time.time() if t is None else t

    @property
    def type(self):
        raise NotImplementedError()

    @property
    def relay_average_bandwidth(self):
        return self._relay.average_bandwidth

    @property
    def relay_burst_bandwidth(self):
        return self._relay.burst_bandwidth

    @property
    def relay_observed_bandwidth(self):
        return self._relay.observed_bandwidth

    @property
    def consensus_bandwidth(self):
        return self._relay.consensus_bandwidth

    @property
    def consensus_bandwidth_is_unmeasured(self):
        return self._relay.consensus_bandwidth_is_unmeasured

    @property
    def fingerprint(self):
        return self._relay.fingerprint

    @property
    def nickname(self):
        return self._relay.nickname

    @property
    def address(self):
        return self._relay.address

    @property
    def master_key_ed25519(self):
        return self._relay.master_key_ed25519

    @property
    def relay_in_recent_consensus(self):
        """Number of times the relay was in a consensus."""
        return self._relay.relay_in_recent_consensus

    @property
    def relay_recent_measurement_attempt(self):
        """Returns the relay recent measurements attemps.

        It is initialized in :class:`~sbws.lib.relaylist.Relay` and
        incremented in :func:`~sbws.core.scanner.main_loop`.
        """
        return self._relay.relay_recent_measurement_attempt

    @property
    def relay_recent_priority_list(self):
        """Returns the relay recent "prioritization"s to be measured.

        It is initialized in :class:`~sbws.lib.relaylist.Relay` and
        incremented in :func:`~sbws.core.scanner.main_loop`.
        """
        return self._relay.relay_recent_priority_list

    @property
    def circ(self):
        return self._circ

    @property
    def dest_url(self):
        return self._dest_url

    @property
    def scanner(self):
        return self._scanner

    @property
    def time(self):
        return self._time

    @property
    def version(self):
        return RESULT_VERSION

    def to_dict(self):
        return {
            'fingerprint': self.fingerprint,
            'nickname': self.nickname,
            'address': self.address,
            'master_key_ed25519': self.master_key_ed25519,
            'circ': self.circ,
            'dest_url': self.dest_url,
            'time': self.time,
            'type': self.type,
            'scanner': self.scanner,
            'version': self.version,
            'relay_in_recent_consensus':
                self.relay_in_recent_consensus,
            'relay_recent_measurement_attempt':
                self.relay_recent_measurement_attempt,
            'relay_recent_priority_list':
                self.relay_recent_priority_list,
        }

    @staticmethod
    def from_dict(d):
        """
        Returns a :class:`~sbws.lib.resultdump.Result` subclass from a
        dictionary.

        Returns None if the ``version`` attribute is not
        :const:`~sbws.globals.RESULT_VERSION`

        It raises ``NotImplementedError`` when the dictionary ``type`` can not
        be parsed.

        .. note:: in a future refactor, the conversions to/from
           object-dictionary will be simpler using ``setattr`` and ``__dict__``

           ``version`` is not being used and should be removed.
        """
        assert 'version' in d
        if d['version'] != RESULT_VERSION:
            return None
        assert 'type' in d
        if d['type'] == _ResultType.Success.value:
            return ResultSuccess.from_dict(d)
        elif d['type'] == _ResultType.Error.value:
            return ResultError.from_dict(d)
        elif d['type'] == _ResultType.ErrorCircuit.value:
            return ResultErrorCircuit.from_dict(d)
        elif d['type'] == _ResultType.ErrorStream.value:
            return ResultErrorStream.from_dict(d)
        elif d['type'] == _ResultType.ErrorAuth.value:
            return ResultErrorAuth.from_dict(d)
        elif d['type'] == _ResultType.ErrorSecondRelay.value:
            return ResultErrorSecondRelay.from_dict(d)
        elif d['type'] == _ResultType.ErrorDestination.value:
            return ResultErrorDestination.from_dict(d)
        else:
            raise NotImplementedError(
                'Unknown result type {}'.format(d['type']))

    def __str__(self):
        return json.dumps(self.to_dict(), cls=CustomEncoder)


class ResultError(Result):
    def __init__(self, *a, msg=None, **kw):
        super().__init__(*a, **kw)
        self._msg = msg

    @property
    def type(self):
        return _ResultType.Error

    @property
    def freshness_reduction_factor(self):
        '''
        When the RelayPrioritizer encounters this Result, how much should it
        adjust its freshness? (See RelayPrioritizer.best_priority() for more
        information about "freshness")

        A higher factor makes the freshness lower (making the Result seem
        older). A lower freshness leads to the relay having better priority,
        and better priority means it will be measured again sooner.

        The value 0.5 was chosen somewhat arbitrarily, but a few weeks of live
        network testing verifies that sbws is still able to perform useful
        measurements in a reasonable amount of time.
        '''
        return 0.5

    @property
    def msg(self):
        return self._msg

    @staticmethod
    def from_dict(d):
        assert isinstance(d, dict)
        return ResultError(
            Result.Relay(
                d['fingerprint'], d['nickname'], d['address'],
                d['master_key_ed25519'],
                relay_in_recent_consensus=  # noqa
                    d.get('relay_in_recent_consensus', None),  # noqa
                relay_recent_measurement_attempt=  # noqa
                    d.get('relay_recent_measurement_attempt', None),  # noqa
                relay_recent_priority_list=  # noqa
                    d.get('relay_recent_priority_list', None),  # noqa
                ),
            d['circ'], d['dest_url'], d['scanner'],
            msg=d['msg'], t=d['time'])

    def to_dict(self):
        d = super().to_dict()
        d.update({
            'msg': self.msg,
        })
        return d


class ResultErrorCircuit(ResultError):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)

    @property
    def type(self):
        return _ResultType.ErrorCircuit

    @property
    def freshness_reduction_factor(self):
        '''
        There are a few instances when it isn't the relay's fault that the
        circuit failed to get built. Maybe someday we'll try detecting whose
        fault it most likely was and subclassing ResultErrorCircuit. But for
        now we don't. So reduce the freshness slightly more than ResultError
        does by default so priority isn't hurt quite as much.

        A (hopefully very very rare) example of when a circuit would fail to
        get built is when the sbws client machine suddenly loses Internet
        access.
        '''
        return 0.6

    @staticmethod
    def from_dict(d):
        assert isinstance(d, dict)
        return ResultErrorCircuit(
            Result.Relay(
                d['fingerprint'], d['nickname'], d['address'],
                d['master_key_ed25519'],
                relay_in_recent_consensus=  # noqa
                    d.get('relay_in_recent_consensus', None),  # noqa
                relay_recent_measurement_attempt=  # noqa
                    d.get('relay_recent_measurement_attempt', None),  # noqa
                relay_recent_priority_list=  # noqa
                    d.get('relay_recent_priority_list', None),  # noqa
                ),
            d['circ'], d['dest_url'], d['scanner'],
            msg=d['msg'], t=d['time'])

    def to_dict(self):
        d = super().to_dict()
        return d


class ResultErrorStream(ResultError):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)

    @property
    def type(self):
        return _ResultType.ErrorStream

    @staticmethod
    def from_dict(d):
        assert isinstance(d, dict)
        return ResultErrorStream(
            Result.Relay(
                d['fingerprint'], d['nickname'], d['address'],
                d['master_key_ed25519'],
                relay_in_recent_consensus=  # noqa
                    d.get('relay_in_recent_consensus', None),  # noqa
                relay_recent_measurement_attempt=  # noqa
                    d.get('relay_recent_measurement_attempt', None),  # noqa
                relay_recent_priority_list=  # noqa
                    d.get('relay_recent_priority_list', None),  # noqa
                ),
            d['circ'], d['dest_url'], d['scanner'],
            msg=d['msg'], t=d['time'])

    def to_dict(self):
        d = super().to_dict()
        return d


class ResultErrorSecondRelay(ResultError):
    """
    Error when it could not be found a second relay suitable to measure
    a relay.

    A second suitable relay is a relay that:
    - Has at least equal bandwidth as the relay to measure.
    - If the relay to measure is not an exit,
      the second relay is an exit without `bad` flag and can exit to port 443.
    - If the relay to measure is an exit, the second relay is not an exit.

    It is instanciated in :func:`~sbws.core.scanner.measure_relay`.

    .. note:: this duplicates code and add more tech-debt,
       since it's the same as the other
       :class:`~sbws.lib.resultdump.ResultError` classes except for the
       ``type``.
       In a future refactor, there should be only one ``ResultError`` class
       and assign the type in the ``scanner`` module.
    """
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)

    @property
    def type(self):
        return _ResultType.ErrorSecondRelay

    @staticmethod
    def from_dict(d):
        assert isinstance(d, dict)
        return ResultErrorSecondRelay(
            Result.Relay(
                d['fingerprint'], d['nickname'], d['address'],
                d['master_key_ed25519'],
                relay_in_recent_consensus=  # noqa
                    d.get('relay_in_recent_consensus', None),  # noqa
                relay_recent_measurement_attempt=  # noqa
                    d.get('relay_recent_measurement_attempt', None),  # noqa
                relay_recent_priority_list=  # noqa
                    d.get('relay_recent_priority_list', None),  # noqa
                ),
            d['circ'], d['dest_url'], d['scanner'],
            msg=d['msg'], t=d['time'])

    def to_dict(self):
        d = super().to_dict()
        return d


class ResultErrorDestination(ResultError):
    """
    Error when there is not a working destination Web Server.

    It is instanciated in :func:`~sbws.core.scanner.measure_relay`.

    .. note:: this duplicates code and add more tech-debt,
       since it's the same as the other
       :class:`~sbws.lib.resultdump.ResultError` classes except for the
       ``type``.
       In a future refactor, there should be only one ``ResultError`` class
       and assign the type in the ``scanner`` module.
    """
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)

    @property
    def type(self):
        return _ResultType.ErrorSecondRelay

    @staticmethod
    def from_dict(d):
        assert isinstance(d, dict)
        return ResultErrorSecondRelay(
            Result.Relay(
                d['fingerprint'], d['nickname'], d['address'],
                d['master_key_ed25519'],
                d['circ'], d['dest_url'], d['scanner'],
                relay_in_recent_consensus=  # noqa
                    d.get('relay_in_recent_consensus', None),  # noqa
                relay_recent_measurement_attempt=  # noqa
                    d.get('relay_recent_measurement_attempt', None),  # noqa
                relay_recent_priority_list=  # noqa
                    d.get('relay_recent_priority_list', None),  # noqa
                ),
            msg=d['msg'], t=d['time'])

    def to_dict(self):
        d = super().to_dict()
        return d


class ResultErrorAuth(ResultError):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)

    @property
    def type(self):
        return _ResultType.ErrorAuth

    @property
    def freshness_reduction_factor(self):
        '''
        Override the default ResultError.freshness_reduction_factor because a
        ResultErrorAuth is most likely not the measured relay's fault, so we
        shouldn't hurt its priority as much. A higher reduction factor means a
        Result's effective freshness is reduced more, which makes the relay's
        priority better.

        The value 0.9 was chosen somewhat arbitrarily.
        '''
        return 0.9

    @staticmethod
    def from_dict(d):
        assert isinstance(d, dict)
        return ResultErrorAuth(
            Result.Relay(
                d['fingerprint'], d['nickname'], d['address'],
                d['master_key_ed25519'],
                relay_in_recent_consensus=  # noqa
                    d.get('relay_in_recent_consensus', None),  # noqa
                relay_recent_measurement_attempt=  # noqa
                    d.get('relay_recent_measurement_attempt', None),  # noqa
                relay_recent_priority_list=  # noqa
                    d.get('relay_recent_priority_list', None),  # noqa
                ),
            d['circ'], d['dest_url'], d['scanner'],
            msg=d['msg'], t=d['time'])

    def to_dict(self):
        d = super().to_dict()
        return d


class ResultSuccess(Result):
    def __init__(self, rtts, downloads, *a, **kw):
        super().__init__(*a, **kw)
        self._rtts = rtts
        self._downloads = downloads

    @property
    def type(self):
        return _ResultType.Success

    @property
    def rtts(self):
        return self._rtts

    @property
    def downloads(self):
        return self._downloads

    @staticmethod
    def from_dict(d):
        assert isinstance(d, dict)
        return ResultSuccess(
            d['rtts'] or [], d['downloads'],
            Result.Relay(
                d['fingerprint'], d['nickname'], d['address'],
                d['master_key_ed25519'], d['relay_average_bandwidth'],
                d.get('relay_burst_bandwidth'), d['relay_observed_bandwidth'],
                d.get('consensus_bandwidth'),
                d.get('consensus_bandwidth_is_unmeasured'),
                relay_in_recent_consensus=  # noqa
                    d.get('relay_in_recent_consensus', None),  # noqa
                relay_recent_measurement_attempt=  # noqa
                    d.get('relay_recent_measurement_attempt', None),  # noqa
                relay_recent_priority_list=  # noqa
                    d.get('relay_recent_priority_list', None),  # noqa
                ),
            d['circ'], d['dest_url'], d['scanner'],
            t=d['time'])

    def to_dict(self):
        d = super().to_dict()
        d.update({
            'rtts': self.rtts,
            'downloads': self.downloads,
            'relay_average_bandwidth': self.relay_average_bandwidth,
            'relay_burst_bandwidth': self.relay_burst_bandwidth,
            'relay_observed_bandwidth': self.relay_observed_bandwidth,
            'consensus_bandwidth': self.consensus_bandwidth,
            'consensus_bandwidth_is_unmeasured':
                self.consensus_bandwidth_is_unmeasured,
        })
        return d


class ResultDump:
    ''' Runs the enter() method in a new thread and collects new Results on its
    queue. Writes them to daily result files in the data directory '''
    def __init__(self, args, conf):
        assert os.path.isdir(conf.getpath('paths', 'datadir'))
        self.conf = conf
        self.fresh_days = conf.getint('general', 'data_period')
        self.datadir = conf.getpath('paths', 'datadir')
        self.data = {}
        self.data_lock = RLock()
        self.thread = Thread(target=self.enter)
        self.queue = Queue()
        try:
            self.thread.start()
        except RuntimeError as e:
            fail_hard(e)

    def store_result(self, result):
        ''' Call from ResultDump thread '''
        assert isinstance(result, Result)
        with self.data_lock:
            fp = result.fingerprint
            if fp not in self.data:
                self.data[fp] = []
            self.data[fp].append(result)
            self.data = trim_results(self.fresh_days, self.data)
            # Not calling trim_results_ip_changed here to do not remove
            # the results for a relay that has changed address.
            # It will be called when loading the results to generate a v3bw
            # file.

    def handle_result(self, result):
        ''' Call from ResultDump thread. If we are shutting down, ignores
        ResultError* types '''
        assert isinstance(result, Result)
        fp = result.fingerprint
        nick = result.nickname
        if isinstance(result, ResultError) and settings.end_event.is_set():
            log.debug('Ignoring %s for %s %s because we are shutting down',
                      type(result).__name__, nick, fp)
            return
        self.store_result(result)
        write_result_to_datadir(result, self.datadir)
        if result.type == "success":
            msg = "Success measuring {} ({}) via circuit {} and " \
                  "destination {}".format(
                    result.fingerprint, result.nickname, result.circ,
                    result.dest_url)
        else:
            msg = "Error measuring {} ({}) via circuit {} and " \
                  "destination {}: {}".format(
                    result.fingerprint, result.nickname, result.circ,
                    result.dest_url, result.msg)
        # When the error is that there are not more functional destinations.
        if result.type == "error-destination":
            log.info("Shutting down because there are not functional "
                     "destinations.")
            # NOTE: Because this is executed in a thread, stop_threads can not
            # be call from here, it has to be call from the main thread.
            # Instead set the singleton end event, that will call stop_threads
            # from the main process.
            settings.end_event.set()
        log.info(msg)

    def enter(self):
        """Main loop for the ResultDump thread.

        When there are results in the queue, queue.get will get them until
        there are not anymore or timeout happen.

        For every result it gets, it process it and store in the filesystem,
        which takes ~1 millisecond and will not trigger the timeout.
        It can then store in the filesystem ~1000 results per second.

        I does not accept any other data type than Results or list of Results,
        therefore is not possible to put big data types in the queue.

        If there are not any results in the queue, it waits 1 second and checks
        again.

        """
        with self.data_lock:
            self.data = load_recent_results_in_datadir(
                self.fresh_days, self.datadir)
        while not (settings.end_event.is_set() and self.queue.empty()):
            try:
                event = self.queue.get(timeout=1)
            except Empty:
                continue
            data = event
            if data is None:
                log.debug('Got None in ResultDump')
                continue
            elif isinstance(data, list):
                for r in data:
                    assert isinstance(r, Result)
                    self.handle_result(r)
            elif isinstance(data, Result):
                self.handle_result(data)
            else:
                log.warning('The only thing we should ever receive in the '
                            'result thread is a Result or list of Results. '
                            'Ignoring %s', type(data))

    def results_for_relay(self, relay):
        assert isinstance(relay, Relay)
        fp = relay.fingerprint
        with self.data_lock:
            if fp not in self.data:
                return []
            return self.data[fp]
