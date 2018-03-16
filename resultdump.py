import os
from threading import Thread
from threading import Event
from queue import Queue
from queue import Empty


class ResultDump:
    def __init__(self, datadir, end_event):
        assert os.path.isdir(datadir)
        assert isinstance(end_event, Event)
        self.datadir = datadir
        self.end_event = end_event
        self.thread = Thread(target=self.enter)
        self.queue = Queue()
        self.thread.start()

    def enter(self):
        while not (self.end_event.is_set() and self.queue.empty()):
            try:
                event = self.queue.get(timeout=1)
            except Empty:
                continue
            nick, result = event
            if result is None:
                print(nick, 'failed')
                continue
            elif not isinstance(result, dict):
                print(nick, 'failure', result, type(result))
                continue
            tamount = result['amount']
            ttime = result['time']
            trate = tamount / ttime
            trate = trate * 8 / 1024 / 1024
            print(nick, '{:.2f} Mbps over {:.1f}s'.format(trate, ttime))
