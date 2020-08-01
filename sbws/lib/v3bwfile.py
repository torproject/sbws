# -*- coding: utf-8 -*-
"""Classes and functions that create the bandwidth measurements document
(v3bw) used by bandwidth authorities."""
# flake8: noqa: E741
# (E741 ambiguous variable name), when using l.

import copy
import logging
import math
import os
from itertools import combinations
from statistics import median, mean
from stem.descriptor import parse_file

from sbws import __version__
from sbws.globals import (SPEC_VERSION, BW_LINE_SIZE, SBWS_SCALE_CONSTANT,
                          TORFLOW_SCALING, SBWS_SCALING, TORFLOW_BW_MARGIN,
                          TORFLOW_OBS_LAST, TORFLOW_OBS_MEAN,
                          PROP276_ROUND_DIG, MIN_REPORT, MAX_BW_DIFF_PERC)
from sbws.lib import scaling
from sbws.lib.resultdump import ResultSuccess, _ResultType
from sbws.util.filelock import DirectoryLock
from sbws.util.timestamp import (now_isodt_str, unixts_to_isodt_str,
                                 now_unixts, isostr_to_dt_obj,
                                 dt_obj_to_isodt_str)
from sbws.util.state import State

log = logging.getLogger(__name__)

LINE_SEP = '\n'
KEYVALUE_SEP_V1 = '='
KEYVALUE_SEP_V2 = ' '

# NOTE: in a future refactor make make all the KeyValues be a dictionary
# with their type, so that it's more similar to stem parser.

# Header KeyValues
# =================
# KeyValues that need to be in a specific order in the Bandwidth File.
HEADER_KEYS_V1_1_ORDERED = ['version']
# KeyValues that are not initialized from the state file nor the measurements.
# They can also be pass as an argument to `Header` to overwrite default values,
# what is done in unit tests.
# `latest bandwidth` is special cause it gets its value from timestamp, which
# is not a KeyValue, but it's always pass as an agument.
# It could be separaed in other list, but so far there is no need, cause:
# 1. when it's pass to the Header to initialize it, it's just ignored.
# 2. when the file is created, it's took into account.
HEADER_KEYS_V1_1_SELF_INITIALIZED = [
    "software",
    "software_version",
    "file_created",
    "latest_bandwidth",
]
# KeyValues that are initialized from arguments.
HEADER_KEYS_V1_1_TO_INIT = [
    "earliest_bandwidth",
    "generator_started",
]

# number_eligible_relays is the number that ends in the bandwidth file
# ie, have not been excluded by one of the filters in 4. below
# They should be call recent_measurement_included_count to be congruent
# with the other KeyValues.
HEADER_KEYS_V1_2 = [
    "number_eligible_relays",
    "minimum_number_eligible_relays",
    "number_consensus_relays",
    "percent_eligible_relays",
    "minimum_percent_eligible_relays",
]

# KeyValues added in the Bandwidth File v1.3.0
HEADER_KEYS_V1_3 = [
    "scanner_country",
    "destinations_countries",
]

# KeyValues that count the number of relays that are in the bandwidth file,
# but ignored by Tor when voting, because they do not have a
# measured bandwidth.
HEADER_RECENT_MEASUREMENTS_EXCLUDED_KEYS = [
    # Number of relays that were measured but all the measurements failed
    # because of network failures or it was
    # not found a suitable helper relay
    'recent_measurements_excluded_error_count',
    # Number of relays that have successful measurements but the measurements
    # were not away from each other in X time (by default 1 day).
    'recent_measurements_excluded_near_count',
    # Number of relays that have successful measurements and they are away from
    # each other but they are not X time recent.
    # By default this is 5 days, which is the same time the older
    # the measurements can be by default.
    'recent_measurements_excluded_old_count',
    # Number of relays that have successful measurements and they are away from
    # each other and recent
    # but the number of measurements are less than X (by default 2).
    'recent_measurements_excluded_few_count',
]
# Added in #29591
# NOTE: recent_consensus_count, recent_priority_list_count,
# recent_measurement_attempt_count and recent_priority_relay_count
# are not reset when the scanner is stop.
# They will accumulate the values since the scanner was ever started.
HEADER_KEYS_V1_4 = [
    # 1.1 header: the number of different consensuses, that sbws has seen,
    # since the last 5 days
    'recent_consensus_count',
    # 2.4 Number of times a priority list has been created
    'recent_priority_list_count',
    # 2.5 Number of relays that there were in a priority list
    # [50, number of relays in the network * 0.05]
    'recent_priority_relay_count',
    # 3.6 header: the number of times that sbws has tried to measure any relay,
    # since the last 5 days
    # This would be the number of times a relays were in a priority list
    'recent_measurement_attempt_count',
    # 3.7 header: the number of times that sbws has tried to measure any relay,
    # since the last 5 days, but it didn't work
    # This should be the number of attempts - number of ResultSuccess -
    # something else we don't know yet
    # So far is the number of ResultError
    'recent_measurement_failure_count',
    # The time it took to report about half of the network.
    'time_to_report_half_network',
] + HEADER_RECENT_MEASUREMENTS_EXCLUDED_KEYS

# KeyValues added in the Bandwidth File v1.5.0
# XXX: Change SPEC_VERSION when all the v1.5.0 keys are added, before a new
# sbws release.
# Tor version will be obtained from the state file, so it won't be pass as an
# argument, but will be self-initialized.
HEADER_KEYS_V1_5_TO_INIT = ['tor_version']
HEADER_KEYS_V1_5 = HEADER_KEYS_V1_5_TO_INIT

# KeyValues that are initialized from arguments, not self-initialized.
HEADER_INIT_KEYS = (
    HEADER_KEYS_V1_1_TO_INIT
    + HEADER_KEYS_V1_3
    + HEADER_KEYS_V1_2
    + HEADER_KEYS_V1_4
    + HEADER_KEYS_V1_5_TO_INIT
)

HEADER_INT_KEYS = HEADER_KEYS_V1_2 + HEADER_KEYS_V1_4
# List of all unordered KeyValues currently being used to generate the file
HEADER_UNORDERED_KEYS = (
    HEADER_KEYS_V1_1_SELF_INITIALIZED
    + HEADER_KEYS_V1_1_TO_INIT
    + HEADER_KEYS_V1_3
    + HEADER_KEYS_V1_2
    + HEADER_KEYS_V1_4
    + HEADER_KEYS_V1_5
)
# List of all the KeyValues currently being used to generate the file
HEADER_ALL_KEYS = HEADER_KEYS_V1_1_ORDERED + HEADER_UNORDERED_KEYS

TERMINATOR = '====='

# Bandwidth Lines KeyValues
# =========================
# Num header lines in v1.X.X using all the KeyValues
NUM_LINES_HEADER_V1 = len(HEADER_ALL_KEYS) + 2
LINE_TERMINATOR = TERMINATOR + LINE_SEP

