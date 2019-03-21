from sbws.lib.resultdump import ResultDump
from sbws.lib.resultdump import ResultSuccess, ResultErrorCircuit
from sbws.lib.relayprioritizer import RelayPrioritizer
from unittest.mock import patch

from sbws import settings


def static_time(value):
    while True:
        yield value


def _build_result_for_relay(conf, rl, result_type, relay_nick,
                            timestamp):
    relay = [r for r in rl.relays if r.nickname == relay_nick]
    assert len(relay) == 1
    relay = relay[0]
    other = [r for r in rl.relays if r.nickname != relay_nick][0]
    circ = [relay.fingerprint, other.fingerprint]
    rtts = [0.5, 0.5, 0.5]
    dls = [
        {'amount': 1024, 'duration': 1},
        {'amount': 1024, 'duration': 1},
        {'amount': 1024, 'duration': 1},
    ]
    if result_type == ResultSuccess:
        return ResultSuccess(rtts, dls, relay, circ,
                             conf['destinations.foo']['url'],
                             'test', t=timestamp)

    elif result_type == ResultErrorCircuit:
        return ResultErrorCircuit(relay, circ,
                                  conf['destinations.foo']['url'],
                                  'test', msg='Test error circ message',
                                  t=timestamp)


@patch('time.time')
def test_relayprioritizer_general(time_mock, sbwshome_empty, args,
                                  conf, rl,
                                  persistent_launch_tor):
    now = 1000000
    time_mock.side_effect = static_time(now)
    rd = ResultDump(args, conf)
    try:
        rp = RelayPrioritizer(args, conf, rl, rd)
        results = []
        results = [
            _build_result_for_relay(conf, rl, ResultSuccess,
                                    'relay{}'.format(i), now - (i * 100))
            for i in range(1, 6)
        ]
        for result in results:
            rd.store_result(result)
        best_list = [_ for _ in rp.best_priority()]
        # Of the relays for which we have added results to the ResultDump,
        # relay1 has the lowest priority (it has the most recent result) and
        # relay5 has the highest prioirty. The relays that we didn't add
        # results for will have the highest priority, but don't test the order
        # of them. Skip to the end of the list and check those guys since they
        # should have a defined order.
        for i in range(1, 5+1):
            nick = 'relay{}'.format(i)
            pos = i * -1
            relay = best_list[pos]
            assert relay.nickname == nick
            assert relay.relay_recent_priority_list_count == 1
    finally:
        settings.end_event.set()
