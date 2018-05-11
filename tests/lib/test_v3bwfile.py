# -*- coding: utf-8 -*-
"""Test generation of bandwidth measurements document (v3bw)"""
from sbws.globals import SPEC_VERSION
from sbws.lib.v3bwfile import V3BwHeader, TERMINATOR, LINE_SEP, K_SEP_V110
from sbws import __version__ as version

timestamp = 1524661857
timestamp_l = str(timestamp)
version_l = K_SEP_V110.join(['version', SPEC_VERSION])
software_l = K_SEP_V110.join(['software', 'sbws'])
software_version_l = K_SEP_V110.join(['software_version', version])
header_ls = [timestamp_l, version_l, software_l, software_version_l,
             TERMINATOR]
header_str = LINE_SEP.join(header_ls) + LINE_SEP
earliest_bandwidth = '2018-04-16T14:09:07'
earliest_bandwidth_l = K_SEP_V110.join(['earliest_bandwidth',
                                        earliest_bandwidth])
generator_started = '2018-04-16T14:09:05'
generator_started_l = K_SEP_V110.join(['generator_started',
                                       generator_started])
header_extra_ls = [timestamp_l, version_l, software_l, software_version_l,
                   earliest_bandwidth_l, generator_started_l, TERMINATOR]
header_extra_str = LINE_SEP.join(header_extra_ls) + LINE_SEP


def test_v3bwheader_str():
    """Test header str"""
    header = V3BwHeader(timestamp)
    assert header_str == str(header)


def test_v3bwheader_extra_str():
    """Test header str with scanner_started and earliest_bandwidth"""
    header = V3BwHeader(timestamp, generator_started=generator_started,
                        earliest_bandwidth=earliest_bandwidth)
    assert header_extra_str == str(header)


def test_v3bwheader_from_lines():
    """"""
    header_obj = V3BwHeader(timestamp, generator_started=generator_started,
                            earliest_bandwidth=earliest_bandwidth)
    header, _ = V3BwHeader().from_lines_v110(header_extra_ls)
    assert str(header_obj) == str(header)


def test_v3bwheader_from_text():
    """"""
    header_obj = V3BwHeader(timestamp, generator_started=generator_started,
                            earliest_bandwidth=earliest_bandwidth)
    header, _ = V3BwHeader().from_text_v110(header_extra_str)
    assert str(header_obj) == str(header)


def test_v3bwfile():
    """Test generate v3bw file (including relay_lines)."""
    pass
