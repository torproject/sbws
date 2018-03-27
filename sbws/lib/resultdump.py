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
from stem.descriptor.router_status_entry import RouterStatusEntryV3


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

    def __init__(self, relay, circ, server_host, rtts, download_results,
                 t=None):
        self._relay = Result.Relay(relay.fingerprint, relay.nickname,
                                   relay.address)
        self._circ = circ
        self._server_host = server_host
        self._downloads = download_results
        self._rtts = rtts
        self._time = time.time() if t is None else t

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
    def rtts(self):
        return self._rtts

    @property
    def time(self):
        return self._time

    @property
    def downloads(self):
        return self._downloads

    @property
    def server_host(self):
        return self._server_host

    @staticmethod
    def from_dict(d):
        assert isinstance(d, dict)
        return Result(
            Result.Relay(d['fingerprint'], d['nickname'], d['address']),
            d['circ'], d['server_host'], d['rtts'], d['downloads'], d['time'])

    def __str__(self):
        return json.dumps({
            'fingerprint': self.fingerprint,
            'nickname': self.nickname,
            'time': self.time,
            'downloads': self.downloads,
            'address': self.address,
            'circ': self.circ,
            'rtts': self.rtts,
            'server_host': self.server_host
        })


class ResultDump:
    ''' Runs the enter() method in a new thread and collects new Results on its
    queue. Writes them to daily result files in the data directory '''
    def __init__(self, args, log, end_event):
        assert os.path.isdir(args.result_directory)
        assert isinstance(end_event, Event)
        self.log = log
        self.fresh_days = args.data_period
        self.datadir = args.result_directory
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
            self.data = self._trim_stale_data(self.data)

    def write_result(self, result):
        ''' Call from ResultDump thread '''
        assert isinstance(result, Result)
        dt = date.fromtimestamp(result.time)
        ext = '.txt'
        result_fname = os.path.join(
            self.datadir, '{}{}'.format(dt, ext))
        with open(result_fname, 'at') as fd:
            fd.write('{}\n'.format(str(result)))

    def _load_data_file(self, fname):
        ''' Call from ResultDump thread '''
        assert os.path.isfile(fname)
        d = []
        with open(fname, 'rt') as fd:
            for line in fd:
                d.append(Result.from_dict(json.loads(line.strip())))
        self.log.info('Read', len(d), 'lines from', fname)
        return d

    def _trim_stale_data(self, in_data):
        ''' Call from ResultDump thread '''
        data = []
        oldest_allowed = time.time() - (self.fresh_days*24*60*60)
        for result in in_data:
            if result.time >= oldest_allowed:
                data.append(result)
        self.log.debug('Keeping {}/{} data'.format(len(data), len(in_data)))
        return data

    def _load_fresh_data(self):
        ''' Call from ResultDump thread '''
        data = []
        today = date.fromtimestamp(time.time())
        # Load a day extra. It's okay: we'll trim it afterward. This should
        # conver any timezone weirdness.
        oldest_day = today - timedelta(days=self.fresh_days+1)
        working_day = oldest_day
        while working_day <= today:
            pattern = os.path.join(
                self.datadir, '**', '{}*'.format(working_day))
            for fname in glob(pattern, recursive=True):
                data.extend(self._load_data_file(fname))
            working_day += timedelta(days=1)
        data = self._trim_stale_data(data)
        return data

    def enter(self):
        ''' Main loop for the ResultDump thread '''
        with self.data_lock:
            self.data = self._load_fresh_data()
        while not (self.end_event.is_set() and self.queue.empty()):
            try:
                event = self.queue.get(timeout=1)
            except Empty:
                continue
            result = event
            if result is None:
                continue
            elif not isinstance(result, Result):
                self.log.warn('failure', result, type(result))
                continue
            fp = result.fingerprint
            nick = result.nickname
            self.store_result(result)
            self.write_result(result)
            self.log.debug(fp, nick, 'finished measurement')

    def results_for_relay(self, relay):
        assert isinstance(relay, RouterStatusEntryV3)
        with self.data_lock:
            return [r for r in self.data if r.fingerprint == relay.fingerprint]
