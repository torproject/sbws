from sbws.lib.resultdump import ResultDump
from sbws.lib.resultdump import (ResultSuccess, ResultErrorCircuit)
from sbws.lib.relaylist import RelayList
from sbws.lib.relayprioritizer import RelayPrioritizer
from sbws.util.config import get_config
from threading import Event
from unittest.mock import patch


def static_time(value):
    while True:
        yield value


def get_global_stuff(dotsbws, cont, parser):
    args = parser.parse_args(
        '-d {} --log-level debug'.format(dotsbws).split())
    conf = get_config(args)
    rl = RelayList(args, conf, cont)
    return {
        'args': args,
        'conf': conf,
        'rl': rl,
        'end': Event(),
    }


def _build_result_for_relay(relay_nick, result_type, timestamp, rl):
    relay = [r for r in rl.relays if r.nickname == relay_nick]
    assert len(relay) == 1
    relay = relay[0]
    other = [r for r in rl.relays if r.nickname != relay_nick][0]
    circ = [relay.fingerprint, other.fingerprint]
    url = 'http://example.com/sbws.bin'
    nick = 'sbws_scanner'
    if result_type == ResultSuccess:
        rtts = [0.5, 0.5, 0.5]
        dls = [
            {'amount': 1024, 'duration': 1},
            {'amount': 1024, 'duration': 1},
            {'amount': 1024, 'duration': 1},
        ]
        return ResultSuccess(rtts, dls, relay, circ, url, nick, t=timestamp)
    elif result_type == ResultErrorCircuit:
        return ResultErrorCircuit(
            relay, circ, url, nick, msg='Test error circ message', t=timestamp)


@patch('time.time')
def test_relayprioritizer_general(
        time_mock, persistent_empty_dotsbws, parser, persistent_launch_tor):
    now = 1000000
    time_mock.side_effect = static_time(now)
    cont = persistent_launch_tor
    dotsbws = persistent_empty_dotsbws.name
    d = get_global_stuff(dotsbws, cont, parser)
    args = d['args']
    conf = d['conf']
    end_event = d['end']
    rl = d['rl']
    rd = ResultDump(args, conf, end_event)
    try:
        rp = RelayPrioritizer(args, conf, rl, rd)
        results = [
            _build_result_for_relay(
                'relay1', ResultSuccess, now - 100, rl),
            _build_result_for_relay(
                'relay2', ResultSuccess, now - 200, rl),
            _build_result_for_relay(
                'relay3', ResultSuccess, now - 300, rl),
            _build_result_for_relay(
                'relay4', ResultSuccess, now - 400, rl),
            _build_result_for_relay(
                'relay5', ResultSuccess, now - 500, rl),
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
    finally:
        end_event.set()
