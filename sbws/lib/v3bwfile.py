# -*- coding: utf-8 -*-
"""Classes and functions that create the bandwidth measurements document
(v3bw) used by bandwidth authorities."""

import logging
from statistics import median

from sbws import __version__
from sbws.globals import SPEC_VERSION, BW_LINE_SIZE
from sbws.lib.resultdump import ResultSuccess, _ResultType
from sbws.util.filelock import FileLock
from sbws.util.timestamp import now_isodt_str, unixts_to_isodt_str

log = logging.getLogger(__name__)

LINE_SEP = '\n'
KEYVALUE_SEP_V110 = '='
KEYVALUE_SEP_V200 = ' '
# List of the extra KeyValues accepted by the class
EXTRA_ARG_KEYVALUES = ['software', 'software_version', 'file_created',
                       'earliest_bandwidth', 'generator_started']
# List of all unordered KeyValues currently being used to generate the file
UNORDERED_KEYVALUES = EXTRA_ARG_KEYVALUES + ['latest_bandwidth']
# List of all the KeyValues currently being used to generate the file
ALL_KEYVALUES = ['version'] + UNORDERED_KEYVALUES
TERMINATOR = '===='
# Num header lines in v1.1.0 using all the KeyValues
NUM_LINES_HEADER_V110 = len(ALL_KEYVALUES) + 2
LINE_TERMINATOR = TERMINATOR + LINE_SEP

# KeyValue separator in Bandwidth Lines
BW_KEYVALUE_SEP_V110 = ' '
BW_EXTRA_ARG_KEYVALUES = ['master_key_ed25519', 'nick', 'rtt', 'time',
                          'success', 'error_stream', 'error_circ',
                          'error_misc']
BW_KEYVALUES_INT = ['bw', 'rtt', 'success', 'error_stream',
                    'error_circ', 'error_misc']
BW_KEYVALUES = ['node_id', 'bw'] + BW_EXTRA_ARG_KEYVALUES


def total_bw(bw_lines):
    return sum([l.bw for l in bw_lines])


def avg_bw(bw_lines):
    assert len(bw_lines) > 0
    return total_bw(bw_lines) / len(bw_lines)


def scale_lines(bw_lines, scale_constant):
    avg = avg_bw(bw_lines)
    for line in bw_lines:
        line.bw = round(line.bw / avg * scale_constant)
    warn_if_not_accurate_enough(bw_lines, scale_constant)
    return bw_lines


def warn_if_not_accurate_enough(bw_lines, scale_constant):
    margin = 0.001
    accuracy_ratio = avg_bw(bw_lines) / scale_constant
    log.info('The generated lines are within {:.5}% of what they should '
             'be'.format((1 - accuracy_ratio) * 100))
    if accuracy_ratio < 1 - margin or accuracy_ratio > 1 + margin:
        log.warning('There was %f%% error and only +/- %f%% is '
                    'allowed', (1 - accuracy_ratio) * 100, margin * 100)


def read_started_ts(conf):
    """Read ISO formated timestamp which represents the date and time
    when scanner started.

    :param ConfigParser conf: configuration
    :returns: str, ISO formated timestamp
    """
    try:
        filepath = conf['paths']['started_filepath']
    except TypeError as e:
        return ''
    try:
        with FileLock(filepath):
            with open(filepath, 'r') as fd:
                generator_started = fd.read()
    except FileNotFoundError as e:
        log.warn('File %s not found.%s', filepath, e)
        return ''
    return generator_started


def num_results_of_type(results, type_str):
    return len([r for r in results if r.type == type_str])


# Better way to use enums?
def result_type_to_key(type_str):
    return type_str.replace('-', '_')


