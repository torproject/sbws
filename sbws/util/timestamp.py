"""Util functions to convert between timestamp formats"""
from datetime import datetime, timedelta

from ..globals import MEASUREMENTS_PERIOD


def dt_obj_to_isodt_str(dt):
    """
    Convert datetime object to ISO 8601 string.

    :param datetime dt: datetime object in UTC timezone
    :returns: ISO 8601 string
    """
    assert isinstance(dt, datetime)
    # Using naive datetime object without timezone, assumed utc
    return dt.replace(microsecond=0).isoformat()


def isostr_to_dt_obj(isostr):
    return datetime.strptime(isostr, "%Y-%m-%dT%H:%M:%S")


def unixts_to_dt_obj(unixts):
    """
    Convert unix timestamp to naive datetime object in UTC time zone.

    :param float/int/str unixts: unix timestamp
    :returns: datetime object in UTC timezone
    """
    if isinstance(unixts, str):
        try:
            unixts = int(unixts)
        except ValueError:
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


# XXX: tech-debt: replace all the code that check whether a
# measurement or relay is older than the measurement period by this.
def is_old(timestamp, measurements_period=MEASUREMENTS_PERIOD):
    """Whether the given timestamp is older that the given measurements
    period.
    """
    if not isinstance(timestamp, datetime):
        if isinstance(timestamp, str):
            # This will raise an exception if the string is not correctly
            # formatted.
            timestamp = isostr_to_dt_obj(timestamp)
        else:
            # This will raise an exception if the type is not int or float or
            # is not actually a timestamp
            timestamp = unixts_to_dt_obj(timestamp)
    oldest_date = datetime.utcnow() - timedelta(measurements_period)
    return timestamp > oldest_date
