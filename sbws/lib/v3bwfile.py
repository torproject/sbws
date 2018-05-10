# -*- coding: utf-8 -*-
"""Classes and functions that create the bandwidth measurements document
(v3bw) used by bandwidth authorities."""

import time
import logging
from sbws import __version__
from sbws.globals import SPEC_VERSION

log = logging.getLogger(__name__)


class V3BwHeader(object):
    """
    Create a bandwidth measurements (V3bw) header
    following bandwidth measurements document spec version 1.1.0.

    :param int timestamp: timestamp in Unix Epoch seconds when the document
                          is created
    :param str version: the spec version
    :param str software: the name of the software that generates this
    :param str software_version: the version of the software
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
            self.scanner_started = kwargs['generator_started']


    def __str__(self):
        """Return header string following spec version 1.1.0."""
        # sorting the list to generate determinist headers
        kv_headers = ' '.join(sorted(['='.join([k, str(v)])
                                      for k, v in self.__dict__.items()]))
        header = '\n'.join([str(self.timestamp), kv_headers, ''])
        log.debug('header %s', header)
        return header
