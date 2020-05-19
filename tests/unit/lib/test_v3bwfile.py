# -*- coding: utf-8 -*-
"""Test generation of bandwidth measurements document (v3bw)"""
import json
import logging
import math
import os.path
from unittest import mock

from sbws import __version__ as version
from sbws.globals import (SPEC_VERSION, SBWS_SCALING, TORFLOW_SCALING,
                          MIN_REPORT, TORFLOW_ROUND_DIG, PROP276_ROUND_DIG)
from sbws.lib.resultdump import Result, load_result_file, ResultSuccess
from sbws.lib.v3bwfile import (
    V3BWHeader, V3BWLine, TERMINATOR, LINE_SEP,
    KEYVALUE_SEP_V1, num_results_of_type,
    V3BWFile, round_sig_dig,
    HEADER_RECENT_MEASUREMENTS_EXCLUDED_KEYS
    )
from sbws.util.state import CustomDecoder
from sbws.util.timestamp import now_fname, now_isodt_str, now_unixts

timestamp = 1523974147
timestamp_l = str(timestamp)
version_l = KEYVALUE_SEP_V1.join(['version', SPEC_VERSION])
scanner_country = 'US'
scanner_country_l = KEYVALUE_SEP_V1.join(['scanner_country', scanner_country])
destinations_countries = '00,DE'
destinations_countries_l = KEYVALUE_SEP_V1.join(['destinations_countries',
                                                destinations_countries])
software_l = KEYVALUE_SEP_V1.join(['software', 'sbws'])
software_version_l = KEYVALUE_SEP_V1.join(['software_version', version])
file_created = '2018-04-25T13:10:57'
file_created_l = KEYVALUE_SEP_V1.join(['file_created', file_created])
latest_bandwidth = '2018-04-17T14:09:07'
latest_bandwidth_l = KEYVALUE_SEP_V1.join(['latest_bandwidth',
                                          latest_bandwidth])
attempts = '1'
attempts_l = KEYVALUE_SEP_V1.join(['recent_measurement_attempt_count',
                                   attempts])
failure = '0'
failure_l = KEYVALUE_SEP_V1.join(['recent_measurement_failure_count',
                                  failure])
header_ls = [timestamp_l, version_l, destinations_countries_l, file_created_l,
             latest_bandwidth_l,
             # attempts_l, failure_l,
             scanner_country_l, software_l, software_version_l, TERMINATOR]
header_str = LINE_SEP.join(header_ls) + LINE_SEP
earliest_bandwidth = '2018-04-16T14:09:07'
earliest_bandwidth_l = KEYVALUE_SEP_V1.join(['earliest_bandwidth',
                                            earliest_bandwidth])
generator_started = '2018-04-16T14:09:05'
generator_started_l = KEYVALUE_SEP_V1.join(['generator_started',
                                           generator_started])
tor_version = '0.4.2.5'
tor_version_l = KEYVALUE_SEP_V1.join(['tor_version', tor_version])

header_extra_ls = [timestamp_l, version_l,
                   earliest_bandwidth_l, file_created_l, generator_started_l,
                   latest_bandwidth_l,
                   software_l, software_version_l, tor_version_l,
                   TERMINATOR]
header_extra_str = LINE_SEP.join(header_extra_ls) + LINE_SEP

# Line produced without any scaling.
# unmeasured and vote are not congruent with the exclusion,
# but `from_data` is only used in the test and doesn't include the
# arg `min_num`
raw_bwl_str = "bw=56 bw_mean=61423 bw_median=55656 "\
    "consensus_bandwidth=600000 consensus_bandwidth_is_unmeasured=False "\
    "desc_bw_avg=1000000000 desc_bw_bur=123456 desc_bw_obs_last=524288 "\
    "desc_bw_obs_mean=524288 error_circ=0 error_destination=0 error_misc=0 " \
    "error_second_relay=0 error_stream=2 " \
    "master_key_ed25519=g+Shk00y9Md0hg1S6ptnuc/wWKbADBgdjT0Kg+TSF3s " \
    "nick=A " \
    "node_id=$AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA "\
    "relay_in_recent_consensus_count=3 "\
    "relay_recent_measurement_attempt_count=2 "\
    "relay_recent_measurements_excluded_error_count=2 "\
    "relay_recent_priority_list_count=3 "\
    "rtt=456 success=1 " \
    "time=2018-04-17T14:09:07\n"

