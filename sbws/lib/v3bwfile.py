# -*- coding: utf-8 -*-
"""Classes and functions that create the bandwidth measurements document
(v3bw) used by bandwidth authorities."""

import copy
import logging
import os
from itertools import combinations
from statistics import median, mean
from stem.descriptor import parse_file

from sbws import __version__
from sbws.globals import (SPEC_VERSION, BW_LINE_SIZE, SBWS_SCALE_CONSTANT,
                          TORFLOW_SCALING, SBWS_SCALING, TORFLOW_BW_MARGIN,
                          TORFLOW_OBS_LAST, TORFLOW_OBS_MEAN,
                          TORFLOW_ROUND_DIG, MIN_REPORT)
from sbws.lib.resultdump import ResultSuccess, _ResultType
from sbws.util.filelock import DirectoryLock
from sbws.util.timestamp import (now_isodt_str, unixts_to_isodt_str,
                                 now_unixts)
from sbws.util.state import State

log = logging.getLogger(__name__)

LINE_SEP = '\n'
KEYVALUE_SEP_V110 = '='
KEYVALUE_SEP_V200 = ' '
# List of the extra KeyValues accepted by the class
EXTRA_ARG_KEYVALUES = ['software', 'software_version', 'file_created',
                       'earliest_bandwidth', 'generator_started']
STATS_KEYVALUES = ['number_eligible_relays', 'minimum_number_eligible_relays',
                   'number_consensus_relays', 'percent_eligible_relays',
                   'minimum_percent_eligible_relays']
KEYVALUES_INT = STATS_KEYVALUES
# List of all unordered KeyValues currently being used to generate the file
UNORDERED_KEYVALUES = EXTRA_ARG_KEYVALUES + STATS_KEYVALUES + \
                      ['latest_bandwidth']
# List of all the KeyValues currently being used to generate the file
ALL_KEYVALUES = ['version'] + UNORDERED_KEYVALUES
TERMINATOR = '===='
# Num header lines in v1.1.0 using all the KeyValues
NUM_LINES_HEADER_V110 = len(ALL_KEYVALUES) + 2
LINE_TERMINATOR = TERMINATOR + LINE_SEP

# KeyValue separator in Bandwidth Lines
BW_KEYVALUE_SEP_V110 = ' '
# not inclding in the files the extra bws for now
BW_KEYVALUES_BASIC = ['node_id', 'bw']
BW_KEYVALUES_FILE = BW_KEYVALUES_BASIC + \
                    ['master_key_ed25519', 'nick', 'rtt', 'time',
                     'success', 'error_stream', 'error_circ', 'error_misc']
BW_KEYVALUES_EXTRA_BWS = ['bw_median', 'bw_mean', 'desc_bw_avg',
                          'desc_bw_obs_last', 'desc_bw_obs_mean']
BW_KEYVALUES_EXTRA = BW_KEYVALUES_FILE + BW_KEYVALUES_EXTRA_BWS
BW_KEYVALUES_INT = ['bw', 'rtt', 'success', 'error_stream',
                    'error_circ', 'error_misc'] + BW_KEYVALUES_EXTRA_BWS
BW_KEYVALUES = BW_KEYVALUES_BASIC + BW_KEYVALUES_EXTRA


def kb_round_x_sig_dig(bw_bs, digits=TORFLOW_ROUND_DIG):
    """Convert bw to KB and round to x most significat digits."""
    bw_kb = bw_bs / 1000
    return max(int(round(bw_kb, -digits)), 1)


def num_results_of_type(results, type_str):
    return len([r for r in results if r.type == type_str])


# Better way to use enums?
def result_type_to_key(type_str):
    return type_str.replace('-', '_')


