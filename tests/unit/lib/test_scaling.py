"""Unit tests for scaling.py."""

from sbws.lib import scaling


def test_bw_filt():
    bw_measurements = [
        96700.00922329757, 70311.63051659254, 45531.743347556374,
        38913.97025485627, 55656.332364676025
    ]
    fb = scaling.bw_filt(bw_measurements)
    # This is greater than the mean, that is 61422.73714139576
    assert fb == 83505.81986994506
