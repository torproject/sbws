from threading import Thread
from threading import Event
import time


class PeriodicEvent:
    def __init__(self, func, *a, _run_interval=60,
                 _resolution=0.5, _run_at_end=True, **kw):
        self.func = func
        self.args = a
        self.kwargs = kw
        self.interval = _run_interval
        self.end_event = Event()
        self.resolution = _resolution
        self.run_at_end = _run_at_end
        self.last_run = time.time()
        self.thread = Thread(target=self.enter)
        self.thread.daemon = True
        self.thread.start()

    def runit(self):
        self.func(*self.args, **self.kwargs)

    def enter(self):
        while not self.end_event.wait(self.resolution):
            if time.time() > self.last_run + self.interval:
                self.runit()
                self.last_run = time.time()
        if self.run_at_end:
            self.runit()

    def cancel(self):
        self.end_event.set()