v3bw_str = header_extra_str + raw_bwl_str


def test_v3bwheader_str():
    """Test header str"""
    header = V3BWHeader(timestamp_l, scanner_country=scanner_country,
                        destinations_countries=destinations_countries,
                        file_created=file_created)
    assert header_str == str(header)


def test_v3bwheader_extra_str():
    """Test header str with additional headers"""
    header = V3BWHeader(timestamp_l,
                        file_created=file_created,
                        generator_started=generator_started,
                        earliest_bandwidth=earliest_bandwidth,
                        tor_version=tor_version)
    assert header_extra_str == str(header)


def test_v3bwheader_from_lines():
    header_obj = V3BWHeader(timestamp_l,
                            file_created=file_created,
                            generator_started=generator_started,
                            earliest_bandwidth=earliest_bandwidth,
                            tor_version=tor_version)
    header, _ = V3BWHeader.from_lines_v1(header_extra_ls)
    assert str(header_obj) == str(header)


def test_v3bwheader_from_text():
    header_obj = V3BWHeader(timestamp_l,
                            file_created=file_created,
                            generator_started=generator_started,
                            earliest_bandwidth=earliest_bandwidth,
                            tor_version=tor_version)
    header, _ = V3BWHeader.from_text_v1(header_extra_str)
    assert str(header_obj) == str(header)


def test_num_results_of_type(result_success, result_error_stream):
    assert num_results_of_type([result_success], 'success') == 1
    assert num_results_of_type([result_error_stream], 'success') == 0
    assert num_results_of_type([result_success], 'error-stream') == 0
    assert num_results_of_type([result_error_stream], 'error-stream') == 1


def assert_round_sig_dig_any_digits(n, result):
    """Test that rounding n to any reasonable number of significant digits
       produces result."""
    max_digits_int64 = int(math.ceil(math.log10(2**64 - 1))) + 1
    for d in range(1, max_digits_int64 + 1):
        assert(round_sig_dig(n, digits=d) == result)


def assert_round_sig_dig_any_digits_error(n, elp_fraction=0.5):
    """Test that rounding n to any reasonable number of significant digits
       produces a result within elp_fraction * 10.0 ** -(digits - 1)."""
    max_digits_int64 = int(math.ceil(math.log10(2**64 - 1))) + 1
    for d in range(1, max_digits_int64 + 1):
        error_fraction = elp_fraction * (10.0 ** -(d - 1))
        # use ceil rather than round, to work around floating-point inaccuracy
        e = int(math.ceil(n * error_fraction))
        assert(round_sig_dig(n, digits=d) >= n - e)
        assert(round_sig_dig(n, digits=d) <= n + e)


