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
        results = [
            _build_result_for_relay(conf, rl, ResultSuccess,
                                    'test{:03d}m'.format(i), now - (i * 100))
            # In chutney the relays are from 003 to 011
            for i in range(3, 12)
        ]
        for result in results:
            rd.store_result(result)
        best_list = list(rp.best_priority())
        # With chutney, the relays not measured, with higher priority, will be
        # the 3 exits and authorities.
        # So take the list from the first measured relay, ie. from the 6th
        # position.
        # The measured relays will be in inverse order to their name.
        best_list_measured = best_list[6:]
        for i in range(3, 12):
            nick = 'test{:03d}m'.format(i)
            # -1 To start by the back, - 2 because their names start by 3,
            # not 1
            pos = (i - 2) * -1
            relay = best_list_measured[pos]
            assert relay.nickname == nick
            assert relay.relay_recent_priority_list_count == 1
    finally:
        settings.end_event.set()
