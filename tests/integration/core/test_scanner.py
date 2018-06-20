from sbws.core.scanner import measure_relay
from sbws.lib.circuitbuilder import GapsCircuitBuilder as CB
from sbws.util.config import get_config
from sbws.lib.relaylist import RelayList
from sbws.lib.destination import DestinationList
from sbws.lib.resultdump import ResultSuccess


def assert_within(value, target, radius):
    '''
    Assert that **value** is within **radius** of **target**

    If target is 10 and radius is 2, value can be anywhere between 8 and 12
    inclusive
    '''
    assert target - radius < value, 'Value is too small. {} is not within '\
        '{} of {}'.format(value, radius, target)
    assert target + radius > value, 'Value is too big. {} is not within '\
        '{} of {}'.format(value, radius, target)


def get_everything_to_measure(dotsbws, cont, parser):
    args = parser.parse_args(
        '-d {} --log-level DEBUG scanner'.format(dotsbws).split())
    conf = get_config(args)
    conf['destinations']['foo'] = 'on'
    conf['destinations.foo'] = {}
    conf['destinations.foo']['url'] = 'http://127.0.0.1:28888/sbws.bin'
    rl = RelayList(args, conf, cont)
    cb = CB(args, conf, cont)
    dests, error_msg = DestinationList.from_config(conf, cb, rl, cont)
    assert dests, error_msg
    return {
        'args': args,
        'conf': conf,
        'rl': rl,
        'cb': cb,
        'dests': dests
    }


def test_measure_relay_with_maxadvertisedbandwidth(
        persistent_launch_tor, parser, persistent_empty_dotsbws):
    cont = persistent_launch_tor
    dotsbws = persistent_empty_dotsbws.name
    d = get_everything_to_measure(dotsbws, cont, parser)
    args = d['args']
    conf = d['conf']
    rl = d['rl']
    dests = d['dests']
    cb = d['cb']
    # 117A456C911114076BEB4E757AC48B16CC0CCC5F is relay1mbyteMAB
    relay = [r for r in rl.relays
             if r.nickname == 'relay1mbyteMAB'][0]
    result = measure_relay(args, conf, dests, cb, rl, relay)
    assert len(result) == 1
    result = result[0]
    assert isinstance(result, ResultSuccess)
    one_mbyte = 1 * 1024 * 1024
    allowed_error = 5  # bytes per second
    dls = result.downloads
    for dl in dls:
        assert_within(dl['amount'] / dl['duration'], one_mbyte, allowed_error)


def test_measure_relay_with_relaybandwidthrate(
        persistent_launch_tor, parser, persistent_empty_dotsbws):
    cont = persistent_launch_tor
    dotsbws = persistent_empty_dotsbws.name
    d = get_everything_to_measure(dotsbws, cont, parser)
    args = d['args']
    conf = d['conf']
    rl = d['rl']
    dests = d['dests']
    cb = d['cb']
    # relay1mbyteRBR 934E06F38A391CB71DF83ECDE05DFF5CDE3AC49D
    relay = [r for r in rl.relays
             if r.nickname == 'relay1mbyteRBR'][0]
    result = measure_relay(args, conf, dests, cb, rl, relay)
    assert len(result) == 1
    result = result[0]
    assert isinstance(result, ResultSuccess)
    one_mbyte = 1 * 1024 * 1024
    allowed_error = 5  # bytes per second
    dls = result.downloads
    for dl in dls:
        assert_within(dl['amount'] / dl['duration'], one_mbyte, allowed_error)