def test_round_sig_dig():
    """Test rounding to a number of significant digits."""
    # Expected values
    assert(round_sig_dig(11, 1) == 10)
    assert(round_sig_dig(11, 2) == 11)

    assert(round_sig_dig(15, 1) == 20)
    assert(round_sig_dig(15, 2) == 15)

    assert(round_sig_dig(54, 1) == 50)
    assert(round_sig_dig(54, 2) == 54)

    assert(round_sig_dig(96, 1) == 100)
    assert(round_sig_dig(96, 2) == 96)

    assert(round_sig_dig(839, 1) == 800)
    assert(round_sig_dig(839, 2) == 840)
    assert(round_sig_dig(839, 3) == 839)

    assert(round_sig_dig(5789, 1) == 6000)
    assert(round_sig_dig(5789, 2) == 5800)
    assert(round_sig_dig(5789, 3) == 5790)
    assert(round_sig_dig(5789, 4) == 5789)

    assert(round_sig_dig(24103, 1) == 20000)
    assert(round_sig_dig(24103, 2) == 24000)
    assert(round_sig_dig(24103, 3) == 24100)
    assert(round_sig_dig(24103, 4) == 24100)
    assert(round_sig_dig(24103, 5) == 24103)

    assert(round_sig_dig(300000, 1) == 300000)

    # Floating-point values

    # Must round based on fractions, must not double-round
    assert(round_sig_dig(14, 1) == 10)
    assert(round_sig_dig(14.0, 1) == 10)
    assert(round_sig_dig(14.9, 1) == 10)
    assert(round_sig_dig(15.0, 1) == 20)
    assert(round_sig_dig(15.1, 1) == 20)

    assert(round_sig_dig(14, 2) == 14)
    assert(round_sig_dig(14.0, 2) == 14)
    assert(round_sig_dig(14.9, 2) == 15)
    assert(round_sig_dig(15.0, 2) == 15)
    assert(round_sig_dig(15.1, 2) == 15)

    # Must round to integer
    assert(round_sig_dig(14, 3) == 14)
    assert(round_sig_dig(14.0, 3) == 14)
    assert(round_sig_dig(14.9, 3) == 15)
    assert(round_sig_dig(15.0, 3) == 15)
    assert(round_sig_dig(15.1, 3) == 15)

    # Small integers
    assert_round_sig_dig_any_digits(0, 1)
    assert_round_sig_dig_any_digits(1, 1)
    assert_round_sig_dig_any_digits(2, 2)
    assert_round_sig_dig_any_digits(3, 3)
    assert_round_sig_dig_any_digits(4, 4)
    assert_round_sig_dig_any_digits(5, 5)
    assert_round_sig_dig_any_digits(6, 6)
    assert_round_sig_dig_any_digits(7, 7)
    assert_round_sig_dig_any_digits(8, 8)
    assert_round_sig_dig_any_digits(9, 9)
    assert_round_sig_dig_any_digits(10, 10)

    # Large values
    assert_round_sig_dig_any_digits_error(2**30)
    assert_round_sig_dig_any_digits_error(2**31)
    assert_round_sig_dig_any_digits_error(2**32)

    # the floating-point accuracy limit for this function is 2**73
    # on some machines
    assert_round_sig_dig_any_digits_error(2**62)
    assert_round_sig_dig_any_digits_error(2**63)
    assert_round_sig_dig_any_digits_error(2**64)

    # Out of range values: must round to 1
    assert_round_sig_dig_any_digits(-0.01, 1)
    assert_round_sig_dig_any_digits(-1, 1)
    assert_round_sig_dig_any_digits(-10.5, 1)
    assert_round_sig_dig_any_digits(-(2**31), 1)

    # test the transition points in the supported range
    # testing the entire range up to 1 million takes 100s
    for n in range(1, 20000):
        assert_round_sig_dig_any_digits_error(n)

    # use a step that is relatively prime, to increase the chance of
    # detecting errors
    for n in range(90000, 200000, 9):
        assert_round_sig_dig_any_digits_error(n)

    for n in range(900000, 2000000, 99):
        assert_round_sig_dig_any_digits_error(n)


def test_v3bwline_from_results_file(datadir):
    lines = datadir.readlines('results.txt')
    d = dict()
    for line in lines:
        r = Result.from_dict(json.loads(line.strip(), cls=CustomDecoder))
        fp = r.fingerprint
        if fp not in d:
            d[fp] = []
        d[fp].append(r)
    bwl, _ = V3BWLine.from_data(d, fp)
    # bw store now B, not KB
    bwl.bw = round(bwl.bw / 1000)
    assert raw_bwl_str == str(bwl)


