# -*- coding: utf-8 -*-
"""Test generation of bandwidth measurements document (v3bw)"""
import json
import os.path

from sbws import __version__ as version
from sbws.globals import SPEC_VERSION, SBWS_SCALING, TORFLOW_SCALING
from sbws.lib.resultdump import Result, load_result_file
from sbws.lib.v3bwfile import (V3BWHeader, V3BWLine, TERMINATOR, LINE_SEP,
                               KEYVALUE_SEP_V110, num_results_of_type,
                               V3BWFile)
from sbws.util.timestamp import now_fname

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
    v3bwfile = V3BWFile.from_results(results, scaling_method=SBWS_SCALING)
    assert v3bwfile.bw_lines[0].bw == 8
