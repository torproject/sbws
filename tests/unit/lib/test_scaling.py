"""Unit tests for scaling.py."""
import os
from statistics import mean

from sbws.lib import scaling
from sbws.lib.resultdump import load_result_file, ResultSuccess


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
    assert 0 == scaling.bw_filt(bw_measurements)

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


def test_bw_filt_from_results(root_data_path):
    results_file = os.path.join(
        root_data_path, ".sbws", "datadir", "2019-03-25.txt"
    )
    results = load_result_file(results_file)
    bw_filts = {}
    for fp, values in results.items():
        success_results = [r for r in values if isinstance(r, ResultSuccess)]
        if success_results:
            bw_measurements = scaling.bw_measurements_from_results(
                success_results
            )
            mu = round(mean(bw_measurements))
            muf = scaling.bw_filt(bw_measurements)
            bw_filts[fp] = (mu, muf)
    for fp, values in bw_filts.items():
        assert bw_filts[fp][0] <= bw_filts[fp][1]
    assert 5526756 == bw_filts['117A456C911114076BEB4E757AC48B16CC0CCC5F'][0]
    assert 5643086 == bw_filts['117A456C911114076BEB4E757AC48B16CC0CCC5F'][1]
    assert 5664965 == bw_filts['693F73187624BE760AAD2A12C5ED89DB1DE044F5'][0]
    assert 5774274 == bw_filts['693F73187624BE760AAD2A12C5ED89DB1DE044F5'][1]
    assert 5508279 == bw_filts['270A861ABED22EC2B625198BCCD7B2B9DBFFC93C'][0]
    assert 5583737 == bw_filts['270A861ABED22EC2B625198BCCD7B2B9DBFFC93C'][1]
    assert 5379911 == bw_filts['E894C65997F8EC96558B554176EEEA39C6A43EF6'][0]
    assert 5485088 == bw_filts['E894C65997F8EC96558B554176EEEA39C6A43EF6'][1]
