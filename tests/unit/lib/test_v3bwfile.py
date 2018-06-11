# -*- coding: utf-8 -*-
"""Test generation of bandwidth measurements document (v3bw)"""
import json

from sbws import __version__ as version
from sbws.globals import SPEC_VERSION, RESULT_VERSION
from sbws.lib.resultdump import Result, load_result_file
from sbws.lib.v3bwfile import (V3BwHeader, V3BWLine, TERMINATOR, LINE_SEP,
                               KEYVALUE_SEP_V110, num_results_of_type,
                               V3BwFile)

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

bwl_str = "bw=54 error_circ=0 error_misc=0 error_stream=1 " \
    "master_key_ed25519=g+Shk00y9Md0hg1S6ptnuc/wWKbADBgdjT0Kg+TSF3s " \
    "nick=A " \
    "node_id=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA rtt=456 success=1 " \
    "time=2018-04-17T14:09:07\n"

v3bw_str = header_extra_str + bwl_str

RESULT_ERROR_STREAM_DICT = {
    "fingerprint": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
    "address": "111.111.111.111",
    "dest_url": "http://y.z",
    "time": 1526894062.6408398,
    "circ": ["AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
             "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"],
    "version": RESULT_VERSION,
    "scanner": "IDidntEditTheSBWSConfig",
    "type": "error-stream",
    "msg": "Something bad happened while measuring bandwidth",
    "nickname": "A",
    "master_key_ed25519": "g+Shk00y9Md0hg1S6ptnuc/wWKbADBgdjT0Kg+TSF3s"
}

RESULT_SUCCESS_DICT = {
    "fingerprint": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
    "address": "111.111.111.111",
    "dest_url": "http://y.z",
    "time": 1526894062.6408398,
    "rtts": [0.4596822261810303, 0.44872617721557617, 0.4563450813293457,
             0.44872212409973145, 0.4561030864715576, 0.4765200614929199,
             0.4495084285736084, 0.45711588859558105, 0.45520496368408203,
             0.4635589122772217],
    "circ": ["AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
             "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"],
    "version": RESULT_VERSION,
    "scanner": "IDidntEditTheSBWSConfig",
    "type": "success",
    "downloads": [
        {"amount": 590009, "duration": 6.1014368534088135},
        {"amount": 590009, "duration": 8.391342878341675},
        {"amount": 321663, "duration": 7.064587831497192},
        {"amount": 321663, "duration": 8.266003131866455},
        {"amount": 321663, "duration": 5.779450178146362}],
    "nickname": "A",
    "master_key_ed25519": "g+Shk00y9Md0hg1S6ptnuc/wWKbADBgdjT0Kg+TSF3s"
}
RESULT_SUCCESS_STR = str(RESULT_SUCCESS_DICT)
RESULT_ERROR_STREAM_STR = str(RESULT_ERROR_STREAM_DICT)


def test_v3bwheader_str():
    """Test header str"""
    header = V3BwHeader(timestamp_l, file_created=file_created)
    assert header_str == str(header)


def test_v3bwheader_extra_str():
    """Test header str with additional headers"""
    header = V3BwHeader(timestamp_l,
                        file_created=file_created,
                        generator_started=generator_started,
                        earliest_bandwidth=earliest_bandwidth)
    assert header_extra_str == str(header)


def test_v3bwheader_from_lines():
    """"""
    header_obj = V3BwHeader(timestamp_l,
                            file_created=file_created,
                            generator_started=generator_started,
                            earliest_bandwidth=earliest_bandwidth)
    header, _ = V3BwHeader.from_lines_v110(header_extra_ls)
    assert str(header_obj) == str(header)


def test_v3bwheader_from_text():
    """"""
    header_obj = V3BwHeader(timestamp_l,
                            file_created=file_created,
                            generator_started=generator_started,
                            earliest_bandwidth=earliest_bandwidth)
    header, _ = V3BwHeader.from_text_v110(header_extra_str)
    assert str(header_obj) == str(header)


def test_v3bwheader_from_file(datadir):
    """Test header str with additional headers"""
    header = V3BwHeader(timestamp_l,
                        file_created=file_created,
                        generator_started=generator_started,
                        earliest_bandwidth=earliest_bandwidth)
    text = datadir.read('v3bw.txt')
    h, _ = V3BwHeader.from_text_v110(text)
    assert str(h) == str(header)


def test_num_results_of_type():
    assert num_results_of_type([Result.from_dict(RESULT_SUCCESS_DICT)],
                               'success') == 1
    assert num_results_of_type([Result.from_dict(RESULT_ERROR_STREAM_DICT)],
                               'success') == 0
    assert num_results_of_type([Result.from_dict(RESULT_SUCCESS_DICT)],
                               'error-stream') == 0
    assert num_results_of_type([Result.from_dict(RESULT_ERROR_STREAM_DICT)],
                               'error-stream') == 1


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
    assert bwl_str == str(bwl)


def test_v3bwfile(datadir, tmpdir):
    """Test generate v3bw file (including relay_lines)."""
    v3bw = datadir.read('v3bw.txt')
    results = load_result_file(str(datadir.join("results.txt")))
    header = V3BwHeader(timestamp_l,
                        file_created=file_created,
                        generator_started=generator_started,
                        earliest_bandwidth=earliest_bandwidth)
    bwls = [V3BWLine.from_results(results[fp]) for fp in results]
    f = V3BwFile(header, bwls)
    assert v3bw == str(f)
