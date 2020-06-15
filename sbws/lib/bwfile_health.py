"""Expected bandwidth file values for KeyValues."""
# flake8: noqa: E741
# (E741 ambiguous variable name), when using l.
import logging

from stem import descriptor

from sbws.globals import (
    PERIOD_DAYS,
    FRACTION_RELAYS,
    MAX_RECENT_PRIORITY_RELAY_COUNT,  # 48000
    MAX_RECENT_PRIORITY_LIST_COUNT,  # 120
    MAX_RECENT_CONSENSUS_COUNT,  # 120
)
from sbws.lib.v3bwfile import HEADER_INT_KEYS, BWLINE_KEYS_V1_4

logging.basicConfig(level=logging.INFO,)
logger = logging.getLogger(__name__)


# Based on observation
MAX_HOURS_PRIORITY_LIST = 5
MIN_RECENT_CONSENSUS_COUNT = PERIOD_DAYS * 12  # 60
MIN_RELAYS = 6000
# 24
MIN_RECENT_PRIORITY_LIST_COUNT = PERIOD_DAYS * 24 / MAX_HOURS_PRIORITY_LIST
MIN_RELAYS_PER_PRIORITY_LIST = int(MIN_RELAYS * FRACTION_RELAYS)  # 300
# 7200
MIN_RECENT_PRIORITY_RELAY_COUNT = (
    MIN_RECENT_PRIORITY_LIST_COUNT * MIN_RELAYS_PER_PRIORITY_LIST
)
# If the number of attempts is not equal to the number of relays being in the
# priority list, there's a bug.
MIN_RECENT_MEASUREMENT_ATTEMPT_COUNT = MIN_RECENT_PRIORITY_RELAY_COUNT
MAX_RECENT_MEASUREMENT_ATTEMPT_COUNT = MAX_RECENT_PRIORITY_RELAY_COUNT

# noqa
REPORT_TEMPLATE_BWFILE = (
    "sum(relay_recent_measurement_attempt_count) "
    "<= recent_measurement_attempt_count, "
    "{self.is_sum_relay_recent_measurement_attempt_count_lte_recent_measurement_attempt_count}\n"  # noqa
)

REPORT_TEMPLATE_BWHEADER = """
Header,
recent_consensus_count >= min, {self.is_consensus_gte_min}
recent_consensus_count <= max, {self.is_consensus_lte_max}
recent_priority_list_count >= min, {self.is_priority_list_gte_min}
recent_priority_list_count <= max, {self.is_priority_list_lte_max}
recent_priority_relay_count >= min, {self.is_priority_relay_gte_min}
recent_priority_relay_count <= max, {self.is_priority_relay_lte_max}
""" + (
    "recent_measurement_attempt_count >= min, "
    "{self.is_measurement_attempt_gte_min}\n"
    "recent_measurement_attempt_count <= max, "
    "{self.is_measurement_attempt_lte_max}\n"
    "recent_measurement_attempt_count == recent_priority_relay_count, "
    "{self.is_attempt_e_priority_relay}\n"
    "recent_measurement_attempt_count >= total excluded, "
    "{self.is_attempt_gte_failure_exclude}\n"
)


REPORT_TEMPLATE_BWLINES = """
relays correct, {self.are_bwlines_correct}
"""

REPORT_TEMPLATE_BWLINE = """
relay_recent_measurement_attempt_count <= relay_recent_priority_list_count,
{self.is_relay_recent_measurement_attempt_count_lte_relay_recent_priority_list_count}
relay_recent_priority_list_count <= relay_recent_consensus_count,
{self.is_relay_recent_priority_list_count_lte_relay_recent_consensus_count}
"""


class BwFile:
    def __init__(self, header, bwlines):
        self.header = BwHeader(header)
        self.bwlines = [BwLine(line) for line in bwlines]

    @classmethod
    def load(cls, file_path):
        logger.info("Parsing content of %s.", file_path)
        document = descriptor.parse_file(file_path)
        bwfiles = list(document)
        if bwfiles:
            # When parsing one file, there is only 1 bwfile
            bwfile = bwfiles[0]
            return cls(bwfile.header, bwfile.measurements.values())

    @property
    def sum_relay_recent_measurement_attempt_count(self):
        return sum(
            [l.relay_recent_measurement_attempt_count for l in self.bwlines]
        )

    @property
    def is_sum_relay_recent_measurement_attempt_count_lte_recent_measurement_attempt_count(  # noqa
        self,
    ):
        return (
            self.sum_relay_recent_measurement_attempt_count
            <= self.header.recent_measurement_attempt_count
        )

    @property
    def are_bwlines_correct(self):
        return not list(filter(lambda x: not x.is_correct, self.bwlines))

    @property
    def is_correct(self):
        methods = [m for m in dir(self) if m.startswith("is_")]
        methods.remove("is_correct")
        return not list(filter(lambda x: not getattr(self, x), methods))

    @property
    def report(self):
        print(REPORT_TEMPLATE_BWFILE.format(self=self))
        self.header.report
        print(REPORT_TEMPLATE_BWLINES.format(self=self))


