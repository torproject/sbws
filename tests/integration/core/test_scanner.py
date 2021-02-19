import pytest

from sbws.core.scanner import measure_relay
from sbws.lib.resultdump import ResultSuccess
import logging


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


@pytest.mark.skip(reason=("Disabled because chutney is not creating a network"
                          "with relay1mbyteMAB."))
def test_measure_relay_with_maxadvertisedbandwidth(
        persistent_launch_tor, sbwshome_dir, args, conf,
        dests, cb, rl, caplog):
    caplog.set_level(logging.DEBUG)
    # d = get_everything_to_measure(sbwshome, cont, args, conf)
    # rl = d['rl']
    # dests = d['dests']
    # cb = d['cb']
    # 117A456C911114076BEB4E757AC48B16CC0CCC5F is relay1mbyteMAB
    relay = [r for r in rl.relays
             if r.nickname == 'relay1mbyteMAB'][0]
    # d['relay'] = relay
    result = measure_relay(args, conf, dests, cb, rl, relay)
    assert len(result) == 1
    result = result[0]
    assert isinstance(result, ResultSuccess)
    one_mbyte = 1 * 1024 * 1024
    dls = result.downloads
    for dl in dls:
        # This relay has MaxAdvertisedBandwidth set, but should not be limited
        # to just 1 Mbyte. Assume and assert that all downloads where at least
        # more than 10% faster than 1 MBps
        assert dl['amount'] / dl['duration'] > one_mbyte * 1.1
    assert result.relay_average_bandwidth == one_mbyte


@pytest.mark.skip(reason="temporally disabled")
def test_measure_relay_with_relaybandwidthrate(
        persistent_launch_tor, args, conf, dests, cb, rl):
    relay = [r for r in rl.relays
             if r.nickname == 'relay1mbyteRBR'][0]
    result = measure_relay(args, conf, dests, cb, rl, relay)
    assert len(result) == 1
    result = result[0]
    assert isinstance(result, ResultSuccess)
    one_mbyte = 1 * 1024 * 1024
    allowed_error = 0.1 * one_mbyte  # allow 10% error in either direction
    dls = result.downloads
    for dl in dls:
        assert_within(dl['amount'] / dl['duration'], one_mbyte, allowed_error)
