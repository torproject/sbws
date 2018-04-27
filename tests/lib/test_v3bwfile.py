# -*- coding: utf-8 -*-
"""Test generation of bandwidth measurements document (v3bw)"""
from sbws.lib.v3bwfile import V3BwHeader
from sbws import __version__ as version


def test_v3bwheader_str():
    """Test header str"""
    timestamp = 1524661857
    header = V3BwHeader(timestamp)
    assert str(header) == '{}\nversion=1.1.0\nsoftware=sbws\n' \
                          'software_version={}\n'.format(timestamp, version)


def test_v3bwheader_earlier_result_str():
    """Test header str with earlier_result"""
    timestamp = 1524661857
    earlier_result_ts = 1523887747.2904038
    header = V3BwHeader(timestamp, earlier_result_ts=earlier_result_ts)
    assert str(header) == '{}\nearlier_result=1523887747.2904038' \
                          '{}\nversion=1.1.0\nsoftware=sbws\n' \
                          'software_version={}\n'.format(timestamp, version)


def test_v3bwheader_scanner_started_str():
    """Test header str with scanner_started"""
    timestamp = 1524661857
    scanner_started_ts = 1523887747.2904038
    header = V3BwHeader(timestamp, scanner_started_ts=scanner_started_ts)
    assert str(header) == '{}\nscanner_started=1523887747.2904038' \
                          '{}\nversion=1.1.0\nsoftware=sbws\n' \
                          'software_version={}\n'.format(timestamp, version)


def test_v3bwfile():
    """Test generate v3bw file (including relay_lines)."""
    pass
