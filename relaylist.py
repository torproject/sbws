import util.stem as stem_utils
from stem import Flag
import time
import random


class RelayList:
    REFRESH_INTERVAL = 300  # seconds

    def __init__(self):
        # self.refresh_event = PeriodicEvent(
        #     self.refresh, _run_interval=self.REFRESH_INTERVAL,
        #     _run_at_end=False)
        self._controller = stem_utils.init_controller()
        self._refresh()

    @property
    def relays(self):
        if time.time() >= self._last_refresh + self.REFRESH_INTERVAL:
            self._refresh()
        return self._relays

    @property
    def exits(self):
        return self._relays_with_flag(Flag.EXIT)

    @property
    def guards(self):
        return self._relays_with_flag(Flag.GUARD)

    @property
    def hsdirs(self):
        return self._relays_with_flag(Flag.HSDIR)

    @property
    def unmeasured(self):
        relays = self.relays
        return [r for r in relays if r.is_unmeasured]

    @property
    def measured(self):
        relays = self.relays
        return [r for r in relays if not r.is_unmeasured]

    def random_relay(self):
        relays = self.relays
        return random.choice(relays)

    def _relays_with_flag(self, flag):
        relays = self.relays
        return [r for r in relays if flag in r.flags]

    def _init_relays(self):
        c = self._controller
        assert stem_utils.is_controller_okay(c)
        return [ns for ns in c.get_network_statuses()]

    def _refresh(self):
        self._relays = self._init_relays()
        self._last_refresh = time.time()
