from decimal import Decimal
from ..lib.resultdump import ResultDump
from ..lib.resultdump import ResultError
from ..lib.relaylist import RelayList
import copy
import time
import logging

from ..globals import MAX_RECENT_PRIORITY_RELAY_COUNT
from ..util import state, timestamps

log = logging.getLogger(__name__)


class RelayPrioritizer:
    def __init__(self, args, conf, relay_list, result_dump):
        assert isinstance(relay_list, RelayList)
        assert isinstance(result_dump, ResultDump)
        self.fresh_seconds = conf.getint('general', 'data_period')*24*60*60
        self.relay_list = relay_list
        self.result_dump = result_dump
        self.measure_authorities = conf.getboolean(
            'relayprioritizer', 'measure_authorities')
        self.min_to_return = conf.getint('relayprioritizer', 'min_relays')
        self.fraction_to_return = conf.getfloat(
            'relayprioritizer', 'fraction_relays')
        self._state = state.State(conf.getpath('paths', 'state_fname'))
        self._recent_priority_list = timestamps.DateTimeSeq(
            [], 120, self._state, "recent_priority_list"
        )
        self._recent_priority_relay = timestamps.DateTimeIntSeq(
            [],  MAX_RECENT_PRIORITY_RELAY_COUNT, self._state,
            "recent_priority_relay"
        )

    def increment_recent_priority_list(self):
        """
        Increment the number of times that
        :meth:`~sbws.lib.relayprioritizer.RelayPrioritizer.best_priority`
        has been run.
        """
        # NOTE: blocking, writes to file!
        self._recent_priority_list.update()

    @property
    def recent_priority_list_count(self):
        return len(self._recent_priority_list)

    def increment_recent_priority_relay(self, relays_count):
        """
        Increment the number of relays that have been "prioritized" to be
        measured in a
        :meth:`~sbws.lib.relayprioritizer.RelayPrioritizer.best_priority`.
        """
        # NOTE: blocking, writes to file!
        self._recent_priority_relay.update(number=relays_count)

    @property
    def recent_priority_relay_count(self):
        return len(self._recent_priority_relay)

    def best_priority(self, prioritize_result_error=False,
                      return_fraction=True):
        """Yields a new ordered list of relays to be measured next.

        The relays that were measured farther away in the past,
        get prioritized (lowest priority number, first in the list).
        The relays that were measured more recently get lower priority (last in
        the list, higher priority number).

        Optionally, the relays which measurements failed can be prioritized
        (first in the list).
        However, unstable relays that fail often to be measured, might fail
        again and stable relays will get measured only when their measurements
        become old enough.
        The opposite might be more suitable: give lower priority to the relays
        that are unstable, to don't spend time measuring relays that might fail
        to be measured.

        Optionally, return only a fraction of all the relays in the network.
        Since there could be new relays in the network while measuring the
        list of relays returned by this method, this method is run again
        before all the relays in the network are measured.

        .. note::

            In a future refactor, instead of having a static fraction of relays
            to be measured, this method could be call when it's known that
            there're X number of new relays in the network.

        Since measurements made before than X days ago (too old) are not
        considered, and the initial list of past measurements is only filtered
        when the scanner starts, it's needed to filter here again to discard
        those measurements.

        :param bool prioritize_result_error: whether prioritize or not
            measurements that did not succed.
        :param bool return_fraction: whether to return only a fraction of the
            relays seen in the network or return all.
        return: a generator of the new ordered list of relays to measure next.

        """
        fn_tstart = Decimal(time.time())
        relays = set(copy.deepcopy(self.relay_list.relays))
        if not self.measure_authorities:
            relays = relays.difference(set(self.relay_list.authorities))
        # Since there will be new measurements every time this method is called
        # again, update the list of results.
        # In a future refactor with other data structure there should not be
        # needed.
        rd = self.result_dump
        for relay in relays:
            results = rd.results_for_relay(relay)
            priority = 0
            # The time before which we do not consider results valid anymore
            oldest_allowed = time.time() - self.fresh_seconds
            for result in results:
                # Ignore results that are too far in the past
                if result.time < oldest_allowed:
                    continue
                # Calculate freshness as the remaining time until this result
                # is no longer valid
                freshness = result.time - oldest_allowed
                if isinstance(result, ResultError) \
                        and prioritize_result_error is True:
                    # log.debug('Cutting freshness for a %s result by %d%% for'
                    #           ' %s', result.type.value,
                    #           result.freshness_reduction_factor * 100,
                    #           relay.nickname)
                    # result.freshness_reduction_factor are hard-coded values
                    # on how much prioritize measurements that failed
                    # depending on the type of error.
                    # In a future refactor, create these values on an algorithm
                    # or create constants.
                    freshness *= max(1.0-result.freshness_reduction_factor, 0)
                priority += freshness
            # In a future refactor, do not create a new attribute
            relay.priority = priority
        # Sort the relays by their priority, with the smallest (best) priority
        # relays at the front
        relays = sorted(relays, key=lambda r: r.priority)

        fn_tstop = Decimal(time.time())
        fn_tdelta = (fn_tstop - fn_tstart) * 1000
        log.info('Spent %f msecs calculating relay best priority', fn_tdelta)

        # Return a fraction of relays in the network if return_fraction is
        # True, otherwise return all.
        cutoff = max(int(len(relays) * self.fraction_to_return),
                     self.min_to_return)
        upper_limit = cutoff if return_fraction else len(relays)
        # NOTE: these two are blocking, write to disk
        # Increment the number of times ``best_priority`` has been run.
        self.increment_recent_priority_list()
        # Increment the number of relays that have been "prioritized".
        # Because in a small testing network the upper limit could be smaller
        # than the number of relays in the network, use the length of the list.
        self.increment_recent_priority_relay(len(relays[0:upper_limit]))
        for relay in relays[0:upper_limit]:
            log.debug('Returning next relay %s with priority %f',
                      relay.nickname, relay.priority)
            # In a future refactor, a new attribute should not be created,
            # then no need to remove it.
            del(relay.priority)
            # Increment the number of times a realy was "prioritized" to be
            # measured.
            relay.increment_relay_recent_priority_list_count()
            yield relay
