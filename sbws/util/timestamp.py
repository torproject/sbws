"""Util functions to convert between timestamp formats"""
from datetime import datetime


def dt_obj_to_isodt_str(dt):
    """
    Convert datetime object to ISO 8601 string.

    :param datetime dt: datetime object in UTC timezone
    :returns: ISO 8601 string
    """
    assert isinstance(dt, datetime)
    # Using naive datetime object without timezone, assumed utc
    return dt.replace(microsecond=0).isoformat()


def unixts_to_dt_obj(unixts):
    """
    Convert unix timestamp to naive datetime object in UTC time zone.

    :param float/int/str unixts: unix timestamp
    :returns: datetime object in UTC timezone
    """
    if isinstance(unixts, str):
        try:
            unixts = int(unixts)
        except ValueError as e:
            unixts = float(unixts)
    if isinstance(unixts, float):
        unixts = int(unixts)
    assert isinstance(unixts, int)
    return datetime.utcfromtimestamp(unixts)


def unixts_to_isodt_str(unixts):
    """
    Convert unix timestamp to ISO 8601 string in UTC time zone.

    :param float/int/str unixts: unix timestamp
    :returns: ISO 8601 string in UTC time zone
    """
    return dt_obj_to_isodt_str(unixts_to_dt_obj(unixts))


def now_unixts():
    return datetime.utcnow().timestamp()


def now_isodt_str():
    """Return datetime now as ISO 8601 string in UTC time zone."""
    return dt_obj_to_isodt_str(datetime.utcnow())


def now_fname():
    """
    Return now timestamp in UTC formatted as %Y%m%d_%H%M%S string for file
    names.

    :returns: now timestamp in UTC formatted as %Y%m%d_%H%M%S string
    """
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")


def unixts_to_str(unixts):
    """Convert unix timestamp integer or float to string"""
    # even if it is only converting to str, ensure that input is nothing else
    # than int or float
    assert isinstance(unixts, int) or isinstance(unixts, float)
    return str(unixts)
