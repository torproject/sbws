# -*- coding: utf-8 -*-
"""Test generation of bandwidth measurements document (v3bw)"""
from sbws.lib.v3bwfile import V3BwHeader
from sbws import __version__ as version


def test_v3bwheader_str():
    """Test header str"""
    timestamp = 1524661857
    header = V3BwHeader(timestamp)
    assert str(header) == '{}\nversion=1.1.0 software=sbws ' \
                          'software_version={}\n'.format(timestamp, version)


def test_v3bwfile():
    """Test generate v3bw file (including relay_lines)."""
    pass