# KeyValue separator in Bandwidth Lines
BWLINE_KEYVALUES_SEP_V1 = ' '
# not inclding in the files the extra bws for now
BWLINE_KEYS_V0 = ['node_id', 'bw']
BWLINE_KEYS_V1_1 = [
    "master_key_ed25519",
    "nick",
    "rtt",
    "time",
    "success",
    "error_stream",
    "error_circ",
    "error_misc",
    # Added in #292951
    "error_second_relay",
    "error_destination",
]
BWLINE_KEYS_V1_2 = [
    "bw_median",
    "bw_mean",
    "desc_bw_avg",
    "desc_bw_bur",
    "desc_bw_obs_last",
    "desc_bw_obs_mean",
    "consensus_bandwidth",
    "consensus_bandwidth_is_unmeasured",
]

# There were no bandwidth lines key added in the specification version 1.3

# Added in #292951
BWLINE_KEYS_V1_4 = [
    # 1.2 relay: the number of different consensuses, that sbws has seen,
    # since the last 5 days, that have this relay
    'relay_in_recent_consensus_count',
    # 2.6 relay: the number of times a relay was "prioritized" to be measured
    # in the recent days (by default 5).
    'relay_recent_priority_list_count',
    # 3.8 relay:  the number of times that sbws has tried to measure
    # this relay, since the last 5 days
    # This would be the number of times a relay was in a priority list (2.6)
    # since once it gets measured, it either returns ResultError,
    # ResultSuccess or something else happened that we don't know yet
    'relay_recent_measurement_attempt_count',
    # 3.9 relay:  the number of times that sbws has tried to measure
    # this relay, since the last 5 days, but it didn't work
    # This should be the number of attempts - number of ResultSuccess -
    # something else we don't know yet
    # So far is the number of ResultError
    'relay_recent_measurement_failure_count',
    # Number of error results created in the last 5 days that are excluded.
    # This is the sum of all the errors.
    'relay_recent_measurements_excluded_error_count',
    # The number of successful results, created in the last 5 days,
    # that were excluded by a rule, for this relay.
    # 'relay_recent_measurements_excluded_error_count' would be the
    # sum of the following 3 + the number of error results.

    # The number of successful measurements that are not X time away
    # from each other (by default 1 day).
    'relay_recent_measurements_excluded_near_count',
    # The number of successful measurements that are away from each other
    # but not X time recent (by default 5 days).
    'relay_recent_measurements_excluded_old_count',
    # The number of measurements excluded because they are not at least X
    # (by default 2).
    'relay_recent_measurements_excluded_few_count',
    # `vote=0` is used for the relays that were excluded to
    # be reported in the bandwidth file and now they are
    # reported.
    # It tells Tor to do not vote on the relay.
    # `unmeasured=1` is used for the same relays and it is
    # added in case Tor would vote on them in future versions.
    # Maybe these keys should not be included for the relays
    # in which vote=1 and unmeasured=0.
    'vote', 'unmeasured',
    # When there not enough eligible relays (not excluded)
    # under_min_report is 1, `vote` is 0.
    # Added in #29853.
    'under_min_report',
]
BWLINE_KEYS_V1 = BWLINE_KEYS_V0 + BWLINE_KEYS_V1_1 + BWLINE_KEYS_V1_2 \
               + BWLINE_KEYS_V1_4
# NOTE: tech-debt: assign boolean type to vote and unmeasured,
# when the attributes are defined with a type, as stem does.
BWLINE_INT_KEYS = (
    [
        "bw",
        "rtt",
        "success",
        "error_stream",
        "error_circ",
        "error_misc",
    ]
    + BWLINE_KEYS_V1_2
    + BWLINE_KEYS_V1_4
)
# This is boolean, not int.
BWLINE_INT_KEYS.remove('consensus_bandwidth_is_unmeasured')


def round_sig_dig(n, digits=PROP276_ROUND_DIG):
    """Round n to 'digits' significant digits in front of the decimal point.
       Results less than or equal to 1 are rounded to 1.
       Returns an integer.

       digits must be greater than 0.
       n must be less than or equal to 2**73, to avoid floating point errors.
       """
    digits = int(digits)
    assert digits >= 1
    if n <= 1:
        return 1
    digits_in_n = int(math.log10(n)) + 1
    round_digits = max(digits_in_n - digits, 0)
    rounded_n = round(n, -round_digits)
    return int(rounded_n)


def kb_round_x_sig_dig(bw_bs, digits=PROP276_ROUND_DIG):
    """Convert bw_bs from bytes to kilobytes, and round the result to
       'digits' significant digits.
       Results less than or equal to 1 are rounded up to 1.
       Returns an integer.

       digits must be greater than 0.
       n must be less than or equal to 2**82, to avoid floating point errors.
       """
    # avoid double-rounding by using floating-point
    bw_kb = bw_bs / 1000.0
    return round_sig_dig(bw_kb, digits=digits)


def num_results_of_type(results, type_str):
    return len([r for r in results if r.type == type_str])


# Better way to use enums?
def result_type_to_key(type_str):
    return type_str.replace('-', '_')