class BwLine:
    def __init__(self, line):
        for k, v in line.items():
            if k in BWLINE_KEYS_V1_4:
                setattr(self, k, int(v))
            else:
                setattr(self, k, v)

    @property
    def is_relay_recent_priority_list_count_lte_relay_recent_consensus_count(
        self,
    ):
        return (
            self.relay_recent_priority_list_count
            <= self.relay_in_recent_consensus_count
        )

    @property
    def is_relay_recent_measurement_attempt_count_lte_relay_recent_priority_list_count(  # noqa
        self,
    ):
        return (
            self.relay_recent_measurement_attempt_count
            <= self.relay_recent_priority_list_count
        )

    def is_relay_recent_consensus_count_lte_recent_consensus_count(
        self, recent_consensus_count
    ):
        return self.relay_in_recent_consensus_count <= recent_consensus_count

    @property
    def is_correct(self):
        methods = [m for m in dir(self) if m.startswith("is_")]
        methods.remove("is_correct")
        return not list(filter(lambda x: not getattr(self, x), methods))

    @property
    def report(self):
        print(REPORT_TEMPLATE_BWLINE.format(self=self))


class BwHeader:
    def __init__(self, header):
        for k, v in header.items():
            if k in HEADER_INT_KEYS:
                setattr(self, k, int(v))
            else:
                setattr(self, k, v)
        # logger.info(self.__dict__)

    @classmethod
    def load(cls, file_path):
        logger.info("Parsing content of %s.", file_path)
        document = descriptor.parse_file(file_path)
        bwfiles = list(document)
        if bwfiles:
            bwfile = bwfiles[0]
            return cls(bwfile.header)

    @property
    def is_consensus_lte_max(self):
        return self.recent_consensus_count <= MAX_RECENT_CONSENSUS_COUNT

    @property
    def is_consensus_gte_min(self):
        return self.recent_consensus_count >= MIN_RECENT_CONSENSUS_COUNT

    @property
    def is_priority_list_lte_max(self):
        return (
            self.recent_priority_list_count <= MAX_RECENT_PRIORITY_LIST_COUNT
        )

    @property
    def is_priority_list_gte_min(self):
        return (
            self.recent_priority_list_count >= MIN_RECENT_PRIORITY_LIST_COUNT
        )

    @property
    def is_priority_relay_lte_max(self):
        return (
            self.recent_priority_relay_count <= MAX_RECENT_PRIORITY_RELAY_COUNT
        )

    @property
    def is_priority_relay_gte_min(self):
        return (
            self.recent_priority_relay_count >= MIN_RECENT_PRIORITY_RELAY_COUNT
        )

    @property
    def is_measurement_attempt_gte_min(self):
        return (
            self.recent_measurement_attempt_count
            >= MIN_RECENT_MEASUREMENT_ATTEMPT_COUNT
        )

    @property
    def is_measurement_attempt_lte_max(self):
        return (
            self.recent_measurement_attempt_count
            <= MAX_RECENT_MEASUREMENT_ATTEMPT_COUNT
        )

    @property
    def is_attempt_e_priority_relay(self):
        return (
            self.recent_measurement_attempt_count
            == self.recent_priority_relay_count
        )

    @property
    def is_attempt_gte_failure(self):
        return (
            self.recent_measurement_attempt_count
            >= self.recent_measurement_failure_count
        )

    @property
    def total_excluded(self):
        return sum(
            [
                self.recent_measurements_excluded_error_count,
                self.recent_measurements_excluded_few_count,
                self.recent_measurements_excluded_near_count,
                self.recent_measurements_excluded_old_count,
            ]
        )

    @property
    def total_excluded_failure(self):
        return sum(
            [self.total_excluded, self.recent_measurement_failure_count]
        )

    @property
    def is_attempt_gte_failure_exclude(self):
        return (
            self.recent_measurement_attempt_count
            >= self.total_excluded_failure
        )

    @property
    def is_correct(self):
        methods = [m for m in dir(self) if m.startswith("is_")]
        methods.remove("is_correct")
        return not list(filter(lambda x: not getattr(self, x), methods))

    @property
    def report(self):
        print(REPORT_TEMPLATE_BWHEADER.format(self=self))
