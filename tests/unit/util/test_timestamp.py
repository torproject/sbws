# -*- coding: utf-8 -*-
"""Test timestamp conversion util functions"""
from datetime import datetime, timezone, timedelta
from sbws.util.timestamp import (dt_obj_to_isodt_str, unixts_to_dt_obj,
                                 unixts_to_isodt_str, unixts_to_str, is_old)


isodt_str = '2018-05-23T12:55:04'
dt_obj = datetime.strptime(isodt_str, '%Y-%m-%dT%H:%M:%S')
unixts = int(dt_obj.replace(tzinfo=timezone.utc).timestamp())


def test_dt_obj_to_isodt_str():
    assert isodt_str == dt_obj_to_isodt_str(dt_obj)


def test_unixts_to_dt_obj():
    assert dt_obj == unixts_to_dt_obj(unixts)


def test_unixts_to_isodt_str():
    assert isodt_str == unixts_to_isodt_str(unixts)


def test_unixts_to_str():
    assert str(unixts) == unixts_to_str(unixts)


def test_is_old():
    # Since this timestamp is generated a few microseconds before checking
    # the oldest timestamp, it will be old.
    old_timestamp = datetime.utcnow() - timedelta(days=5)
    assert is_old(old_timestamp)
    # A recent timestamp should be at least 1 second newer that the oldest
    recent_timestamp = datetime.utcnow() - timedelta(days=5) \
        + timedelta(seconds=1)
    assert not is_old(recent_timestamp)
