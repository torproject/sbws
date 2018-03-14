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
            print('RESULT', event)