class V3BwHeader(object):
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

    def __str__(self):
        if self.version == '1.1.0':
            return self.strv110
        return self.strv200

    @classmethod
    def from_lines_v110(cls, lines):
        """
        :param list lines: list of lines to parse
        :returns: tuple of V3BwHeader object and non-header lines
        """
        assert isinstance(lines, list)
        try:
            index_terminator = lines.index(TERMINATOR)
        except ValueError as e:
            # is not a bw file or is v100
            log.warn('Terminator is not in lines')
            return None
        ts = lines[0]
        kwargs = dict([l.split(KEYVALUE_SEP_V110)
                       for l in lines[:index_terminator]
                       if l.split(KEYVALUE_SEP_V110)[0] in ALL_KEYVALUES])
        h = cls(ts, **kwargs)
        return h, lines[index_terminator + 1:]

    @classmethod
    def from_text_v110(self, text):
        """
        :param str text: text to parse
        :returns: tuple of V3BwHeader object and non-header lines
        """
        assert isinstance(text, str)
        return self.from_lines_v110(text.split(LINE_SEP))

    @property
    def num_lines(self):
        return len(self.__str__().split(LINE_SEP))

    @staticmethod
    def generator_started_from_file(conf):
        return read_started_ts(conf)

    @staticmethod
    def latest_bandwidth_from_results(results):
        return round(max([r.time for fp in results for r in results[fp]]))

    @staticmethod
    def earliest_bandwidth_from_results(results):
        return round(min([r.time for fp in results for r in results[fp]]))

    @classmethod
    def from_results(cls, conf, results):
        kwargs = dict()
        latest_bandwidth = cls.latest_bandwidth_from_results(results)
        earliest_bandwidth = cls.latest_bandwidth_from_results(results)
        generator_started = cls.generator_started_from_file(conf)
        timestamp = str(latest_bandwidth)
        kwargs['latest_bandwidth'] = unixts_to_isodt_str(latest_bandwidth)
        kwargs['earliest_bandwidth'] = unixts_to_isodt_str(earliest_bandwidth)
        kwargs['generator_started'] = generator_started
        h = cls(timestamp, **kwargs)
        return h


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
        self.node_id = node_id
        self.bw = bw
        [setattr(self, k, v) for k, v in kwargs.items()
         if k in BW_EXTRA_ARG_KEYVALUES]

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

    def __str__(self):
        return self.bw_strv110

    @classmethod
    def from_bw_line_v110(cls, line):
        assert isinstance(line, str)
        kwargs = dict([kv.split(KEYVALUE_SEP_V110)
                       for kv in line.split(BW_KEYVALUE_SEP_V110)
                       if kv.split(KEYVALUE_SEP_V110)[0] in BW_KEYVALUES])
        for k, v in kwargs.items():
            if k in BW_KEYVALUES_INT:
                kwargs[k] = int(v)
        bw_line = cls(**kwargs)
        return bw_line

    @staticmethod
    def bw_from_results(results):
        median_bw = median([dl['amount'] / dl['duration']
                            for r in results for dl in r.downloads])
        # convert to KB and ensure it's at least 1
        bw_kb = max(round(median_bw / 1024), 1)
        return bw_kb

    @staticmethod
    def last_time_from_results(results):
        return unixts_to_isodt_str(round(max([r.time for r in results])))

    @staticmethod
    def rtt_from_results(results):
        # convert from miliseconds to seconds
        rtts = [(round(rtt * 1000)) for r in results for rtt in r.rtts]
        rtt = round(median(rtts))
        return rtt

    @staticmethod
    def result_types_from_results(results):
        rt_dict = dict([(result_type_to_key(rt.value),
                         num_results_of_type(results, rt.value))
                        for rt in _ResultType])
        return rt_dict

    @classmethod
    def from_results(cls, results):
        success_results = [r for r in results if isinstance(r, ResultSuccess)]
        log.debug('len(success_results) %s', len(success_results))
        node_id = results[0].fingerprint
        bw = cls.bw_from_results(success_results)
        kwargs = dict()
        kwargs['nick'] = results[0].nickname
        if getattr(results[0], 'master_key_ed25519'):
            kwargs['master_key_ed25519'] = results[0].master_key_ed25519
        kwargs['rtt'] = cls.rtt_from_results(success_results)
        kwargs['time'] = cls.last_time_from_results(results)
        kwargs.update(cls.result_types_from_results(results))
        bwl = cls(node_id, bw, **kwargs)
        return bwl

    @classmethod
    def from_data(cls, data, fingerprint):
        assert fingerprint in data
        return cls.from_results(data[fingerprint])


class V3BwFile(object):
    """
    Create a Bandwidth List file following spec version 1.1.0

    :param V3BWHeader v3bwheader: header
    :param list v3bwlines: V3BWLines
    """
    def __init__(self, v3bwheader, v3bwlines):
        self.header = v3bwheader
        self.bw_lines = v3bwlines

    def __str__(self):
        return str(self.header) + ''.join([str(bw_line)
                                           for bw_line in self.bw_lines])

    @property
    def total_bw(self):
        return total_bw(self.bw_lines)

    @property
    def num_lines(self):
        return len(self.bw_lines)

    @property
    def avg_bw(self):
        return self.total_bw / self.num_lines

    @classmethod
    def from_results(cls, conf, output, results):
        bw_lines = [V3BWLine.from_results(results[fp]) for fp in results]
        bw_lines = sorted(bw_lines, key=lambda d: d.bw, reverse=True)
        header = V3BwHeader.from_results(conf, results)
        f = cls(header, bw_lines)
        f.write(output)
        return f

    @classmethod
    def from_arg_results(cls, args, conf, results):
        bw_lines = [V3BWLine.from_results(results[fp]) for fp in results]
        bw_lines = sorted(bw_lines, key=lambda d: d.bw, reverse=True)
        if args.scale:
            bw_lines = scale_lines(bw_lines, args.scale_constant)
        header = V3BwHeader.from_results(conf, results)
        f = cls(header, bw_lines)
        output = args.output or conf['paths']['v3bw_fname']
        f.write(output)
        return f

    def write(self, output):
        log.info('Writing v3bw file to %s', output)
        with open(output, 'wt') as fd:
            fd.write(str(self.header))
            for line in self.bw_lines:
                fd.write(str(line))
