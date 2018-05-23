# -*- coding: utf-8 -*-
"""Test generation of bandwidth measurements document (v3bw)"""
from sbws.globals import SPEC_VERSION
from sbws.lib.v3bwfile import V3BwHeader, TERMINATOR, LINE_SEP, KEYVALUE_SEP_V110
from sbws import __version__ as version

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


def test_v3bwfile():
    """Test generate v3bw file (including relay_lines)."""
    pass
