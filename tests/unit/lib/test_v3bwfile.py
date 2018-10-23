# -*- coding: utf-8 -*-
"""Test generation of bandwidth measurements document (v3bw)"""
import json
import os.path

from sbws import __version__ as version
from sbws.globals import SPEC_VERSION, SBWS_SCALING, TORFLOW_SCALING
from sbws.lib.resultdump import Result, load_result_file, ResultSuccess
from sbws.lib.v3bwfile import (V3BWHeader, V3BWLine, TERMINATOR, LINE_SEP,
                               KEYVALUE_SEP_V110, num_results_of_type,
                               V3BWFile)
from sbws.util.timestamp import now_fname, now_isodt_str, now_unixts

timestamp = 1523974147
timestamp_l = str(timestamp)
version_l = KEYVALUE_SEP_V110.join(['version', SPEC_VERSION])
software_l = KEYVALUE_SEP_V110.join(['software', 'sbws'])
software_version_l = KEYVALUE_SEP_V110.join(['software_version', version])
file_created = '2018-04-25T13:10:57'
file_created_l = KEYVALUE_SEP_V110.join(['file_created', file_created])
latest_bandwidth = '2018-04-17T14:09:07'
latest_bandwidth_l = KEYVALUE_SEP_V110.join(['latest_bandwidth',
                                             latest_bandwidth])
header_ls = [timestamp_l, version_l, file_created_l, latest_bandwidth_l,
             software_l, software_version_l, TERMINATOR]
header_str = LINE_SEP.join(header_ls) + LINE_SEP
earliest_bandwidth = '2018-04-16T14:09:07'
earliest_bandwidth_l = KEYVALUE_SEP_V110.join(['earliest_bandwidth',
                                               earliest_bandwidth])
generator_started = '2018-04-16T14:09:05'
generator_started_l = KEYVALUE_SEP_V110.join(['generator_started',
                                              generator_started])
header_extra_ls = [timestamp_l, version_l,
                   earliest_bandwidth_l, file_created_l, generator_started_l,
                   latest_bandwidth_l,
                   software_l, software_version_l, TERMINATOR]
header_extra_str = LINE_SEP.join(header_extra_ls) + LINE_SEP

bwl_str = "bw=56 bw_bs_mean=61423 bw_bs_median=55656 "\
    "desc_avg_bw_bs=1000000000 desc_obs_bw_bs_last=524288 "\
    "desc_obs_bw_bs_mean=524288 error_circ=0 error_misc=0 error_stream=1 " \
    "master_key_ed25519=g+Shk00y9Md0hg1S6ptnuc/wWKbADBgdjT0Kg+TSF3s " \
    "nick=A " \
    "node_id=$AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA rtt=456 success=1 " \
    "time=2018-04-17T14:09:07\n"

v3bw_str = header_extra_str + bwl_str


def test_v3bwheader_str():
    """Test header str"""
    header = V3BWHeader(timestamp_l, file_created=file_created)
    assert header_str == str(header)


def test_v3bwheader_extra_str():
    """Test header str with additional headers"""
    header = V3BWHeader(timestamp_l,
                        file_created=file_created,
                        generator_started=generator_started,
                        earliest_bandwidth=earliest_bandwidth)
    assert header_extra_str == str(header)


def test_v3bwheader_from_lines():
    """"""
    header_obj = V3BWHeader(timestamp_l,
                            file_created=file_created,
                            generator_started=generator_started,
                            earliest_bandwidth=earliest_bandwidth)
    header, _ = V3BWHeader.from_lines_v110(header_extra_ls)
    assert str(header_obj) == str(header)


def test_v3bwheader_from_text():
    """"""
    header_obj = V3BWHeader(timestamp_l,
                            file_created=file_created,
                            generator_started=generator_started,
                            earliest_bandwidth=earliest_bandwidth)
    header, _ = V3BWHeader.from_text_v110(header_extra_str)
    assert str(header_obj) == str(header)