class V3BWHeader(object):
    """
    Create a bandwidth measurements (V3bw) header
    following bandwidth measurements document spec version 1.X.X.

    :param str timestamp: timestamp in Unix Epoch seconds of the most recent
        generator result.
    :param str version: the spec version
    :param str software: the name of the software that generates this
    :param str software_version: the version of the software
    :param dict kwargs: extra headers. Currently supported:

        - earliest_bandwidth: str, ISO 8601 timestamp in UTC time zone
          when the first bandwidth was obtained
        - generator_started: str, ISO 8601 timestamp in UTC time zone
          when the generator started
    """
    def __init__(self, timestamp, **kwargs):
        assert isinstance(timestamp, str)
        for v in kwargs.values():
            assert isinstance(v, str)
        self.timestamp = timestamp
        # KeyValues with default value when not given by kwargs
        self.version = kwargs.get('version', SPEC_VERSION)
        self.software = kwargs.get('software', 'sbws')
        self.software_version = kwargs.get('software_version', __version__)
        self.file_created = kwargs.get('file_created', now_isodt_str())
        # latest_bandwidth should not be in kwargs, since it MUST be the
        # same as timestamp
        self.latest_bandwidth = unixts_to_isodt_str(timestamp)
        [setattr(self, k, v) for k, v in kwargs.items()
         if k in HEADER_INIT_KEYS]

    def __str__(self):
        if self.version.startswith('1.'):
            return self.strv1
        return self.strv2

    @classmethod
    def from_results(cls, results, scanner_country=None,
                     destinations_countries=None, state_fpath=''):
        kwargs = dict()
        latest_bandwidth = cls.latest_bandwidth_from_results(results)
        earliest_bandwidth = cls.earliest_bandwidth_from_results(results)
        # NOTE: Blocking, reads file
        generator_started = cls.generator_started_from_file(state_fpath)
        recent_consensus_count = cls.consensus_count_from_file(state_fpath)
        timestamp = str(latest_bandwidth)

        # XXX: tech-debt: obtain the other values from the state file using
        # this state variable.
        # Store the state as an attribute of the object?
        state = State(state_fpath)
        tor_version = state.get('tor_version', None)
        if tor_version:
            kwargs['tor_version'] = tor_version

        kwargs['latest_bandwidth'] = unixts_to_isodt_str(latest_bandwidth)
        kwargs['earliest_bandwidth'] = unixts_to_isodt_str(earliest_bandwidth)
        if generator_started is not None:
            kwargs['generator_started'] = generator_started
        # To be compatible with older bandwidth files, do not require it.
        if scanner_country is not None:
            kwargs['scanner_country'] = scanner_country
        if destinations_countries is not None:
            kwargs['destinations_countries'] = destinations_countries
        if recent_consensus_count is not None:
            kwargs['recent_consensus_count'] = recent_consensus_count

        recent_measurement_attempt_count = \
            cls.recent_measurement_attempt_count_from_file(state_fpath)
        if recent_measurement_attempt_count is not None:
            kwargs['recent_measurement_attempt_count'] = \
                str(recent_measurement_attempt_count)

        # If it is a failure that is not a ResultError, then
        # failures = attempts - all mesaurements
        # Works only in the case that old measurements files already had
        # measurements count
        # If this is None or 0, the failures can't be calculated
        if recent_measurement_attempt_count:
            all_measurements = 0
            for result_list in results.values():
                all_measurements += len(result_list)
            measurement_failures = (recent_measurement_attempt_count
                                    - all_measurements)
            kwargs['recent_measurement_failure_count'] = \
                str(measurement_failures)

        priority_lists = cls.recent_priority_list_count_from_file(state_fpath)
        if priority_lists is not None:
            kwargs['recent_priority_list_count'] = str(priority_lists)

        priority_relays = \
            cls.recent_priority_relay_count_from_file(state_fpath)
        if priority_relays is not None:
            kwargs['recent_priority_relay_count'] = str(priority_relays)

        h = cls(timestamp, **kwargs)
        return h

    @classmethod
    def from_lines_v1(cls, lines):
        """
        :param list lines: list of lines to parse
        :returns: tuple of V3BWHeader object and non-header lines
        """
        assert isinstance(lines, list)
        try:
            index_terminator = lines.index(TERMINATOR)
        except ValueError:
            # is not a bw file or is v100
            log.warn('Terminator is not in lines')
            return None
        ts = lines[0]
        kwargs = dict([l.split(KEYVALUE_SEP_V1)
                       for l in lines[:index_terminator]
                       if l.split(KEYVALUE_SEP_V1)[0] in HEADER_ALL_KEYS])
        h = cls(ts, **kwargs)
        # last line is new line
        return h, lines[index_terminator + 1:-1]

    @classmethod
    def from_text_v1(self, text):
        """
        :param str text: text to parse
        :returns: tuple of V3BWHeader object and non-header lines
        """
        assert isinstance(text, str)
        return self.from_lines_v1(text.split(LINE_SEP))

    @classmethod
    def from_lines_v100(cls, lines):
        """
        :param list lines: list of lines to parse
        :returns: tuple of V3BWHeader object and non-header lines
        """
        assert isinstance(lines, list)
        h = cls(lines[0])
        # last line is new line
        return h, lines[1:-1]

    @staticmethod
    def generator_started_from_file(state_fpath):
        '''
        ISO formatted timestamp for the time when the scanner process most
        recently started.
        '''
        state = State(state_fpath)
        if 'scanner_started' in state:
            # From v1.1.0-dev `state` is capable of converting strs to datetime
            return dt_obj_to_isodt_str(state['scanner_started'])
        else:
            return None

    @staticmethod
    def consensus_count_from_file(state_fpath):
        state = State(state_fpath)
        count = state.count("recent_consensus")
        if count:
            return str(count)
        return None

    # NOTE: in future refactor store state in the class
    @staticmethod
    def recent_measurement_attempt_count_from_file(state_fpath):
        """
        Returns the number of times any relay was queued to be measured
        in the recent (by default 5) days from the state file.
        """
        state = State(state_fpath)
        return state.count('recent_measurement_attempt')

    @staticmethod
    def recent_priority_list_count_from_file(state_fpath):
        """
        Returns the number of times
        :meth:`~sbws.lib.relayprioritizer.RelayPrioritizer.best_priority`
        was run
        in the recent (by default 5) days from the state file.
        """
        state = State(state_fpath)
        return state.count('recent_priority_list')

    @staticmethod
    def recent_priority_relay_count_from_file(state_fpath):
        """
        Returns the number of times any relay was "prioritized" to be measured
        in the recent (by default 5) days from the state file.
        """
        state = State(state_fpath)
        return state.count('recent_priority_relay')

    @staticmethod
    def latest_bandwidth_from_results(results):
        return round(max([r.time for fp in results for r in results[fp]]))

    @staticmethod
    def earliest_bandwidth_from_results(results):
        return round(min([r.time for fp in results for r in results[fp]]))

    @property
    def keyvalue_unordered_tuple_ls(self):
        """Return list of KeyValue tuples that do not have specific order."""
        # sort the list to generate determinist headers
        keyvalue_tuple_ls = sorted([(k, v) for k, v in self.__dict__.items()
                                    if k in HEADER_UNORDERED_KEYS])
        return keyvalue_tuple_ls

    @property
    def keyvalue_tuple_ls(self):
        """Return list of all KeyValue tuples"""
        return [('version', self.version)] + self.keyvalue_unordered_tuple_ls

    @property
    def keyvalue_v1str_ls(self):
        """Return KeyValue list of strings following spec v1.X.X."""
        keyvalues = [self.timestamp] + [KEYVALUE_SEP_V1.join([k, v])
                                        for k, v in self.keyvalue_tuple_ls]
        return keyvalues

    @property
    def strv1(self):
        """Return header string following spec v1.X.X."""
        header_str = LINE_SEP.join(self.keyvalue_v1str_ls) + LINE_SEP + \
            LINE_TERMINATOR
        return header_str

    @property
    def keyvalue_v2_ls(self):
        """Return KeyValue list of strings following spec v2.X.X."""
        keyvalue = [self.timestamp] + [KEYVALUE_SEP_V2.join([k, v])
                                       for k, v in self.keyvalue_tuple_ls]
        return keyvalue

    @property
    def strv2(self):
        """Return header string following spec v2.X.X."""
        header_str = LINE_SEP.join(self.keyvalue_v2_ls) + LINE_SEP + \
            LINE_TERMINATOR
        return header_str

    @property
    def num_lines(self):
        return len(self.__str__().split(LINE_SEP))

    def add_stats(self, **kwargs):
        # Using kwargs because attributes might chage.
        [setattr(self, k, str(v)) for k, v in kwargs.items()
         if k in HEADER_KEYS_V1_2]

    def add_time_report_half_network(self):
        """Add to the header the time it took to measure half of the network.

        It is not the time the scanner actually takes on measuring all the
        network, but the ``number_eligible_relays`` that are reported in the
        bandwidth file and directory authorities will vote on.

        This is calculated for half of the network, so that failed or not
        reported relays do not affect too much.

        For instance, if there are 6500 relays in the network, half of the
        network would be 3250. And if there were 4000 eligible relays
        measured in an interval of 3 days, the time to measure half of the
        network would be 3 days * 3250 / 4000.

        Since the elapsed time is calculated from the earliest and the
        latest measurement and a relay might have more than 2 measurements,
        this would give an estimate on how long it would take to measure
        the network including all the valid measurements.

        Log also an estimated on how long it would take with the current
        number of relays included in the bandwidth file.
        """
        # NOTE: in future refactor do not convert attributes to str until
        # writing to the file, so that they do not need to be converted back
        # to do some calculations.
        elapsed_time = (
            (isostr_to_dt_obj(self.latest_bandwidth)
             - isostr_to_dt_obj(self.earliest_bandwidth))
            .total_seconds())

        # This attributes were added later and some tests that
        # do not initialize them would fail.
        eligible_relays = int(getattr(self, 'number_eligible_relays', 0))
        consensus_relays = int(getattr(self, 'number_consensus_relays', 0))
        if not(eligible_relays and consensus_relays):
            return

        half_network = consensus_relays / 2
        # Calculate the time it would take to measure half of the network
        if eligible_relays >= half_network:
            time_half_network = round(
                elapsed_time * half_network / eligible_relays
            )
            self.time_to_report_half_network = str(time_half_network)

        # In any case log an estimated on the time to measure all the network.
        estimated_time = round(
            elapsed_time * consensus_relays / eligible_relays
        )
        log.info("Estimated time to measure the network: %s hours.",
                 round(estimated_time / 60 / 60))

    def add_relays_excluded_counters(self, exclusion_dict):
        """
        Add the monitoring KeyValues to the header about the number of
        relays not included because they were not ``eligible``.
        """
        log.debug("Adding relays excluded counters.")
        for k, v in exclusion_dict.items():
            setattr(self, k, str(v))


