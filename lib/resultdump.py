import os
import time
import json
from threading import Thread
from threading import Event
from queue import Queue
from queue import Empty
from datetime import date


class Result:
    ''' A simple struct to pack a measurement result into so that other code
    can be confident it is handling a well-formed result. '''
    def __init__(self, relay, circ, server_host, rtts, duration, amount):
        self._relay = relay
        self._circ = circ
        self._duration = duration
        self._amount = amount
        self._server_host = server_host
        self._rtts = rtts
        self._time = time.time()

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
    def duration(self):
        return self._duration

    @property
    def amount(self):
        return self._amount

    @property
    def server_host(self):
        return self._server_host

    def __str__(self):
        d = {
            'fingerprint': self.fingerprint,
            'nickname': self.nickname,
            'time': self.time,
            'duration': self.duration,
            'amount': self.amount,
            'address': self.address,
            'circ': self.circ,
            'rtts': self.rtts,
            'server_host': self.server_host
        }
        return json.dumps(d)


class ResultDump:
    ''' Runs the enter() method in a new thread and collects new Results on its
    queue. Writes them to daily result files in the data directory '''
    def __init__(self, datadir, end_event):
        assert os.path.isdir(datadir)
        assert isinstance(end_event, Event)
        self.datadir = datadir
        self.end_event = end_event
        self.thread = Thread(target=self.enter)
        self.queue = Queue()
        self.thread.start()

    def write_result(self, result):
        assert isinstance(result, Result)
        dt = date.fromtimestamp(result.time)
        ext = '.txt'
        result_fname = os.path.join(
            self.datadir, '{}{}'.format(dt, ext))
        with open(result_fname, 'at') as fd:
            fd.write('{}\n'.format(str(result)))

    def enter(self):
        while not (self.end_event.is_set() and self.queue.empty()):
            try:
                event = self.queue.get(timeout=1)
            except Empty:
                continue
            result = event
            if result is None:
                continue
            elif not isinstance(result, Result):
                print('failure', result, type(result))
                continue
            fp = result.fingerprint
            nick = result.nickname
            self.write_result(result)
            amount = result.amount
            duration = result.duration
            rate = amount / duration
            rate = rate * 8 / 1024 / 1024
            print(fp, nick, rate, duration)
