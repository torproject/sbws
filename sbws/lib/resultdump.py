import os
import time
import json
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


def load_result_file(fname, success_only=False, log_fn=print):
    ''' Reads in all lines from the given file, and parses them into Result
    structures (or subclasses of Result). Optionally only keeps ResultSuccess.
    Returns all kept Results as a list. This function does not care about the
    age of the results '''
    assert os.path.isfile(fname)
    d = []
    num_ignored = 0
    with open(fname, 'rt') as fd:
        for line in fd:
            r = Result.from_dict(json.loads(line.strip()))
            if r is None:
                num_ignored += 1
                continue
            if success_only and isinstance(r, ResultError):
                continue
            d.append(r)
    log_fn('Read', len(d), 'lines from', fname)
    if num_ignored > 0:
        log_fn('Had to ignore', num_ignored,
               'results due to not knowing how to parse them.')
    return d


def trim_results(fresh_days, results, log_fn=print):
    ''' Given a result list, remove all Results that are no longer valid and
    return the new list '''
    assert isinstance(fresh_days, int)
    assert isinstance(results, list)
    data_period = fresh_days * 24*60*60
    oldest_allowed = time.time() - data_period
    out_results = []
    for result in results:
        if result.time >= oldest_allowed:
            out_results.append(result)
    log_fn('Keeping {}/{} results'.format(len(out_results), len(results)))
    return out_results


def load_recent_results_in_datadir(fresh_days, datadir, success_only=False,
                                   log_fn=print):
    ''' Given a data directory, read all results files in it that could have
    results in them that are still valid. Trim them, and return the valid
    Results as a list '''
    assert isinstance(fresh_days, int)
    assert os.path.isdir(datadir)
    results = []
    today = date.fromtimestamp(time.time())
    data_period = fresh_days + 2
    oldest_day = today - timedelta(days=data_period)
    working_day = oldest_day
    while working_day <= today:
        pattern = os.path.join(datadir, '**', '{}*.txt'.format(working_day))
        for fname in glob(pattern, recursive=True):
            results.extend(load_result_file(fname, success_only=success_only,
                                            log_fn=log_fn))
        working_day += timedelta(days=1)
    results = trim_results(fresh_days, results, log_fn=log_fn)
    if len(results) == 0:
        log_fn('Results files that are valid not found. '
               'Probably sbws client was not run first or '
               'it ran more than {} days ago or '
               'it was using a different datadir than {}.'.
               format(data_period, datadir))
    return results


def write_result_to_datadir(result, datadir):
    ''' Can be called from any thread '''
    assert isinstance(result, Result)
    assert os.path.isdir(datadir)
    dt = date.fromtimestamp(result.time)
    ext = '.txt'
    result_fname = os.path.join(
        datadir, '{}{}'.format(dt, ext))
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

    def __init__(self, relay, circ, server_host, client_nick, t=None):
        self._relay = Result.Relay(relay.fingerprint, relay.nickname,
                                   relay.address)
        self._circ = circ
        self._server_host = server_host
        self._scanner = client_nick
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
        try:
            super().__init__(*a, **kw)
        except TypeError as e:
            print('ERROR doing super init:', e)
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
    def __init__(self, args, conf, log, end_event):
        assert os.path.isdir(conf['paths']['datadir'])
        assert isinstance(end_event, Event)
        self.conf = conf
        self.log = log
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
            self.data = trim_results(self.fresh_days, self.data,
                                     self.log.debug)

    def enter(self):
        ''' Main loop for the ResultDump thread '''
        with self.data_lock:
            self.data = load_recent_results_in_datadir(
                self.fresh_days, self.datadir, log_fn=self.log.debug)
        while not (self.end_event.is_set() and self.queue.empty()):
            try:
                event = self.queue.get(timeout=1)
            except Empty:
                continue
            result = event
            if result is None:
                self.log.debug('Got None in ResultDump')
                continue
            elif not isinstance(result, Result):
                self.log.warn('The only thing we should ever receive in the '
                              'result thread is a Result type. Ignoring',
                              type(result))
                continue
            fp = result.fingerprint
            nick = result.nickname
            self.store_result(result)
            write_result_to_datadir(result, self.datadir)
            self.log.debug(fp, nick, 'finished measurement')

    def results_for_relay(self, relay):
        assert isinstance(relay, RouterStatusEntryV3)
        with self.data_lock:
            return [r for r in self.data if r.fingerprint == relay.fingerprint]
