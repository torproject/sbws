"""
Classes and functions to implement a heartbeat system to monitor the progress.
"""
import logging
import time

log = logging.getLogger(__name__)


def total_measured_percent(measured_percent, consensus_fp_set,
                           measured_fp_set, main_loop_tstart, loops_count):
    """Returns the new percentage of the different relays that were measured.

    This way it can be known whether the scanner is making progress measuring
    all the Network.

    Log the percentage, the number of relays measured and not measured,
    the number of loops and the time elapsed since it started measuring.
    """
    not_measured_fp_set = consensus_fp_set.difference(measured_fp_set)
    main_loop_tdelta = (time.monotonic() - main_loop_tstart) / 60
    new_measured_percent = round(
        len(measured_fp_set) / len(consensus_fp_set) * 100)
    log.info("Run %s main loops.", loops_count)
    log.info("Measured in total %s (%s%%) unique relays in %s minutes",
             len(measured_fp_set), new_measured_percent, main_loop_tdelta)
    log.info("%s relays still not measured.", len(not_measured_fp_set))
    # The case when it is equal will only happen when all the relays have been
    # measured.
    if (new_measured_percent <= measured_percent):
        log.warning("There is no progress measuring relays!.")
    return new_measured_percent
