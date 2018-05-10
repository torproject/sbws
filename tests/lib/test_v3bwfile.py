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


def test_v3bwheader_earliest_bandwidth_str():
    """Test header str with earliest_bandwidth"""
    timestamp = 1524661857
    earliest_bandwidth = 1523887747.2904038
    header = V3BwHeader(timestamp, earliest_bandwidth=earliest_bandwidth)
    assert str(header) == '{}\nearliest_bandwidth=1523887747.2904038' \
                          '{}\nversion=1.1.0\nsoftware=sbws\n' \
                          'software_version={}\n'.format(timestamp, version)


def test_v3bwheader_scanner_started_str():
    """Test header str with scanner_started"""
    timestamp = 1524661857
    generator_started = 1523887747.2904038
    header = V3BwHeader(timestamp, generator_started=generator_started)
    assert str(header) == '{}\nscanner_started=1523887747.2904038' \
                          '{}\nversion=1.1.0\nsoftware=sbws\n' \
                          'software_version={}\n'.format(timestamp, version)


def test_v3bwheader_earliest_bandwidth_str():
    """Test header str with earliest_bandwidth"""
    timestamp = 1524661857
    earliest_bandwidth = 1523887747.2904038
    header = V3BwHeader(timestamp, earliest_bandwidth=earliest_bandwidth)
    assert str(header) == '{}\nearliest_bandwidth=1523887747.2904038 ' \
        'software=sbws software_version=0.1.0 ' \
        'timestamp=1524661857 version=1.1.0\n'.format(timestamp)


def test_v3bwfile():
    """Test generate v3bw file (including relay_lines)."""
    pass