def test_num_results_of_type(result_success, result_error_stream):
    assert num_results_of_type([result_success], 'success') == 1
    assert num_results_of_type([result_error_stream], 'success') == 0
    assert num_results_of_type([result_success], 'error-stream') == 0
    assert num_results_of_type([result_error_stream], 'error-stream') == 1


def test_v3bwline_from_results_file(datadir):
    lines = datadir.readlines('results.txt')
    d = dict()
    for line in lines:
        r = Result.from_dict(json.loads(line.strip()))
        fp = r.fingerprint
        if fp not in d:
            d[fp] = []
        d[fp].append(r)
    bwl = V3BWLine.from_data(d, fp)
    # bw store now B, not KB
    bwl.bw = round(bwl.bw / 1000)
    assert bwl_str == str(bwl)


def test_from_results_read(datadir, tmpdir, conf, args):
    results = load_result_file(str(datadir.join("results.txt")))
    expected_header = V3BWHeader(timestamp_l,
                                 earliest_bandwidth=earliest_bandwidth,
                                 latest_bandwidth=latest_bandwidth)
    expected_bwls = [V3BWLine.from_results(results[fp]) for fp in results]
    # bw store now B, not KB
    expected_bwls[0].bw = round(expected_bwls[0].bw / 1000)
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


def test_torflow_scale(datadir):
    results = load_result_file(str(datadir.join("results.txt")))
    v3bwfile = V3BWFile.from_results(results, scaling_method=TORFLOW_SCALING)
    assert v3bwfile.bw_lines[0].bw == 1000
    v3bwfile = V3BWFile.from_results(results, scaling_method=TORFLOW_SCALING,
                                     torflow_cap=0.0001)
    assert v3bwfile.bw_lines[0].bw == 1000
    v3bwfile = V3BWFile.from_results(results, scaling_method=TORFLOW_SCALING,
                                     torflow_cap=1, torflow_round_digs=0)
    assert v3bwfile.bw_lines[0].bw == 524


def test_results_away_each_other(datadir):
    min_num = 2
    secs_away = 86400  # 1d
    results = load_result_file(str(datadir.join("results_away.txt")))
    # A has 4 results, 3 are success, 2 are 1 day away, 1 is 12h away
    values = results["AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"]
    success_results = [r for r in values if isinstance(r, ResultSuccess)]
    assert len(success_results) >= min_num
    results_away = V3BWLine.results_away_each_other(success_results, secs_away)
    assert len(results_away) == 3
    # B has 2 results, 12h away from each other
    values = results["BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"]
    success_results = [r for r in values if isinstance(r, ResultSuccess)]
    assert len(success_results) >= min_num
    results_away = V3BWLine.results_away_each_other(success_results, secs_away)
    assert results_away is None
    secs_away = 43200  # 12h
    values = results["BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"]
    success_results = [r for r in values if isinstance(r, ResultSuccess)]
    assert len(success_results) >= min_num
    results_away = V3BWLine.results_away_each_other(success_results, secs_away)
    assert len(results_away) == 2
    # C has 1 result
    values = results["CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC"]
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
        line = V3BWLine.from_results(values)
        if line is not None:
            bw_lines_raw.append(line)
    assert len(bw_lines_raw) == 3
    bw_lines = V3BWFile.bw_torflow_scale(bw_lines_raw)
    assert len(bw_lines) == 3
    statsd, success = V3BWFile.measured_progress_stats(
        bw_lines, number_consensus_relays, min_perc_reached_before)
    assert success
    assert statsd == statsd_exp
    number_consensus_relays = 6
    statsd, success = V3BWFile.measured_progress_stats(
        bw_lines, number_consensus_relays, min_perc_reached_before)
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
    bwfile.update_progress(bw_lines_raw, header, number_consensus_relays,
                           state)
    assert header.percent_eligible_relays == '50'
    assert state.get('min_perc_reached') is None
    number_consensus_relays = 3
    header = V3BWHeader(str(now_unixts()))
    bwfile.update_progress(bw_lines_raw, header, number_consensus_relays,
                           state)
    assert state.get('min_perc_reached') == now_isodt_str()
    assert not hasattr(header, 'percent_eligible_relays')
