"""
Classes and functions to implement a heartbeat system to monitor the progress.
"""
import logging
import time

from ..util.state import State


log = logging.getLogger(__name__)

# NOTE tech-debt: this could go be tracked globally as a singleton
consensus_fp_set = set()


def total_measured_percent(measured_percent, relays_fingerprints,
                           measured_fp_set, main_loop_tstart, state_path):
    """Returns the new percentage of the different relays that were measured.

    This way it can be known whether the scanner is making progress measuring
    all the Network.

    Log the percentage, the number of relays measured and not measured,
    the number of loops and the time elapsed since it started measuring.
    """
    global consensus_fp_set
    # NOTE: in a future refactor make State a singleton in __init__.py
    state_dict = State(state_path)
    loops_count = state_dict.get('recent_priority_list_count', 0)

    # Store all the relays seen in all the consensuses.
    [consensus_fp_set.add(r) for r in relays_fingerprints]

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
