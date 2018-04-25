from sbws.globals import time_now
import os
import json
import logging
from glob import glob
from threading import Thread
from threading import Event
from threading import RLock
from queue import Queue
from queue import Empty
from datetime import date
from datetime import timedelta
from enum import Enum
from stem.descriptor.router_status_entry import RouterStatusEntryV3
from sbws import res_proto_ver
from sbws.util.filelock import DirectoryLock

log = logging.getLogger(__name__)


def group_results_by_relay(results, starting_dict=None):
    ''' Given a list of Results, sort them by the relay fingerprint that they
    measured and return the resulting dict. Optionally start with the given
    dict instead of an empty one. '''
    data = starting_dict if starting_dict else {}
    assert isinstance(data, dict)
    assert isinstance(results, list)
    for result in results:
        assert isinstance(result, Result)
        fp = result.fingerprint
        if fp not in data:
            data[fp] = []
        data[fp].append(result)
    return data


def load_result_file(fname, success_only=False):
    ''' Reads in all lines from the given file, and parses them into Result
    structures (or subclasses of Result). Optionally only keeps ResultSuccess.
    Returns all kept Results as a list. This function does not care about the
    age of the results '''
    assert os.path.isfile(fname)
    d = []
    num_ignored = 0
    with DirectoryLock(os.path.dirname(fname)):
        with open(fname, 'rt') as fd:
            for line in fd:
                r = Result.from_dict(json.loads(line.strip()))
                if r is None:
                    num_ignored += 1
                    continue
                if success_only and isinstance(r, ResultError):
                    continue
                d.append(r)
    log.debug('Read %d lines from %s', len(d), fname)
    if num_ignored > 0:
        log.warning('Had to ignore %d results due to not knowing how to '
                    'parse them.', num_ignored)
    return d


def trim_results(fresh_days, results):
    ''' Given a result list, remove all Results that are no longer valid and
    return the new list '''
    assert isinstance(fresh_days, int)
    assert isinstance(results, list)
    data_period = fresh_days * 24*60*60
    oldest_allowed = time_now() - data_period
    out_results = []
    for result in results:
        if result.time >= oldest_allowed:
            out_results.append(result)
    log.info('Keeping %d/%d results', len(out_results), len(results))
    return out_results


def load_recent_results_in_datadir(fresh_days, datadir, success_only=False):
    ''' Given a data directory, read all results files in it that could have
    results in them that are still valid. Trim them, and return the valid
    Results as a list '''
    assert isinstance(fresh_days, int)
    assert os.path.isdir(datadir)
    results = []
    today = date.fromtimestamp(time_now())
    data_period = fresh_days + 2
    oldest_day = today - timedelta(days=data_period)
    working_day = oldest_day
    while working_day <= today:
        # Cannot use ** and recursive=True in glob() because we support 3.4
        # So instead settle on finding files in the datadir and one
        # subdirectory below the datadir that fit the form of YYYY-MM-DD*.txt
        patterns = [os.path.join(datadir, '{}*.txt'.format(working_day)),
                    os.path.join(datadir, '*', '{}*.txt'.format(working_day))]
        for pattern in patterns:
            for fname in glob(pattern):
                results.extend(load_result_file(
                    fname, success_only=success_only))
        working_day += timedelta(days=1)
    results = trim_results(fresh_days, results)
    if len(results) == 0:
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
    dt = date.fromtimestamp(result.time)
    ext = '.txt'
    result_fname = os.path.join(
        datadir, '{}{}'.format(dt, ext))
    with DirectoryLock(datadir):
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
        def __init__(self, fingerprint, nickname, address):
            self.fingerprint = fingerprint
            self.nickname = nickname
            self.address = address

    def __init__(self, relay, circ, server_host, scanner_nick, t=None):
        self._relay = Result.Relay(relay.fingerprint, relay.nickname,
                                   relay.address)
        self._circ = circ
        self._server_host = server_host
        self._scanner = scanner_nick
        self._time = time_now() if t is None else t

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
    def circ(self):
        return self._circ

    @property
    def server_host(self):
        return self._server_host

    @property
    def scanner(self):
        return self._scanner

    @property
    def time(self):
        return self._time

    @property
    def version(self):
        return res_proto_ver

    def to_dict(self):
        return {
            'fingerprint': self.fingerprint,
            'nickname': self.nickname,
            'address': self.address,
            'circ': self.circ,
            'server_host': self.server_host,
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
        if d['version'] != res_proto_ver:
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
            Result.Relay(d['fingerprint'], d['nickname'], d['address']),
            d['circ'], d['server_host'], d['scanner'],
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
            Result.Relay(d['fingerprint'], d['nickname'], d['address']),
            d['circ'], d['server_host'], d['scanner'],
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
            Result.Relay(d['fingerprint'], d['nickname'], d['address']),
            d['circ'], d['server_host'], d['scanner'],
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
            Result.Relay(d['fingerprint'], d['nickname'], d['address']),
            d['circ'], d['server_host'], d['scanner'],
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
            Result.Relay(d['fingerprint'], d['nickname'], d['address']),
            d['circ'], d['server_host'], d['scanner'],
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
            self.data.append(result)
            self.data = trim_results(self.fresh_days, self.data)

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
            result = event
            if result is None:
                log.debug('Got None in ResultDump')
                continue
            elif not isinstance(result, Result):
                log.warning('The only thing we should ever receive in the '
                            'result thread is a Result type. Ignoring %s',
                            type(result))
                continue
            fp = result.fingerprint
            nick = result.nickname
            self.store_result(result)
            write_result_to_datadir(result, self.datadir)
            log.debug('%s %s finished measurement', fp, nick)

    def results_for_relay(self, relay):
        assert isinstance(relay, RouterStatusEntryV3)
        with self.data_lock:
            return [r for r in self.data if r.fingerprint == relay.fingerprint]
