from decimal import Decimal
from ..lib.resultdump import ResultDump
from ..lib.resultdump import Result
from ..lib.resultdump import ResultError
from ..lib.relaylist import RelayList
from sbws.globals import time_now
import copy
import logging

log = logging.getLogger(__name__)


# We want to at least return the MIN_TO_RETURN best priority relays ...
MIN_TO_RETURN = 50
# But ideally, we return PERCENT_TO_RETURN of the relays because it will be
# larger and we won't have to recalculate priority so much. In a network of
# ~6500 relays and with a ResultDump containing 1 result per relay, the
# best_priority() function takes ~11 seconds to complete on my home desktop.
# Using this parameter allows us to balance between calling best_priority()
# more often (but wasting more CPU), and calling it less often (but taking
# longer to get back to relays with non-successful results).
#
# Alternatively, we could rewrite best_priority() to not suck so much.
PERCENT_TO_RETURN = 0.05  # 5%
# How much we reduce freshness for results that were non-successful. A larger
# penality reduces freshness more, therefore the relay's priority will be
# better, therefore we'll measure it again sooner.
ERROR_PENALTY = 0.5


class RelayPrioritizer:
    def __init__(self, args, conf, relay_list, result_dump):
        assert isinstance(relay_list, RelayList)
        assert isinstance(result_dump, ResultDump)
        self.fresh_seconds = conf.getint('general', 'data_period')*24*60*60
        self.relay_list = relay_list
        self.result_dump = result_dump
        self.measure_authorities = conf.getboolean(
            'client', 'measure_authorities')

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
        fn_tstart = Decimal(time_now())
        if self.measure_authorities:
            relays = copy.deepcopy(self.relay_list.relays)
        else:
            relays = copy.deepcopy(self.relay_list.relays)
            relays = [r for r in relays
                      if r not in self.relay_list.authorities]
        rd = self.result_dump
        for relay in relays:
            results = rd.results_for_relay(relay)
            priority = 0
            # The time before which we do not consider results valid anymore
            oldest_allowed = time_now() - self.fresh_seconds
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
                    log.debug('Cutting freshness for a %s result for %s',
                              result.type.value, relay.nickname)
                    freshness *= (1 - ERROR_PENALTY)
                priority += freshness
            relay.priority = priority
        # Sort the relays by their priority, with the smallest (best) priority
        # relays at the front
        relays = sorted(relays, key=lambda r: r.priority)
        cutoff = max(int(len(relays) * PERCENT_TO_RETURN), MIN_TO_RETURN)
        fn_tstop = Decimal(time_now())
        fn_tdelta = (fn_tstop - fn_tstart) * 1000
        log.info('Spent %f msecs calculating relay best priority', fn_tdelta)
        # Finally, slowly return the relays to the caller (after removing the
        # priority member we polluted the variable with ...)
        for relay in relays[0:cutoff]:
            log.debug('Returning next relay %s with priority %f',
                      relay.nickname, relay.priority)
            del(relay.priority)
            yield relay
