import os
import json
import time
import logging
from glob import glob
from threading import Thread
from threading import Event
from threading import RLock
from queue import Queue
from queue import Empty
from datetime import datetime
from datetime import timedelta
from enum import Enum
from sbws.globals import RESULT_VERSION
from sbws.util.filelock import DirectoryLock
from sbws.lib.relaylist import Relay

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
                r = Result.from_dict(json.loads(line.strip()))
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


def load_recent_results_in_datadir(fresh_days, datadir, success_only=False):
    ''' Given a data directory, read all results files in it that could have
    results in them that are still valid. Trim them, and return the valid
    Results as a list '''
    assert isinstance(fresh_days, int)
    assert os.path.isdir(datadir)
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


class Result:
    ''' A simple struct to pack a measurement result into so that other code
    can be confident it is handling a well-formed result. '''

    class Relay:
        ''' Implements just enough of a stem RouterStatusEntryV3 for this
        Result class to be happy '''
        def __init__(self, fingerprint, nickname, address, master_key_ed25519):
            self.fingerprint = fingerprint
            self.nickname = nickname
            self.address = address
            self.master_key_ed25519 = master_key_ed25519

    def __init__(self, relay, circ, dest_url, scanner_nick, t=None):
        self._relay = Result.Relay(relay.fingerprint, relay.nickname,
                                   relay.address, relay.master_key_ed25519)
        self._circ = circ
        self._dest_url = dest_url
        self._scanner = scanner_nick
        self._time = time.time() if t is None else t

    @property
    def type(self):
        raise NotImplementedError()

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
        }

    @staticmethod
    def from_dict(d):
        ''' Given a dict, returns the Result* subtype that is represented by
        the dict. If we don't know how to parse the dict into a Result and it's
        likely because the programmer forgot to implement something, raises
        NotImplementedError. If we can't parse the dict for some other reason,
        return None. '''
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
        else:
            raise NotImplementedError(
                'Unknown result type {}'.format(d['type']))

    def __str__(self):
        return json.dumps(self.to_dict())


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
                d['master_key_ed25519']),
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
                d['master_key_ed25519']),
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
                d['master_key_ed25519']),
            d['circ'], d['dest_url'], d['scanner'],
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
                d['master_key_ed25519']),
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
            d['rtts'], d['downloads'],
            Result.Relay(
                d['fingerprint'], d['nickname'], d['address'],
                d['master_key_ed25519']),
            d['circ'], d['dest_url'], d['scanner'],
            t=d['time'])

    def to_dict(self):
        d = super().to_dict()
        d.update({
            'rtts': self.rtts,
            'downloads': self.downloads,
        })
        return d


class ResultDump:
    ''' Runs the enter() method in a new thread and collects new Results on its
    queue. Writes them to daily result files in the data directory '''
    def __init__(self, args, conf, end_event):
        assert os.path.isdir(conf['paths']['datadir'])
        assert isinstance(end_event, Event)
        self.conf = conf
        self.fresh_days = conf.getint('general', 'data_period')
        self.datadir = conf['paths']['datadir']
        self.end_event = end_event
        self.data = None
        self.data_lock = RLock()
        self.thread = Thread(target=self.enter)
        self.queue = Queue()
        self.thread.start()

    def store_result(self, result):
        ''' Call from ResultDump thread '''
        assert isinstance(result, Result)
        with self.data_lock:
            fp = result.fingerprint
            if fp not in self.data:
                self.data[fp] = []
            self.data[fp].append(result)
            self.data = trim_results(self.fresh_days, self.data)

    def handle_result(self, result):
        ''' Call from ResultDump thread. If we are shutting down, ignores
        ResultError* types '''
        assert isinstance(result, Result)
        fp = result.fingerprint
        nick = result.nickname
        if isinstance(result, ResultError) and self.end_event.is_set():
            log.debug('Ignoring %s for %s %s because we are shutting down',
                      type(result).__name__, nick, fp)
            return
        self.store_result(result)
        write_result_to_datadir(result, self.datadir)
        log.info('%s %s finished measurement with %s', nick, fp[0:8],
                 type(result).__name__)

    def enter(self):
        ''' Main loop for the ResultDump thread '''
        with self.data_lock:
            self.data = load_recent_results_in_datadir(
                self.fresh_days, self.datadir)
        while not (self.end_event.is_set() and self.queue.empty()):
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