def test_from_results_read(datadir, tmpdir, conf, args):
    results = load_result_file(str(datadir.join("results.txt")))
    expected_header = V3BWHeader(timestamp_l,
                                 earliest_bandwidth=earliest_bandwidth,
                                 latest_bandwidth=latest_bandwidth)
    exclusion_dict = dict(
        [(k, 0) for k in HEADER_RECENT_MEASUREMENTS_EXCLUDED_KEYS]
        )
    expected_header.add_relays_excluded_counters(exclusion_dict)
    raw_bwls = [V3BWLine.from_results(results[fp])[0] for fp in results]
    # Scale BWLines using torflow method, since it's the default and BWLines
    # bandwidth is the raw bandwidth.
    expected_bwls = V3BWFile.bw_torflow_scale(raw_bwls)
    # Since the scaled lines will be less than the 60% relays in the network,
    # set under_min_report.
    expected_bwls[0].under_min_report = 1
    expected_bwls[0].vote = 0
    expected_f = V3BWFile(expected_header, expected_bwls)
    # This way is going to convert bw to KB
    v3bwfile = V3BWFile.from_results(results)
    assert str(expected_f)[1:] == str(v3bwfile)[1:]
    output = os.path.join(args.output, now_fname())
    v3bwfile.write(output)


def test_from_arg_results_write(datadir, tmpdir, conf, args):
    results = load_result_file(str(datadir.join("results.txt")))
    v3bwfile = V3BWFile.from_results(results)
    output = os.path.join(args.output, now_fname())
    v3bwfile.write(output)
    assert os.path.isfile(output)


def test_from_arg_results_write_read(datadir, tmpdir, conf, args):
    results = load_result_file(str(datadir.join("results.txt")))
    v3bwfile = V3BWFile.from_results(results)
    output = os.path.join(args.output, now_fname())
    v3bwfile.write(output)
    with open(output) as fd:
        v3bw = fd.read()
    assert v3bw == str(v3bwfile)


def test_sbws_scale(datadir):
    results = load_result_file(str(datadir.join("results.txt")))
    v3bwfile = V3BWFile.from_results(results, scaling_method=SBWS_SCALING)
    assert v3bwfile.bw_lines[0].bw == 8


def num_consensus_relays(fpath):
    return 1


# To do not have to create a consensus-cache file and set the path,
# mock the result since it only returns the number of relays.
@mock.patch.object(V3BWFile, 'read_number_consensus_relays')
def test_torflow_scale(mock_consensus, datadir, tmpdir, conf):
    mock_consensus.return_value = 1
    # state_fpath = str(tmpdir.join('.sbws', 'state.dat'))
    state_fpath = conf['paths']['state_fpath']
    results = load_result_file(str(datadir.join("results.txt")))
    # Since v1.1.0, it'll write bw=1 if the minimum percent of measured relays
    # wasn't reached. Therefore mock the consensus number.
    # Because the consensus number is mocked, it'll try to read the sate path.
    # Obtain it from conf, so that the root directory exists.
    v3bwfile = V3BWFile.from_results(results, '', '',
                                     state_fpath,
                                     scaling_method=TORFLOW_SCALING,
                                     round_digs=TORFLOW_ROUND_DIG)
    assert v3bwfile.bw_lines[0].bw == 123
    v3bwfile = V3BWFile.from_results(results, '', '',
                                     state_fpath,
                                     scaling_method=TORFLOW_SCALING,
                                     torflow_cap=0.0001,
                                     round_digs=TORFLOW_ROUND_DIG)
    assert v3bwfile.bw_lines[0].bw == 6.1423000000000005
    v3bwfile = V3BWFile.from_results(results, '', '',
                                     state_fpath,
                                     scaling_method=TORFLOW_SCALING,
                                     torflow_cap=1,
                                     round_digs=TORFLOW_ROUND_DIG)
    assert v3bwfile.bw_lines[0].bw == 123
    v3bwfile = V3BWFile.from_results(results, '', '',
                                     state_fpath,
                                     scaling_method=TORFLOW_SCALING,
                                     torflow_cap=1,
                                     round_digs=PROP276_ROUND_DIG)
    assert v3bwfile.bw_lines[0].bw == 120


def test_torflow_scale_no_desc_bw_avg(datadir, conf, caplog):
    state_fpath = conf['paths']['state_fpath']
    results = load_result_file(str(datadir.join("results_no_desc_bw_avg.txt")))
    caplog.set_level(logging.DEBUG)
    v3bwfile = V3BWFile.from_results(results, '', '', state_fpath)
    assert v3bwfile.bw_lines[0].bw == 520


