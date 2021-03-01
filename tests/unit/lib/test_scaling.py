"""Unit tests for scaling.py."""
from statistics import mean

from sbws.lib import scaling


def test_bw_filt():
    bw_measurements = [
        96700.00922329757, 70311.63051659254, 45531.743347556374,
        38913.97025485627, 55656.332364676025
    ]
    fb = scaling.bw_filt(bw_measurements)
    # This is greater than the mean, that is 61422.73714139576
    assert fb == 83506

    # When there are no measurements what can not be the case for successful
    # results.
    bw_measurements = []
    assert 1 == scaling.bw_filt(bw_measurements)

    bw_measurements = [1, 0]
    # Because rounded to int
    assert 0 == round(mean(bw_measurements))
    # So the filtered bw will be also 0
    assert 0 == scaling.bw_filt(bw_measurements)

    bw_measurements = [1, 2, 3]
    # Because rounded to int
    assert 2 == round(mean(bw_measurements))
    assert 2 == scaling.bw_filt(bw_measurements)

    bw_measurements = [10, 0]
    assert 5 == round(mean(bw_measurements))
    # Because the value 10 is bigger than the mean
    assert 10 == scaling.bw_filt(bw_measurements)

    bw_measurements = [0, 10, 20]
    assert 10 == round(mean(bw_measurements))
    # Because 10 and 20 are bigger or equal than the mean
    assert 15 == scaling.bw_filt(bw_measurements)
