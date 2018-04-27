# -*- coding: utf-8 -*-
"""Test generation of bandwidth measurements document (v3bw)"""
from sbws.lib.v3bwfile import V3BwHeader


def test_v3bwheader_str():
    """Test header str"""
    timestamp = 1524661857
    header = V3BwHeader(timestamp)
    assert str(header) == '{} version=1.1.0 software=sbws ' \
                          'software_version=0.1.0\n'.format(timestamp)


def test_v3bwfile():
    """Test generate v3bw file (including relay_lines)."""
    pass