def test_torflow_scale_no_desc_bw_obs(datadir, conf, caplog):
    state_fpath = conf['paths']['state_fpath']
    results = load_result_file(str(datadir.join("results_no_desc_bw_obs.txt")))
    caplog.set_level(logging.DEBUG)
    v3bwfile = V3BWFile.from_results(results, '', '', state_fpath)
    assert v3bwfile.bw_lines[0].bw == 600


def test_torflow_scale_no_desc_bw_avg_obs(datadir, conf, caplog):
    state_fpath = conf['paths']['state_fpath']
    results = load_result_file(
        str(datadir.join("results_no_desc_bw_avg_obs.txt"))
    )
    caplog.set_level(logging.DEBUG)
    v3bwfile = V3BWFile.from_results(results, '', '', state_fpath)
    assert v3bwfile.bw_lines[0].bw == 600


def test_torflow_scale_no_consensus_bw(datadir, conf, caplog):
    state_fpath = conf['paths']['state_fpath']
    results = load_result_file(str(
        datadir.join("results_no_consensus_bw.txt"))
    )
    caplog.set_level(logging.DEBUG)
    v3bwfile = V3BWFile.from_results(results, '', '', state_fpath)
    assert v3bwfile.bw_lines[0].bw == 520


def test_torflow_scale_0_consensus_bw(datadir, conf, caplog):
    state_fpath = conf['paths']['state_fpath']
    results = load_result_file(str(datadir.join("results_0_consensus_bw.txt")))
    caplog.set_level(logging.DEBUG)
    v3bwfile = V3BWFile.from_results(results, '', '', state_fpath)
    assert v3bwfile.bw_lines[0].bw == 520

def test_results_away_each_other(datadir):
    min_num = 2
    secs_away = 86400  # 1d
    results = load_result_file(str(datadir.join("results_away.txt")))
    # A has 4 results, 3 are success, 2 are 1 day away, 1 is 12h away
    values = results["AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"]

    # There is one result excluded, but the relay is not excluded
    bwl, reason = V3BWLine.from_results(values, secs_away=secs_away, min_num=2)
    assert bwl.relay_recent_measurements_excluded_error_count == 1
    assert reason is None
    assert not hasattr(bwl, "vote")
    assert not hasattr(bwl, "unmeasured")

    success_results = [r for r in values if isinstance(r, ResultSuccess)]
    assert len(success_results) >= min_num
    results_away = V3BWLine.results_away_each_other(success_results, secs_away)
    assert len(results_away) == 3

    # B has 2 results, 12h away from each other
    values = results["BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"]

    # Two measurements are excluded and there were only 2,
    # the relay is excluded
    bwl, reason = V3BWLine.from_results(values, secs_away=secs_away, min_num=2)
    assert bwl.relay_recent_measurements_excluded_near_count == 2
    assert reason == 'recent_measurements_excluded_near_count'
    assert bwl.vote == 0
    assert bwl.unmeasured == 1

    success_results = [r for r in values if isinstance(r, ResultSuccess)]
    assert len(success_results) >= min_num
    results_away = V3BWLine.results_away_each_other(success_results, secs_away)
    assert not results_away

    secs_away = 43200  # 12h
    values = results["BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"]
    success_results = [r for r in values if isinstance(r, ResultSuccess)]
    assert len(success_results) >= min_num
    results_away = V3BWLine.results_away_each_other(success_results, secs_away)
    assert len(results_away) == 2

    # C has 1 result
    values = results["CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC"]

    # There is only 1 result, the relay is excluded
    bwl, reason = V3BWLine.from_results(values, min_num=2)
    assert bwl.relay_recent_measurements_excluded_few_count == 1
    assert reason == 'recent_measurements_excluded_few_count'
    assert bwl.vote == 0
    assert bwl.unmeasured == 1

    success_results = [r for r in values if isinstance(r, ResultSuccess)]
    assert len(success_results) < min_num


