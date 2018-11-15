# -*- coding: utf-8 -*-
"""Test destination"""
from sbws.lib.destination import Destination


def test_destination_port():
    d = Destination("http://whatever.example", 0, False)
    assert d.port == 80
    d = Destination("http://whatever.example:1111", 0, False)
    assert d.port == 1111
    d = Destination("https://whatever.example:1111", 0, False)
    assert d.port == 1111
    d = Destination("https://whatever.example", 0, False)
    assert d.port == 443