class V3BWLine(object):
    """
    Create a Bandwidth List line following the spec version 1.X.X.

    :param str node_id: the relay fingerprint
    :param int bw: the bandwidth value that directory authorities will include
        in their votes.
    :param dict kwargs: extra headers.

    .. note:: tech-debt: move node_id and bw to kwargs and just ensure that
       the required values are in **kwargs
    """
    def __init__(self, node_id, bw, **kwargs):
        assert isinstance(node_id, str)
        assert node_id.startswith('$')
        self.node_id = node_id
        self.bw = bw
        # For now, we do not want to add ``bw_filt`` to the bandwidth file,
        # therefore it is set here but not added to ``BWLINE_KEYS_V1``.
        [setattr(self, k, v) for k, v in kwargs.items()
         if k in BWLINE_KEYS_V1 + ["bw_filt"]]

    def __str__(self):
        return self.bw_strv1

    @classmethod
    def from_results(cls, results, secs_recent=None, secs_away=None,
                     min_num=0, router_statuses_d=None):
        """Convert sbws results to relays' Bandwidth Lines

        ``bs`` stands for Bytes/seconds
        ``bw_mean`` means the bw is obtained from the mean of the all the
        downloads' bandwidth.
        Downloads' bandwidth are calculated as the amount of data received
        divided by the the time it took to received.
        bw = data (Bytes) / time (seconds)
        """
        # log.debug("Len success_results %s", len(success_results))
        node_id = '$' + results[0].fingerprint
        kwargs = dict()
        kwargs['nick'] = results[0].nickname
        if getattr(results[0], 'master_key_ed25519'):
            kwargs['master_key_ed25519'] = results[0].master_key_ed25519
        kwargs['time'] = cls.last_time_from_results(results)
        kwargs.update(cls.result_types_from_results(results))

        # If it has not the attribute, return list to be able to call len
        # If it has the attribute, but it is None, return also list
        kwargs['relay_in_recent_consensus_count'] = str(
            max([
                len(getattr(r, 'relay_in_recent_consensus', []) or [])
                for r in results
            ])
        )

        # Workaround for #34309.
        # Because of a bug, probably in relaylist, resultdump, relayprioritizer
        # or scanner, only the last timestamp is being stored in each result.
        # Temporally count the number of timestamps for all results.
        # If there is an unexpected failure and the result is not stored, this
        # number would be lower than what would be the correct one.
        # This should happen rarely or never.
        ts = set([])
        for r in results:
            if getattr(r, "relay_recent_priority_list", None):
                ts.update(r.relay_recent_priority_list)
        kwargs["relay_recent_priority_list_count"] = str(len(ts))

        # Same comment as the previous paragraph.
        ts = set()
        for r in results:
            if getattr(r, "relay_recent_measurement_attempt", None):
                ts.update(r.relay_recent_measurement_attempt)
        kwargs["relay_recent_measurement_attempt_count"] = str(len(ts))

        success_results = [r for r in results if isinstance(r, ResultSuccess)]

        # NOTE: The following 4 conditions exclude relays from the bandwidth
        # file when the measurements does not satisfy some rules, what makes
        # the relay non-`eligible`.
        # In BWLINE_KEYS_V1_4 it is explained what they mean.
        # In HEADER_RECENT_MEASUREMENTS_EXCLUDED_KEYS it is also
        # explained the what it means the strings returned.
        # They rules were introduced in #28061 and #27338
        # In #28565 we introduce the KeyValues to know why they're excluded.
        # In #28563 we report these relays, but make Tor ignore them.
        # This might confirm #28042.

        # If the relay is non-`eligible`:
        # Create a bandwidth line with the relay, but set ``vote=0`` so that
        # Tor versions with patch #29806 does not vote on the relay.
        # Set ``bw=1`` so that Tor versions without the patch,
        # will give the relay low bandwidth.
        # Include ``unmeasured=1`` in case Tor would vote on unmeasured relays
        # in future versions.
        # And return because there are not bandwidth values.
        # NOTE: the bandwidth values could still be obtained if:
        # 1. ``ResultError`` will store them
        # 2. assign ``results_recent = results`` when there is a ``exclusion
        # reason.
        # This could be done in a better way as part of a refactor #28684.

        kwargs['vote'] = 0
        kwargs['unmeasured'] = 1

        exclusion_reason = None

        number_excluded_error = len(results) - len(success_results)
        if number_excluded_error > 0:
            # then the number of error results is the number of results
            kwargs['relay_recent_measurements_excluded_error_count'] = \
                number_excluded_error
        if not success_results:
            exclusion_reason = 'recent_measurements_excluded_error_count'
            return (cls(node_id, 1, **kwargs), exclusion_reason)

        results_away = \
            cls.results_away_each_other(success_results, secs_away)
        number_excluded_near = len(success_results) - len(results_away)
        if number_excluded_near > 0:
            kwargs['relay_recent_measurements_excluded_near_count'] = \
                number_excluded_near
        if not results_away:
            exclusion_reason = \
                'recent_measurements_excluded_near_count'
            return (cls(node_id, 1, **kwargs), exclusion_reason)
        # log.debug("Results away from each other: %s",
        #           [unixts_to_isodt_str(r.time) for r in results_away])

        results_recent = cls.results_recent_than(results_away, secs_recent)
        number_excluded_old = len(results_away) - len(results_recent)
        if number_excluded_old > 0:
            kwargs['relay_recent_measurements_excluded_old_count'] = \
                number_excluded_old
        if not results_recent:
            exclusion_reason = \
                'recent_measurements_excluded_old_count'
            return (cls(node_id, 1, **kwargs), exclusion_reason)

        if not len(results_recent) >= min_num:
            kwargs['relay_recent_measurements_excluded_few_count'] = \
                len(results_recent)
            # log.debug('The number of results is less than %s', min_num)
            exclusion_reason = \
                'recent_measurements_excluded_few_count'
            return (cls(node_id, 1, **kwargs), exclusion_reason)

        # Use the last consensus if available, since the results' consensus
        # values come from the moment the measurement was made.
        if router_statuses_d and node_id in router_statuses_d:
            consensus_bandwidth = \
                router_statuses_d[node_id].bandwidth * 1000
            consensus_bandwidth_is_unmeasured = \
                router_statuses_d[node_id].is_unmeasured
        else:
            consensus_bandwidth = \
                cls.consensus_bandwidth_from_results(results_recent)
            consensus_bandwidth_is_unmeasured = \
                cls.consensus_bandwidth_is_unmeasured_from_results(
                    results_recent)
        # If there is no last observed bandwidth, there won't be mean either.
        desc_bw_obs_last = \
            cls.desc_bw_obs_last_from_results(results_recent)

        # Exclude also relays without consensus bandwidth nor observed
        # bandwidth, since they can't be scaled
        if (desc_bw_obs_last is None and consensus_bandwidth is None):
            # This reason is not counted, not added in the file, but it will
            # have vote = 0
            return(cls(node_id, 1), "no_consensus_no_observed_bw")

        # For any line not excluded, do not include vote and unmeasured
        # KeyValues
        del kwargs['vote']
        del kwargs['unmeasured']

        rtt = cls.rtt_from_results(results_recent)
        if rtt:
            kwargs['rtt'] = rtt
        bw = cls.bw_median_from_results(results_recent)
        # XXX: all the class functions could use the bw_measurements instead of
        # obtaining them each time or use a class Measurements.
        bw_measurements = scaling.bw_measurements_from_results(results_recent)
        kwargs['bw_mean'] = cls.bw_mean_from_results(results_recent)
        kwargs['bw_filt'] = scaling.bw_filt(bw_measurements)
        kwargs['bw_median'] = cls.bw_median_from_results(
            results_recent)
        kwargs['desc_bw_avg'] = \
            cls.desc_bw_avg_from_results(results_recent)
        kwargs['desc_bw_bur'] = \
            cls.desc_bw_bur_from_results(results_recent)
        kwargs['consensus_bandwidth'] = consensus_bandwidth
        kwargs['consensus_bandwidth_is_unmeasured'] = \
            consensus_bandwidth_is_unmeasured
        kwargs['desc_bw_obs_last'] = desc_bw_obs_last
        kwargs['desc_bw_obs_mean'] = \
            cls.desc_bw_obs_mean_from_results(results_recent)

        bwl = cls(node_id, bw, **kwargs)
        return bwl, None

    @classmethod
    def from_data(cls, data, fingerprint):
        assert fingerprint in data
        return cls.from_results(data[fingerprint])

    @classmethod
    def from_bw_line_v1(cls, line):
        assert isinstance(line, str)
        kwargs = dict([kv.split(KEYVALUE_SEP_V1)
                       for kv in line.split(BWLINE_KEYVALUES_SEP_V1)
                       if kv.split(KEYVALUE_SEP_V1)[0] in BWLINE_KEYS_V1])
        for k, v in kwargs.items():
            if k in BWLINE_INT_KEYS:
                kwargs[k] = int(v)
        node_id = kwargs['node_id']
        bw = kwargs['bw']
        del kwargs['node_id']
        del kwargs['bw']
        bw_line = cls(node_id, bw, **kwargs)
        return bw_line

    @staticmethod
    def results_away_each_other(results, secs_away=None):
        # log.debug("Checking whether results are away from each other in %s "
        #           "secs.", secs_away)
        if secs_away is None or len(results) < 2:
            return results
        for a, b in combinations(results, 2):
            if abs(a.time - b.time) > secs_away:
                return results
        # log.debug("Results are NOT away from each other in at least %ss: %s",
        #           secs_away, [unixts_to_isodt_str(r.time) for r in results])
        return []

    @staticmethod
    def results_recent_than(results, secs_recent=None):
        if secs_recent is None:
            return results
        results_recent = list(filter(
                            lambda x: (now_unixts() - x.time) < secs_recent,
                            results))
        # if not results_recent:
        #     log.debug("Results are NOT more recent than %ss: %s",
        #               secs_recent,
        #               [unixts_to_isodt_str(r.time) for r in results])
        return results_recent

    @staticmethod
    def bw_median_from_results(results):
        return max(round(median([dl['amount'] / dl['duration']
                                 for r in results for dl in r.downloads])), 1)

    @staticmethod
    def bw_mean_from_results(results):
        return max(round(mean([dl['amount'] / dl['duration']
                               for r in results for dl in r.downloads])), 1)

    @staticmethod
    def last_time_from_results(results):
        return unixts_to_isodt_str(round(max([r.time for r in results])))

    @staticmethod
    def rtt_from_results(results):
        # convert from miliseconds to seconds
        rtts = [(round(rtt * 1000)) for r in results for rtt in r.rtts]
        rtt = round(median(rtts)) if rtts else None
        return rtt

    @staticmethod
    def result_types_from_results(results):
        rt_dict = dict([(result_type_to_key(rt.value),
                         num_results_of_type(results, rt.value))
                        for rt in _ResultType])
        return rt_dict

    @staticmethod
    def desc_bw_avg_from_results(results):
        """Obtain the last descriptor bandwidth average from the results."""
        for r in reversed(results):
            if r.relay_average_bandwidth is not None:
                return r.relay_average_bandwidth
        log.warning("Descriptor average bandwidth is None.")
        return None

    @staticmethod
    def desc_bw_bur_from_results(results):
        """Obtain the last descriptor bandwidth burst from the results."""
        for r in reversed(results):
            if r.relay_burst_bandwidth is not None:
                return r.relay_burst_bandwidth
        log.warning("Descriptor burst bandwidth is None.")
        return None

    @staticmethod
    def consensus_bandwidth_from_results(results):
        """Obtain the last consensus bandwidth from the results."""
        for r in reversed(results):
            if r.consensus_bandwidth is not None:
                return r.consensus_bandwidth
        log.warning("Consensus bandwidth is None.")
        return None

    @staticmethod
    def consensus_bandwidth_is_unmeasured_from_results(results):
        """Obtain the last consensus unmeasured flag from the results."""
        for r in reversed(results):
            if r.consensus_bandwidth_is_unmeasured is not None:
                return r.consensus_bandwidth_is_unmeasured
            log.warning("Consensus bandwidth is unmeasured is None.")
        return None

    @staticmethod
    def desc_bw_obs_mean_from_results(results):
        desc_bw_obs_ls = []
        for r in results:
            if r.relay_observed_bandwidth is not None:
                desc_bw_obs_ls.append(r.relay_observed_bandwidth)
        if desc_bw_obs_ls:
            return round(mean(desc_bw_obs_ls))
        log.warning("Descriptor observed bandwidth is None.")
        return None

    @staticmethod
    def desc_bw_obs_last_from_results(results):
        # the last is at the end of the list
        for r in reversed(results):
            if r.relay_observed_bandwidth is not None:
                return r.relay_observed_bandwidth
        log.warning("Descriptor observed bandwidth is None.")
        return None

    @property
    def bw_keyvalue_tuple_ls(self):
        """Return list of KeyValue Bandwidth Line tuples."""
        # sort the list to generate determinist headers
        keyvalue_tuple_ls = sorted([(k, v) for k, v in self.__dict__.items()
                                    if k in BWLINE_KEYS_V1])
        return keyvalue_tuple_ls

    @property
    def bw_keyvalue_v1str_ls(self):
        """Return list of KeyValue Bandwidth Line strings following
        spec v1.X.X.
        """
        bw_keyvalue_str = [KEYVALUE_SEP_V1 .join([k, str(v)])
                           for k, v in self.bw_keyvalue_tuple_ls]
        return bw_keyvalue_str

    @property
    def bw_strv1(self):
        """Return Bandwidth Line string following spec v1.X.X."""
        bw_line_str = BWLINE_KEYVALUES_SEP_V1.join(
                        self.bw_keyvalue_v1str_ls) + LINE_SEP
        if len(bw_line_str) > BW_LINE_SIZE:
            # if this is the case, probably there are too many KeyValues,
            # or the limit needs to be changed in Tor
            log.warn("The bandwidth line %s is longer than %s",
                     len(bw_line_str), BW_LINE_SIZE)
        return bw_line_str