def test_measured_progress_stats(datadir):
    number_consensus_relays = 3
    bw_lines_raw = []
    statsd_exp = {'percent_eligible_relays': 100,
                  'minimum_percent_eligible_relays': 60,
                  'number_consensus_relays': 3,
                  'minimum_number_eligible_relays': 2,
                  'number_eligible_relays': 3}
    min_perc_reached_before = None
    results = load_result_file(str(datadir.join("results_away.txt")))
    for fp, values in results.items():
        # log.debug("Relay fp %s", fp)
        line, _ = V3BWLine.from_results(values)
        if line is not None:
            bw_lines_raw.append(line)
    assert len(bw_lines_raw) == 3
    bw_lines = V3BWFile.bw_torflow_scale(bw_lines_raw)
    assert len(bw_lines) == 3
    statsd, success = V3BWFile.measured_progress_stats(
        len(bw_lines), number_consensus_relays, min_perc_reached_before)
    assert success
    assert statsd == statsd_exp
    number_consensus_relays = 6
    statsd, success = V3BWFile.measured_progress_stats(
        len(bw_lines), number_consensus_relays, min_perc_reached_before)
    assert not success
    statsd_exp = {'percent_eligible_relays': 50,
                  'minimum_percent_eligible_relays': 60,
                  'number_consensus_relays': 6,
                  'minimum_number_eligible_relays': 4,
                  'number_eligible_relays': 3}
    assert statsd_exp == statsd


def test_update_progress(datadir, tmpdir):
    bw_lines_raw = []
    number_consensus_relays = 6
    state = {}
    header = V3BWHeader(str(now_unixts()))
    results = load_result_file(str(datadir.join("results_away.txt")))
    for fp, values in results.items():
        # log.debug("Relay fp %s", fp)
        line = V3BWLine.from_results(values)
        if line is not None:
            bw_lines_raw.append(line)
    bwfile = V3BWFile(header, [])
    bwfile.update_progress(len(bw_lines_raw), header, number_consensus_relays,
                           state)
    assert header.percent_eligible_relays == '50'
    assert state.get('min_perc_reached') is None
    # Test that the headers are also included when there are enough eligible
    # relays
    number_consensus_relays = 3
    header = V3BWHeader(str(now_unixts()))
    bwfile.update_progress(len(bw_lines_raw), header, number_consensus_relays,
                           state)
    assert state.get('min_perc_reached') == now_isodt_str()
    assert header.minimum_number_eligible_relays == '2'
    assert header.minimum_percent_eligible_relays == str(MIN_REPORT)
    assert header.number_consensus_relays == '3'
    assert header.number_eligible_relays == '3'
    assert header.percent_eligible_relays == '100'


def test_time_measure_half_network(caplog):
    header = V3BWHeader(timestamp_l,
                        file_created=file_created,
                        generator_started=generator_started,
                        earliest_bandwidth=earliest_bandwidth)
    header.number_consensus_relays = '6500'
    header.number_eligible_relays = '4000'
    caplog.set_level(logging.INFO)
    header.add_time_report_half_network()
    assert header.time_to_report_half_network == '70200'  # 19.5h
    expected_log = "Estimated time to measure the network: 39 hours."  # 19.5*2
    assert caplog.records[-1].getMessage() == expected_log


@mock.patch.object(V3BWFile, 'read_number_consensus_relays')
def test_set_under_min_report(mock_consensus, conf, datadir):
    # The number of relays (1) is the same as the ones in the consensus,
    # therefore there is no any relay excluded and under_min_report is not set.
    mock_consensus.return_value = 1
    state_fpath = conf['paths']['state_fpath']
    results = load_result_file(str(datadir.join("results.txt")))
    v3bwfile = V3BWFile.from_results(results, '', '', state_fpath)
    bwl = v3bwfile.bw_lines[0]
    assert not hasattr(bwl, "vote")
    assert not hasattr(bwl, "under_min_report")
    assert bwl.bw != 1

    # The number of relays is the same as the ones in the consensus,
    # but after filtering there's no any, under_min_report is set to 1
    # and unmeasured was also set to 1.
    # After filtering the relay is excluded because there's only 1 success
    # result and it should have at least 2 (min_num)
    v3bwfile = V3BWFile.from_results(results, '', '', state_fpath, min_num=2)
    bwl = v3bwfile.bw_lines[0]
    assert bwl.vote == 0
    assert bwl.under_min_report == 1
    assert bwl.unmeasured == 1
    assert bwl.bw == 1

    # The number of relays after scaling is than the 60% in the network,
    # therefore the relays are excluded and under_min_report is set to 1.
    mock_consensus.return_value = 3
    v3bwfile = V3BWFile.from_results(results, '', '', state_fpath)
    bwl = v3bwfile.bw_lines[0]
    assert bwl.vote == 0
    assert bwl.under_min_report == 1
    assert bwl.bw != 1


