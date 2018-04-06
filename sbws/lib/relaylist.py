import sbws.util.stem as stem_utils
from stem import Flag
import time
import random


class RelayList:
    ''' Keeps a list of all relays in the current Tor network and updates it
    transparently in the background. Provides useful interfaces for getting
    only relays of a certain type.
    '''
    REFRESH_INTERVAL = 300  # seconds

    def __init__(self, args, conf, log, controller=None):
        if controller is None:
            c, error_msg = stem_utils.init_controller_with_config(conf)
            assert c, error_msg
        else:
            self._controller = controller
        self.rng = random.SystemRandom()
        self.log = log
        self._refresh()

    @property
    def relays(self):
        if time.time() >= self._last_refresh + self.REFRESH_INTERVAL:
            self._refresh()
        return self._relays

    @property
    def fast(self):
        return self._relays_with_flag(Flag.FAST)

    @property
    def slow(self):
        ''' Returns relays without the Fast flag '''
        return self._relays_without_flag(Flag.FAST)

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
    def authorities(self):
        return self._relays_with_flag(Flag.AUTHORITY)

    @property
    def unmeasured(self):
        ''' SEEMS BROKEN in stem 1.6.0 as it always returns no relays '''
        relays = self.relays
        # return [r for r in relays if r.measured is None]
        return [r for r in relays if r.is_unmeasured]

    @property
    def measured(self):
        ''' SEEMS BROKEN in stem 1.6.0 as it always returns all relays '''
        relays = self.relays
        # return [r for r in relays if r.measured is not None]
        return [r for r in relays if not r.is_unmeasured]

    def random_relay(self):
        relays = self.relays
        return self.rng.choice(relays)

    def _relays_with_flag(self, flag):
        relays = self.relays
        return [r for r in relays if flag in r.flags]

    def _relays_without_flag(self, flag):
        relays = self.relays
        return [r for r in relays if flag not in r.flags]

    def _init_relays(self):
        c = self._controller
        assert stem_utils.is_controller_okay(c)
        return [ns for ns in c.get_network_statuses()]

    def _refresh(self):
        self._relays = self._init_relays()
        self._last_refresh = time.time()
