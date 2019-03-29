"""
Classes and functions to implement a heartbeat system to monitor the progress.
"""
import logging
import time

from ..util.state import State


log = logging.getLogger(__name__)


class Heartbeat(object):
    """
    Tracks current status of sbws and is capable of printing periodic
    information about the current state
    """

    def __init__(self, state_path):
        # Variable to count total progress in the last days:
        # In case it is needed to see which relays are not being measured,
        # store their fingerprint, not only their number.
        self.measured_fp_set = set()
        self.consensus_fp_set = set()
        self.measured_percent = 0
        self.main_loop_tstart = time.monotonic()

        self.state_dict = State(state_path)

        self.previous_measurement_percent = 0

    def register_measured_fpr(self, async_result):
        self.measured_fp_set.add(async_result)

    def register_consensus_fprs(self, relay_fprs):
        for r in relay_fprs:
            self.consensus_fp_set.add(r)

    def print_heartbeat_message(self):
        """Print the new percentage of the different relays that were measured.

        This way it can be known whether the scanner is making progress
        measuring all the Network.

        Log the percentage, the number of relays measured and not measured,
        the number of loops and the time elapsed since it started measuring.
        """
        loops_count = self.state_dict.get('recent_priority_list_count', 0)

        not_measured_fp_set = self.consensus_fp_set.difference(
            self.measured_fp_set
            )
        main_loop_tdelta = (time.monotonic() - self.main_loop_tstart) / 60
        new_measured_percent = round(
            len(self.measured_fp_set) / len(self.consensus_fp_set) * 100
            )

        log.info("Run %s main loops.", loops_count)
        log.info("Measured in total %s (%s%%) unique relays in %s minutes",
                 len(self.measured_fp_set), new_measured_percent,
                 main_loop_tdelta)
        log.info("%s relays still not measured.", len(not_measured_fp_set))

        # The case when it is equal will only happen when all the relays
        # have been measured.
        if (new_measured_percent <= self.previous_measurement_percent):
            log.warning("There is no progress measuring new unique relays.")

        self.previous_measurement_percent = new_measured_percent