def test_generator_started(root_data_path, datadir):
    state_fpath = os.path.join(root_data_path, '.sbws/state.dat')
    # The method is correct
    assert "2020-02-29T10:00:00" == V3BWHeader.generator_started_from_file(
        state_fpath
    )
    # `results` does not matter here, using them to not have an empty list.
    results = load_result_file(str(datadir.join("results.txt")))
    header = V3BWHeader.from_results(results, '', '', state_fpath)
    # And the header is correct
    assert "2020-02-29T10:00:00" == header.generator_started


def test_recent_consensus_count(root_data_path, datadir):
    # This state has recent_consensus_count
    state_fpath = os.path.join(root_data_path, '.sbws/state.dat')
    assert "1" == V3BWHeader.consensus_count_from_file(state_fpath)
    # `results` does not matter here, using them to not have an empty list.
    results = load_result_file(str(datadir.join("results.txt")))
    header = V3BWHeader.from_results(results, '', '', state_fpath)
    assert "1" == header.recent_consensus_count


def test_recent_measurement_attempt_count(root_data_path, datadir):
    state_fpath = os.path.join(root_data_path, '.sbws/state.dat')
    assert 15 == V3BWHeader.recent_measurement_attempt_count_from_file(
        state_fpath
    )
    # `results` does not matter here, using them to not have an empty list.
    results = load_result_file(str(datadir.join("results.txt")))
    header = V3BWHeader.from_results(results, '', '', state_fpath)
    assert "15" == header.recent_measurement_attempt_count


def test_recent_priority_list_count(root_data_path, datadir):
    # This state has recent_priority_list
    state_fpath = os.path.join(root_data_path, '.sbws/state.dat')
    assert 1 == V3BWHeader.recent_priority_list_count_from_file(state_fpath)
    # `results` does not matter here, using them to don't have an empty list.
    results = load_result_file(str(datadir.join("results.txt")))
    header = V3BWHeader.from_results(results, '', '', state_fpath)
    assert "1" == header.recent_priority_list_count


def test_recent_priority_relay_count(root_data_path, datadir):
    # This state has recent_priority_relay_count
    state_fpath = os.path.join(root_data_path, '.sbws/state.dat')
    assert 15 == V3BWHeader.recent_priority_relay_count_from_file(state_fpath)
    # `results` does not matter here, using them to don't have an empty list.
    results = load_result_file(str(datadir.join("results.txt")))
    header = V3BWHeader.from_results(results, '', '', state_fpath)
    assert "15" == header.recent_priority_relay_count


def test_relay_recent_measurement_attempt_count(root_data_path, datadir):
    results = load_result_file(str(datadir.join("results.txt")))
    for fp, values in results.items():
        line = V3BWLine.from_results(values)
    assert "2" == line[0].relay_recent_measurement_attempt_count


def test_relay_recent_priority_list_count(root_data_path, datadir):
    results = load_result_file(str(datadir.join("results.txt")))
    for fp, values in results.items():
        line = V3BWLine.from_results(values)
    assert "3" == line[0].relay_recent_priority_list_count


def test_relay_in_recent_consensus_count(root_data_path, datadir):
    results = load_result_file(str(datadir.join("results.txt")))
    for fp, values in results.items():
        line = V3BWLine.from_results(values)
    assert "3" == line[0].relay_in_recent_consensus_count
