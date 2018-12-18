from decimal import Decimal
from ..lib.resultdump import ResultDump
from ..lib.resultdump import Result
from ..lib.resultdump import ResultError
from ..lib.relaylist import RelayList
import copy
import time
import logging

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

    def best_priority(self, prioritize_result_error=False):
        """
        Return a generator of a new list of relays ordereded by priority to
        be measured. The relays that were measured farther away in the past,
        get prioritized (lowest priority number, first in the generator).

        The relays that were measured more recently get lower priority (last in
        the generator, higher priority number).

        Optionally, the measurements that failed can be prioritized (be
        measured first).
        However, unstable relays that often fail to be measured, might fail
        again and stable relays will get measured only when their measurements
        become old enough.
        The opposite might be more suitable: give lower priority to the relays
        that are unstable, to don't spend time measuring relays that might fail
        to be measured.

        Since measurements made before than X days ago (too old) are not
        considered, and the initial list of past measurements is only filtered
        when the scanner starts, it's needed to filter here again to discard
        those measurements that are too old.

        """
        fn_tstart = Decimal(time.time())
        relays = set(copy.deepcopy(self.relay_list.relays))
        if not self.measure_authorities:
            relays = relays.difference(set(self.relay_list.authorities))
        rd = self.result_dump
        for relay in relays:
            results = rd.results_for_relay(relay)
            priority = 0
            # The time before which we do not consider results valid anymore
            oldest_allowed = time.time() - self.fresh_seconds
            for result in results:
                assert isinstance(result, Result)
                # Ignore results that are too far in the past
                if result.time < oldest_allowed:
                    continue
                # Calculate freshness as the remaining time until this result
                # is no longer valid
                freshness = result.time - oldest_allowed
                if isinstance(result, ResultError) \
                    and prioritize_result_error is True:
                    # Reduce the freshness for results containing errors so
                    # that they are not de-prioritized as much. This way, we
                    # will come back to them sooner to try again.
                    assert result.freshness_reduction_factor >= 0.0
                    assert result.freshness_reduction_factor <= 1.0
                    log.debug('Cutting freshness for a %s result by %d%% for '
                              '%s', result.type.value,
                              result.freshness_reduction_factor * 100,
                              relay.nickname)
                    freshness *= max(1.0-result.freshness_reduction_factor, 0)
                priority += freshness
            relay.priority = priority
        # Sort the relays by their priority, with the smallest (best) priority
        # relays at the front
        relays = sorted(relays, key=lambda r: r.priority)
        cutoff = max(int(len(relays) * self.fraction_to_return),
                     self.min_to_return)
        fn_tstop = Decimal(time.time())
        fn_tdelta = (fn_tstop - fn_tstart) * 1000
        log.info('Spent %f msecs calculating relay best priority', fn_tdelta)
        # Finally, slowly return the relays to the caller (after removing the
        # priority member we polluted the variable with ...)
        for relay in relays[0:cutoff]:
            log.debug('Returning next relay %s with priority %f',
                      relay.nickname, relay.priority)
            del(relay.priority)
            yield relay