class V3BWFile(object):
    """
    Create a Bandwidth List file following spec version 1.X.X

    :param V3BWHeader v3bwheader: header
    :param list v3bwlines: V3BWLines
    """
    def __init__(self, v3bwheader, v3bwlines):
        self.header = v3bwheader
        self.bw_lines = v3bwlines

    def __str__(self):
        return str(self.header) + ''.join([str(bw_line) or ''
                                           for bw_line in self.bw_lines])

    @classmethod
    def from_results(cls, results, scanner_country=None,
                     destinations_countries=None, state_fpath='',
                     scale_constant=SBWS_SCALE_CONSTANT,
                     scaling_method=TORFLOW_SCALING,
                     torflow_obs=TORFLOW_OBS_LAST,
                     torflow_cap=TORFLOW_BW_MARGIN,
                     round_digs=PROP276_ROUND_DIG,
                     secs_recent=None, secs_away=None, min_num=0,
                     consensus_path=None, max_bw_diff_perc=MAX_BW_DIFF_PERC,
                     reverse=False):
        """Create V3BWFile class from sbws Results.

        :param dict results: see below
        :param str state_fpath: path to the state file
        :param int scaling_method:
            Scaling method to obtain the bandwidth
            Possible values: {None, SBWS_SCALING, TORFLOW_SCALING} = {0, 1, 2}
        :param int scale_constant: sbws scaling constant
        :param int torflow_obs: method to choose descriptor observed bandwidth
        :param bool reverse: whether to sort the bw lines descending or not

        Results are in the form::

            {'relay_fp1': [Result1, Result2, ...],
             'relay_fp2': [Result1, Result2, ...]}

        """
        log.info('Processing results to generate a bandwidth list file.')
        header = V3BWHeader.from_results(results, scanner_country,
                                         destinations_countries, state_fpath)
        bw_lines_raw = []
        bw_lines_excluded = []
        router_statuses_d = cls.read_router_statuses(consensus_path)
        # XXX: Use router_statuses_d to not parse again the file.
        number_consensus_relays = \
            cls.read_number_consensus_relays(consensus_path)
        state = State(state_fpath)

        # Create a dictionary with the number of relays excluded by any of the
        # of the filtering rules that makes relays non-`eligible`.
        # NOTE: In HEADER_RECENT_MEASUREMENTS_EXCLUDED_KEYS it is
        # explained what are the KeyValues.
        # See also the comments in `from_results`.
        exclusion_dict = dict(
            [(k, 0) for k in HEADER_RECENT_MEASUREMENTS_EXCLUDED_KEYS]
            )
        for fp, values in results.items():
            # log.debug("Relay fp %s", fp)
            line, reason = V3BWLine.from_results(values, secs_recent,
                                                 secs_away, min_num,
                                                 router_statuses_d)
            # If there is no reason it means the line will not be excluded.
            if not reason:
                bw_lines_raw.append(line)
            else:
                # Store the excluded lines to include them in the bandwidth
                # file.
                bw_lines_excluded.append(line)
                exclusion_dict[reason] = exclusion_dict.get(reason, 0) + 1
        # Add the headers with the number of excluded relays by reason
        header.add_relays_excluded_counters(exclusion_dict)

        if not bw_lines_raw:
            # It could be possible to scale the lines that were successful
            # even if excluded, but is not done here.
            log.info("After applying restrictions to the raw results, "
                     "there is not any. Scaling can not be applied.")
            # Update the header and log the progress.
            cls.update_progress(
                cls, 0, header, number_consensus_relays, state)
            # Set the lines that would be excluded anyway (`vote=0`) with
            # `under_min_report=1`
            cls.set_under_min_report(bw_lines_excluded)
            # Create the bandwidth file with the lines that would be excluded.
            return cls(header, bw_lines_excluded)
        if scaling_method == SBWS_SCALING:
            bw_lines = cls.bw_sbws_scale(bw_lines_raw, scale_constant)
            cls.warn_if_not_accurate_enough(bw_lines, scale_constant)
            # log.debug(bw_lines[-1])
        elif scaling_method == TORFLOW_SCALING:
            bw_lines = cls.bw_torflow_scale(
                bw_lines_raw, torflow_obs, torflow_cap, round_digs,
                router_statuses_d=router_statuses_d
            )
            # log.debug(bw_lines[-1])
            # Update the header and log the progress.
            min_perc = cls.update_progress(
                cls, len(bw_lines), header, number_consensus_relays, state
                )
            # If after scaling the number of lines is less than the percentage
            # of lines to report, set them with `under_min_report`.
            if not min_perc:
                cls.set_under_min_report(bw_lines)
        else:
            bw_lines = cls.bw_kb(bw_lines_raw)
            # log.debug(bw_lines[-1])
        # Not using the result for now, just warning
        cls.is_max_bw_diff_perc_reached(
            bw_lines, max_bw_diff_perc, router_statuses_d
        )
        header.add_time_report_half_network()
        f = cls(header, bw_lines + bw_lines_excluded)
        return f

    @classmethod
    def from_v1_fpath(cls, fpath):
        log.info('Parsing bandwidth file %s', fpath)
        with open(fpath) as fd:
            text = fd.read()
        all_lines = text.split(LINE_SEP)
        header, lines = V3BWHeader.from_lines_v1(all_lines)
        bw_lines = [V3BWLine.from_bw_line_v1(line) for line in lines]
        return cls(header, bw_lines)

    @classmethod
    def from_v100_fpath(cls, fpath):
        log.info('Parsing bandwidth file %s', fpath)
        with open(fpath) as fd:
            text = fd.read()
        all_lines = text.split(LINE_SEP)
        header, lines = V3BWHeader.from_lines_v100(all_lines)
        bw_lines = sorted([V3BWLine.from_bw_line_v1(l) for l in lines],
                          key=lambda l: l.bw)
        return cls(header, bw_lines)

    @staticmethod
    def set_under_min_report(bw_lines):
        """
        Mondify the Bandwidth Lines adding the KeyValue `under_min_report`,
        `vote`.
        """
        log.debug("Setting `under_min_report` to %s lines.", len(bw_lines))
        for l in bw_lines:
            l.under_min_report = 1
            l.vote = 0

    @staticmethod
    def bw_kb(bw_lines, reverse=False):
        bw_lines_scaled = copy.deepcopy(bw_lines)
        for l in bw_lines_scaled:
            l.bw = max(round(l.bw / 1000), 1)
        return sorted(bw_lines_scaled, key=lambda x: x.bw, reverse=reverse)

    @staticmethod
    def bw_sbws_scale(bw_lines, scale_constant=SBWS_SCALE_CONSTANT,
                      reverse=False):
        """Return a new V3BwLine list scaled using sbws method.

        :param list bw_lines:
            bw lines to scale, not self.bw_lines,
            since this method will be before self.bw_lines have been
            initialized.
        :param int scale_constant:
            the constant to multiply by the ratio and
            the bandwidth to obtain the new bandwidth
        :returns list: V3BwLine list
        """
        log.debug('Scaling bandwidth using sbws method.')
        m = median([l.bw for l in bw_lines])
        bw_lines_scaled = copy.deepcopy(bw_lines)
        for l in bw_lines_scaled:
            # min is to limit the bw to descriptor average-bandwidth
            # max to avoid bandwidth with 0 value
            l.bw = max(round(min(l.desc_bw_avg,
                                 l.bw * scale_constant / m)
                             / 1000), 1)
        return sorted(bw_lines_scaled, key=lambda x: x.bw, reverse=reverse)

    @staticmethod
    def warn_if_not_accurate_enough(bw_lines,
                                    scale_constant=SBWS_SCALE_CONSTANT):
        margin = 0.001
        accuracy_ratio = median([l.bw for l in bw_lines]) / scale_constant
        log.info('The generated lines are within {:.5}% of what they should '
                 'be'.format((1 - accuracy_ratio) * 100))
        if accuracy_ratio < 1 - margin or accuracy_ratio > 1 + margin:
            log.warning('There was %f%% error and only +/- %f%% is '
                        'allowed', (1 - accuracy_ratio) * 100, margin * 100)

    @staticmethod
    def is_max_bw_diff_perc_reached(bw_lines,
                                    max_bw_diff_perc=MAX_BW_DIFF_PERC,
                                    router_statuses_d=None):
        if router_statuses_d:
            sum_consensus_bw = sum(list(map(
                lambda x: x.bandwidth * 1000,
                router_statuses_d.values()
            )))
        else:
            sum_consensus_bw = sum([
                l.consensus_bandwidth for l in bw_lines
                if getattr(l, 'consensus_bandwidth', None)
            ])
        # Because the scaled bandwidth is in KB, but not the stored consensus
        # bandwidth, multiply by 1000.
        # Do not count the bandwidths for the relays that were excluded
        sum_bw = sum([l.bw for l in bw_lines if getattr(l, "vote", 1)]) * 1000
        # Percentage difference
        diff_perc = (
            abs(sum_consensus_bw - sum_bw)
            # Avoid ZeroDivisionError
            / (max(1, (sum_consensus_bw + sum_bw)) / 2)
            ) * 100
        log.info("The difference between the total consensus bandwidth (%s)"
                 "and the total measured bandwidth (%s) is %s%%.",
                 sum_consensus_bw, sum_bw, round(diff_perc))
        if diff_perc > MAX_BW_DIFF_PERC:
            log.warning("It is more than %s%%", max_bw_diff_perc)
            return True
        return False

    @staticmethod
    def bw_torflow_scale(bw_lines, desc_bw_obs_type=TORFLOW_OBS_MEAN,
                         cap=TORFLOW_BW_MARGIN,
                         num_round_dig=PROP276_ROUND_DIG, reverse=False,
                         router_statuses_d=None):
        """
        Obtain final bandwidth measurements applying Torflow's scaling
        method.

        See details in :ref:`torflow_aggr`.
        """
        log.info("Calculating relays' bandwidth using Torflow method.")
        bw_lines_tf = copy.deepcopy(bw_lines)
        # mean (Torflow's strm_avg)
        mu = mean([l.bw_mean for l in bw_lines])
        # filtered mean (Torflow's filt_avg)
        muf = mean([l.bw_filt for l in bw_lines])
        log.debug('mu %s', mu)
        log.debug('muf %s', muf)

        # Torflow's ``tot_net_bw``, sum of the scaled bandwidth for the relays
        # that are in the last consensus
        sum_bw = 0
        for l in bw_lines_tf:
            # First, obtain the observed bandwidth, later check what to do
            # if it is 0 or None.
            if desc_bw_obs_type == TORFLOW_OBS_LAST:
                # In case there's no last, use the mean, because it is possible
                # that it went down for a few days, but no more than 5,
                # otherwise the mean will be 1
                desc_bw_obs = l.desc_bw_obs_last or l.desc_bw_obs_mean
            # Assume that if it is not TORFLOW_OBS_LAST, then it is
            # TORFLOW_OBS_MEAN
            else:
                desc_bw_obs = l.desc_bw_obs_mean

            # Excerpt from bandwidth-file-spec.txt section 2.3
            # A relay's MaxAdvertisedBandwidth limits the bandwidth-avg in its
            # descriptor.
            # Therefore generators MUST limit a relay's measured bandwidth to
            # its descriptor's bandwidth-avg.
            # Generators SHOULD NOT limit measured bandwidths based on
            # descriptors' bandwidth-observed, because that penalises new
            # relays.
            # See https://trac.torproject.org/projects/tor/ticket/8494
            # If the observed bandwidth is None, it is not possible to
            # calculate the minimum with the other descriptors.
            # Only in this case, take the consensus bandwidth.
            # In the case that descriptor average or burst are None,
            # ignore them since it must be a bug in ``Resultdump``, already
            # logged in x_bw/bandwidth_x_from_results, but scale.
            if desc_bw_obs is not None:
                if l.desc_bw_bur is not None:
                    if l.desc_bw_avg is not None:
                        desc_bw = min(
                            desc_bw_obs, l.desc_bw_bur, l.desc_bw_avg
                        )
                    else:
                        desc_bw = min(desc_bw_obs, l.desc_bw_bur)
                else:
                    if l.desc_bw_avg is not None:
                        desc_bw = min(desc_bw_obs, l.desc_bw_avg)
                    else:
                        desc_bw = desc_bw_obs
                # If the relay is unmeasured and consensus bandwidth is None or
                # 0, use the descriptor bandwidth
                if l.consensus_bandwidth_is_unmeasured \
                        or not l.consensus_bandwidth:
                    min_bandwidth = desc_bw_obs
                else:
                    min_bandwidth = min(desc_bw, l.consensus_bandwidth)
            elif l.consensus_bandwidth is not None:
                min_bandwidth = l.consensus_bandwidth
            else:
                log.warning("Can not scale relay missing descriptor and"
                            " consensus bandwidth.")
                continue

            # Torflow's scaling
            ratio_stream = l.bw_mean / mu
            ratio_stream_filtered = l.bw_filt / muf
            ratio = max(ratio_stream, ratio_stream_filtered)

            # Assign it to an attribute, so it's not lost before capping and
            # rounding
            l.bw = ratio * min_bandwidth

            # If the consensus is available, sum only the bw for the relays
            # that are in the consensus
            if router_statuses_d:
                if l.node_id.replace("$", "") in router_statuses_d:
                    sum_bw += l.bw
            # Otherwise sum all bw, for compatibility with tests that were not
            # using the consensus file.
            else:
                sum_bw += l.bw

        # Cap maximum bw, only possible when the ``sum_bw`` is calculated.
        # Torflow's clipping
        hlimit = sum_bw * cap
        log.debug("sum_bw: %s, hlimit: %s", sum_bw, hlimit)
        for l in bw_lines_tf:
            bw_scaled = min(hlimit, l.bw)
            # round and convert to KB
            l.bw = kb_round_x_sig_dig(bw_scaled, digits=num_round_dig)
        return sorted(bw_lines_tf, key=lambda x: x.bw, reverse=reverse)

    @staticmethod
    def read_number_consensus_relays(consensus_path):
        """Read the number of relays in the Network from the cached consensus
        file."""
        num = None
        try:
            num = len(list(parse_file(consensus_path)))
        except (FileNotFoundError, AttributeError):
            log.info("It is not possible to obtain statistics about the "
                     "percentage of measured relays because the cached "
                     "consensus file is not found.")
        log.debug("Number of relays in the network %s", num)
        return num

    @staticmethod
    def read_router_statuses(consensus_path):
        """Read the router statuses from the cached consensus file."""
        router_statuses_d = None
        try:
            router_statuses_d = dict([
                (r.fingerprint, r)
                for r in parse_file(consensus_path)
            ])
        except (FileNotFoundError, AttributeError):
            log.warning("It is not possible to obtain the last consensus"
                        "cached file %s.", consensus_path)
        return router_statuses_d

    @staticmethod
    def measured_progress_stats(num_bw_lines, number_consensus_relays,
                                min_perc_reached_before):
        """ Statistics about measurements progress,
        to be included in the header.

        :param list bw_lines: the bw_lines after scaling and applying filters.
        :param str consensus_path: the path to the cached consensus file.
        :param str state_fpath: the path to the state file
        :returns dict, bool: Statistics about the progress made with
            measurements and whether the percentage of measured relays has been
            reached.

        """
        # cached-consensus should be updated every time that scanner get the
        # network status or descriptors?
        # It will not be updated to the last consensus, but the list of
        # measured relays is not either.
        assert isinstance(number_consensus_relays, int)
        assert isinstance(num_bw_lines, int)
        statsd = {}
        statsd['number_eligible_relays'] = num_bw_lines
        statsd['number_consensus_relays'] = number_consensus_relays
        statsd['minimum_number_eligible_relays'] = round(
            statsd['number_consensus_relays'] * MIN_REPORT / 100)
        statsd['percent_eligible_relays'] = round(
            num_bw_lines * 100 / statsd['number_consensus_relays'])
        statsd['minimum_percent_eligible_relays'] = MIN_REPORT
        if statsd['number_eligible_relays'] < \
                statsd['minimum_number_eligible_relays']:
            # if min percent was was reached before, warn
            # otherwise, debug
            if min_perc_reached_before is not None:
                log.warning('The percentage of the measured relays is less '
                            'than the %s%% of the relays in the network (%s).',
                            MIN_REPORT, statsd['number_consensus_relays'])
            else:
                log.info('The percentage of the measured relays is less '
                         'than the %s%% of the relays in the network (%s).',
                         MIN_REPORT, statsd['number_consensus_relays'])
            return statsd, False
        return statsd, True

    @property
    def is_min_perc(self):
        if getattr(self.header, 'number_eligible_relays', 0) \
                < getattr(self.header, 'minimum_number_eligible_relays', 0):
            return False
        return True

    @property
    def sum_bw(self):
        return sum([l.bw for l in self.bw_lines if hasattr(l, 'bw')])

    @property
    def num(self):
        return len(self.bw_lines)

    @property
    def mean_bw(self):
        return mean([l.bw for l in self.bw_lines if hasattr(l, 'bw')])

    @property
    def median_bw(self):
        return median([l.bw for l in self.bw_lines if hasattr(l, 'bw')])

    @property
    def max_bw(self):
        return max([l.bw for l in self.bw_lines if hasattr(l, 'bw')])

    @property
    def min_bw(self):
        return min([l.bw for l in self.bw_lines if hasattr(l, 'bw')])

    @property
    def info_stats(self):
        if not self.bw_lines:
            return
        [log.info(': '.join([attr, str(getattr(self, attr))])) for attr in
         ['sum_bw', 'mean_bw', 'median_bw', 'num',
          'max_bw', 'min_bw']]

    def update_progress(self, num_bw_lines, header, number_consensus_relays,
                        state):
        """
        Returns True if the minimim percent of Bandwidth Lines was reached
        and False otherwise.
        Update the header with the progress.
        """
        min_perc_reached_before = state.get('min_perc_reached')
        if number_consensus_relays is not None:
            statsd, success = self.measured_progress_stats(
                num_bw_lines, number_consensus_relays, min_perc_reached_before)
            # add statistics about progress always
            header.add_stats(**statsd)
            if not success:
                # From sbws 1.1.0 the lines are reported (#29853) even if they
                # are less than the minimum percent.
                state['min_perc_reached'] = None
                return False
            else:
                state['min_perc_reached'] = now_isodt_str()
                return True

    def bw_line_for_node_id(self, node_id):
        """Returns the bandwidth line for a given node fingerprint.

        Used to combine data when plotting.
        """
        bwl = [l for l in self.bw_lines if l.node_id == node_id]
        if bwl:
            return bwl[0]
        return None

    def to_plt(self, attrs=['bw'], sorted_by=None):
        """Return bandwidth data in a format useful for matplotlib.

        Used from external tool to plot.
        """
        x = [i for i in range(0, self.num)]
        ys = [[getattr(l, k) for l in self.bw_lines] for k in attrs]
        return x, ys, attrs

    def write(self, output):
        if output == '/dev/stdout':
            log.info("Writing to stdout is not supported.")
            return
        log.info('Writing v3bw file to %s', output)
        # To avoid inconsistent reads, the bandwidth data is written to an
        # archive path, then atomically symlinked to 'latest.v3bw'
        out_dir = os.path.dirname(output)
        out_link = os.path.join(out_dir, 'latest.v3bw')
        out_link_tmp = out_link + '.tmp'
        with DirectoryLock(out_dir):
            with open(output, 'wt') as fd:
                fd.write(str(self.header))
                for line in self.bw_lines:
                    fd.write(str(line))
            output_basename = os.path.basename(output)
            # To atomically symlink a file, we need to create a temporary link,
            # then rename it to the final link name. (POSIX guarantees that
            # rename is atomic.)
            log.debug('Creating symlink {} -> {}.'
                      .format(out_link_tmp, output_basename))
            os.symlink(output_basename, out_link_tmp)
            log.debug('Renaming symlink {} -> {} to {} -> {}.'
                      .format(out_link_tmp, output_basename,
                              out_link, output_basename))
            os.rename(out_link_tmp, out_link)