class V3BWHeader(object):
    """
    Create a bandwidth measurements (V3bw) header
    following bandwidth measurements document spec version 1.1.0.

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
         if k in EXTRA_ARG_KEYVALUES]

    def __str__(self):
        if self.version == '1.1.0':
            return self.strv110
        return self.strv200

    @classmethod
    def from_results(cls, results, state_fpath=''):
        kwargs = dict()
        latest_bandwidth = cls.latest_bandwidth_from_results(results)
        earliest_bandwidth = cls.earliest_bandwidth_from_results(results)
        generator_started = cls.generator_started_from_file(state_fpath)
        timestamp = str(latest_bandwidth)
        kwargs['latest_bandwidth'] = unixts_to_isodt_str(latest_bandwidth)
        kwargs['earliest_bandwidth'] = unixts_to_isodt_str(earliest_bandwidth)
        if generator_started is not None:
            kwargs['generator_started'] = generator_started
        h = cls(timestamp, **kwargs)
        return h

    @classmethod
    def from_lines_v110(cls, lines):
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
        kwargs = dict([l.split(KEYVALUE_SEP_V110)
                       for l in lines[:index_terminator]
                       if l.split(KEYVALUE_SEP_V110)[0] in ALL_KEYVALUES])
        h = cls(ts, **kwargs)
        # last line is new line
        return h, lines[index_terminator + 1:-1]

    @classmethod
    def from_text_v110(self, text):
        """
        :param str text: text to parse
        :returns: tuple of V3BWHeader object and non-header lines
        """
        assert isinstance(text, str)
        return self.from_lines_v110(text.split(LINE_SEP))

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
            return state['scanner_started']
        else:
            return None

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
                                    if k in UNORDERED_KEYVALUES])
        return keyvalue_tuple_ls

    @property
    def keyvalue_tuple_ls(self):
        """Return list of all KeyValue tuples"""
        return [('version', self.version)] + self.keyvalue_unordered_tuple_ls

    @property
    def keyvalue_v110str_ls(self):
        """Return KeyValue list of strings following spec v1.1.0."""
        keyvalues = [self.timestamp] + [KEYVALUE_SEP_V110.join([k, v])
                                        for k, v in self.keyvalue_tuple_ls]
        return keyvalues

    @property
    def strv110(self):
        """Return header string following spec v1.1.0."""
        header_str = LINE_SEP.join(self.keyvalue_v110str_ls) + LINE_SEP + \
            LINE_TERMINATOR
        return header_str

    @property
    def keyvalue_v200_ls(self):
        """Return KeyValue list of strings following spec v2.0.0."""
        keyvalue = [self.timestamp] + [KEYVALUE_SEP_V200.join([k, v])
                                       for k, v in self.keyvalue_tuple_ls]
        return keyvalue

    @property
    def strv200(self):
        """Return header string following spec v2.0.0."""
        header_str = LINE_SEP.join(self.keyvalue_v200_ls) + LINE_SEP + \
            LINE_TERMINATOR
        return header_str

    @property
    def num_lines(self):
        return len(self.__str__().split(LINE_SEP))

    def add_stats(self, **kwargs):
        # Using kwargs because attributes might chage.
        [setattr(self, k, str(v)) for k, v in kwargs.items()
         if k in STATS_KEYVALUES]


class V3BWLine(object):
    """
    Create a Bandwidth List line following the spec version 1.1.0.

    :param str node_id:
    :param int bw:
    :param dict kwargs: extra headers. Currently supported:

        - nickname, str
        - master_key_ed25519, str
        - rtt, int
        - time, str
        - sucess, int
        - error_stream, int
        - error_circ, int
        - error_misc, int
    """
    def __init__(self, node_id, bw, **kwargs):
        assert isinstance(node_id, str)
        assert isinstance(bw, int)
        assert node_id.startswith('$')
        self.node_id = node_id
        self.bw = bw
        [setattr(self, k, v) for k, v in kwargs.items()
         if k in BW_KEYVALUES_EXTRA]

    def __str__(self):
        return self.bw_strv110

    @classmethod
    def from_results(cls, results, secs_recent=None, secs_away=None,
                     min_num=0):
        """Convert sbws results to relays' Bandwidth Lines

        ``bs`` stands for Bytes/seconds
        ``bw_mean`` means the bw is obtained from the mean of the all the
        downloads' bandwidth.
        Downloads' bandwidth are calculated as the amount of data received
        divided by the the time it took to received.
        bw = data (Bytes) / time (seconds)
        """
        success_results = [r for r in results if isinstance(r, ResultSuccess)]
        # log.debug("Len success_results %s", len(success_results))
        node_id = '$' + results[0].fingerprint
        kwargs = dict()
        kwargs['nick'] = results[0].nickname
        if getattr(results[0], 'master_key_ed25519'):
            kwargs['master_key_ed25519'] = results[0].master_key_ed25519
        kwargs['time'] = cls.last_time_from_results(results)
        kwargs.update(cls.result_types_from_results(results))
        # useful args for scaling
        if success_results:
            if not len(success_results) >= min_num:
                # log.debug('The number of results is les than %s', min_num)
                return None
            results_away = \
                cls.results_away_each_other(success_results, secs_away)
            if not results_away:
                return None
            # log.debug("Results away from each other: %s",
            #           [unixts_to_isodt_str(r.time) for r in results_away])
            results_recent = cls.results_recent_than(results_away, secs_recent)
            if not results_recent:
                return None
            kwargs['desc_bw_avg'] = \
                results_recent[-1].relay_average_bandwidth
            rtt = cls.rtt_from_results(results_recent)
            if rtt:
                kwargs['rtt'] = rtt
            bw = cls.bw_median_from_results(results_recent)
            kwargs['bw_mean'] = cls.bw_mean_from_results(results_recent)
            kwargs['bw_median'] = cls.bw_median_from_results(
                results_recent)
            kwargs['desc_bw_obs_last'] = \
                cls.desc_bw_obs_last_from_results(results_recent)
            kwargs['desc_bw_obs_mean'] = \
                cls.desc_bw_obs_mean_from_results(results_recent)
            bwl = cls(node_id, bw, **kwargs)
            return bwl
        return None

    @classmethod
    def from_data(cls, data, fingerprint):
        assert fingerprint in data
        return cls.from_results(data[fingerprint])

    @classmethod
    def from_bw_line_v110(cls, line):
        assert isinstance(line, str)
        kwargs = dict([kv.split(KEYVALUE_SEP_V110)
                       for kv in line.split(BW_KEYVALUE_SEP_V110)
                       if kv.split(KEYVALUE_SEP_V110)[0] in BW_KEYVALUES])
        for k, v in kwargs.items():
            if k in BW_KEYVALUES_INT:
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
        return None

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
    def desc_bw_obs_mean_from_results(results):
        desc_bw_obs_ls = []
        for r in results:
            if r.relay_observed_bandwidth is not None:
                desc_bw_obs_ls.append(r.relay_observed_bandwidth)
        if desc_bw_obs_ls:
            return max(round(mean(desc_bw_obs_ls)), 1)
        return None

    @staticmethod
    def desc_bw_obs_last_from_results(results):
        # the last is at the end of the list
        for r in reversed(results):
            if r.relay_observed_bandwidth is not None:
                return r.relay_observed_bandwidth
        return None

    @property
    def bw_keyvalue_tuple_ls(self):
        """Return list of KeyValue Bandwidth Line tuples."""
        # sort the list to generate determinist headers
        keyvalue_tuple_ls = sorted([(k, v) for k, v in self.__dict__.items()
                                    if k in BW_KEYVALUES])
        return keyvalue_tuple_ls

    @property
    def bw_keyvalue_v110str_ls(self):
        """Return list of KeyValue Bandwidth Line strings following
        spec v1.1.0.
        """
        bw_keyvalue_str = [KEYVALUE_SEP_V110 .join([k, str(v)])
                           for k, v in self.bw_keyvalue_tuple_ls]
        return bw_keyvalue_str

    @property
    def bw_strv110(self):
        """Return Bandwidth Line string following spec v1.1.0."""
        bw_line_str = BW_KEYVALUE_SEP_V110.join(
                        self.bw_keyvalue_v110str_ls) + LINE_SEP
        if len(bw_line_str) > BW_LINE_SIZE:
            # if this is the case, probably there are too many KeyValues,
            # or the limit needs to be changed in Tor
            log.warn("The bandwidth line %s is longer than %s",
                     len(bw_line_str), BW_LINE_SIZE)
        return bw_line_str


class V3BWFile(object):
    """
    Create a Bandwidth List file following spec version 1.1.0

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
    def from_results(cls, results, state_fpath='',
                     scale_constant=SBWS_SCALE_CONSTANT,
                     scaling_method=None, torflow_obs=TORFLOW_OBS_LAST,
                     torflow_cap=TORFLOW_BW_MARGIN,
                     torflow_round_digs=TORFLOW_ROUND_DIG,
                     secs_recent=None, secs_away=None, min_num=0,
                     consensus_path=None, reverse=False):
        """Create V3BWFile class from sbws Results.

        :param dict results: see below
        :param str state_fpath: path to the state file
        :param int scaling_method:
            Scaling method to obtain the bandwidth
            Posiable values: {NONE, SBWS_SCALING, TORFLOW_SCALING} = {0, 1, 2}
        :param int scale_constant: sbws scaling constant
        :param int torflow_obs: method to choose descriptor observed bandwidth
        :param bool reverse: whether to sort the bw lines descending or not

        Results are in the form::

            {'relay_fp1': [Result1, Result2, ...],
             'relay_fp2': [Result1, Result2, ...]}

        """
        # TODO: change scaling_method to TORFLOW_SCALING before getting this
        # in production
        log.info('Processing results to generate a bandwidth list file.')
        header = V3BWHeader.from_results(results, state_fpath)
        bw_lines_raw = []
        number_consensus_relays = cls.read_number_consensus_relays(
            consensus_path)
        state = State(state_fpath)
        for fp, values in results.items():
            # log.debug("Relay fp %s", fp)
            line = V3BWLine.from_results(values, secs_recent, secs_away,
                                         min_num)
            if line is not None:
                bw_lines_raw.append(line)
        if not bw_lines_raw:
            log.info("After applying restrictions to the raw results, "
                     "there is not any. Scaling can not be applied.")
            cls.update_progress(
                cls, bw_lines_raw, header, number_consensus_relays, state)
            return cls(header, [])
        if scaling_method == SBWS_SCALING:
            bw_lines = cls.bw_sbws_scale(bw_lines_raw, scale_constant)
            cls.warn_if_not_accurate_enough(bw_lines, scale_constant)
            # log.debug(bw_lines[-1])
        elif scaling_method == TORFLOW_SCALING:
            bw_lines = cls.bw_torflow_scale(bw_lines_raw, torflow_obs,
                                            torflow_cap, torflow_round_digs)
            # log.debug(bw_lines[-1])
            cls.update_progress(
                cls, bw_lines, header, number_consensus_relays, state)
        else:
            bw_lines = cls.bw_kb(bw_lines_raw)
            # log.debug(bw_lines[-1])
        f = cls(header, bw_lines)
        return f

    @classmethod
    def from_v110_fpath(cls, fpath):
        log.info('Parsing bandwidth file %s', fpath)
        with open(fpath) as fd:
            text = fd.read()
        all_lines = text.split(LINE_SEP)
        header, lines = V3BWHeader.from_lines_v110(all_lines)
        bw_lines = [V3BWLine.from_bw_line_v110(line) for line in lines]
        return cls(header, bw_lines)

    @classmethod
    def from_v100_fpath(cls, fpath):
        log.info('Parsing bandwidth file %s', fpath)
        with open(fpath) as fd:
            text = fd.read()
        all_lines = text.split(LINE_SEP)
        header, lines = V3BWHeader.from_lines_v100(all_lines)
        bw_lines = sorted([V3BWLine.from_bw_line_v110(l) for l in lines],
                          key=lambda l: l.bw)
        return cls(header, bw_lines)

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
        # If a relay has MaxAdvertisedBandwidth set, they may be capable of
        # some large amount of bandwidth but prefer if they didn't receive it.
        # We also could have managed to measure them faster than their
        # {,Relay}BandwidthRate somehow.
        #
        # See https://github.com/pastly/simple-bw-scanner/issues/155 and
        # https://trac.torproject.org/projects/tor/ticket/8494
        #
        # Note how this isn't some measured-by-us average of bandwidth. It's
        # the first value on the 'bandwidth' line in the relay's server
        # descriptor.
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
    def bw_torflow_scale(bw_lines, desc_bw_obs_type=TORFLOW_OBS_MEAN,
                         cap=TORFLOW_BW_MARGIN,
                         num_round_dig=TORFLOW_ROUND_DIG, reverse=False):
        """
        Obtain final bandwidth measurements applying Torflow's scaling
        method.

        From Torflow's README.spec.txt (section 2.2)::

            In this way, the resulting network status consensus bandwidth values  # NOQA
            are effectively re-weighted proportional to how much faster the node  # NOQA
            was as compared to the rest of the network.

        The variables and steps used in Torflow:

        **strm_bw**::

            The strm_bw field is the average (mean) of all the streams for the relay  # NOQA
            identified by the fingerprint field.
            strm_bw = sum(bw stream x)/|n stream|

        **filt_bw**::

            The filt_bw field is computed similarly, but only the streams equal to  # NOQA
            or greater than the strm_bw are counted in order to filter very slow  # NOQA
            streams due to slow node pairings.

        **filt_sbw and strm_sbw**::

            for rs in RouterStats.query.filter(stats_clause).\
                  options(eagerload_all('router.streams.circuit.routers')).all():  # NOQA
              tot_sbw = 0
              sbw_cnt = 0
              for s in rs.router.streams:
                if isinstance(s, ClosedStream):
                  skip = False
                  #for br in badrouters:
                  #  if br != rs:
                  #    if br.router in s.circuit.routers:
                  #      skip = True
                  if not skip:
                    # Throw out outliers < mean
                    # (too much variance for stddev to filter much)
                    if rs.strm_closed == 1 or s.bandwidth() >= rs.sbw:
                      tot_sbw += s.bandwidth()
                      sbw_cnt += 1

            if sbw_cnt: rs.filt_sbw = tot_sbw/sbw_cnt
            else: rs.filt_sbw = None

        **filt_avg, and strm_avg**::

            Once we have determined the most recent measurements for each node, we  # NOQA
            compute an average of the filt_bw fields over all nodes we have measured.  # NOQA

        ::

            filt_avg = sum(map(lambda n: n.filt_bw, nodes.itervalues()))/float(len(nodes))  # NOQA
            strm_avg = sum(map(lambda n: n.strm_bw, nodes.itervalues()))/float(len(nodes))  # NOQA

        **true_filt_avg and true_strm_avg**::

            for cl in ["Guard+Exit", "Guard", "Exit", "Middle"]:
                true_filt_avg[cl] = filt_avg
                true_strm_avg[cl] = strm_avg

        In the non-pid case, all types of nodes get the same avg

        **n.fbw_ratio and n.fsw_ratio**::

            for n in nodes.itervalues():
                n.fbw_ratio = n.filt_bw/true_filt_avg[n.node_class()]
                n.sbw_ratio = n.strm_bw/true_strm_avg[n.node_class()]

        **n.ratio**::

            These averages are used to produce ratios for each node by dividing the  # NOQA
            measured value for that node by the network average.

        ::

            # Choose the larger between sbw and fbw
              if n.sbw_ratio > n.fbw_ratio:
                n.ratio = n.sbw_ratio
              else:
                n.ratio = n.fbw_ratio

        **desc_bw**:

        It is the ``observed bandwidth`` in the descriptor, NOT the ``average
        bandwidth``::

            return Router(ns.idhex, ns.nickname, bw_observed, dead, exitpolicy,
            ns.flags, ip, version, os, uptime, published, contact, rate_limited,  # NOQA
            ns.orhash, ns.bandwidth, extra_info_digest, ns.unmeasured)
            self.desc_bw = max(bw,1) # Avoid div by 0

        **new_bw**::

            These ratios are then multiplied by the most recent observed descriptor  # NOQA
            bandwidth we have available for each node, to produce a new value for  # NOQA
            the network status consensus process.

        ::

            n.new_bw = n.desc_bw*n.ratio

        The descriptor observed bandwidth is multiplied by the ratio.

        **Limit the bandwidth to a maximum**::

            NODE_CAP = 0.05

        ::

            if n.new_bw > tot_net_bw*NODE_CAP:
              plog("INFO", "Clipping extremely fast "+n.node_class()+" node "+n.idhex+"="+n.nick+  # NOQA
                   " at "+str(100*NODE_CAP)+"% of network capacity ("+
                   str(n.new_bw)+"->"+str(int(tot_net_bw*NODE_CAP))+") "+
                   " pid_error="+str(n.pid_error)+
                   " pid_error_sum="+str(n.pid_error_sum))
              n.new_bw = int(tot_net_bw*NODE_CAP)

        However, tot_net_bw does not seems to be updated when not using pid.
        This clipping would make faster relays to all have the same value.

        All of that can be expressed as:

        .. math::

            bwn_i &=
                max\\left(
                    \\frac{bw_i}{\\mu},
                    \\frac{bwf_i}{\\mu_{bwf}}
                    \\right)
                \\times bwobs_i

        .. math::

             bwn_i &=
                max\\left(
                    \\frac{bw_i}{\\mu},
                    min \\left(
                        bw_i,
                        bw_i \\times \\mu
                        \\right)
                            \\times
                            \\frac{bw_i}{\\sum_{i=1}^{n}
                            min \\left(bw_i,
                                bw_i \\times \\mu
                            \\right)}
                    \\right)
                \\times bwobs_i \\

             &=
                max\\left(
                    \\frac{bw_i}{\\frac{\\sum_{i=1}^{n}bw_i}{n}},
                    min \\left(
                        bw_i,
                        bw_i \\times \\frac{\\sum_{i=1}^{n}bw_i}{n}
                        \\right)
                            \\times
                            \\frac{bw_i}{\\sum_{i=1}^{n}
                            min \\left(bw_i,
                                bw_i \\times \\frac{\\sum_{i=1}^{n}bw_i}{n}
                            \\right)}
                    \\right)
                \\times bwobs_i

        """
        log.info("Calculating relays' bandwidth using Torflow method.")
        bw_lines_tf = copy.deepcopy(bw_lines)
        # mean (Torflow's strm_avg)
        mu = mean([l.bw_mean for l in bw_lines])
        # filtered mean (Torflow's filt_avg)
        muf = mean([min(l.bw_mean, mu) for l in bw_lines])
        # bw sum (Torflow's tot_net_bw or tot_sbw)
        sum_bw = sum([l.bw_mean for l in bw_lines])
        # Torflow's clipping
        hlimit = sum_bw * TORFLOW_BW_MARGIN
        log.debug('sum %s', sum_bw)
        log.debug('mu %s', mu)
        log.debug('muf %s', muf)
        log.debug('hlimit %s', hlimit)
        for l in bw_lines_tf:
            if desc_bw_obs_type == TORFLOW_OBS_LAST:
                desc_bw_obs = l.desc_bw_obs_last
            elif desc_bw_obs_type == TORFLOW_OBS_MEAN:
                desc_bw_obs = l.desc_bw_obs_mean
            # just applying the formula above:
            bw_new = kb_round_x_sig_dig(
                max(
                    l.bw_mean / mu,  # ratio
                    min(l.bw_mean, mu) / muf  # ratio filtered
                    ) * desc_bw_obs, \
                digits=num_round_dig)  # convert to KB
            # Cap maximum bw
            if cap is not None:
                bw_new = min(hlimit, bw_new)
            # remove decimals and avoid 0
            l.bw = max(round(bw_new), 1)
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
    def measured_progress_stats(bw_lines, number_consensus_relays,
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
        assert isinstance(bw_lines, list)
        statsd = {}
        statsd['number_eligible_relays'] = len(bw_lines)
        statsd['number_consensus_relays'] = number_consensus_relays
        statsd['minimum_number_eligible_relays'] = round(
            statsd['number_consensus_relays'] * MIN_REPORT / 100)
        statsd['percent_eligible_relays'] = round(
            len(bw_lines) * 100 / statsd['number_consensus_relays'])
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
        return sum([l.bw for l in self.bw_lines])

    @property
    def num(self):
        return len(self.bw_lines)

    @property
    def mean_bw(self):
        return mean([l.bw for l in self.bw_lines])

    @property
    def median_bw(self):
        return median([l.bw for l in self.bw_lines])

    @property
    def max_bw(self):
        return max([l.bw for l in self.bw_lines])

    @property
    def min_bw(self):
        return min([l.bw for l in self.bw_lines])

    @property
    def info_stats(self):
        if not self.bw_lines:
            return
        [log.info(': '.join([attr, str(getattr(self, attr))])) for attr in
         ['sum_bw', 'mean_bw', 'median_bw', 'num',
          'max_bw', 'min_bw']]

    def update_progress(self, bw_lines, header, number_consensus_relays,
                        state):
        min_perc_reached_before = state.get('min_perc_reached')
        if number_consensus_relays is not None:
            statsd, success = self.measured_progress_stats(
                bw_lines, number_consensus_relays, min_perc_reached_before)
            # add statistics about progress only when there are not enough
            # measured relays. Should some stats be added always?
            if not success:
                header.add_stats(**statsd)
                bw_lines = []
                state['min_perc_reached'] = None
            else:
                state['min_perc_reached'] = now_isodt_str()
        return bw_lines

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
