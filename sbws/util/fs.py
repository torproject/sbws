"""Utils file system functions"""

import logging
import shutil

log = logging.getLogger(__name__)


def sbws_required_disk_space(conf):
    """Disk space required by sbws files.
    Rough calculations.

    :param ConfigParser conf: sbws configuration
    :returns: int, size in MiB
    """
    # Number of relays per line average size in Bytes
    size_v3bw_file = 7500 * 220
    # the minimum number of required v3bw files
    num_v3bw_files = 2
    # ~1000 is the length of a line when the result is successfull
    # ~4550 is the number of lines of the biggest result file
    size_result_file = 4550 * 1000
    num_result_files = int(conf['general']['data_period'])
    # not counting compressed files
    space_v3bw_files = size_v3bw_file * num_v3bw_files
    space_result_files = size_result_file * num_result_files
    # not counted rotated files and assuming that when it is not rotated the
    # size will be aproximately 10MiB
    size_log_file = conf.getint('logging', 'to_file_max_bytes') or 10485760 \
        if conf.getboolean('logging', 'to_stdout') else 0
    # roughly, size of a current tor dir
    space_tor_dir = 19828000
    # duplicate everything to warn early
    size_total = (space_v3bw_files + size_log_file + space_result_files) * 2
    size_total_mb = round(size_total / (1024 ** 2))
    return size_total_mb


def df(path):
    """Return space left on device where path is."""
    return round(shutil.disk_usage(path).free / (1024 ** 2))


def is_low_space(conf):
    """Warn and return True when the space left on the device is less than
    what is needed for sbws and False otherwise needs.
    """
    disk_required_mb = sbws_required_disk_space(conf)
    disk_avail_mb = df(conf['paths']['sbws_home'])
    if disk_avail_mb < disk_required_mb:
        log.warn("The space left on the device (%s MiB) is less than "
                 "the minimum recommented to run sbws (%s MiB)."
                 "Run sbws cleanup to delete old sbws generated files.",
                 disk_avail_mb, disk_required_mb)
        return True
    return False
