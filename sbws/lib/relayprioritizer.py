from ..lib.resultdump import ResultDump
from ..lib.resultdump import Result
from ..lib.relaylist import RelayList
import time
import copy


class RelayPrioritizer:
    def __init__(self, args, log, relay_list, result_dump):
        assert isinstance(relay_list, RelayList)
        assert isinstance(result_dump, ResultDump)
        self.fresh_seconds = args.data_period*24*60*60
        self.log = log
        self.relay_list = relay_list
        self.result_dump = result_dump

    def best_priority(self):
        ''' Return a short list of the best priority relays '''
        relays = copy.deepcopy(self.relay_list.relays)
        rd = self.result_dump
        for relay in relays:
            results = rd.results_for_relay(relay)
            priority = 0
            oldest_allowed = time.time() - self.fresh_seconds
            for result in results:
                assert isinstance(result, Result)
                if result.time < oldest_allowed:
                    continue
                freshness = result.time - oldest_allowed
                priority += freshness
            relay.priority = priority
        relays = sorted(relays, key=lambda r: r.priority)
        cutoff = max(int(len(relays) * 0.05), 50)
        for relay in relays[0:cutoff]:
            self.log.debug('Returning next relay', relay.nickname,
                           'with priority', relay.priority)
            del(relay.priority)
            yield relay
