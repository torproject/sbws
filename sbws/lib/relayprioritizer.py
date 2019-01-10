import copy
import logging
import time
from decimal import Decimal

from ..lib.relaylist import RelayList
from ..lib.resultdump import Result, ResultDump, ResultError

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

    def best_priority(self):
        ''' Return a generator containing the best priority relays.

        NOTE: A lower value for priority means better priority. Remember your
        data structures class in university and consider this something like a
        min-priority queue.

        Priority is calculated as the sum of the "freshness" of each
        result for a relay. First we determine <oldest_allowed>, the time at
        which we stop considering results to be valid. From there, a result's
        freshness is determined to be the amount of time between when the
        measurement was made and <oldest_allowed>. Therefore, you should see
        that a measurement made more recently will have a higher freshness.

        We adjust down the freshness for results containing errors. If we
        ignored errors and didn't increase a relay's priority value for them,
        then we'll get stuck trying to measure a few relays that have the best
        priority but are having issues getting measured. If we treated errors
        with equal weight as successful results, then it would take a while to
        get around to giving the relay another chance at a getting a successful
        measurement.
        '''
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
                if isinstance(result, ResultError):
                    # Reduce the freshness for results containing errors so
                    # that they are not de-prioritized as much. This way, we
                    # will come back to them sooner to try again.
                    assert result.freshness_reduction_factor >= 0.0
                    assert result.freshness_reduction_factor <= 1.0
                    # After several days, these would log many relays.
                    # log.debug('Cutting freshness for a %s result by %d%% for'
                    #           ' %s', result.type.value,
                    #           result.freshness_reduction_factor * 100,
                    #           relay.nickname)
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
        log.debug('Spent %f msecs calculating relay best priority', fn_tdelta)
        # Finally, slowly return the relays to the caller (after removing the
        # priority member we polluted the variable with ...)
        for relay in relays[0:cutoff]:
            log.debug('Returning next relay %s with priority %f',
                      relay.nickname, relay.priority)
            del(relay.priority)
            yield relay
