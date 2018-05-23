# -*- coding: utf-8 -*-
"""Classes and functions that create the bandwidth measurements document
(v3bw) used by bandwidth authorities."""

import logging

from sbws import __version__
from sbws.globals import SPEC_VERSION
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


def read_started_ts(conf):
    """Read ISO formated timestamp which represents the date and time
    when scanner started.

    :param ConfigParser conf: configuration
    :returns: str, ISO formated timestamp
    """
    filepath = conf['paths']['started_filepath']
    try:
        with FileLock(filepath):
            with open(filepath, 'r') as fd:
                generator_started = fd.read()
    except FileNotFoundError as e:
        log.warn('File %s not found.%s', filepath, e)
        return ''
    return generator_started


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
        log.debug('keyvalue_tuple_ls %s', keyvalue_tuple_ls)
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
        log.debug('keyvalue %s', keyvalues)
        return keyvalues

    @property
    def strv110(self):
        """Return header string following spec v1.1.0."""
        header_str = LINE_SEP.join(self.keyvalue_v110str_ls) + LINE_SEP + \
            LINE_TERMINATOR
        log.debug('header_str %s', header_str)
        return header_str

    @property
    def keyvalue_v200_ls(self):
        """Return KeyValue list of strings following spec v2.0.0."""
        keyvalue = [self.timestamp] + [KEYVALUE_SEP_V200.join([k, v])
                                       for k, v in self.keyvalue_tuple_ls]
        log.debug('keyvalue %s', keyvalue)
        return keyvalue

    @property
    def strv200(self):
        """Return header string following spec v2.0.0."""
        header_str = LINE_SEP.join(self.keyvalue_v200_ls) + LINE_SEP + \
            LINE_TERMINATOR
        log.debug('header_str %s', header_str)
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
        # not checking order
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
