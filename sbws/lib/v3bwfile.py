# -*- coding: utf-8 -*-
"""Classes and functions that create the bandwidth measurements document
(v3bw) used by bandwidth authorities."""

import time
import logging
from sbws import __version__
from sbws.globals import SPEC_VERSION

log = logging.getLogger(__name__)

LINE_SEP = '\n'
K_SEP_V110 = '='
KV_SEP_V110 = '\n'
K_SEP_V200 = ' '
KV_SEP_V200 = ' '
ORDERED_KV = ['version', 'software', 'software_version']
ORDERED_K = ['timestamp', 'version', 'software', 'software_version']
ALLOWED_K = ORDERED_KV + ['earliest_bandwidth', 'generator_started']
TERMINATOR = '===='
LINE_TERMINATOR = TERMINATOR + LINE_SEP


class V3BwHeader(object):
    """
    Create a bandwidth measurements (V3bw) header
    following bandwidth measurements document spec version 1.1.0.

    :param int timestamp: timestamp in Unix Epoch seconds when the document
                          is created
    :param str version: the spec version
    :param str software: the name of the software that generates this
    :param str software_version: the version of the software
    :param dict kwargs: extra headers. Currently supported:
        - earliest_bandwidth: str, ISO timestamp when the first bandwidth was
          obtained
        - generator_started: str, ISO timestamp when the generator started
    """
    def __init__(self, timestamp=None, version=SPEC_VERSION, software='sbws',
                 software_version=__version__, **kwargs):
        self.timestamp = timestamp or int(time.time())
        self.version = version
        self.software = software
        self.software_version = software_version
        if kwargs.get('earliest_bandwidth'):
            self.earliest_bandwidth = kwargs['earliest_bandwidth']
        if kwargs.get('generator_started'):
            self.generator_started = kwargs['generator_started']

    @property
    def kv_ordered_ls(self):
        """Return list of headers KeyValue tuples for the KeyValues
        that have specific order.
        """
        kv_ls = [(k, str(getattr(self, k, ''))) for k in ORDERED_KV]
        log.debug('kv_ls %s', kv_ls)
        return kv_ls

    @property
    def k_extra_ls(self):
        """Return list of headers Keywords that do not have specific order."""
        k_extra = list(set(self.__dict__.keys()).difference(ORDERED_K)
                       .intersection(ALLOWED_K))
        log.debug('k_extra %s', k_extra)
        return k_extra

    @property
    def kv_extra_ls(self):
        """Return list of headers KeyValue tuples for the KeyValues
        that do not have specific order.
        """
        # sorting the list to generate determinist headers
        kv_extra = sorted([(k, str(getattr(self, k)))
                          for k in self.k_extra_ls])
        log.debug('kv_extra %s', kv_extra)
        return kv_extra

    @property
    def kv_ls(self):
        return self.kv_ordered_ls + self.kv_extra_ls

    @property
    def kv_v110_ls(self):
        """Return header kv list of strings following spec v1.1.0."""
        kv = [str(self.timestamp)] + [K_SEP_V110.join([k, v])
                                      for k, v in self.kv_ls]
        log.debug('kv %s', kv)
        return kv

    def strv110(self):
        """Return header string following spec v1.1.0."""
        header_str = LINE_SEP.join(self.kv_v110_ls) + LINE_SEP + \
            LINE_TERMINATOR
        log.debug('header_str %s', header_str)
        return header_str

    @property
    def kv_v200_ls(self):
        """Return header kv following spec v2.0.0."""
        kv = [str(self.timestamp)] + [K_SEP_V200.join([k, v])
                                      for k, v in self.kv_ls]
        log.debug('kv %s', kv)
        return kv

    @property
    def strv200(self):
        """Return header string following spec v2.0.0."""
        header_str = LINE_SEP.join(self.kv_v200_ls) + LINE_SEP + \
            LINE_TERMINATOR
        log.debug('header_str %s', header_str)
        return header_str

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
        ts = int(lines[0])
        # not checking order
        kwargs = dict([l.split(K_SEP_V110)
                       for l in lines[:index_terminator]
                       if l.split(K_SEP_V110)[0] in ALLOWED_K])
        h = cls(ts, **kwargs)
        return h, lines[index_terminator + 1:]

    @classmethod
    def from_text_v110(self, text):
        """
        :param list lines: text to parse
        :returns: tuple of V3BwHeader object and non-header lines
        """
        assert isinstance(text, str)
        return self.from_lines_v110(text.split(LINE_SEP))

    def __str__(self):
        if self.version == '1.1.0':
            return self.strv110()
        return self.strv200
